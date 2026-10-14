"""Public deployment: the web app and the API from one address (sandbox only; no real money moves).

    uvicorn app.web:site --host 0.0.0.0 --port 8000 --proxy-headers

* The API is mounted under /api (the app's own routes, such as /emergency, would clash with API paths otherwise).
* The Expo web build (mobile/dist, or SATHI_WEB_DIR) is served for every other path; unknown paths get index.html
  so links into the app work. Only files inside the build folder are ever served.
* Rate limits per address, because anyone can open a public demo and the AI calls cost money:
  AI-backed writes (chat, documents, mandate proposals, inbox) 20 per 10 minutes, other writes 120 per 10 minutes.
  The DeepSeek client also has a daily budget (SATHI_LLM_DAILY_CALLS); past it the agent answers with its rules.
"""
from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse

DEFAULT_WEB_DIR = Path(__file__).resolve().parents[2] / "mobile" / "dist"
AI_PATHS = ("/api/agent/chat", "/api/documents", "/api/mandates/proposals", "/api/inbox")
LIMITS = {"ai": (20, 600.0), "write": (120, 600.0)}  # (requests, seconds) per address


def client_address(request: Request) -> str:
    # Behind the host's proxy the last X-Forwarded-For entry is the one the proxy added (earlier ones can be forged).
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[-1].strip()
    return request.client.host if request.client else "?"


def create_site(api: FastAPI | None = None, web_dir: Path | None = None, limits: dict | None = None) -> FastAPI:
    if api is None:
        from app.main import app as api
    root = (web_dir or Path(os.environ.get("SATHI_WEB_DIR", DEFAULT_WEB_DIR))).resolve()
    limits = limits or LIMITS
    hits: dict[tuple[str, str], deque] = defaultdict(deque)
    site = FastAPI(title="Sathi", docs_url=None, redoc_url=None, openapi_url=None)

    @site.middleware("http")
    async def rate_limit(request: Request, call_next):
        if request.method == "POST" and request.url.path.startswith("/api/"):
            kind = "ai" if request.url.path.startswith(AI_PATHS) else "write"
            n, window = limits[kind]
            if len(hits) > 20000:
                hits.clear()  # bounded memory under a flood of addresses
            q, now = hits[(client_address(request), kind)], time.monotonic()
            while q and now - q[0] > window:
                q.popleft()
            if len(q) >= n:
                return JSONResponse({"detail": "Too many requests from this address. Please try again in a few minutes."},
                                    status_code=429, headers={"Retry-After": str(int(window))})
            q.append(now)
        return await call_next(request)

    site.mount("/api", api)

    @site.get("/{path:path}", include_in_schema=False)
    def web_app(path: str):
        for candidate in (root / path, root / f"{path}.html", root / path / "index.html"):
            try:
                c = candidate.resolve()
            except (OSError, ValueError):
                continue
            if c.is_file() and c.is_relative_to(root):
                return FileResponse(c)
        index = root / "index.html"
        if index.is_file():
            return FileResponse(index)
        return JSONResponse({"detail": "The web app is not built. Run: npx expo export --platform web"}, status_code=404)

    return site


site = create_site()
