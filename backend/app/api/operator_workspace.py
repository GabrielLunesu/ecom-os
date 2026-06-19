"""A07 operator workspace API routes."""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import require_user_auth
from app.core.time import utcnow
from app.db.session import get_session
from app.schemas.operator_workspace import (
    AskHermesLaunchIntent,
    AskHermesLaunchRequest,
    AttentionInput,
    AttentionItemRead,
    AttentionSnapshotCreate,
    AttentionSnapshotRead,
    BriefTaskInputRead,
    KnowledgeDocumentRead,
    KnowledgeDocumentSearchResult,
    KnowledgeDocumentUpsert,
    KnowledgeRoleTest,
    OperatorTaskCommentCreate,
    OperatorTaskCommentRead,
    OperatorTaskCreate,
    OperatorTaskRead,
    OperatorTaskUpdate,
    ToolCatalogManifest,
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
    search_documents,
    update_operator_task,
    upsert_document_version,
)
from app.services.stores import ensure_seed

router = APIRouter(
    prefix="/operator-workspace",
    tags=["operator-workspace"],
    dependencies=[Depends(require_user_auth)],
)


class KnowledgeSearchResponse(KnowledgeRoleTest):
    accessible_count: int
    results: list[KnowledgeDocumentSearchResult]


@router.get("/tool-manifest", response_model=ToolCatalogManifest)
async def get_tool_manifest() -> ToolCatalogManifest:
    return operator_workspace_tool_manifest()


@router.get("/tasks", response_model=list[OperatorTaskRead])
async def list_tasks(
    include_done: bool = True,
    role: str = Query(default="operator"),
    session: AsyncSession = Depends(get_session),
) -> list[OperatorTaskRead]:
    brand = await ensure_seed(session)
    return await list_operator_tasks(
        session,
        brand.id,
        include_done=include_done,
        allowed_access_labels=access_labels_for_role(role),
    )


@router.post("/tasks", response_model=OperatorTaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: OperatorTaskCreate,
    session: AsyncSession = Depends(get_session),
) -> OperatorTaskRead:
    brand = await ensure_seed(session)
    return await create_operator_task(session, brand, payload)


@router.get("/tasks/{task_id}", response_model=OperatorTaskRead)
async def get_task(
    task_id: UUID,
    role: str = Query(default="operator"),
    session: AsyncSession = Depends(get_session),
) -> OperatorTaskRead:
    task = await get_operator_task(
        session,
        task_id,
        allowed_access_labels=access_labels_for_role(role),
    )
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return task


@router.patch("/tasks/{task_id}", response_model=OperatorTaskRead)
async def update_task(
    task_id: UUID,
    payload: OperatorTaskUpdate,
    role: str = Query(default="operator"),
    session: AsyncSession = Depends(get_session),
) -> OperatorTaskRead:
    task = await update_operator_task(
        session,
        task_id,
        payload,
        allowed_access_labels=access_labels_for_role(role),
    )
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return task


@router.post("/tasks/{task_id}/comments", response_model=OperatorTaskCommentRead)
async def add_task_comment(
    task_id: UUID,
    payload: OperatorTaskCommentCreate,
    role: str = Query(default="operator"),
    session: AsyncSession = Depends(get_session),
) -> OperatorTaskCommentRead:
    comment = await add_operator_task_comment(
        session,
        task_id,
        payload,
        allowed_access_labels=access_labels_for_role(role),
    )
    if comment is None:
        raise HTTPException(status_code=404, detail="task not found")
    return comment


@router.post(
    "/knowledge/documents",
    response_model=KnowledgeDocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upsert_knowledge_document(
    payload: KnowledgeDocumentUpsert,
    session: AsyncSession = Depends(get_session),
) -> KnowledgeDocumentRead:
    brand = await ensure_seed(session)
    return await upsert_document_version(session, brand, payload)


@router.get("/knowledge/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(
    query: str = "",
    role: str = Query(default="operator"),
    limit: int = Query(default=10, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
) -> KnowledgeSearchResponse:
    brand = await ensure_seed(session)
    page = await search_documents(
        session,
        brand.id,
        query,
        allowed_access_labels=access_labels_for_role(role),
        limit=limit,
    )
    return KnowledgeSearchResponse(
        role=role,
        query=query,
        accessible_count=page.accessible_count,
        results=page.results,
    )


@router.post("/knowledge/role-test", response_model=KnowledgeSearchResponse)
async def role_test_knowledge(
    payload: KnowledgeRoleTest,
    session: AsyncSession = Depends(get_session),
) -> KnowledgeSearchResponse:
    brand = await ensure_seed(session)
    page = await role_test_retrieval(
        session,
        brand.id,
        role=payload.role,
        query=payload.query,
    )
    return KnowledgeSearchResponse(
        role=payload.role,
        query=payload.query,
        accessible_count=page.accessible_count,
        results=page.results,
    )


@router.get("/knowledge/documents/{document_id}", response_model=KnowledgeDocumentRead)
async def get_knowledge_document(
    document_id: UUID,
    version_id: UUID | None = None,
    role: str = Query(default="operator"),
    session: AsyncSession = Depends(get_session),
) -> KnowledgeDocumentRead:
    doc = await get_document_version(
        session,
        document_id,
        version_id=version_id,
        allowed_access_labels=access_labels_for_role(role),
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="document not found or inaccessible")
    return doc


@router.post("/attention/rank", response_model=list[AttentionItemRead])
async def rank_attention_items(inputs: list[AttentionInput]) -> list[AttentionItemRead]:
    return rank_attention(inputs)


@router.post(
    "/attention/snapshots",
    response_model=AttentionSnapshotRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_attention_snapshot_route(
    payload: AttentionSnapshotCreate,
    session: AsyncSession = Depends(get_session),
) -> AttentionSnapshotRead:
    brand = await ensure_seed(session)
    return await create_attention_snapshot(session, brand, payload)


@router.get("/attention/snapshots/{snapshot_id}", response_model=AttentionSnapshotRead)
async def get_attention_snapshot_route(
    snapshot_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> AttentionSnapshotRead:
    snapshot = await get_attention_snapshot(session, snapshot_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="attention snapshot not found")
    return snapshot


@router.get("/brief/task-inputs", response_model=BriefTaskInputRead)
async def get_brief_task_inputs(
    role: str = Query(default="operator"),
    horizon_hours: int = Query(default=24, ge=1, le=168),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> BriefTaskInputRead:
    brand = await ensure_seed(session)
    horizon_end = utcnow() + timedelta(hours=horizon_hours)
    return await brief_task_inputs(
        session,
        brand.id,
        allowed_access_labels=access_labels_for_role(role),
        role=role,
        horizon_end=horizon_end,
        limit=limit,
    )


@router.post("/ask-hermes-intents", response_model=AskHermesLaunchIntent)
async def ask_hermes_intent(
    payload: AskHermesLaunchRequest,
) -> AskHermesLaunchIntent:
    return build_ask_hermes_intent(
        surface=payload.surface,
        entity_refs=payload.entity_refs,
        trace_id=payload.trace_id,
        suggested_prompt=payload.suggested_prompt,
        access_label=payload.access_label,
    )
