from datetime import datetime, timezone, timedelta
import os
import uuid

import bcrypt
import jwt
from authlib.integrations.starlette_client import OAuth
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from backend.server import (
    app as backend_app,
    db,
    public_user,
)

# Vercel is now the authentication boundary. Google sign-in uses standard
# OpenID Connect through Authlib; no third-party auth broker is involved.
app = FastAPI(title="FitCheck Vercel API")

JWT_SECRET = os.environ.get("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = "HS256"
ACCESS_TTL_MIN = int(os.environ.get("ACCESS_TTL_MIN", "60"))
REFRESH_TTL_DAYS = int(os.environ.get("REFRESH_TTL_DAYS", "30"))
AUTH_VERSION = "2026-09-11-google-auth-v3"
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://fitcheck-org.vercel.app").rstrip("/")
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "true").lower() == "true"
COOKIE_SAMESITE = "none" if COOKIE_SECURE else "lax"

app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("AUTH_SESSION_SECRET") or JWT_SECRET,
    same_site="lax",
    https_only=COOKIE_SECURE,
)

oauth = OAuth()
oauth.register(
    name="google",
    client_id=os.environ.get("GOOGLE_CLIENT_ID", ""),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET", ""),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid email profile",
        "code_challenge_method": "S256",
    },
)


def issue_access(user_id: str, email: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "type": "access",
        "ver": AUTH_VERSION,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TTL_MIN),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def issue_refresh(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "ver": AUTH_VERSION,
        "iat": now,
        "exp": now + timedelta(days=REFRESH_TTL_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    response.set_cookie(
        "access_token", access_token, httponly=True,
        samesite=COOKIE_SAMESITE, secure=COOKIE_SECURE, path="/",
    )
    response.set_cookie(
        "refresh_token", refresh_token, httponly=True,
        samesite=COOKIE_SAMESITE, secure=COOKIE_SECURE, path="/api/auth",
    )


def clear_auth_cookies(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/api/auth")


def bearer_or_cookie(request: Request):
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip()
    return request.cookies.get("access_token")


PUBLIC_AUTH_PATHS = {
    "/api/health",
    "/api/auth/google",
    "/api/auth/google/callback",
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/refresh",
    "/api/auth/logout",
}


@app.middleware("http")
async def invalidate_previous_sessions(request: Request, call_next):
    # Every pre-migration token is rejected. This is the global login reset the
    # user requested. A new AUTH_VERSION is enough to invalidate every old JWT.
    if request.url.path.startswith("/api/") and request.url.path not in PUBLIC_AUTH_PATHS:
        token = bearer_or_cookie(request)
        if token:
            try:
                claims = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                if claims.get("type") != "access" or claims.get("ver") != AUTH_VERSION:
                    response = Response(
                        content='{"detail":"Session reset. Please sign in again."}',
                        status_code=401,
                        media_type="application/json",
                    )
                    clear_auth_cookies(response)
                    return response
            except jwt.PyJWTError:
                response = Response(
                    content='{"detail":"Session expired. Please sign in again."}',
                    status_code=401,
                    media_type="application/json",
                )
                clear_auth_cookies(response)
                return response
    return await call_next(request)


@app.get("/api/health")
async def health():
    return {"ok": True, "service": "fitcheck-api", "deployment": "vercel", "auth": "google-oidc"}


@app.get("/api/auth/google")
async def google_login(request: Request):
    if not os.environ.get("GOOGLE_CLIENT_ID") or not os.environ.get("GOOGLE_CLIENT_SECRET"):
        raise HTTPException(503, "Google authentication is not configured on this deployment.")
    redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI", "").strip()
    if not redirect_uri:
        redirect_uri = str(request.url_for("google_callback"))
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/api/auth/google/callback", name="google_callback")
async def google_callback(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
        google_user = token.get("userinfo") or await oauth.google.userinfo(token=token)
        google_sub = str(google_user.get("sub", "")).strip()
        email = str(google_user.get("email", "")).strip().lower()
        verified = google_user.get("email_verified")
        name = str(google_user.get("name", "")).strip()
        picture = google_user.get("picture")
        if not google_sub or not email or verified is False:
            raise ValueError("Google did not return a verified account")

        user = await db.users.find_one({"$or": [{"google_sub": google_sub}, {"email": email}]})
        if not user:
            user = {
                "id": str(uuid.uuid4()),
                "email": email,
                "password_hash": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "auth_provider": "google",
                "google_sub": google_sub,
                "name": name,
                "picture": picture,
                "age": None,
                "height_cm": None,
                "weight_kg": None,
                "goal": "",
                "plan": "free",
                "subscription_status": None,
                "current_period_end": None,
            }
            await db.users.insert_one(user)
        else:
            updates = {"google_sub": google_sub, "auth_provider": "google"}
            if name and not user.get("name"):
                updates["name"] = name
            if picture:
                updates["picture"] = picture
            await db.users.update_one({"id": user["id"]}, {"$set": updates})
            user = await db.users.find_one({"id": user["id"]})

        response = RedirectResponse(f"{FRONTEND_URL}/app?google=success", status_code=302)
        set_auth_cookies(response, issue_access(user["id"], user["email"]), issue_refresh(user["id"]))
        return response
    except Exception:
        return RedirectResponse(f"{FRONTEND_URL}/?google=error", status_code=302)


@app.post("/api/auth/register")
async def register(request: Request):
    body = await request.json()
    email = str(body.get("email") or "").strip().lower()
    password = str(body.get("password") or "")
    if not email or "@" not in email or len(password) < 6:
        raise HTTPException(400, "Enter a valid email and a password of at least 6 characters.")
    if await db.users.find_one({"email": email}):
        raise HTTPException(409, "An account with this email already exists. Try logging in.")

    user = {
        "id": str(uuid.uuid4()),
        "email": email,
        "password_hash": bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "auth_provider": "password",
        "name": "",
        "age": None,
        "height_cm": None,
        "weight_kg": None,
        "goal": "",
        "plan": "free",
        "subscription_status": None,
        "current_period_end": None,
    }
    await db.users.insert_one(user)
    access = issue_access(user["id"], email)
    refresh = issue_refresh(user["id"])
    response = Response(content=public_user(user) | {"access_token": access}, media_type="application/json")
    set_auth_cookies(response, access, refresh)
    return response


@app.post("/api/auth/login")
async def login(request: Request):
    body = await request.json()
    email = str(body.get("email") or "").strip().lower()
    password = str(body.get("password") or "")
    user = await db.users.find_one({"email": email})
    stored = (user or {}).get("password_hash")
    if not user or not stored or not bcrypt.checkpw(password.encode(), stored.encode()):
        raise HTTPException(401, "Invalid email or password.")
    access = issue_access(user["id"], user["email"])
    refresh = issue_refresh(user["id"])
    response = Response(content=public_user(user) | {"access_token": access}, media_type="application/json")
    set_auth_cookies(response, access, refresh)
    return response


@app.get("/api/auth/me")
async def me(request: Request):
    token = bearer_or_cookie(request)
    if not token:
        raise HTTPException(401, "Not authenticated")
    try:
        claims = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(401, "Session expired. Please sign in again.")
    if claims.get("type") != "access" or claims.get("ver") != AUTH_VERSION:
        raise HTTPException(401, "Session reset. Please sign in again.")
    user = await db.users.find_one({"id": claims.get("sub")})
    if not user:
        raise HTTPException(401, "Account not found")
    return public_user(user)


@app.post("/api/auth/refresh")
async def refresh(request: Request):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(401, "No refresh session")
    try:
        claims = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(401, "Session expired. Please sign in again.")
    if claims.get("type") != "refresh" or claims.get("ver") != AUTH_VERSION:
        raise HTTPException(401, "Session reset. Please sign in again.")
    user = await db.users.find_one({"id": claims.get("sub")})
    if not user:
        raise HTTPException(401, "Account not found")
    access = issue_access(user["id"], user["email"])
    new_refresh = issue_refresh(user["id"])
    response = Response(content='{"access_token":"' + access + '"}', media_type="application/json")
    set_auth_cookies(response, access, new_refresh)
    return response


@app.post("/api/auth/logout")
async def logout():
    response = Response(content='{"ok":true}', media_type="application/json")
    clear_auth_cookies(response)
    return response


# Everything else remains on the existing FitCheck backend.
app.mount("/", backend_app)
