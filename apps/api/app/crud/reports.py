from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report import Report
from app.models.user_item import UserItem


async def update_embedding(db: AsyncSession, report: Report, embedding: list[float]) -> None:
    report.embedding = embedding
    await db.commit()


async def semantic_search(
    db: AsyncSession,
    user_id: UUID,
    embedding: list[float],
    limit: int = 5,
) -> list[Report]:
    from sqlalchemy import func as sa_func
    result = await db.execute(
        select(Report)
        .where(Report.user_id == user_id, Report.embedding.isnot(None))
        .order_by(Report.embedding.cosine_distance(embedding))
        .limit(limit)
    )
    return list(result.scalars().all())


async def create(
    db: AsyncSession,
    user_id: UUID,
    *,
    title: str,
    body_md: str,
    summary: str | None = None,
    source_item_ids: list | None = None,
    last_edited_by: str = "ai",
) -> Report:
    report = Report(
        user_id=user_id,
        title=title,
        body_md=body_md or "",
        summary=summary,
        source_item_ids=[str(i) for i in (source_item_ids or [])],
        last_edited_by=last_edited_by,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


async def get_one(db: AsyncSession, user_id: UUID, report_id: UUID) -> Report | None:
    result = await db.execute(
        select(Report).where(
            Report.id == report_id,
            Report.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def list_by_user(db: AsyncSession, user_id: UUID) -> list[Report]:
    result = await db.execute(
        select(Report)
        .where(Report.user_id == user_id)
        .order_by(Report.updated_at.desc())
    )
    return list(result.scalars().all())


async def update(
    db: AsyncSession,
    report: Report,
    *,
    title: str | None = None,
    body_md: str | None = None,
    summary: str | None = None,
    last_edited_by: str | None = None,
) -> Report:
    if title is not None:
        report.title = title
    if body_md is not None:
        report.body_md = body_md
    if summary is not None:
        report.summary = summary
    if last_edited_by is not None:
        report.last_edited_by = last_edited_by
    await db.commit()
    await db.refresh(report)
    return report


async def delete(db: AsyncSession, report: Report) -> None:
    """硬刪除：報告為產出層，直接從 DB 移除。"""
    await db.delete(report)
    await db.commit()


async def resolve_sources(
    db: AsyncSession, user_id: UUID, source_item_ids: list | None
) -> list[UserItem]:
    """把 source_item_ids 解析成 UserItem（user-scoped），供 provenance 顯示。"""
    if not source_item_ids:
        return []
    ids: list[UUID] = []
    for i in source_item_ids:
        try:
            ids.append(UUID(i) if isinstance(i, str) else i)
        except (ValueError, TypeError):
            continue
    if not ids:
        return []
    result = await db.execute(
        select(UserItem).where(UserItem.user_id == user_id, UserItem.id.in_(ids))
    )
    return list(result.scalars().all())
