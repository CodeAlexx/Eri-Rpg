"""FastAPI server for EriRPG dashboard."""

import asyncio
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from erirpg.ui.data import (
    get_all_projects, get_active_task, get_project, get_project_path,
    load_state, load_knowledge, load_runs, load_roadmap, load_graph,
    get_git_log, get_drift_status, check_staleness, count_modules, count_learned
)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="EriRPG Dashboard",
        version="0.0.1-alpha",
        docs_url=None,
        redoc_url=None
    )

    ui_dir = Path(__file__).parent
    app.mount("/static", StaticFiles(directory=ui_dir / "static"), name="static")
    templates = Jinja2Templates(directory=ui_dir / "templates")

    # Add custom filters
    templates.env.filters["relative_time"] = lambda ts: _format_time(ts)

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        """Dashboard home page - IDE Layout."""
        projects = get_all_projects()
        active = get_active_task()
        return templates.TemplateResponse("base.html", {
            "request": request,
            "projects": projects,
            "active": active
        })

    # ─────────────────────────────────────────────────────────────
    # Content partials (loaded into main content area via fetch)
    # ─────────────────────────────────────────────────────────────

    @app.get("/content/{project}/runs", response_class=HTMLResponse)
    async def content_runs(request: Request, project: str):
        """Runs content partial."""
        proj = get_project(project)
        if not proj:
            return "<div class='error'>Project not found</div>"

        path = proj.get("path", "")
        runs = load_runs(path)
        state = load_state(path)

        return templates.TemplateResponse("partials/content/runs.html", {
            "request": request,
            "project": proj,
            "runs": runs,
            "state": state
        })

    @app.get("/content/{project}/learnings", response_class=HTMLResponse)
    async def content_learnings(
        request: Request,
        project: str,
        page: int = Query(default=1, ge=1),
        search: str = ""
    ):
        """Learnings content partial."""
        proj = get_project(project)
        if not proj:
            return "<div class='error'>Project not found</div>"

        path = proj.get("path", "")
        knowledge = load_knowledge(path)

        learnings = []
        for file_path, data in knowledge.get("learnings", {}).items():
            if search and search.lower() not in file_path.lower():
                continue
            learnings.append({
                "path": file_path,
                "summary": data.get("summary", ""),
                "confidence": data.get("confidence", 1.0),
                "version": data.get("version", 1),
                "stale": check_staleness(path, file_path, data.get("source_ref", {})),
                "drift_pattern": data.get("drift_pattern_id"),
                "drift_confidence": data.get("drift_confidence")
            })

        learnings.sort(key=lambda x: (not x["stale"], x["path"]))

        page_size = 50
        total = len(learnings)
        start = (page - 1) * page_size
        end = start + page_size

        return templates.TemplateResponse("partials/content/learnings.html", {
            "request": request,
            "project": proj,
            "learnings": learnings[start:end],
            "total": total,
            "page": page,
            "pages": (total + page_size - 1) // page_size if total > 0 else 1,
            "search": search,
            "modules": count_modules(path)
        })

    @app.get("/content/{project}/roadmap", response_class=HTMLResponse)
    async def content_roadmap(request: Request, project: str):
        """Roadmap content partial."""
        proj = get_project(project)
        if not proj:
            return "<div class='error'>Project not found</div>"

        roadmap = load_roadmap(proj.get("path", ""))

        return templates.TemplateResponse("partials/content/roadmap.html", {
            "request": request,
            "project": proj,
            "roadmap": roadmap
        })

    @app.get("/content/{project}/decisions", response_class=HTMLResponse)
    async def content_decisions(request: Request, project: str):
        """Decisions content partial."""
        proj = get_project(project)
        if not proj:
            return "<div class='error'>Project not found</div>"

        knowledge = load_knowledge(proj.get("path", ""))
        decisions = knowledge.get("decisions", [])

        return templates.TemplateResponse("partials/content/decisions.html", {
            "request": request,
            "project": proj,
            "decisions": decisions
        })

    @app.get("/content/{project}/git", response_class=HTMLResponse)
    async def content_git(request: Request, project: str):
        """Git content partial."""
        proj = get_project(project)
        if not proj:
            return "<div class='error'>Project not found</div>"

        commits = get_git_log(proj.get("path", ""))

        return templates.TemplateResponse("partials/content/git.html", {
            "request": request,
            "project": proj,
            "commits": commits
        })

    @app.get("/content/{project}/graph", response_class=HTMLResponse)
    async def content_graph(request: Request, project: str):
        """Graph content partial."""
        proj = get_project(project)
        if not proj:
            return "<div class='error'>Project not found</div>"

        graph = load_graph(proj.get("path", ""))

        return templates.TemplateResponse("partials/content/graph.html", {
            "request": request,
            "project": proj,
            "graph": graph
        })

    @app.get("/content/{project}/drift", response_class=HTMLResponse)
    async def content_drift(request: Request, project: str):
        """Drift content partial."""
        proj = get_project(project)
        if not proj:
            return "<div class='error'>Project not found</div>"

        drift = get_drift_status(proj.get("path", ""))

        return templates.TemplateResponse("partials/content/drift.html", {
            "request": request,
            "project": proj,
            "drift": drift
        })

    @app.get("/api/status")
    async def api_status():
        """Get current status for all projects."""
        projects = get_all_projects()
        active = get_active_task()
        return {
            "active": active,
            "projects": projects,
            "timestamp": datetime.now().isoformat()
        }

    @app.get("/api/stream")
    async def api_stream(interval: float = Query(default=1.0, ge=0.5, le=10.0)):
        """Server-Sent Events stream for real-time updates."""
        from sse_starlette.sse import EventSourceResponse

        async def generate():
            last_hash = None
            while True:
                try:
                    status = {
                        "active": get_active_task(),
                        "projects": get_all_projects(),
                        "timestamp": datetime.now().isoformat()
                    }
                    status_str = json.dumps(status, sort_keys=True)
                    current_hash = hashlib.md5(status_str.encode()).hexdigest()

                    if current_hash != last_hash:
                        last_hash = current_hash
                        yield {"event": "status", "data": status_str}

                    await asyncio.sleep(interval)
                except Exception:
                    await asyncio.sleep(interval)

        return EventSourceResponse(generate())

    @app.get("/api/project/{name}")
    async def api_project(name: str):
        """Get project details."""
        project = get_project(name)
        if not project:
            return {"error": "Project not found"}

        path = project.get("path", "")
        return {
            "project": project,
            "state": load_state(path),
            "modules": count_modules(path),
            "learned": count_learned(path)
        }

    @app.get("/api/project/{name}/runs")
    async def api_runs(name: str):
        """Get project runs."""
        path = get_project_path(name)
        if not path:
            return {"error": "Project not found", "runs": [], "state": {}}

        return {
            "runs": load_runs(str(path)),
            "state": load_state(str(path))
        }

    @app.get("/api/project/{name}/learnings")
    async def api_learnings(
        name: str,
        page: int = Query(default=1, ge=1),
        limit: int = Query(default=50, ge=10, le=200),
        search: Optional[str] = None
    ):
        """Get project learnings with pagination."""
        path = get_project_path(name)
        if not path:
            return {"error": "Project not found", "learnings": [], "total": 0}

        knowledge = load_knowledge(str(path))
        learnings_data = knowledge.get("learnings", {})

        learnings = []
        for file_path, data in learnings_data.items():
            if search and search.lower() not in file_path.lower():
                continue

            is_stale = check_staleness(str(path), file_path, data.get("source_ref", {}))
            learnings.append({
                "path": file_path,
                "summary": data.get("summary", ""),
                "purpose": data.get("purpose", ""),
                "key_functions": data.get("key_functions", {}),
                "gotchas": data.get("gotchas", []),
                "confidence": data.get("confidence", 1.0),
                "version": data.get("version", 1),
                "stale": is_stale,
                "drift_pattern": data.get("drift_pattern_id"),
                "drift_confidence": data.get("drift_confidence"),
                "is_outlier": data.get("is_outlier", False)
            })

        # Sort: stale first, then by path
        learnings.sort(key=lambda x: (not x["stale"], x["path"]))

        total = len(learnings)
        start = (page - 1) * limit
        end = start + limit

        return {
            "learnings": learnings[start:end],
            "total": total,
            "page": page,
            "pages": (total + limit - 1) // limit if total > 0 else 1,
            "stale_count": sum(1 for l in learnings if l["stale"])
        }

    @app.get("/api/project/{name}/decisions")
    async def api_decisions(name: str, search: Optional[str] = None):
        """Get project decisions."""
        path = get_project_path(name)
        if not path:
            return {"error": "Project not found", "decisions": []}

        knowledge = load_knowledge(str(path))
        decisions = knowledge.get("decisions", [])

        if search:
            search_lower = search.lower()
            decisions = [
                d for d in decisions
                if search_lower in d.get("choice", "").lower()
                or search_lower in d.get("context", "").lower()
            ]

        return {"decisions": decisions}

    @app.get("/api/project/{name}/roadmap")
    async def api_roadmap(name: str):
        """Get project roadmap."""
        path = get_project_path(name)
        if not path:
            return {"error": "Project not found", "content": None}

        content = load_roadmap(str(path))
        return {"content": content}

    @app.get("/api/project/{name}/git")
    async def api_git(name: str, limit: int = Query(default=20, ge=5, le=100)):
        """Get git history."""
        path = get_project_path(name)
        if not path:
            return {"error": "Project not found", "commits": []}

        return {"commits": get_git_log(str(path), limit)}

    @app.get("/api/project/{name}/drift")
    async def api_drift(name: str):
        """Get Drift analysis status."""
        path = get_project_path(name)
        if not path:
            return {"error": "Project not found"}

        return get_drift_status(str(path))

    @app.get("/api/project/{name}/graph")
    async def api_graph(name: str):
        """Get dependency graph."""
        path = get_project_path(name)
        if not path:
            return {"error": "Project not found", "nodes": [], "edges": []}

        graph = load_graph(str(path))
        return graph

    return app


def _format_time(ts) -> str:
    """Format timestamp for templates."""
    if isinstance(ts, str):
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return dt.strftime("%H:%M:%S")
        except ValueError:
            return ts
    return str(ts)


# For running directly
app = create_app()
