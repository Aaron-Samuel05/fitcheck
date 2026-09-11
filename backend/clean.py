from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List
import logging
import os
import uuid

import bcrypt
import httpx
import jwt
import pymongo
import stripe
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

JWT_ALGORITHM = "HS256"
AUTH_VERSION = "2026-09-11-fresh-v1"
ACCESS_TTL_MIN = int(os.environ.get("ACCESS_TTL_MIN", "60"))
REFRESH_TTL_DAYS = int(os.environ.get("REFRESH_TTL_DAYS", "30"))
FREE_AI_DAILY_LIMIT = int(os.environ.get("FREE_AI_DAILY_LIMIT", "5"))
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://fitcheck-org.vercel.app").rstrip("/")
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "true").lower() == "true"
COOKIE_SAMESITE = "none" if COOKIE_SECURE else "lax"

mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
db_name = os.environ.get("DB_NAME", "fitcheck")
try:
    sync_client = pymongo.MongoClient(mongo_url, serverSelectionTimeoutMS=1500)
    sync_client.admin.command("ping")
    sync_client.close()
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
except Exception as exc:
    logging.warning("MongoDB unavailable; using in-memory database: %s", exc)
    from mongomock_motor import AsyncMongoMockClient
    client = AsyncMongoMockClient()
    db = client[db_name]

app = FastAPI(title="FitCheck API")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("AUTH_SESSION_SECRET", os.environ.get("JWT_SECRET", "dev-only-change-me")),
    same_site="lax",
    https_only=COOKIE_SECURE,
)

cors_origins = [x.strip() for x in os.environ.get("CORS_ORIGINS", f"http://localhost:3000,{FRONTEND_URL}").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

oauth = OAuth()
oauth.register(
    name="google",
    client_id=os.environ.get("GOOGLE_CLIENT_ID", ""),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET", ""),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile", "code_challenge_method": "S256"},
)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ProfileUpdateRequest(BaseModel):
    name: str = Field(default="", max_length=80)
    age: Optional[int] = Field(default=None, ge=13, le=100)
    height_cm: Optional[float] = Field(default=None, ge=100, le=250)
    weight_kg: Optional[float] = Field(default=None, ge=25, le=300)
    goal: str = Field(default="", max_length=120)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: Optional[str] = None


class CheckoutRequest(BaseModel):
    plan_id: str = Field(min_length=1, max_length=80)


class SetExercise(BaseModel):
    reps: int = Field(ge=0, le=1000)
    weight: float = Field(ge=0, le=100000)


class Exercise(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    sets: List[SetExercise] = Field(default_factory=list, max_length=50)


class WorkoutCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    exercises: List[Exercise] = Field(default_factory=list, max_length=50)
    date: Optional[str] = None
    notes: Optional[str] = Field(default=None, max_length=1000)


class PlanDay(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    exercises: List[str] = Field(default_factory=list, max_length=50)


class PlanCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    goal: Optional[str] = Field(default=None, max_length=120)
    days: List[PlanDay] = Field(default_factory=list, max_length=14)


def secret() -> str:
    value = os.environ.get("JWT_SECRET", "").strip()
    if not value:
        raise HTTPException(503, "Authentication is not configured. Add JWT_SECRET to the deployment environment.")
    return value


def issue_access(user_id: str, email: str) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": user_id, "email": email, "type": "access", "ver": AUTH_VERSION, "iat": now, "exp": now + timedelta(minutes=ACCESS_TTL_MIN)}, secret(), algorithm=JWT_ALGORITHM)


def issue_refresh(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": user_id, "type": "refresh", "ver": AUTH_VERSION, "iat": now, "exp": now + timedelta(days=REFRESH_TTL_DAYS)}, secret(), algorithm=JWT_ALGORITHM)


def public_user(user: dict) -> dict:
    return {
        "id": user["id"],
        "email": user["email"],
        "profile": {"name": user.get("name", ""), "age": user.get("age"), "height_cm": user.get("height_cm"), "weight_kg": user.get("weight_kg"), "goal": user.get("goal", "")},
        "plan": user.get("plan", "free"),
        "subscription_status": user.get("subscription_status"),
        "current_period_end": user.get("current_period_end"),
    }


def paid(user: dict) -> bool:
    return user.get("plan", "free") == "buddy_pro" and user.get("subscription_status") in ("active", "trialing")


def set_cookies(response: Response, access: str, refresh: str) -> None:
    response.set_cookie("access_token", access, httponly=True, secure=COOKIE_SECURE, samesite=COOKIE_SAMESITE, path="/")
    response.set_cookie("refresh_token", refresh, httponly=True, secure=COOKIE_SECURE, samesite=COOKIE_SAMESITE, path="/api/auth")


def clear_cookies(response: Response) -> None:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/api/auth")


def bearer_or_cookie(request: Request) -> Optional[str]:
    header = request.headers.get("Authorization", "")
    return header[7:].strip() if header.startswith("Bearer ") else request.cookies.get("access_token")


async def current_user(request: Request) -> dict:
    token = bearer_or_cookie(request)
    if not token:
        raise HTTPException(401, "Not authenticated")
    try:
        claims = jwt.decode(token, secret(), algorithms=[JWT_ALGORITHM])
    except Exception:
        raise HTTPException(401, "Session expired. Please sign in again.")
    if claims.get("type") != "access" or claims.get("ver") != AUTH_VERSION:
        raise HTTPException(401, "Session reset. Please sign in again.")
    user = await db.users.find_one({"id": claims.get("sub")})
    if not user or user.get("auth_generation") != AUTH_VERSION:
        raise HTTPException(401, "Account reset. Please create a new account.")
    return user


@app.middleware("http")
async def reject_old_sessions(request: Request, call_next):
    if request.url.path.startswith("/api/") and not request.url.path.startswith("/api/auth/"):
        token = bearer_or_cookie(request)
        if token:
            try:
                claims = jwt.decode(token, secret(), algorithms=[JWT_ALGORITHM])
                if claims.get("type") != "access" or claims.get("ver") != AUTH_VERSION:
                    response = JSONResponse({"detail": "Session reset. Please sign in again."}, status_code=401)
                    clear_cookies(response)
                    return response
            except Exception:
                response = JSONResponse({"detail": "Session expired. Please sign in again."}, status_code=401)
                clear_cookies(response)
                return response
    return await call_next(request)


@app.get("/api/health")
async def health():
    return {"ok": True, "service": "fitcheck-api", "auth": "google-oidc", "ai": "gemini", "version": AUTH_VERSION}


@app.get("/api/auth/google")
async def google_login(request: Request):
    if not os.environ.get("GOOGLE_CLIENT_ID") or not os.environ.get("GOOGLE_CLIENT_SECRET"):
        raise HTTPException(503, "Google authentication is not configured. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.")
    redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI", "").strip() or str(request.url_for("google_callback"))
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/api/auth/google/callback", name="google_callback")
async def google_callback(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
        info = token.get("userinfo") or await oauth.google.userinfo(token=token)
        google_sub = str(info.get("sub", "")).strip()
        email = str(info.get("email", "")).strip().lower()
        if not google_sub or not email or info.get("email_verified") is False:
            raise ValueError("Unverified Google account")

        old = await db.users.find_one({"$or": [{"google_sub": google_sub}, {"email": email}]})
        if old and old.get("auth_generation") != AUTH_VERSION:
            await db.users.delete_one({"id": old["id"]})
            old = None
        if not old:
            old = {
                "id": str(uuid.uuid4()), "email": email, "password_hash": None,
                "created_at": datetime.now(timezone.utc).isoformat(), "auth_provider": "google",
                "google_sub": google_sub, "auth_generation": AUTH_VERSION,
                "name": str(info.get("name", "")).strip(), "picture": info.get("picture"),
                "age": None, "height_cm": None, "weight_kg": None, "goal": "",
                "plan": "free", "subscription_status": None, "current_period_end": None,
            }
            await db.users.insert_one(old)
        else:
            await db.users.update_one({"id": old["id"]}, {"$set": {"google_sub": google_sub, "auth_provider": "google", "auth_generation": AUTH_VERSION, "picture": info.get("picture")}})
            old = await db.users.find_one({"id": old["id"]})

        response = RedirectResponse(f"{FRONTEND_URL}/app?google=success", status_code=302)
        set_cookies(response, issue_access(old["id"], email), issue_refresh(old["id"]))
        return response
    except Exception:
        logging.exception("Google authentication failed")
        return RedirectResponse(f"{FRONTEND_URL}/?google=error", status_code=302)


@app.post("/api/auth/register")
async def register(body: RegisterRequest, response: Response):
    email = body.email.lower()
    old = await db.users.find_one({"email": email})
    if old and old.get("auth_generation") != AUTH_VERSION:
        await db.users.delete_one({"id": old["id"]})
        old = None
    if old:
        raise HTTPException(409, "An account with this email already exists. Try logging in.")
    user = {
        "id": str(uuid.uuid4()), "email": email, "password_hash": bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode(),
        "created_at": datetime.now(timezone.utc).isoformat(), "auth_provider": "password", "auth_generation": AUTH_VERSION,
        "name": "", "age": None, "height_cm": None, "weight_kg": None, "goal": "",
        "plan": "free", "subscription_status": None, "current_period_end": None,
    }
    await db.users.insert_one(user)
    access, refresh = issue_access(user["id"], email), issue_refresh(user["id"])
    set_cookies(response, access, refresh)
    return public_user(user) | {"access_token": access}


@app.post("/api/auth/login")
async def login(body: LoginRequest, response: Response):
    email = body.email.lower()
    user = await db.users.find_one({"email": email})
    if user and user.get("auth_generation") != AUTH_VERSION:
        await db.users.delete_one({"id": user["id"]})
        user = None
    if not user or not user.get("password_hash") or not bcrypt.checkpw(body.password.encode(), user["password_hash"].encode()):
        raise HTTPException(401, "Invalid email or password. If this is an old account, create it again.")
    access, refresh = issue_access(user["id"], email), issue_refresh(user["id"])
    set_cookies(response, access, refresh)
    return public_user(user) | {"access_token": access}


@app.get("/api/auth/me")
async def me(request: Request):
    return public_user(await current_user(request))


@app.post("/api/auth/refresh")
async def refresh(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(401, "No refresh session")
    try:
        claims = jwt.decode(token, secret(), algorithms=[JWT_ALGORITHM])
    except Exception:
        raise HTTPException(401, "Session expired. Please sign in again.")
    if claims.get("type") != "refresh" or claims.get("ver") != AUTH_VERSION:
        raise HTTPException(401, "Session reset. Please sign in again.")
    user = await db.users.find_one({"id": claims.get("sub"), "auth_generation": AUTH_VERSION})
    if not user:
        raise HTTPException(401, "Account reset. Please create a new account.")
    access, new_refresh = issue_access(user["id"], user["email"]), issue_refresh(user["id"])
    set_cookies(response, access, new_refresh)
    return {"ok": True, "access_token": access}


@app.post("/api/auth/logout")
async def logout(response: Response):
    clear_cookies(response)
    return {"ok": True}


@app.get("/api/profile")
async def get_profile(user=Depends(current_user)):
    return public_user(user)


@app.patch("/api/profile")
async def update_profile(body: ProfileUpdateRequest, user=Depends(current_user)):
    values = body.model_dump()
    values["name"] = values["name"].strip()
    values["goal"] = values["goal"].strip()
    await db.users.update_one({"id": user["id"]}, {"$set": values})
    return public_user(await db.users.find_one({"id": user["id"]}))


AI_SYSTEM_PROMPT = """You are FitCheck Coach, a knowledgeable and encouraging fitness coach. Give practical, concise advice about training, exercise selection, recovery, nutrition, progressive overload, cardio, and healthy habits. Use the user's profile and conversation context. Do not diagnose medical conditions. For injuries, serious symptoms, eating disorders, or medical concerns, recommend professional care. Never claim to perform actions you did not perform."""


async def daily_ai_usage(user_id: str) -> int:
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    return await db.chat_messages.count_documents({"user_id": user_id, "role": "user", "created_at": {"$gte": start}})


async def generate_ai_reply(session_id: str, message: str, user_id: str) -> str:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(503, "AI Buddy is not configured. Add GEMINI_API_KEY to the backend environment and redeploy.")
    user = await db.users.find_one({"id": user_id})
    profile = user.get("profile", {}) if user else {}
    profile = {"name": user.get("name", ""), "age": user.get("age"), "height_cm": user.get("height_cm"), "weight_kg": user.get("weight_kg"), "goal": user.get("goal", "")} if user else {}
    profile_text = ", ".join(f"{k}: {v}" for k, v in profile.items() if v not in (None, "")) or "No profile details provided"
    previous = await db.chat_messages.find({"user_id": user_id, "session_id": session_id}).sort("created_at", -1).to_list(12)
    previous.reverse()
    context = "\n".join(f"{m.get('role', 'user').upper()}: {m.get('message', '')}" for m in previous)
    prompt = f"User profile: {profile_text}\n\nConversation so far:\n{context}\n\nUSER: {message}\n\nReply as FitCheck Coach."
    model = os.environ.get("FITCHECK_AI_MODEL", "gemini-2.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {"system_instruction": {"parts": [{"text": AI_SYSTEM_PROMPT}]}, "contents": [{"role": "user", "parts": [{"text": prompt}]}]}
    try:
        async with httpx.AsyncClient(timeout=45) as client_http:
            result = await client_http.post(url, headers={"x-goog-api-key": api_key, "Content-Type": "application/json"}, json=payload)
            result.raise_for_status()
            data = result.json()
        reply = "".join(p.get("text", "") for p in data.get("candidates", [{}])[0].get("content", {}).get("parts", [])).strip()
        if not reply:
            raise RuntimeError("Empty Gemini response")
        return reply
    except HTTPException:
        raise
    except Exception:
        logging.exception("Gemini AI request failed")
        raise HTTPException(502, "AI Buddy is temporarily unavailable. Please try again.")


@app.get("/api/ai/status")
async def ai_status(user=Depends(current_user)):
    return {"configured": bool(os.environ.get("GEMINI_API_KEY", "").strip()), "model": os.environ.get("FITCHECK_AI_MODEL", "gemini-2.5-flash"), "plan": user.get("plan", "free"), "paid": paid(user), "daily_limit": None if paid(user) else FREE_AI_DAILY_LIMIT, "daily_used": await daily_ai_usage(user["id"])}


@app.post("/api/ai/chat")
async def ai_chat(body: ChatRequest, user=Depends(current_user)):
    if not paid(user) and await daily_ai_usage(user["id"]) >= FREE_AI_DAILY_LIMIT:
        raise HTTPException(402, "You have reached today's free AI Buddy limit. Upgrade to AI Buddy Pro for unlimited coaching.")
    session_id = body.session_id or str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    await db.chat_messages.insert_one({"id": str(uuid.uuid4()), "user_id": user["id"], "session_id": session_id, "role": "user", "message": body.message, "created_at": now})
    try:
        reply = await generate_ai_reply(session_id, body.message, user["id"])
    except HTTPException:
        await db.chat_messages.delete_one({"user_id": user["id"], "session_id": session_id, "role": "user", "created_at": now})
        raise
    await db.chat_messages.insert_one({"id": str(uuid.uuid4()), "user_id": user["id"], "session_id": session_id, "role": "assistant", "message": reply, "created_at": datetime.now(timezone.utc).isoformat()})
    return {"session_id": session_id, "reply": reply}


@app.get("/api/ai/history")
async def ai_history(session_id: Optional[str] = None, user=Depends(current_user)):
    query = {"user_id": user["id"]}
    if session_id:
        query["session_id"] = session_id
    cursor = db.chat_messages.find(query).sort("created_at", 1)
    messages = []
    async for doc in cursor:
        messages.append({"role": doc["role"], "message": doc["message"]})
    return {"messages": messages}


BILLING_PLANS = {
    "buddy_pro_monthly": {"name": "AI Buddy Pro", "price_label": "$9.99 / month", "price_env": "STRIPE_PRICE_BUDDY_PRO_MONTHLY"},
    "buddy_pro_yearly": {"name": "AI Buddy Pro", "price_label": "$79.99 / year", "price_env": "STRIPE_PRICE_BUDDY_PRO_YEARLY"},
}


@app.get("/api/billing/plans")
async def billing_plans():
    return {"plans": [{"id": "free", "name": "FitCheck Free", "price": "$0", "period": "forever", "features": ["Unlimited workout logging", "Progress & volume tracking", "Training programs", "Streaks & weekly trends"]}, {"id": "buddy_pro_monthly", "name": "AI Buddy Pro", "price": "$9.99", "period": "month", "features": ["Everything in Free", "Unlimited AI coaching", "Personalized training guidance", "Profile-aware coaching"]}, {"id": "buddy_pro_yearly", "name": "AI Buddy Pro", "price": "$79.99", "period": "year", "features": ["Everything in Free", "Unlimited AI coaching", "Best value", "Profile-aware coaching"]}]}


@app.get("/api/billing/status")
async def billing_status(user=Depends(current_user)):
    return {"plan": user.get("plan", "free"), "subscription_status": user.get("subscription_status"), "current_period_end": user.get("current_period_end"), "paid": paid(user)}


@app.post("/api/billing/checkout")
async def billing_checkout(body: CheckoutRequest, request: Request, user=Depends(current_user)):
    if not os.environ.get("STRIPE_SECRET_KEY", "").strip():
        raise HTTPException(503, "Billing is not configured. Add STRIPE_SECRET_KEY and Stripe Price IDs to the backend environment.")
    if paid(user):
        raise HTTPException(409, "AI Buddy Pro is already active on this account.")
    plan = BILLING_PLANS.get(body.plan_id)
    if not plan:
        raise HTTPException(400, "Unknown billing plan")
    price_id = os.environ.get(plan["price_env"], "").strip()
    if not price_id:
        raise HTTPException(503, "This billing plan is not configured yet.")
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
    frontend_url = os.environ.get("FRONTEND_URL", str(request.base_url).rstrip("/"))
    try:
        customer_id = user.get("stripe_customer_id")
        if not customer_id:
            customer = stripe.Customer.create(email=user["email"], metadata={"fitcheck_user_id": user["id"]})
            customer_id = customer.id
            await db.users.update_one({"id": user["id"]}, {"$set": {"stripe_customer_id": customer_id}})
        session = stripe.checkout.Session.create(mode="subscription", customer=customer_id, line_items=[{"price": price_id, "quantity": 1}], success_url=f"{frontend_url}/app?billing=success", cancel_url=f"{frontend_url}/app?billing=cancelled", client_reference_id=user["id"], metadata={"fitcheck_user_id": user["id"], "plan_id": body.plan_id}, subscription_data={"metadata": {"fitcheck_user_id": user["id"], "plan_id": body.plan_id}})
        return {"url": session.url, "session_id": session.id}
    except Exception:
        logging.exception("Stripe checkout creation failed")
        raise HTTPException(502, "Unable to start checkout right now. Please try again.")


@app.post("/api/billing/portal")
async def billing_portal(request: Request, user=Depends(current_user)):
    if not os.environ.get("STRIPE_SECRET_KEY", "").strip() or not user.get("stripe_customer_id"):
        raise HTTPException(400, "No billing account is connected to this user yet.")
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
    frontend_url = os.environ.get("FRONTEND_URL", str(request.base_url).rstrip("/"))
    try:
        portal = stripe.billing_portal.Session.create(customer=user["stripe_customer_id"], return_url=f"{frontend_url}/app")
        return {"url": portal.url}
    except Exception:
        logging.exception("Stripe portal failed")
        raise HTTPException(502, "Unable to open billing management right now.")


@app.post("/api/webhook/stripe")
async def stripe_webhook(request: Request):
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()
    if not webhook_secret:
        raise HTTPException(503, "Stripe webhook is not configured.")
    try:
        event = stripe.Webhook.construct_event(await request.body(), request.headers.get("Stripe-Signature"), webhook_secret)
    except ValueError:
        raise HTTPException(400, "Invalid webhook payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(400, "Invalid webhook signature")
    event_type = event.get("type")
    obj = event.get("data", {}).get("object", {})
    if event_type == "checkout.session.completed":
        user_id = obj.get("client_reference_id") or obj.get("metadata", {}).get("fitcheck_user_id")
        if user_id:
            await db.users.update_one({"id": user_id}, {"$set": {"stripe_customer_id": obj.get("customer"), "stripe_subscription_id": obj.get("subscription"), "plan": "buddy_pro", "subscription_status": "active"}})
    elif event_type and event_type.startswith("customer.subscription."):
        user_id = obj.get("metadata", {}).get("fitcheck_user_id")
        status = obj.get("status")
        values = {"stripe_customer_id": obj.get("customer"), "stripe_subscription_id": obj.get("id"), "subscription_status": status, "current_period_end": datetime.fromtimestamp(obj["current_period_end"], timezone.utc).isoformat() if obj.get("current_period_end") else None, "plan": "buddy_pro" if status in ("active", "trialing") else "free"}
        if user_id:
            await db.users.update_one({"id": user_id}, {"$set": values})
        elif obj.get("customer"):
            await db.users.update_one({"stripe_customer_id": obj.get("customer")}, {"$set": values})
    return {"received": True}


@app.post("/api/workouts")
async def create_workout(body: WorkoutCreateRequest, user=Depends(current_user)):
    workout = {"id": str(uuid.uuid4()), "user_id": user["id"], "name": body.name.strip(), "exercises": [x.model_dump() for x in body.exercises], "volume": sum(s.reps * s.weight for x in body.exercises for s in x.sets), "total_sets": sum(len(x.sets) for x in body.exercises), "date": body.date or datetime.now().astimezone().date().isoformat(), "notes": (body.notes or "").strip(), "created_at": datetime.now(timezone.utc).isoformat()}
    await db.workouts.insert_one(workout)
    workout.pop("_id", None)
    return workout


@app.get("/api/workouts")
async def list_workouts(user=Depends(current_user)):
    cursor = db.workouts.find({"user_id": user["id"]}).sort("created_at", -1)
    workouts = []
    async for doc in cursor:
        doc.pop("_id", None)
        workouts.append(doc)
    return {"workouts": workouts}


@app.delete("/api/workouts/{workout_id}")
async def delete_workout(workout_id: str, user=Depends(current_user)):
    result = await db.workouts.delete_one({"id": workout_id, "user_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(404, "Workout not found")
    return {"message": "Workout deleted"}


@app.get("/api/workouts/stats")
async def workout_stats(user=Depends(current_user)):
    cursor = db.workouts.find({"user_id": user["id"]}).sort("created_at", -1)
    workouts = [doc async for doc in cursor]
    total_workouts = len(workouts)
    total_volume = sum(w.get("volume", 0) for w in workouts)
    total_sets = sum(w.get("total_sets", 0) for w in workouts)
    dates = set()
    for w in workouts:
        try:
            dates.add(datetime.fromisoformat(w.get("date", "")).date())
        except Exception:
            pass
    streak = 0
    if dates:
        today = datetime.now().astimezone().date()
        current = max(dates)
        if current in (today, today - timedelta(days=1)):
            streak = 1
            while current - timedelta(days=1) in dates:
                current -= timedelta(days=1)
                streak += 1
    today = datetime.now().astimezone().date()
    monday = today - timedelta(days=today.weekday())
    weekly = []
    for i in range(8):
        start = monday - timedelta(weeks=7 - i)
        end = start + timedelta(days=6)
        weekly.append({"week": start.isoformat(), "volume": sum(w.get("volume", 0) for w in workouts if start <= datetime.fromisoformat(w.get("date", "1970-01-01")).date() <= end), "workouts": sum(1 for w in workouts if start <= datetime.fromisoformat(w.get("date", "1970-01-01")).date() <= end)})
    return {"total_workouts": total_workouts, "total_volume": total_volume, "total_sets": total_sets, "streak_days": streak, "weekly": weekly}


@app.post("/api/plans")
async def create_plan(body: PlanCreateRequest, user=Depends(current_user)):
    plan = {"id": str(uuid.uuid4()), "user_id": user["id"], "name": body.name.strip(), "goal": (body.goal or "").strip(), "days": [d.model_dump() for d in body.days], "created_at": datetime.now(timezone.utc).isoformat()}
    await db.plans.insert_one(plan)
    plan.pop("_id", None)
    return plan


@app.get("/api/plans")
async def list_plans(user=Depends(current_user)):
    cursor = db.plans.find({"user_id": user["id"]}).sort("created_at", -1)
    plans = []
    async for doc in cursor:
        doc.pop("_id", None)
        plans.append(doc)
    return {"plans": plans}


@app.delete("/api/plans/{plan_id}")
async def delete_plan(plan_id: str, user=Depends(current_user)):
    result = await db.plans.delete_one({"id": plan_id, "user_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(404, "Plan not found")
    return {"message": "Plan deleted"}


@app.get("/api/")
async def root():
    return {"message": "FitCheck API", "version": AUTH_VERSION}
