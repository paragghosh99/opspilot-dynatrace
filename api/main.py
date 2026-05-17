from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from agent.orchestrator import poll_and_respond
from api.dashboard import router as dashboard_router
from api.health import router as health_router


app = FastAPI(title="OpsPilot", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(dashboard_router)


@app.post("/poll")
async def poll():
    return await poll_and_respond()


web_root = Path("web/dist") if Path("web/dist/index.html").exists() else Path("web")
app.mount("/", StaticFiles(directory=web_root, html=True), name="web")
