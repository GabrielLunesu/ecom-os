"""Per-person task board service (Build Spec §7.3)."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.time import utcnow
from app.models.brand import Brand
from app.models.team_task import TeamTask

_SEED = [
    ("Review weekly refund-risk insights", "Alex", "todo"),
    ("Refresh shipping policy in the vault", "Sam", "doing"),
    ("Audit CS auto-resolved tickets", "Jordan", "todo"),
    ("Reconcile last week's revenue", "Alex", "done"),
]


async def ensure_seed_tasks(session: AsyncSession, brand: Brand) -> None:
    existing = (await session.exec(select(TeamTask).limit(1))).first()
    if existing is None:
        for title, assignee, status in _SEED:
            session.add(
                TeamTask(brand_id=brand.id, title=title, assignee=assignee, status=status)
            )
        await session.commit()


async def list_tasks(session: AsyncSession) -> list[TeamTask]:
    return list(
        (await session.exec(select(TeamTask).order_by(TeamTask.created_at))).all()  # type: ignore[arg-type]
    )


async def create_task(
    session: AsyncSession, brand: Brand, *, title: str, assignee: str
) -> TeamTask:
    task = TeamTask(brand_id=brand.id, title=title, assignee=assignee, status="todo")
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


async def update_task(
    session: AsyncSession, task_id: UUID, *, status: str | None, assignee: str | None
) -> TeamTask | None:
    task = (await session.exec(select(TeamTask).where(TeamTask.id == task_id))).first()
    if task is None:
        return None
    if status is not None:
        task.status = status
    if assignee is not None:
        task.assignee = assignee
    task.updated_at = utcnow()
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task
