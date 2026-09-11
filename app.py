from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent
FRONTEND_BUILD = ROOT / "frontend" / "build"
INDEX = FRONTEND_BUILD / "index.html"

app = FastAPI(title="FitCheck")

if (FRONTEND_BUILD / "static").exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_BUILD / "static"), name="static")

_backend = None
_backend_error = None


def load_backend():
    global _backend, _backend_error
    if _backend is not None or _backend_error is not None:
        return _backend
    try:
        from backend.clean import app as backend_app
        _backend = backend_app
    except Exception as exc:
        _backend_error = f"{type(exc).__name__}: {exc}"
        print(f"FitCheck backend import failed: {_backend_error}")
    return _backend


@app.get("/api/health")
async def health():
    backend = load_backend()
    return {
        "ok": True,
        "service": "fitcheck",
        "frontend": INDEX.exists(),
        "backend_loaded": backend is not None,
        "backend_error": _backend_error,
    }


@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def api_proxy(request: Request, path: str):
    backend = load_backend()
    if backend is None:
        return JSONResponse(
            {"detail": "FitCheck API is temporarily unavailable.", "error": _backend_error},
            status_code=503,
        )

    body = await request.body()
    query = request.url.query
    target = f"/api/{path}" + (f"?{query}" if query else "")
    headers = [(k.decode(), v.decode()) for k, v in request.headers.raw if k.lower() != b"host"]

    transport = httpx.ASGITransport(app=backend)
    async with httpx.AsyncClient(transport=transport, base_url="http://fitcheck.internal") as client:
        upstream = await client.request(request.method, target, content=body, headers=headers)

    response = Response(content=upstream.content, status_code=upstream.status_code)
    response.raw_headers = [
        (k, v)
        for k, v in upstream.headers.raw
        if k.lower() not in {b"content-length", b"transfer-encoding", b"connection"}
    ]
    return response


@app.get("/{path:path}")
async def frontend(path: str):
    if not INDEX.exists():
        return JSONResponse({"detail": "Frontend build is missing."}, status_code=503)

    requested = (FRONTEND_BUILD / path).resolve()
    try:
        requested.relative_to(FRONTEND_BUILD.resolve())
    except ValueError:
        return FileResponse(INDEX)

    if requested.is_file():
        return FileResponse(requested)
    return FileResponse(INDEX)
