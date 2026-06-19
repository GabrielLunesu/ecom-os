from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.time import utcnow
from app.models.brand import Brand
from app.schemas.operator_workspace import (
    AttentionInput,
    AttentionSnapshotCreate,
    EntityLinkIn,
    KnowledgeDocumentUpsert,
    OperatorTaskCommentCreate,
    OperatorTaskCreate,
    OperatorTaskUpdate,
)
from app.services.operator_workspace import (
    access_labels_for_role,
    add_operator_task_comment,
    brief_task_inputs,
    build_ask_hermes_intent,
    create_attention_snapshot,
    create_operator_task,
    get_attention_snapshot,
    get_document_version,
    get_operator_task,
    list_operator_tasks,
    operator_workspace_tool_manifest,
    rank_attention,
    role_test_retrieval,
    update_operator_task,
    upsert_document_version,
)


async def _engine_and_brand() -> tuple[AsyncEngine, Brand]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.connect() as conn, conn.begin():
        await conn.run_sync(SQLModel.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    brand = Brand(name="A07 Test")
    session.add(brand)
    await session.commit()
    await session.refresh(brand)
    await session.close()
    return engine, brand


def test_agent_created_task_requires_run_and_trace_provenance() -> None:
    with pytest.raises(ValidationError, match="agent-created tasks require"):
        OperatorTaskCreate(
            title="Follow up with supplier",
            provenance="agent",
            created_by_actor_type="hermes_profile",
            created_by_actor_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_agent_task_persists_provenance_entity_links_and_comments() -> None:
    engine, brand = await _engine_and_brand()
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            trace_id = uuid4()
            run_id = uuid4()
            task = await create_operator_task(
                session,
                brand,
                OperatorTaskCreate(
                    title="Contact carrier about delayed order",
                    priority="urgent",
                    provenance="agent",
                    created_by_actor_type="hermes_profile",
                    created_by_actor_id=uuid4(),
                    source_trace_id=trace_id,
                    source_run_id=run_id,
                    entity_links=[
                        EntityLinkIn(
                            entity_type="order",
                            entity_id="ord_1001",
                            label="#1001",
                            trace_id=trace_id,
                        )
                    ],
                ),
            )
            assert task.provenance == "agent"
            assert task.source_trace_id == trace_id
            assert task.source_run_id == run_id
            assert task.entity_links[0].entity_type == "order"

            comment = await add_operator_task_comment(
                session,
                task.id,
                OperatorTaskCommentCreate(body="Carrier SLA exceeded.", trace_id=trace_id),
            )
            assert comment is not None
            assert comment.trace_id == trace_id
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_task_access_filtering_hides_restricted_tasks_and_comments() -> None:
    engine, brand = await _engine_and_brand()
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            public_task = await create_operator_task(
                session,
                brand,
                OperatorTaskCreate(
                    title="Public operations task",
                    access_label="operations",
                ),
            )
            restricted_task = await create_operator_task(
                session,
                brand,
                OperatorTaskCreate(
                    title="Founder acquisition task",
                    access_label="founder_private",
                ),
            )

            viewer_tasks = await list_operator_tasks(
                session,
                brand.id,
                allowed_access_labels=access_labels_for_role("viewer"),
            )
            assert [task.title for task in viewer_tasks] == ["Public operations task"]

            assert (
                await get_operator_task(
                    session,
                    restricted_task.id,
                    allowed_access_labels=access_labels_for_role("viewer"),
                )
                is None
            )
            assert (
                await update_operator_task(
                    session,
                    restricted_task.id,
                    payload=OperatorTaskUpdate(title="Should not update"),
                    allowed_access_labels=access_labels_for_role("viewer"),
                )
                is None
            )
            assert (
                await add_operator_task_comment(
                    session,
                    restricted_task.id,
                    OperatorTaskCommentCreate(body="Should not append"),
                    allowed_access_labels=access_labels_for_role("viewer"),
                )
                is None
            )

            owner_tasks = await list_operator_tasks(
                session,
                brand.id,
                allowed_access_labels=access_labels_for_role("owner"),
            )
            assert {task.id for task in owner_tasks} == {
                public_task.id,
                restricted_task.id,
            }
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_brief_task_inputs_are_due_access_filtered_refs_only() -> None:
    engine, brand = await _engine_and_brand()
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            now = utcnow()
            trace_id = uuid4()
            due_task = await create_operator_task(
                session,
                brand,
                OperatorTaskCreate(
                    title="Call carrier before cutoff",
                    priority="urgent",
                    due_at=now + timedelta(hours=2),
                    source_trace_id=trace_id,
                    entity_links=[
                        EntityLinkIn(
                            entity_type="order",
                            entity_id="ord_due",
                            label="#1002",
                            trace_id=trace_id,
                        )
                    ],
                ),
            )
            await add_operator_task_comment(
                session,
                due_task.id,
                OperatorTaskCommentCreate(body="Internal note must not enter brief input."),
            )
            await create_operator_task(
                session,
                brand,
                OperatorTaskCreate(
                    title="Future task outside horizon",
                    due_at=now + timedelta(days=5),
                ),
            )
            await create_operator_task(
                session,
                brand,
                OperatorTaskCreate(
                    title="Done task excluded",
                    status="done",
                    due_at=now - timedelta(hours=1),
                ),
            )
            await create_operator_task(
                session,
                brand,
                OperatorTaskCreate(
                    title="Founder private task",
                    access_label="founder_private",
                    due_at=now + timedelta(hours=1),
                ),
            )
            await create_operator_task(
                session,
                brand,
                OperatorTaskCreate(
                    title="Brief opt-out task",
                    daily_brief_include=False,
                    due_at=now + timedelta(hours=1),
                ),
            )

            viewer_input = await brief_task_inputs(
                session,
                brand.id,
                allowed_access_labels=access_labels_for_role("viewer"),
                role="viewer",
                horizon_end=now + timedelta(hours=24),
            )
            assert viewer_input.source_status == "available"
            assert viewer_input.coverage == "verified"
            assert viewer_input.accessible_count == 1
            assert [task.title for task in viewer_input.tasks] == ["Call carrier before cutoff"]
            ref = viewer_input.tasks[0]
            assert ref.task_id == due_task.id
            assert ref.source_trace_id == trace_id
            assert ref.entity_links[0].entity_id == "ord_due"
            dumped = ref.model_dump()
            assert "comments" not in dumped
            assert "Internal note" not in str(dumped)

            owner_input = await brief_task_inputs(
                session,
                brand.id,
                allowed_access_labels=access_labels_for_role("owner"),
                role="owner",
                horizon_end=now + timedelta(hours=24),
            )
            assert owner_input.accessible_count == 2
            assert {task.title for task in owner_input.tasks} == {
                "Call carrier before cutoff",
                "Founder private task",
            }
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_document_search_filters_access_before_counts_and_snippets() -> None:
    engine, brand = await _engine_and_brand()
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            await upsert_document_version(
                session,
                brand,
                KnowledgeDocumentUpsert(
                    logical_path="public-shipping.md",
                    title="Public Shipping SOP",
                    body="shared returns handling phrase",
                    access_label="operations",
                ),
            )
            await upsert_document_version(
                session,
                brand,
                KnowledgeDocumentUpsert(
                    logical_path="founder-private.md",
                    title="Founder Private SOP",
                    body="shared secret acquisition margin phrase",
                    access_label="founder_private",
                    trust_label="verified",
                ),
            )

            viewer = await role_test_retrieval(
                session,
                brand.id,
                role="viewer",
                query="shared",
            )
            assert viewer.accessible_count == 1
            assert [result.title for result in viewer.results] == ["Public Shipping SOP"]
            assert "secret acquisition" not in (viewer.results[0].snippet or "")

            owner = await role_test_retrieval(
                session,
                brand.id,
                role="owner",
                query="shared",
            )
            assert owner.accessible_count == 2
            assert {result.access_label for result in owner.results} == {
                "operations",
                "founder_private",
            }
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_html_document_extraction_ignores_active_content() -> None:
    engine, brand = await _engine_and_brand()
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            doc = await upsert_document_version(
                session,
                brand,
                KnowledgeDocumentUpsert(
                    logical_path="returns-policy.html",
                    title="Returns Policy",
                    document_type="html",
                    body=(
                        "<h1>Returns policy</h1>"
                        "<script>secret acquisition phrase</script>"
                        "<style>.hidden{display:none}</style>"
                        "<p>visible warranty phrase</p>"
                    ),
                ),
            )
            assert doc.extraction_status == "indexed"
            assert doc.ingestion_status == "indexed"

            visible = await role_test_retrieval(
                session,
                brand.id,
                role="operator",
                query="visible warranty",
            )
            assert visible.accessible_count == 1
            assert "visible warranty phrase" in (visible.results[0].snippet or "")

            hidden = await role_test_retrieval(
                session,
                brand.id,
                role="operator",
                query="secret acquisition",
            )
            assert hidden.accessible_count == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_unsupported_document_type_is_visible_but_not_indexed() -> None:
    engine, brand = await _engine_and_brand()
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            doc = await upsert_document_version(
                session,
                brand,
                KnowledgeDocumentUpsert(
                    logical_path="vendor-file.pdf",
                    title="Vendor PDF",
                    document_type="pdf",
                    body="PDF body text should not become searchable without extraction.",
                ),
            )
            assert doc.extraction_status == "unavailable"
            assert doc.ingestion_status == "unavailable"

            matched = await role_test_retrieval(
                session,
                brand.id,
                role="operator",
                query="PDF body text",
            )
            assert matched.accessible_count == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_superseded_document_version_remains_retrievable() -> None:
    engine, brand = await _engine_and_brand()
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            first = await upsert_document_version(
                session,
                brand,
                KnowledgeDocumentUpsert(
                    logical_path="shipping-policy.md",
                    title="Shipping Policy",
                    body="Version one shipping text.",
                    effective_date=None,
                ),
            )
            second = await upsert_document_version(
                session,
                brand,
                KnowledgeDocumentUpsert(
                    logical_path="shipping-policy.md",
                    title="Shipping Policy",
                    body="Version two shipping text.",
                    effective_date=None,
                ),
            )

            old = await get_document_version(
                session,
                first.document_id,
                version_id=first.version_id,
                allowed_access_labels=access_labels_for_role("operator"),
            )
            assert old is not None
            assert old.supersession_state == "superseded"
            assert old.body == "Version one shipping text."
            assert second.supersedes_version_id == first.version_id
    finally:
        await engine.dispose()


def test_attention_ranking_is_deterministic_and_missing_inputs_are_unavailable() -> None:
    trace_id = uuid4()
    ranked = rank_attention(
        [
            AttentionInput(
                kind="due_tasks",
                id="task-1",
                title="Task due today",
                severity="medium",
                coverage="verified",
                trace_id=trace_id,
            ),
            AttentionInput(
                kind="cs_backlog",
                id="cs-source",
                title="CS backlog source unavailable",
                severity="medium",
                source_status="unavailable",
                coverage="unknown",
            ),
            AttentionInput(
                kind="failed_action",
                id="act-1",
                title="Reply action failed",
                severity="high",
                coverage="verified",
            ),
        ]
    )

    assert [item.id for item in ranked] == ["act-1", "cs-source", "task-1"]
    unavailable = ranked[1]
    assert unavailable.source_status == "unavailable"
    assert unavailable.unavailable_dependencies == ["cs_backlog"]
    assert "missing input is unavailable, not zero" in unavailable.reasons
    assert [item.rank for item in ranked] == [1, 2, 3]


@pytest.mark.asyncio
async def test_attention_snapshot_persists_ranked_items_for_replay() -> None:
    engine, brand = await _engine_and_brand()
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            trace_id = uuid4()
            snapshot = await create_attention_snapshot(
                session,
                brand,
                AttentionSnapshotCreate(
                    inputs=[
                        AttentionInput(
                            kind="due_tasks",
                            id="task-1",
                            title="Task due today",
                            severity="medium",
                            coverage="verified",
                            trace_id=trace_id,
                            source_refs=[
                                {"type": "task", "id": "task-1", "label": "Task due today"}
                            ],
                        ),
                        AttentionInput(
                            kind="incidents",
                            id="incidents:unavailable",
                            title="Incident source unavailable",
                            severity="medium",
                            source_status="unavailable",
                            coverage="unknown",
                            reasons=["A02 incident source pending"],
                        ),
                    ]
                ),
            )

            assert snapshot.status == "ready"
            assert snapshot.source_status == "partial"
            assert snapshot.input_count == 2
            assert snapshot.item_count == 2
            assert [item.rank for item in snapshot.items] == [1, 2]
            assert snapshot.items[0].id == "incidents:unavailable"
            assert snapshot.items[0].unavailable_dependencies == ["incidents"]
            assert "missing input is unavailable, not zero" in snapshot.items[0].reasons
            assert snapshot.items[1].trace_id == trace_id
            assert snapshot.items[1].source_refs[0].type == "task"

            replayed = await get_attention_snapshot(session, snapshot.id)
            assert replayed is not None
            assert replayed.id == snapshot.id
            assert replayed.items[0].id == snapshot.items[0].id
            assert replayed.inputs[0].trace_id == trace_id
    finally:
        await engine.dispose()


def test_ask_hermes_launch_intent_contains_only_safe_refs() -> None:
    trace_id = uuid4()
    intent = build_ask_hermes_intent(
        surface="knowledge",
        entity_refs=[
            EntityLinkIn(
                entity_type="document",
                entity_id="doc_1",
                label="Shipping Policy",
                trace_id=trace_id,
            )
        ],
        trace_id=trace_id,
        suggested_prompt="Inspect this document version.",
    )

    dumped = intent.model_dump()
    assert dumped["trace_id"] == trace_id
    assert dumped["entity_refs"][0]["entity_id"] == "doc_1"
    assert "body" not in dumped
    assert "transcript" not in dumped
    assert "credential" not in dumped


def test_tool_manifest_is_stable_and_safe_for_a03_registration() -> None:
    manifest = operator_workspace_tool_manifest()
    assert manifest.version == "a07.local.v0"
    assert manifest.schema_hash.startswith("sha256:")
    assert manifest.schema_hash == operator_workspace_tool_manifest().schema_hash

    tools = {tool.name: tool for tool in manifest.tools}
    assert {
        "ecom.task.list",
        "ecom.task.get",
        "ecom.task.create",
        "ecom.document.search",
        "ecom.document.get",
        "ecom.operator.ask_hermes_intent.create",
    } <= set(tools)

    required_metadata = {
        "name",
        "version",
        "description",
        "input_schema",
        "output_schema",
        "read_or_write",
        "risk_class",
        "required_ecom_permissions",
        "required_connection_types",
        "store_scope_rule",
        "supports_simulation",
        "supports_idempotency",
        "reconciliation_strategy",
        "sensitive_fields",
        "minimum_trace_coverage",
    }
    for tool in manifest.tools:
        dumped = tool.model_dump()
        assert required_metadata <= set(dumped)
        assert tool.version == manifest.version
        assert tool.sensitive_fields == []
        assert tool.required_connection_types == []
        assert "default" not in tool.store_scope_rule

    assert tools["ecom.task.create"].read_or_write == "write"
    assert tools["ecom.task.create"].risk_class == "internal_state"
    assert tools["ecom.task.create"].minimum_trace_coverage == "verified"
    assert tools["ecom.document.search"].read_or_write == "read"
    assert tools["ecom.document.get"].read_or_write == "read"

    intent_tool = tools["ecom.operator.ask_hermes_intent.create"]
    assert intent_tool.read_or_write == "read"
    assert "AskHermesLaunchRequest" in str(intent_tool.input_schema)
    assert "credential" not in str(manifest.model_dump()).lower()
