"""FastAPI application factory for the Coauthor web server."""
from __future__ import annotations

import logging
import os
import threading
import uuid
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

log = logging.getLogger(__name__)

# In-memory scan status tracker (scan_id -> {"status": ..., "report": ...})
_scans: dict = {}


def create_app() -> FastAPI:
    """Create and configure the Coauthor FastAPI application."""
    from . import __version__

    app = FastAPI(
        title="BespokeAgile Coauthor",
        description="Code authorship analysis for any git repository",
        version=__version__,
    )

    # CORS -- permissive for local dev
    cors_origins = os.environ.get("COAUTHOR_CORS_ORIGINS", "*")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in cors_origins.split(",")],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Routes ---

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/config")
    async def config():
        from .llm_config import has_llm_key, get_provider
        return {
            "llm_api_key_set": has_llm_key(),
            "llm_provider": get_provider(),
            "version": __version__,
        }

    @app.post("/scan")
    async def start_scan(request: Request):
        body = await request.json()
        target = body.get("target", "")
        if not target:
            return JSONResponse({"error": "target is required"}, status_code=400)

        scan_id = uuid.uuid4().hex[:12]
        max_commits = body.get("max_commits", 0)
        exclude_bots = body.get("exclude_bots", True)

        _scans[scan_id] = {"status": "running"}

        def _run():
            try:
                from .scanner import run_scan
                from .store import save_scan

                report = run_scan(
                    target,
                    max_commits=max_commits,
                    exclude_bots=exclude_bots,
                )
                save_scan(scan_id, target, report.get("commit_sha", ""), report)
                _scans[scan_id] = {"status": "complete", "report": report}
            except Exception as exc:
                log.exception("Scan %s failed", scan_id)
                _scans[scan_id] = {"status": "error", "error": str(exc)}

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

        return {"scan_id": scan_id, "status": "running"}

    @app.get("/scan/{scan_id}")
    async def get_scan(scan_id: str):
        # Check in-memory first (for running/just-completed scans)
        if scan_id in _scans:
            entry = _scans[scan_id]
            if entry["status"] == "running":
                return {"scan_id": scan_id, "status": "running"}
            if entry["status"] == "error":
                return JSONResponse(
                    {"scan_id": scan_id, "status": "error", "error": entry.get("error", "")},
                    status_code=500,
                )
            return entry.get("report", {})

        # Fall back to persistent store
        from .store import get_scan as store_get

        report = store_get(scan_id)
        if report is None:
            return JSONResponse({"error": "scan not found"}, status_code=404)
        return report

    @app.get("/scans")
    async def list_scans(limit: int = 20):
        from .store import list_scans as store_list

        return store_list(limit=limit)

    @app.get("/authors")
    async def get_authors():
        from .store import list_scans as store_list, get_scan as store_get

        scans = store_list(limit=1)
        if not scans:
            return {"authors": [], "clusters": {}}
        report = store_get(scans[0]["id"])
        if not report:
            return {"authors": [], "clusters": {}}
        return report.get("authorship", {"authors": [], "clusters": {}})

    @app.get("/impacts")
    async def get_impacts():
        from .store import list_scans as store_list, get_scan as store_get

        scans = store_list(limit=1)
        if not scans:
            return {"commits": []}
        report = store_get(scans[0]["id"])
        if not report:
            return {"commits": []}
        return report.get("impact", {"commits": []})

    @app.post("/alice")
    async def alice_chat(request: Request):
        from .llm_config import has_llm_key

        if not has_llm_key():
            return JSONResponse(
                {"error": "No LLM API key configured. Set ANTHROPIC_API_KEY or OPENAI_API_KEY."},
                status_code=503,
            )
        body = await request.json()
        message = body.get("message", "")
        # Placeholder -- Alice integration is future work
        return {"reply": "Alice integration is not yet available. Message received: " + message[:200]}

    # --- Static files ---

    dashboard_dir = os.path.join(os.path.dirname(__file__), "dashboard")
    if os.path.isdir(dashboard_dir):
        app.mount("/dashboard", StaticFiles(directory=dashboard_dir), name="dashboard")

    @app.get("/", response_class=HTMLResponse)
    async def index():
        index_path = os.path.join(dashboard_dir, "index.html")
        if os.path.exists(index_path):
            with open(index_path) as f:
                return HTMLResponse(f.read())
        return HTMLResponse("<h1>Coauthor</h1><p>Dashboard not found.</p>")

    return app
