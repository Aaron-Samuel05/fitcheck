from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import bcrypt
import httpx
import jwt
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field

try:
    from pymongo import MongoClient
except Exception:
    MongoClient = None

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "public"
INDEX = PUBLIC / "index.html"

JWT_SECRET = os.getenv("JWT_SECRET") or secrets.token_urlsafe(48)
JWT_ALG = "HS256"
COOKIE_NAME = "fitcheck_session"
FRONTEND_URL = os.getenv("FRONTEND_URL", "")
MONGO_URL = os.getenv("MONGO_URL", "")
DB_NAME = os.getenv("DB_NAME", "fitcheck")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
AI_MODEL = os.getenv("FITCHECK_AI_MODEL", "gemini-2.5-flash")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID", "")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "")

app = FastAPI(title="FitCheck", version="3.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL] if FRONTEND_URL else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

mongo_client = None
users = None
workouts = None

if MongoClient and MONGO_URL:
    try:
        mongo_client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=2500)
        mongo_client.admin.command("ping")
        db = mongo_client[DB_NAME]
        users = db.users
        workouts = db.workouts
        users.create_index("email", unique=True)
    except Exception as exc:
        print(f"MongoDB unavailable: {type(exc).__name__}: {exc}")
        mongo_client = None

# Small development fallback so the app can boot even before Mongo is configured.
MEM_USERS: dict[str, dict[str, Any]] = {}
MEM_WORKOUTS: dict[str, dict[str, Any]] = {}


def now() -> datetime:
    return datetime.now(timezone.utc)


def public_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(user["_id"]),
        "name": user.get("name", "Athlete"),
        "email": user.get("email", ""),
        "plan": user.get("plan", "free"),
        "createdAt": user.get("created_at", now()).isoformat(),
    }


def make_id(prefix: str = "") -> str:
    return prefix + secrets.token_urlsafe(16)


def token_for(user: dict[str, Any]) -> str:
    return jwt.encode(
        {"sub": str(user["_id"]), "email": user["email"], "exp": now() + timedelta(days=14)},
        JWT_SECRET,
        algorithm=JWT_ALG,
    )


def cookie_kwargs() -> dict[str, Any]:
    return {
        "key": COOKIE_NAME,
        "httponly": True,
        "secure": os.getenv("COOKIE_SECURE", "true").lower() == "true",
        "samesite": "none" if os.getenv("COOKIE_SECURE", "true").lower() == "true" else "lax",
        "path": "/",
        "max_age": 60 * 60 * 24 * 14,
    }


def find_user_by_email(email: str) -> dict[str, Any] | None:
    email = email.lower().strip()
    if users is not None:
        return users.find_one({"email": email})
    return MEM_USERS.get(email)


def find_user_by_id(user_id: str) -> dict[str, Any] | None:
    if users is not None:
        from bson import ObjectId
        try:
            return users.find_one({"_id": ObjectId(user_id)})
        except Exception:
            return None
    return next((u for u in MEM_USERS.values() if str(u["_id"]) == user_id), None)


def current_user(request: Request) -> dict[str, Any]:
    raw = request.cookies.get(COOKIE_NAME)
    if not raw:
        raise HTTPException(status_code=401, detail="Sign in to continue.")
    try:
        payload = jwt.decode(raw, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Your session expired. Please sign in again.")
    user = find_user_by_id(str(payload.get("sub", "")))
    if not user:
        raise HTTPException(status_code=401, detail="Account not found.")
    return user


class AuthBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(default="", max_length=80)


class WorkoutBody(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    duration: int = Field(default=45, ge=1, le=600)
    exercises: list[dict[str, Any]] = Field(default_factory=list)
    notes: str = Field(default="", max_length=2000)


class AIBody(BaseModel):
    message: str = Field(min_length=1, max_length=3000)


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {"ok": True, "service": "fitcheck", "version": "3.0.0", "database": "mongodb" if users is not None else "memory"}


@app.post("/api/auth/register")
async def register(body: AuthBody):
    email = body.email.lower().strip()
    if find_user_by_email(email):
        raise HTTPException(status_code=409, detail="An account with that email already exists.")
    user = {
        "_id": make_id("usr_"),
        "name": body.name.strip() or email.split("@")[0].title(),
        "email": email,
        "password_hash": bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode(),
        "plan": "free",
        "created_at": now(),
    }
    if users is not None:
        try:
            result = users.insert_one(user)
            user["_id"] = result.inserted_id
        except Exception as exc:
            if "duplicate" in str(exc).lower():
                raise HTTPException(status_code=409, detail="An account with that email already exists.")
            raise HTTPException(status_code=500, detail="Could not create the account.")
    else:
        MEM_USERS[email] = user
    response = JSONResponse({"user": public_user(user)})
    response.set_cookie(value=token_for(user), **cookie_kwargs())
    return response


@app.post("/api/auth/login")
async def login(body: AuthBody):
    user = find_user_by_email(body.email)
    if not user or not bcrypt.checkpw(body.password.encode(), user.get("password_hash", "").encode()):
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    response = JSONResponse({"user": public_user(user)})
    response.set_cookie(value=token_for(user), **cookie_kwargs())
    return response


@app.post("/api/auth/logout")
async def logout():
    response = JSONResponse({"ok": True})
    response.delete_cookie(COOKIE_NAME, path="/")
    return response


@app.get("/api/auth/me")
async def me(request: Request):
    return {"user": public_user(current_user(request))}


@app.get("/api/auth/google/login")
async def google_login():
    if not (GOOGLE_CLIENT_ID and GOOGLE_REDIRECT_URI):
        raise HTTPException(status_code=503, detail="Google sign-in is not configured yet.")
    from urllib.parse import urlencode
    state = secrets.token_urlsafe(24)
    query = urlencode({
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    })
    response = RedirectResponse("https://accounts.google.com/o/oauth2/v2/auth?" + query)
    response.set_cookie("fitcheck_oauth_state", state, httponly=True, secure=cookie_kwargs()["secure"], samesite=cookie_kwargs()["samesite"], path="/", max_age=600)
    return response


@app.get("/api/auth/google/callback")
async def google_callback(request: Request, code: str = "", state: str = ""):
    expected = request.cookies.get("fitcheck_oauth_state")
    if not code or not state or not expected or not hmac.compare_digest(state, expected):
        raise HTTPException(status_code=400, detail="Google sign-in could not be verified.")
    if not (GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET and GOOGLE_REDIRECT_URI):
        raise HTTPException(status_code=503, detail="Google sign-in is not configured yet.")
    async with httpx.AsyncClient(timeout=15) as client:
        token_res = await client.post("https://oauth2.googleapis.com/token", data={
            "code": code, "client_id": GOOGLE_CLIENT_ID, "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": GOOGLE_REDIRECT_URI, "grant_type": "authorization_code",
        })
        if token_res.status_code >= 400:
            raise HTTPException(status_code=400, detail="Google authorization failed.")
        access_token = token_res.json().get("access_token")
        profile_res = await client.get("https://openidconnect.googleapis.com/v1/userinfo", headers={"Authorization": f"Bearer {access_token}"})
        if profile_res.status_code >= 400:
            raise HTTPException(status_code=400, detail="Could not read your Google profile.")
    profile = profile_res.json()
    email = str(profile.get("email", "")).lower().strip()
    if not email:
        raise HTTPException(status_code=400, detail="Google did not provide an email address.")
    user = find_user_by_email(email)
    if not user:
        user = {"_id": make_id("usr_"), "name": profile.get("name") or email.split("@")[0].title(), "email": email, "password_hash": bcrypt.hashpw(secrets.token_urlsafe(32).encode(), bcrypt.gensalt()).decode(), "plan": "free", "created_at": now()}
        if users is not None:
            result = users.insert_one(user)
            user["_id"] = result.inserted_id
        else:
            MEM_USERS[email] = user
    target = FRONTEND_URL or "/"
    response = RedirectResponse(target + ("&" if "?" in target else "?") + "google=success")
    response.set_cookie(value=token_for(user), **cookie_kwargs())
    response.delete_cookie("fitcheck_oauth_state", path="/")
    return response


@app.get("/api/workouts")
async def list_workouts(request: Request):
    user = current_user(request)
    uid = str(user["_id"])
    if workouts is not None:
        docs = list(workouts.find({"user_id": uid}).sort("created_at", -1).limit(100))
    else:
        docs = sorted([w for w in MEM_WORKOUTS.values() if w["user_id"] == uid], key=lambda x: x["created_at"], reverse=True)[:100]
    for d in docs:
        d["id"] = str(d.pop("_id", d.get("id", "")))
        d["createdAt"] = d.pop("created_at", now()).isoformat()
        d.pop("user_id", None)
    return {"workouts": docs}


@app.post("/api/workouts")
async def create_workout(body: WorkoutBody, request: Request):
    user = current_user(request)
    doc = {"_id": make_id("wo_"), "user_id": str(user["_id"]), "title": body.title.strip(), "duration": body.duration, "exercises": body.exercises, "notes": body.notes.strip(), "created_at": now()}
    if workouts is not None:
        result = workouts.insert_one(doc)
        doc["_id"] = result.inserted_id
    else:
        MEM_WORKOUTS[doc["_id"]] = doc
    return {"workout": {"id": str(doc["_id"]), "title": doc["title"], "duration": doc["duration"], "exercises": doc["exercises"], "notes": doc["notes"], "createdAt": doc["created_at"].isoformat()}}


@app.delete("/api/workouts/{workout_id}")
async def delete_workout(workout_id: str, request: Request):
    user = current_user(request)
    uid = str(user["_id"])
    if workouts is not None:
        result = workouts.delete_one({"_id": workout_id, "user_id": uid})
        if result.deleted_count == 0:
            from bson import ObjectId
            try:
                result = workouts.delete_one({"_id": ObjectId(workout_id), "user_id": uid})
            except Exception:
                pass
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Workout not found.")
    else:
        if workout_id not in MEM_WORKOUTS or MEM_WORKOUTS[workout_id]["user_id"] != uid:
            raise HTTPException(status_code=404, detail="Workout not found.")
        del MEM_WORKOUTS[workout_id]
    return {"ok": True}


@app.post("/api/ai/buddy")
async def ai_buddy(body: AIBody, request: Request):
    user = current_user(request)
    if user.get("plan", "free") != "pro":
        raise HTTPException(status_code=402, detail="AI Buddy is a Pro feature.")
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="AI Buddy is not configured yet.")
    prompt = f"You are FitCheck AI Buddy, a concise but motivating fitness coach. User: {user.get('name','Athlete')}. Answer safely and practically. Never diagnose injuries or prescribe medication. User message: {body.message}"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{AI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.7, "maxOutputTokens": 700}}
    async with httpx.AsyncClient(timeout=25) as client:
        result = await client.post(url, json=payload)
    if result.status_code >= 400:
        print("Gemini error", result.status_code, result.text[:500])
        raise HTTPException(status_code=502, detail="AI Buddy could not answer right now.")
    data = result.json()
    text = "".join(p.get("text", "") for p in data.get("candidates", [{}])[0].get("content", {}).get("parts", []))
    return {"reply": text or "Let's get back to work. Tell me what you're training today."}


@app.post("/api/billing/checkout")
async def billing_checkout(request: Request):
    user = current_user(request)
    if user.get("plan") == "pro":
        return {"alreadyPro": True}
    if not STRIPE_SECRET_KEY or not STRIPE_PRICE_ID:
        raise HTTPException(status_code=503, detail="Billing is not configured yet.")
    try:
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY
        session = stripe.checkout.Session.create(
            mode="subscription", line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
            success_url=(FRONTEND_URL or str(request.base_url).rstrip("/")) + "/?checkout=success",
            cancel_url=(FRONTEND_URL or str(request.base_url).rstrip("/")) + "/?checkout=cancelled",
            customer_email=user.get("email"), metadata={"user_id": str(user["_id"])},
        )
        return {"url": session.url}
    except Exception as exc:
        print("Stripe error", exc)
        raise HTTPException(status_code=502, detail="Could not start checkout.")


@app.get("/{path:path}")
async def frontend(path: str):
    if not INDEX.exists():
        return JSONResponse({"detail": "FitCheck frontend is missing."}, status_code=503)
    requested = (PUBLIC / path).resolve()
    try:
        requested.relative_to(PUBLIC.resolve())
    except ValueError:
        return FileResponse(INDEX)
    if requested.is_file():
        return FileResponse(requested)
    return FileResponse(INDEX)
