from fastapi import APIRouter, BackgroundTasks

from app.workers.maintenance import run_maintenance

router = APIRouter()


@router.post("/maintenance/run")
async def trigger_maintenance():
    result = await run_maintenance()
    return {"status": "ok", **result}


@router.post("/backfill/embeddings")
async def backfill_embeddings(background_tasks: BackgroundTasks):
    """補齊 reports 和 trips 的 embedding（一次性 backfill 用）。"""
    background_tasks.add_task(_run_backfill)
    return {"status": "queued"}


async def _run_backfill():
    import logging
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import select
    from app.models.report import Report
    from app.models.trip import Trip
    from app.services import ai_service
    from app.crud import reports as crud_reports, trips as crud_trips

    log = logging.getLogger("garner.admin.backfill")

    async with AsyncSessionLocal() as db:
        # backfill reports
        result = await db.execute(select(Report).where(Report.embedding.is_(None)))
        reports = result.scalars().all()
        log.info("backfill: %d reports without embedding", len(reports))
        for r in reports:
            try:
                parts = [r.title]
                if r.summary:
                    parts.append(r.summary)
                elif r.body_md:
                    parts.append(r.body_md[:500])
                emb = await ai_service.embed(" ".join(parts))
                await crud_reports.update_embedding(db, r, emb)
            except Exception:
                log.exception("backfill report %s failed", r.id)

        # backfill trips
        result2 = await db.execute(select(Trip).where(Trip.embedding.is_(None)))
        trips = result2.scalars().all()
        log.info("backfill: %d trips without embedding", len(trips))
        for t in trips:
            try:
                from sqlalchemy.orm import selectinload
                trip = (await db.execute(
                    select(Trip).where(Trip.id == t.id).options(selectinload(Trip.items))
                )).scalar_one()
                parts = [trip.title]
                if trip.summary:
                    parts.append(trip.summary)
                card_titles = [it.title for it in (trip.items or []) if it.title]
                if card_titles:
                    parts.append(" ".join(card_titles))
                emb = await ai_service.embed(" ".join(parts))
                await crud_trips.update_trip_embedding(db, trip, emb)
            except Exception:
                log.exception("backfill trip %s failed", t.id)
