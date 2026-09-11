from pathlib import Path
import os

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "frontend" / "build" / "index.html"
BACKEND = None
BACKEND_ERROR = None

app = FastAPI(title="FitCheck")


def get_backend():
    global BACKEND, BACKEND_ERROR
    if BACKEND is not None or BACKEND_ERROR is not None:
        return BACKEND
    try:
        from backend.clean import app as backend_app
        BACKEND = backend_app
    except Exception as exc:
        BACKEND_ERROR = f"{type(exc).__name__}: {exc}"
        print("FitCheck backend import failed:", BACKEND_ERROR)
    return BACKEND


@app.get("/api/health")
async def health():
    backend = get_backend()
    required = {
        "MONGO_URL": bool(os.environ.get("MONGO_URL", "").strip()),
        "JWT_SECRET": bool(os.environ.get("JWT_SECRET", "").strip()),
        "AUTH_SESSION_SECRET": bool(os.environ.get("AUTH_SESSION_SECRET", "").strip()),
        "GOOGLE_CLIENT_ID": bool(os.environ.get("GOOGLE_CLIENT_ID", "").strip()),
        "GOOGLE_CLIENT_SECRET": bool(os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()),
        "GOOGLE_REDIRECT_URI": bool(os.environ.get("GOOGLE_REDIRECT_URI", "").strip()),
        "GEMINI_API_KEY": bool(os.environ.get("GEMINI_API_KEY", "").strip()),
    }
    return {
        "ok": backend is not None and INDEX.exists(),
        "service": "fitcheck",
        "frontend": INDEX.exists(),
        "backend_loaded": backend is not None,
        "backend_error": BACKEND_ERROR,
        "database": "mongodb" if required["MONGO_URL"] else "NOT_CONFIGURED",
        "google": "configured" if required["GOOGLE_CLIENT_ID"] and required["GOOGLE_CLIENT_SECRET"] and required["GOOGLE_REDIRECT_URI"] else "NOT_CONFIGURED",
        "ai": "gemini" if required["GEMINI_API_KEY"] else "NOT_CONFIGURED",
        "missing_environment": [name for name, present in required.items() if not present],
        "frontend_url": os.environ.get("FRONTEND_URL", "https://fitcheck-org.vercel.app").rstrip("/"),
        "ai_model": os.environ.get("FITCHECK_AI_MODEL", "gemini-2.5-flash"),
    }


@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def api_proxy(request: Request, path: str):
    backend = get_backend()
    if backend is None:
        return JSONResponse({"detail": "FitCheck API is temporarily unavailable.", "error": BACKEND_ERROR}, status_code=503)
    body = await request.body()
    target = f"/api/{path}" + (f"?{request.url.query}" if request.url.query else "")
    headers = [(k.decode(), v.decode()) for k, v in request.headers.raw if k.lower() != b"host"]
    transport = httpx.ASGITransport(app=backend)
    async with httpx.AsyncClient(transport=transport, base_url="http://fitcheck.internal") as client:
        upstream = await client.request(request.method, target, content=body, headers=headers)
    response = Response(content=upstream.content, status_code=upstream.status_code)
    response.raw_headers = [(k, v) for k, v in upstream.headers.raw if k.lower() not in {b"content-length", b"transfer-encoding", b"connection"}]
    return response


@app.get("/{path:path}")
async def frontend(path: str):
    if not INDEX.exists():
        return JSONResponse({"detail": "FitCheck frontend build is missing."}, status_code=503)
    public_root = (ROOT / "frontend" / "build").resolve()
    requested = (public_root / path).resolve()
    try:
        requested.relative_to(public_root)
    except ValueError:
        return FileResponse(INDEX)
    return FileResponse(requested) if requested.is_file() else FileResponse(INDEX)
