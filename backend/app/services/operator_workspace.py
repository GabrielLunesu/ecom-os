"""A07 services for operator tasks, knowledge, attention, and launch intents."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.time import utcnow
from app.models.brand import Brand
from app.models.operator_workspace import (
    AttentionSnapshot,
    KnowledgeDocument,
    KnowledgeDocumentChunk,
    KnowledgeDocumentVersion,
    OperatorTask,
    OperatorTaskComment,
    OperatorTaskEntityLink,
)
from app.schemas.operator_workspace import (
    AskHermesLaunchIntent,
    AttentionInput,
    AttentionItemRead,
    AttentionSnapshotCreate,
    AttentionSnapshotRead,
    BriefTaskInputRead,
    BriefTaskRef,
    EntityLinkIn,
    EntityLinkRead,
    KnowledgeDocumentRead,
    KnowledgeDocumentSearchResult,
    KnowledgeDocumentUpsert,
    OperatorTaskCommentCreate,
    OperatorTaskCommentRead,
    OperatorTaskCreate,
    OperatorTaskRead,
    OperatorTaskUpdate,
    ToolCatalogEntry,
    ToolCatalogManifest,
)

ROLE_ACCESS_LABELS: dict[str, frozenset[str]] = {
    "owner": frozenset({"public", "operations", "cs", "finance", "founder_private"}),
    "admin": frozenset({"public", "operations", "cs", "finance"}),
    "operator": frozenset({"public", "operations", "cs"}),
    "cs_lead": frozenset({"public", "operations", "cs"}),
    "cs_rep": frozenset({"public", "cs"}),
    "finance": frozenset({"public", "operations", "finance"}),
    "viewer": frozenset({"public", "operations"}),
}

SEVERITY_SCORE = {
    "critical": 1000,
    "high": 800,
    "medium": 500,
    "low": 250,
    "info": 100,
}
SOURCE_STATUS_SCORE = {
    "unavailable": 150,
    "stale": 100,
    "partial": 50,
    "available": 0,
}
COVERAGE_SCORE = {
    "verified": 0,
    "imported": 30,
    "observed": 60,
    "unknown": 120,
}

TOOL_CATALOG_VERSION = "a07.local.v0"


@dataclass(frozen=True)
class DocumentSearchPage:
    """Accessible-only document search page."""

    results: list[KnowledgeDocumentSearchResult]
    accessible_count: int


@dataclass(frozen=True)
class ExtractedDocument:
    text: str
    status: str


class _VisibleTextHTMLParser(HTMLParser):
    """Extract visible text while ignoring active/metadata HTML content."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._ignored_stack: list[str] = []
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "template", "noscript"}:
            self._ignored_stack.append(tag.lower())

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if self._ignored_stack and self._ignored_stack[-1] == lowered:
            self._ignored_stack.pop()

    def handle_data(self, data: str) -> None:
        if not self._ignored_stack and data.strip():
            self._parts.append(data)

    def text(self) -> str:
        return _collapse_whitespace(" ".join(self._parts))


def access_labels_for_role(role: str) -> frozenset[str]:
    """Return document labels visible to a role."""
    return ROLE_ACCESS_LABELS.get(role, frozenset({"public"}))


def operator_workspace_tool_manifest() -> ToolCatalogManifest:
    """Return A07's local tool manifest for A03 catalog registration."""
    tools = [
        _tool(
            name="ecom.task.list",
            description="List access-filtered operator tasks for the current Ecom-OS brand.",
            input_schema={
                "type": "object",
                "properties": {
                    "include_done": {"type": "boolean", "default": True},
                    "role": {"type": "string", "default": "operator"},
                },
                "additionalProperties": False,
            },
            output_schema={"type": "array", "items": {"$ref": "OperatorTaskRead"}},
            read_or_write="read",
            risk_class="low",
        ),
        _tool(
            name="ecom.task.get",
            description="Read one access-filtered operator task by id.",
            input_schema={
                "type": "object",
                "required": ["task_id"],
                "properties": {
                    "task_id": {"type": "string", "format": "uuid"},
                    "role": {"type": "string", "default": "operator"},
                },
                "additionalProperties": False,
            },
            output_schema={"$ref": "OperatorTaskRead"},
            read_or_write="read",
            risk_class="low",
        ),
        _tool(
            name="ecom.task.create",
            description="Create an internal Ecom-OS operator task with explicit provenance.",
            input_schema={"$ref": "OperatorTaskCreate"},
            output_schema={"$ref": "OperatorTaskRead"},
            read_or_write="write",
            risk_class="internal_state",
            required_ecom_permissions=["task:create"],
            supports_idempotency=False,
            reconciliation_strategy="ecom_database_transaction",
            minimum_trace_coverage="verified",
        ),
        _tool(
            name="ecom.document.search",
            description="Search current knowledge documents after access filtering.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "default": ""},
                    "role": {"type": "string", "default": "operator"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
                },
                "additionalProperties": False,
            },
            output_schema={"$ref": "KnowledgeSearchResponse"},
            read_or_write="read",
            risk_class="low",
        ),
        _tool(
            name="ecom.document.get",
            description="Read one accessible knowledge document version by document id.",
            input_schema={
                "type": "object",
                "required": ["document_id"],
                "properties": {
                    "document_id": {"type": "string", "format": "uuid"},
                    "version_id": {"type": "string", "format": "uuid"},
                    "role": {"type": "string", "default": "operator"},
                },
                "additionalProperties": False,
            },
            output_schema={"$ref": "KnowledgeDocumentRead"},
            read_or_write="read",
            risk_class="medium",
            required_ecom_permissions=["knowledge:read"],
        ),
        _tool(
            name="ecom.operator.ask_hermes_intent.create",
            description="Build a safe contextual Hermes launch intent from entity refs.",
            input_schema={"$ref": "AskHermesLaunchRequest"},
            output_schema={"$ref": "AskHermesLaunchIntent"},
            read_or_write="read",
            risk_class="low",
        ),
    ]
    dumped = [
        tool.model_dump(mode="json", exclude_none=True, exclude={"schema_hash"}) for tool in tools
    ]
    digest = hashlib.sha256(
        json.dumps(
            {"version": TOOL_CATALOG_VERSION, "tools": dumped},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return ToolCatalogManifest(
        version=TOOL_CATALOG_VERSION,
        schema_hash=f"sha256:{digest}",
        tools=tools,
    )


def _tool(
    *,
    name: str,
    description: str,
    input_schema: dict[str, Any],
    output_schema: dict[str, Any],
    read_or_write: str,
    risk_class: str,
    required_ecom_permissions: list[str] | None = None,
    required_connection_types: list[str] | None = None,
    supports_simulation: bool = False,
    supports_idempotency: bool = True,
    reconciliation_strategy: str = "not_applicable_read_only",
    sensitive_fields: list[str] | None = None,
    minimum_trace_coverage: str = "verified",
) -> ToolCatalogEntry:
    return ToolCatalogEntry(
        name=name,
        version=TOOL_CATALOG_VERSION,
        description=description,
        input_schema=input_schema,
        output_schema=output_schema,
        read_or_write=read_or_write,  # type: ignore[arg-type]
        risk_class=risk_class,
        required_ecom_permissions=required_ecom_permissions or ["operator_workspace:read"],
        required_connection_types=required_connection_types or [],
        store_scope_rule="brand_scoped_explicit_store_for_writes",
        supports_simulation=supports_simulation,
        supports_idempotency=supports_idempotency,
        reconciliation_strategy=reconciliation_strategy,
        sensitive_fields=sensitive_fields or [],
        minimum_trace_coverage=minimum_trace_coverage,  # type: ignore[arg-type]
    )


async def create_operator_task(
    session: AsyncSession,
    brand: Brand,
    payload: OperatorTaskCreate,
) -> OperatorTaskRead:
    """Create an operator task, enforcing agent provenance at schema boundary."""
    task = OperatorTask(
        brand_id=brand.id,
        title=payload.title,
        description=payload.description,
        status=payload.status,
        priority=payload.priority,
        due_at=payload.due_at,
        assignee_type=payload.assignee_type,
        assignee_id=payload.assignee_id,
        assignee_label=payload.assignee_label,
        provenance=payload.provenance,
        created_by_actor_type=payload.created_by_actor_type,
        created_by_actor_id=payload.created_by_actor_id,
        source_trace_id=payload.source_trace_id,
        source_run_id=payload.source_run_id,
        source_evidence_ref=payload.source_evidence_ref,
        access_label=payload.access_label,
        daily_brief_include=payload.daily_brief_include,
    )
    session.add(task)
    await session.flush()
    for link in payload.entity_links:
        session.add(
            OperatorTaskEntityLink(
                task_id=task.id,
                entity_type=link.entity_type,
                entity_id=link.entity_id,
                label=link.label,
                trace_id=link.trace_id,
            )
        )
    await session.commit()
    return await get_operator_task(session, task.id)  # type: ignore[return-value]


async def update_operator_task(
    session: AsyncSession,
    task_id: UUID,
    payload: OperatorTaskUpdate,
    *,
    allowed_access_labels: set[str] | frozenset[str] | None = None,
) -> OperatorTaskRead | None:
    task = await session.get(OperatorTask, task_id)
    if task is None:
        return None
    if allowed_access_labels is not None and task.access_label not in allowed_access_labels:
        return None
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(task, key, value)
    task.updated_at = utcnow()
    session.add(task)
    await session.commit()
    return await get_operator_task(
        session,
        task_id,
        allowed_access_labels=allowed_access_labels,
    )


async def add_operator_task_comment(
    session: AsyncSession,
    task_id: UUID,
    payload: OperatorTaskCommentCreate,
    *,
    allowed_access_labels: set[str] | frozenset[str] | None = None,
) -> OperatorTaskCommentRead | None:
    task = await session.get(OperatorTask, task_id)
    if task is None:
        return None
    if allowed_access_labels is not None and task.access_label not in allowed_access_labels:
        return None
    comment = OperatorTaskComment(
        task_id=task_id,
        actor_type=payload.actor_type,
        actor_id=payload.actor_id,
        body=payload.body,
        trace_id=payload.trace_id,
    )
    session.add(comment)
    await session.commit()
    await session.refresh(comment)
    return _comment_read(comment)


async def list_operator_tasks(
    session: AsyncSession,
    brand_id: UUID,
    *,
    include_done: bool = True,
    allowed_access_labels: set[str] | frozenset[str] | None = None,
) -> list[OperatorTaskRead]:
    statement = select(OperatorTask).where(col(OperatorTask.brand_id) == brand_id)
    if allowed_access_labels is not None:
        statement = statement.where(col(OperatorTask.access_label).in_(allowed_access_labels))
    if not include_done:
        statement = statement.where(col(OperatorTask.status) != "done")
    statement = statement.order_by(
        col(OperatorTask.due_at).is_(None),
        col(OperatorTask.due_at).asc(),
        col(OperatorTask.created_at).asc(),
    )
    tasks = list((await session.exec(statement)).all())
    return [await _task_read(session, task) for task in tasks]


async def get_operator_task(
    session: AsyncSession,
    task_id: UUID,
    *,
    allowed_access_labels: set[str] | frozenset[str] | None = None,
) -> OperatorTaskRead | None:
    task = await session.get(OperatorTask, task_id)
    if task is None:
        return None
    if allowed_access_labels is not None and task.access_label not in allowed_access_labels:
        return None
    return await _task_read(session, task)


async def brief_task_inputs(
    session: AsyncSession,
    brand_id: UUID,
    *,
    allowed_access_labels: set[str] | frozenset[str],
    role: str,
    horizon_end: datetime,
    limit: int = 20,
) -> BriefTaskInputRead:
    """Return due/overdue task refs for A08, filtered before counts or titles."""
    generated_at = utcnow()
    statement = (
        select(OperatorTask)
        .where(col(OperatorTask.brand_id) == brand_id)
        .where(col(OperatorTask.access_label).in_(allowed_access_labels))
        .where(col(OperatorTask.daily_brief_include).is_(True))
        .where(col(OperatorTask.status).not_in(["done", "cancelled"]))
        .where(col(OperatorTask.due_at).is_not(None))
        .where(col(OperatorTask.due_at) <= horizon_end)
        .order_by(
            col(OperatorTask.due_at).asc(),
            col(OperatorTask.priority).desc(),
            col(OperatorTask.created_at).asc(),
        )
        .limit(limit)
    )
    tasks = list((await session.exec(statement)).all())
    refs = [await _brief_task_ref(session, task, generated_at=generated_at) for task in tasks]
    return BriefTaskInputRead(
        role=role,
        generated_at=generated_at,
        horizon_end=horizon_end,
        accessible_count=len(refs),
        tasks=refs,
    )


async def upsert_document_version(
    session: AsyncSession,
    brand: Brand,
    payload: KnowledgeDocumentUpsert,
) -> KnowledgeDocumentRead:
    """Create a document or append an immutable version and searchable chunk."""
    statement = (
        select(KnowledgeDocument)
        .where(col(KnowledgeDocument.brand_id) == brand.id)
        .where(col(KnowledgeDocument.logical_path) == payload.logical_path)
    )
    document = (await session.exec(statement)).first()
    if document is None:
        document = KnowledgeDocument(
            brand_id=brand.id,
            logical_path=payload.logical_path,
            title=payload.title,
            document_type=payload.document_type,
            source=payload.source,
            owner_actor_type=payload.owner_actor_type,
            owner_actor_id=payload.owner_actor_id,
            access_label=payload.access_label,
            trust_label=payload.trust_label,
            effective_date=payload.effective_date,
            ingestion_status="pending",
        )
        session.add(document)
        await session.flush()
        version_number = 1
        supersedes = None
    else:
        version_number = await _next_document_version_number(session, document.id)
        supersedes = document.current_version_id
        document.title = payload.title
        document.document_type = payload.document_type
        document.source = payload.source
        document.owner_actor_type = payload.owner_actor_type
        document.owner_actor_id = payload.owner_actor_id
        document.access_label = payload.access_label
        document.trust_label = payload.trust_label
        document.effective_date = payload.effective_date
        document.updated_at = utcnow()

    checksum = hashlib.sha256(payload.body.encode("utf-8")).hexdigest()
    extraction = _extract_document_text(payload.document_type, payload.body)
    version = KnowledgeDocumentVersion(
        document_id=document.id,
        version_number=version_number,
        body=payload.body,
        checksum=f"sha256:{checksum}",
        extracted_text=extraction.text,
        extraction_status=extraction.status,
        supersedes_version_id=supersedes,
        source_trace_id=payload.source_trace_id,
        created_by_actor_type=payload.owner_actor_type,
        created_by_actor_id=payload.owner_actor_id,
    )
    session.add(version)
    await session.flush()
    session.add(
        KnowledgeDocumentChunk(
            document_id=document.id,
            version_id=version.id,
            chunk_index=0,
            text=extraction.text,
            access_label=payload.access_label,
            trust_label=payload.trust_label,
        )
    )
    document.current_version_id = version.id
    document.ingestion_status = extraction.status
    session.add(document)
    await session.commit()
    return await get_document_version(
        session,
        document.id,
        allowed_access_labels={payload.access_label},
    )  # type: ignore[return-value]


async def search_documents(
    session: AsyncSession,
    brand_id: UUID,
    query: str,
    *,
    allowed_access_labels: set[str] | frozenset[str],
    limit: int = 10,
) -> DocumentSearchPage:
    """Search documents after access filtering, so restricted counts do not leak."""
    base = (
        select(KnowledgeDocument, KnowledgeDocumentVersion, KnowledgeDocumentChunk)
        .join(
            KnowledgeDocumentVersion,
            col(KnowledgeDocumentVersion.id) == col(KnowledgeDocument.current_version_id),
        )
        .join(
            KnowledgeDocumentChunk,
            col(KnowledgeDocumentChunk.version_id) == col(KnowledgeDocumentVersion.id),
        )
        .where(col(KnowledgeDocument.brand_id) == brand_id)
        .where(col(KnowledgeDocument.access_label).in_(allowed_access_labels))
        .where(col(KnowledgeDocumentChunk.access_label).in_(allowed_access_labels))
    )
    if query.strip():
        if _dialect_name(session) == "postgresql":
            base = base.where(
                func.to_tsvector("english", KnowledgeDocumentChunk.text).op("@@")(
                    func.plainto_tsquery("english", query)
                )
            )
        else:
            like = f"%{query}%"
            base = base.where(
                or_(
                    col(KnowledgeDocument.title).ilike(like),
                    col(KnowledgeDocument.logical_path).ilike(like),
                    col(KnowledgeDocumentChunk.text).ilike(like),
                )
            )
    rows = list(
        (await session.exec(base.order_by(col(KnowledgeDocument.title)).limit(limit))).all()
    )
    results = [
        _document_search_result(document, version, chunk, query)
        for document, version, chunk in rows
    ]
    return DocumentSearchPage(results=results, accessible_count=len(results))


async def role_test_retrieval(
    session: AsyncSession,
    brand_id: UUID,
    *,
    role: str,
    query: str,
    limit: int = 10,
) -> DocumentSearchPage:
    """Search as a role using the same access-filtered retrieval path."""
    return await search_documents(
        session,
        brand_id,
        query,
        allowed_access_labels=access_labels_for_role(role),
        limit=limit,
    )


async def get_document_version(
    session: AsyncSession,
    document_id: UUID,
    *,
    allowed_access_labels: set[str] | frozenset[str],
    version_id: UUID | None = None,
) -> KnowledgeDocumentRead | None:
    document = await session.get(KnowledgeDocument, document_id)
    if document is None or document.access_label not in allowed_access_labels:
        return None
    selected_version_id = version_id or document.current_version_id
    if selected_version_id is None:
        return None
    version = await session.get(KnowledgeDocumentVersion, selected_version_id)
    if version is None or version.document_id != document.id:
        return None
    supersession_state = "current" if version.id == document.current_version_id else "superseded"
    return KnowledgeDocumentRead(
        document_id=document.id,
        version_id=version.id,
        title=document.title,
        logical_path=document.logical_path,
        source=document.source,
        effective_date=document.effective_date,
        access_label=document.access_label,
        trust_label=document.trust_label,
        supersession_state=supersession_state,
        snippet=None,
        evidence_ref=f"document_version:{version.id}",
        ingestion_status=document.ingestion_status,
        extraction_status=version.extraction_status,
        body=version.body,
        version_number=version.version_number,
        supersedes_version_id=version.supersedes_version_id,
        checksum=version.checksum,
        created_at=version.created_at,
    )


def rank_attention(inputs: list[AttentionInput]) -> list[AttentionItemRead]:
    """Return deterministic Today attention items with explicit reasons."""
    items = []
    for item in inputs:
        score = (
            SEVERITY_SCORE.get(item.severity, 0)
            + SOURCE_STATUS_SCORE.get(item.source_status, 0)
            + COVERAGE_SCORE.get(item.coverage, 0)
        )
        reasons = list(item.reasons)
        reasons.append(f"severity:{item.severity}")
        reasons.append(f"source_status:{item.source_status}")
        reasons.append(f"coverage:{item.coverage}")
        unavailable = []
        if item.source_status == "unavailable":
            unavailable = [item.kind]
            reasons.append("missing input is unavailable, not zero")
        data = item.model_dump()
        data["reasons"] = reasons
        items.append(
            AttentionItemRead(
                **data,
                rank=0,
                score=score,
                unavailable_dependencies=unavailable,
            )
        )
    ordered = sorted(
        items,
        key=lambda value: (
            -value.score,
            value.kind,
            value.id,
            value.title,
        ),
    )
    return [value.model_copy(update={"rank": index + 1}) for index, value in enumerate(ordered)]


async def create_attention_snapshot(
    session: AsyncSession,
    brand: Brand,
    payload: AttentionSnapshotCreate,
) -> AttentionSnapshotRead:
    """Persist deterministic Today ranking inputs and outputs for replay."""
    items = rank_attention(payload.inputs)
    snapshot = AttentionSnapshot(
        brand_id=brand.id,
        status="ready",
        source_status=_attention_snapshot_source_status(payload.inputs),
        window_start=payload.window_start,
        window_end=payload.window_end,
        input_count=len(payload.inputs),
        item_count=len(items),
        inputs_json=[item.model_dump(mode="json", exclude_none=True) for item in payload.inputs],
        items_json=[item.model_dump(mode="json", exclude_none=True) for item in items],
    )
    session.add(snapshot)
    await session.commit()
    await session.refresh(snapshot)
    return _attention_snapshot_read(snapshot)


async def get_attention_snapshot(
    session: AsyncSession,
    snapshot_id: UUID,
) -> AttentionSnapshotRead | None:
    snapshot = await session.get(AttentionSnapshot, snapshot_id)
    if snapshot is None:
        return None
    return _attention_snapshot_read(snapshot)


def build_ask_hermes_intent(
    *,
    surface: str,
    entity_refs: list[EntityLinkIn],
    suggested_prompt: str,
    trace_id: UUID | None = None,
    access_label: str = "operations",
) -> AskHermesLaunchIntent:
    """Build a safe A03 launch intent without transcript/content payloads."""
    return AskHermesLaunchIntent(
        surface=surface,
        entity_refs=entity_refs,
        trace_id=trace_id,
        suggested_prompt=suggested_prompt,
        access_label=access_label,  # type: ignore[arg-type]
    )


def _attention_snapshot_source_status(inputs: list[AttentionInput]) -> str:
    if not inputs:
        return "unavailable"
    statuses = {item.source_status for item in inputs}
    if statuses == {"available"}:
        return "available"
    if "unavailable" in statuses or "partial" in statuses or "stale" in statuses:
        return "partial"
    return "available"


def _attention_snapshot_read(snapshot: AttentionSnapshot) -> AttentionSnapshotRead:
    return AttentionSnapshotRead(
        id=snapshot.id,
        brand_id=snapshot.brand_id,
        status=snapshot.status,
        source_status=snapshot.source_status,
        window_start=snapshot.window_start,
        window_end=snapshot.window_end,
        input_count=snapshot.input_count,
        item_count=snapshot.item_count,
        inputs=[AttentionInput.model_validate(item) for item in snapshot.inputs_json],
        items=[AttentionItemRead.model_validate(item) for item in snapshot.items_json],
        created_at=snapshot.created_at,
    )


async def _task_read(session: AsyncSession, task: OperatorTask) -> OperatorTaskRead:
    links = list(
        (
            await session.exec(
                select(OperatorTaskEntityLink)
                .where(col(OperatorTaskEntityLink.task_id) == task.id)
                .order_by(col(OperatorTaskEntityLink.created_at).asc())
            )
        ).all()
    )
    comments = list(
        (
            await session.exec(
                select(OperatorTaskComment)
                .where(col(OperatorTaskComment.task_id) == task.id)
                .order_by(col(OperatorTaskComment.created_at).asc())
            )
        ).all()
    )
    return OperatorTaskRead(
        id=task.id,
        brand_id=task.brand_id,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        due_at=task.due_at,
        assignee_type=task.assignee_type,
        assignee_id=task.assignee_id,
        assignee_label=task.assignee_label,
        provenance=task.provenance,
        created_by_actor_type=task.created_by_actor_type,
        created_by_actor_id=task.created_by_actor_id,
        source_trace_id=task.source_trace_id,
        source_run_id=task.source_run_id,
        source_evidence_ref=task.source_evidence_ref,
        access_label=task.access_label,
        daily_brief_include=task.daily_brief_include,
        entity_links=[
            EntityLinkRead(
                id=link.id,
                entity_type=link.entity_type,
                entity_id=link.entity_id,
                label=link.label,
                trace_id=link.trace_id,
            )
            for link in links
        ],
        comments=[_comment_read(comment) for comment in comments],
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def _comment_read(comment: OperatorTaskComment) -> OperatorTaskCommentRead:
    return OperatorTaskCommentRead(
        id=comment.id,
        body=comment.body,
        actor_type=comment.actor_type,
        actor_id=comment.actor_id,
        trace_id=comment.trace_id,
        created_at=comment.created_at,
    )


async def _brief_task_ref(
    session: AsyncSession,
    task: OperatorTask,
    *,
    generated_at: datetime,
) -> BriefTaskRef:
    links = list(
        (
            await session.exec(
                select(OperatorTaskEntityLink)
                .where(col(OperatorTaskEntityLink.task_id) == task.id)
                .order_by(col(OperatorTaskEntityLink.created_at).asc())
            )
        ).all()
    )
    due_label = "no due date"
    if task.due_at is not None:
        due_label = task.due_at.isoformat()
    assignee = task.assignee_label or "Unassigned"
    return BriefTaskRef(
        task_id=task.id,
        title=task.title,
        status=task.status,
        priority=task.priority,
        due_at=task.due_at,
        overdue=bool(task.due_at and task.due_at < generated_at),
        assignee_type=task.assignee_type,
        assignee_id=task.assignee_id,
        assignee_label=task.assignee_label,
        provenance=task.provenance,
        access_label=task.access_label,
        source_trace_id=task.source_trace_id,
        source_run_id=task.source_run_id,
        source_evidence_ref=task.source_evidence_ref,
        entity_links=[
            EntityLinkRead(
                id=link.id,
                entity_type=link.entity_type,
                entity_id=link.entity_id,
                label=link.label,
                trace_id=link.trace_id,
            )
            for link in links
        ],
        summary=f"{task.priority} task for {assignee}; due {due_label}; status {task.status}",
    )


async def _next_document_version_number(session: AsyncSession, document_id: UUID) -> int:
    max_version = (
        await session.exec(
            select(func.max(KnowledgeDocumentVersion.version_number)).where(
                col(KnowledgeDocumentVersion.document_id) == document_id
            )
        )
    ).first()
    return int(max_version or 0) + 1


def _document_search_result(
    document: KnowledgeDocument,
    version: KnowledgeDocumentVersion,
    chunk: KnowledgeDocumentChunk,
    query: str,
) -> KnowledgeDocumentSearchResult:
    supersession_state = "current" if version.id == document.current_version_id else "superseded"
    return KnowledgeDocumentSearchResult(
        document_id=document.id,
        version_id=version.id,
        title=document.title,
        logical_path=document.logical_path,
        source=document.source,
        effective_date=document.effective_date,
        access_label=document.access_label,
        trust_label=document.trust_label,
        supersession_state=supersession_state,
        snippet=_safe_snippet(chunk.text, query),
        evidence_ref=f"document_version:{version.id}",
        ingestion_status=document.ingestion_status,
        extraction_status=version.extraction_status,
    )


def _safe_snippet(text: str, query: str, *, max_len: int = 220) -> str:
    if not text:
        return ""
    if not query.strip():
        return text[:max_len]
    lowered = text.lower()
    index = lowered.find(query.lower())
    if index < 0:
        return text[:max_len]
    start = max(index - 60, 0)
    return text[start : start + max_len]


def _extract_document_text(document_type: str, body: str) -> ExtractedDocument:
    """Extract search text without treating arbitrary content as executable authority."""
    normalized_type = document_type.strip().lower()
    if not body.strip():
        return ExtractedDocument(text="", status="unavailable")

    if normalized_type in {"markdown", "md", "text", "txt", "plain_text", "text/plain"}:
        return ExtractedDocument(text=body, status="indexed")

    if normalized_type in {"html", "text/html"}:
        parser = _VisibleTextHTMLParser()
        parser.feed(body)
        parser.close()
        text = parser.text()
        status = "indexed" if text else "unavailable"
        return ExtractedDocument(text=text, status=status)

    return ExtractedDocument(text="", status="unavailable")


def _collapse_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _dialect_name(session: AsyncSession) -> str:
    bind = session.get_bind()
    return bind.dialect.name if bind is not None else "unknown"
