from pathlib import Path

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
    return {"ok": True, "service": "fitcheck", "frontend": INDEX.exists(), "backend_loaded": backend is not None, "backend_error": BACKEND_ERROR}


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
