from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from agent.self_learn.incident_logger import list_incidents
from agent.self_learn.runbook_updater import get_runbook
from agent.tools.dynatrace_mcp import get_open_problems


router = APIRouter(prefix="/api")


@router.get("/problems")
async def problems():
    return {"problems": await get_open_problems()}


@router.get("/incidents")
def incidents():
    return {"incidents": list_incidents()}


@router.get("/runbook")
def runbook():
    return {"runbook": get_runbook()}


@router.get("/mttr")
def mttr():
    rows = list(reversed(list_incidents()))
    points = [
        {
            "label": row.get("created_at", "")[:10] or row.get("problem_id", "incident"),
            "minutes": row.get("mttr_minutes", 0),
        }
        for row in rows[-30:]
    ]
    return {"points": points}


@router.get("/events")
async def events():
    async def stream():
        while True:
            payload = {"problems": await get_open_problems()}
            yield f"data: {json.dumps(payload)}\n\n"
            await asyncio.sleep(10)

    return StreamingResponse(stream(), media_type="text/event-stream")
