from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List

import bcrypt
import httpx
import jwt
from fastapi import FastAPI, APIRouter, Request, Response, HTTPException, Depends
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field

from emergentintegrations.llm.chat import LlmChat, UserMessage
from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout,
    CheckoutSessionRequest,
)


# --- Config ---
JWT_ALGORITHM = "HS256"
ACCESS_TTL_MIN = 15
REFRESH_TTL_DAYS = 7

# Fixed server-side pricing. Never take amounts from the client.
PREMIUM_PLANS = {
    "premium_monthly": {"amount": 9.99, "currency": "usd", "label": "FitCheck Premium (monthly)"},
}

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="FitCheck API")
api_router = APIRouter(prefix="/api")


# --- Models ---
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ChatMessageIn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: Optional[str] = None


class CheckoutRequest(BaseModel):
    plan_id: str
    origin_url: str


class GoogleExchangeRequest(BaseModel):
    session_id: str = Field(min_length=4, max_length=512)


# --- Password helpers ---
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# --- JWT helpers ---
def get_jwt_secret() -> str:
    return os.environ["JWT_SECRET"]


def create_access_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TTL_MIN),
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_TTL_DAYS),
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def set_auth_cookies(response: Response, access: str, refresh: str) -> None:
    response.set_cookie(
        "access_token", access,
        httponly=True, secure=False, samesite="lax",
        max_age=ACCESS_TTL_MIN * 60, path="/",
    )
    response.set_cookie(
        "refresh_token", refresh,
        httponly=True, secure=False, samesite="lax",
        max_age=REFRESH_TTL_DAYS * 86400, path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    for name in ("access_token", "refresh_token"):
        response.set_cookie(
            name, "",
            httponly=True, secure=False, samesite="lax",
            max_age=0, expires=0, path="/",
        )


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def public_user(u: dict) -> dict:
    created_at = u.get("created_at")
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at)
    return {
        "id": u["id"],
        "email": u["email"],
        "created_at": created_at,
        "is_premium": bool(u.get("is_premium", False)),
    }


# --- Auth routes ---
@api_router.get("/")
async def root():
    return {"message": "FitCheck API"}


@api_router.post("/auth/register")
async def register(body: RegisterRequest, response: Response):
    email = body.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")

    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    doc = {
        "id": user_id,
        "email": email,
        "password_hash": hash_password(body.password),
        "is_premium": False,
        "created_at": now.isoformat(),
    }
    await db.users.insert_one(doc)

    access = create_access_token(user_id, email)
    refresh = create_refresh_token(user_id)
    set_auth_cookies(response, access, refresh)
    return public_user({**doc, "created_at": now})


@api_router.post("/auth/login")
async def login(body: LoginRequest, response: Response):
    email = body.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access = create_access_token(user["id"], email)
    refresh = create_refresh_token(user["id"])
    set_auth_cookies(response, access, refresh)
    return public_user(user)


@api_router.post("/auth/logout")
async def logout(response: Response, user: dict = Depends(get_current_user)):
    clear_auth_cookies(response)
    return {"ok": True}


@api_router.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return public_user(user)


@api_router.post("/auth/refresh")
async def refresh_token(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        access = create_access_token(payload["sub"], payload.get("email", ""))
        response.set_cookie(
            "access_token", access,
            httponly=True, secure=False, samesite="lax",
            max_age=ACCESS_TTL_MIN * 60, path="/",
        )
        return {"ok": True}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


# --- Google (Emergent-managed) auth exchange ---
EMERGENT_SESSION_DATA_URL = (
    "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"
)


@api_router.post("/auth/google/exchange")
async def google_exchange(body: GoogleExchangeRequest, response: Response):
    """
    Exchanges an Emergent Google OAuth session_id (from URL fragment) for
    a FitCheck session. Upserts the user in MongoDB and issues the same
    httpOnly access/refresh JWT cookies used by email/password auth so the
    rest of the app (premium flag, /auth/me, logout, AI chat, Stripe) keeps
    working unchanged.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as http:
            r = await http.get(
                EMERGENT_SESSION_DATA_URL,
                headers={"X-Session-ID": body.session_id},
            )
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Google auth unreachable: {e}")

    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid or expired Google session")

    data = r.json() or {}
    email = (data.get("email") or "").lower().strip()
    name = data.get("name") or ""
    picture = data.get("picture") or ""
    if not email:
        raise HTTPException(status_code=400, detail="Google session missing email")

    existing = await db.users.find_one({"email": email})
    if existing:
        # Merge profile data if missing.
        patch = {}
        if name and not existing.get("name"):
            patch["name"] = name
        if picture and not existing.get("picture"):
            patch["picture"] = picture
        patch["google_linked"] = True
        if patch:
            await db.users.update_one({"id": existing["id"]}, {"$set": patch})
        user = {**existing, **patch}
    else:
        user_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()
        user = {
            "id": user_id,
            "email": email,
            "name": name,
            "picture": picture,
            "is_premium": False,
            "google_linked": True,
            "created_at": now_iso,
            # No password_hash — Google-only accounts can't log in with password
            # until they set one via a future "add password" flow.
        }
        await db.users.insert_one(user)

    access = create_access_token(user["id"], email)
    refresh = create_refresh_token(user["id"])
    set_auth_cookies(response, access, refresh)
    return public_user(user)


# --- AI Buddy chat ---
AI_SYSTEM_PROMPT = (
    "You are FitCheck Coach, a premium AI fitness buddy. "
    "You help users with workout planning, exercise form cues, recovery, nutrition basics, and motivation. "
    "Keep replies concise (2-5 short paragraphs), encouraging, and practical. "
    "Ask clarifying questions when a user's goal or context is unclear. "
    "Never prescribe medical advice — suggest consulting a professional for injuries or medical concerns."
)


@api_router.post("/ai/chat")
async def ai_chat(body: ChatRequest, user: dict = Depends(get_current_user)):
    if not user.get("is_premium"):
        raise HTTPException(status_code=402, detail="Premium subscription required")

    session_id = body.session_id or str(uuid.uuid4())

    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="AI service not configured")

    chat = LlmChat(
        api_key=api_key,
        session_id=session_id,
        system_message=AI_SYSTEM_PROMPT,
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")

    # Persist user message first
    now = datetime.now(timezone.utc).isoformat()
    await db.chat_messages.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "session_id": session_id,
        "role": "user",
        "content": body.message,
        "created_at": now,
    })

    try:
        reply = await chat.send_message(UserMessage(text=body.message))
    except Exception as e:
        logging.exception("AI chat failed")
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)[:200]}")

    await db.chat_messages.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "session_id": session_id,
        "role": "assistant",
        "content": reply,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    return {"session_id": session_id, "reply": reply}


@api_router.get("/ai/history")
async def ai_history(session_id: Optional[str] = None, user: dict = Depends(get_current_user)):
    if not user.get("is_premium"):
        raise HTTPException(status_code=402, detail="Premium subscription required")
    query = {"user_id": user["id"]}
    if session_id:
        query["session_id"] = session_id
    msgs = await db.chat_messages.find(query, {"_id": 0}).sort("created_at", 1).to_list(500)
    return {"messages": msgs}


# --- Stripe payments ---
def _get_stripe(http_request: Request) -> StripeCheckout:
    api_key = os.environ.get("STRIPE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Payments not configured")
    host_url = str(http_request.base_url).rstrip("/")
    webhook_url = f"{host_url}/api/webhook/stripe"
    return StripeCheckout(api_key=api_key, webhook_url=webhook_url)


@api_router.get("/payments/plans")
async def get_plans():
    return {
        "plans": [
            {"id": k, **v} for k, v in PREMIUM_PLANS.items()
        ]
    }


@api_router.post("/payments/checkout")
async def create_checkout(
    body: CheckoutRequest,
    http_request: Request,
    user: dict = Depends(get_current_user),
):
    if body.plan_id not in PREMIUM_PLANS:
        raise HTTPException(status_code=400, detail="Invalid plan")

    plan = PREMIUM_PLANS[body.plan_id]
    origin = body.origin_url.rstrip("/")
    success_url = f"{origin}/?payment=success&session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/?payment=cancelled"

    stripe_checkout = _get_stripe(http_request)
    req = CheckoutSessionRequest(
        amount=float(plan["amount"]),
        currency=plan["currency"],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "user_id": user["id"],
            "user_email": user["email"],
            "plan_id": body.plan_id,
        },
    )
    session = await stripe_checkout.create_checkout_session(req)

    await db.payment_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "session_id": session.session_id,
        "user_id": user["id"],
        "user_email": user["email"],
        "plan_id": body.plan_id,
        "amount": float(plan["amount"]),
        "currency": plan["currency"],
        "status": "initiated",
        "payment_status": "unpaid",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    return {"url": session.url, "session_id": session.session_id}


@api_router.get("/payments/status/{session_id}")
async def payment_status(session_id: str, http_request: Request, user: dict = Depends(get_current_user)):
    txn = await db.payment_transactions.find_one({"session_id": session_id, "user_id": user["id"]}, {"_id": 0})
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # If already finalized as paid, return cached state.
    if txn.get("payment_status") == "paid":
        return {
            "status": txn.get("status"),
            "payment_status": txn.get("payment_status"),
            "amount_total": int(round(txn.get("amount", 0) * 100)),
            "currency": txn.get("currency"),
            "is_premium": True,
        }

    stripe_checkout = _get_stripe(http_request)
    status = await stripe_checkout.get_checkout_status(session_id)

    update = {
        "status": status.status,
        "payment_status": status.payment_status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    # Idempotent premium grant: only mark premium once per session.
    if status.payment_status == "paid" and txn.get("payment_status") != "paid":
        await db.users.update_one({"id": user["id"]}, {"$set": {"is_premium": True}})

    await db.payment_transactions.update_one({"session_id": session_id}, {"$set": update})

    is_premium = status.payment_status == "paid" or bool(txn.get("payment_status") == "paid")
    return {
        "status": status.status,
        "payment_status": status.payment_status,
        "amount_total": status.amount_total,
        "currency": status.currency,
        "is_premium": is_premium,
    }


@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    try:
        body = await request.body()
        stripe_checkout = _get_stripe(request)
        event = await stripe_checkout.handle_webhook(body, request.headers.get("Stripe-Signature"))

        if getattr(event, "payment_status", None) == "paid":
            session_id = getattr(event, "session_id", None)
            if session_id:
                txn = await db.payment_transactions.find_one({"session_id": session_id})
                if txn and txn.get("payment_status") != "paid":
                    await db.users.update_one({"id": txn["user_id"]}, {"$set": {"is_premium": True}})
                    await db.payment_transactions.update_one(
                        {"session_id": session_id},
                        {"$set": {
                            "payment_status": "paid",
                            "status": "complete",
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        }},
                    )
        return {"received": True}
    except Exception as e:
        logging.exception("Stripe webhook failed")
        raise HTTPException(status_code=400, detail=str(e))


app.include_router(api_router)


app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def on_startup():
    await db.users.create_index("email", unique=True)
    await db.payment_transactions.create_index("session_id", unique=True)
    await db.chat_messages.create_index([("user_id", 1), ("created_at", 1)])
    logger.info("FitCheck API started; indexes ensured.")


@app.on_event("shutdown")
async def on_shutdown():
    client.close()
