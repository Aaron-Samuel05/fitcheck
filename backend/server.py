from fastapi import Depends
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

import bcrypt
import jwt
from fastapi import FastAPI, APIRouter, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field

# --- Config ---
JWT_ALGORITHM = "HS256"
ACCESS_TTL_MIN = 15
REFRESH_TTL_DAYS = 7

mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get("DB_NAME", "fitcheck")]

app = FastAPI(title="FitCheck API")
api_router = APIRouter(prefix="/api")

# --- Models ---
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: Optional[str] = None

# --- Password ---
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())

# --- JWT ---
def get_secret():
    return os.environ.get("JWT_SECRET", "dev_secret")

def create_access(user_id, email):
    return jwt.encode({
        "sub": user_id,
        "email": email,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TTL_MIN)
    }, get_secret(), algorithm=JWT_ALGORITHM)

def create_refresh(user_id):
    return jwt.encode({
        "sub": user_id,
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_TTL_DAYS)
    }, get_secret(), algorithm=JWT_ALGORITHM)

# --- Helper: Get current user ---
async def get_current_user(request: Request):
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        raise HTTPException(401, "Not authenticated")

    try:
        token = auth_header.split(" ")[1]
        payload = jwt.decode(token, get_secret(), algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")

        user = await db.users.find_one({"id": user_id})
        if not user:
            raise HTTPException(404, "User not found")

        return user

    except Exception:
        raise HTTPException(401, "Invalid token")

# --- Auth Routes ---
@api_router.post("/auth/register")
async def register(body: RegisterRequest):
    if await db.users.find_one({"email": body.email}):
        raise HTTPException(400, "User already exists")

    user = {
        "id": str(uuid.uuid4()),
        "email": body.email,
        "password_hash": hash_password(body.password),
        "created_at": datetime.utcnow().isoformat()
    }

    await db.users.insert_one(user)

    return {
        "access_token": create_access(user["id"], user["email"]),
        "refresh_token": create_refresh(user["id"])
    }

@api_router.post("/auth/login")
async def login(body: LoginRequest):
    user = await db.users.find_one({"email": body.email})

    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, "Invalid credentials")

    return {
        "access_token": create_access(user["id"], user["email"]),
        "refresh_token": create_refresh(user["id"])
    }

# --- CURRENT USER ---
@api_router.get("/auth/me")
async def get_me(current_user=Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "email": current_user["email"]
    }

# --- GOOGLE LOGIN (TEMP MOCK) ---
@api_router.post("/auth/google/exchange")
async def google_exchange():
    return {
        "access_token": create_access("google_user", "google@gmail.com"),
        "refresh_token": create_refresh("google_user")
    }

# --- AI (dummy) ---
@api_router.post("/ai/chat")
async def ai_chat(body: ChatRequest):
    return {
        "session_id": body.session_id or str(uuid.uuid4()),
        "reply": "AI disabled (local version)"
    }

# --- Root ---
@api_router.get("/")
async def root():
    return {"message": "FitCheck API running"}

app.include_router(api_router)

# --- CORS (FIXED) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://fitcheck-org.vercel.app",
        "https://fitcheck-20dns635-aaron-samuel05s-projects.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
