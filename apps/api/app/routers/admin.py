from fastapi import APIRouter

from app.workers.maintenance import run_maintenance

router = APIRouter()


@router.post("/maintenance/run")
async def trigger_maintenance():
    result = await run_maintenance()
    return {"status": "ok", **result}
