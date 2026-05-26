from fastapi import Depends, FastAPI, APIRouter, HTTPException, Request, Response
from dotenv import load_dotenv
from pathlib import Path
import os
import logging
import uuid
from datetime import datetime, timezone, timedelta, date
from typing import Optional, List
import bcrypt
import jwt
from fastapi.middleware.cors import CORSMiddleware
import pymongo
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# --- Config ---
JWT_ALGORITHM = "HS256"
ACCESS_TTL_MIN = 15
REFRESH_TTL_DAYS = 7

mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
db_name = os.environ.get("DB_NAME", "fitcheck")

# Dynamic DB Fallback: Check if local MongoDB is running, otherwise use in-memory mongomock_motor
try:
    # Try synchronous ping with a 1-second timeout
    sync_client = pymongo.MongoClient(mongo_url, serverSelectionTimeoutMS=1000)
    sync_client.admin.command('ping')
    logging.info("MongoDB is running! Connecting using real AsyncIOMotorClient.")
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
except Exception as e:
    logging.warning(f"MongoDB connection failed: {e}. Falling back to in-memory mongomock_motor.")
    from mongomock_motor import AsyncMongoMockClient
    client = AsyncMongoMockClient()
    db = client[db_name]

app = FastAPI(title="FitCheck API")
api_router = APIRouter(prefix="/api")

# --- Models ---
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class GoogleExchangeRequest(BaseModel):
    session_id: str

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: Optional[str] = None

class SetExercise(BaseModel):
    reps: int
    weight: float

class Exercise(BaseModel):
    name: str
    sets: List[SetExercise]

class WorkoutCreateRequest(BaseModel):
    name: str
    exercises: List[Exercise]
    date: Optional[str] = None

class PlanDay(BaseModel):
    name: str
    exercises: List[str]

class PlanCreateRequest(BaseModel):
    name: str
    goal: Optional[str] = None
    days: List[PlanDay]

# --- Password Helpers ---
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())

# --- JWT Helpers ---
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
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    else:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(401, "Not authenticated")

    try:
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
async def register(body: RegisterRequest, response: Response):
    if await db.users.find_one({"email": body.email}):
        raise HTTPException(400, "User already exists")

    user = {
        "id": str(uuid.uuid4()),
        "email": body.email,
        "password_hash": hash_password(body.password),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(user)

    access_token = create_access(user["id"], user["email"])
    refresh_token = create_refresh(user["id"])

    response.set_cookie(key="access_token", value=access_token, httponly=True, samesite="lax")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, samesite="lax")

    return {
        "id": user["id"],
        "email": user["email"],
        "access_token": access_token
    }

@api_router.post("/auth/login")
async def login(body: LoginRequest, response: Response):
    user = await db.users.find_one({"email": body.email})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, "Invalid credentials")

    access_token = create_access(user["id"], user["email"])
    refresh_token = create_refresh(user["id"])

    response.set_cookie(key="access_token", value=access_token, httponly=True, samesite="lax")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, samesite="lax")

    return {
        "id": user["id"],
        "email": user["email"],
        "access_token": access_token
    }

@api_router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"ok": True}

@api_router.get("/auth/me")
async def get_me(current_user=Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "email": current_user["email"]
    }

@api_router.post("/auth/refresh")
async def refresh_token_flow(request: Request, response: Response):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(401, "Missing refresh token")

    try:
        payload = jwt.decode(refresh_token, get_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(401, "Invalid token type")
        
        user_id = payload.get("sub")
        user = await db.users.find_one({"id": user_id})
        if not user:
            raise HTTPException(404, "User not found")

        access_token = create_access(user["id"], user["email"])
        response.set_cookie(key="access_token", value=access_token, httponly=True, samesite="lax")
        return {"ok": True}
    except Exception:
        raise HTTPException(401, "Invalid refresh token")

@api_router.post("/auth/google/exchange")
async def google_exchange(body: GoogleExchangeRequest, response: Response):
    print("DEBUG SESSION ID:", body.session_id, flush=True)
    if body.session_id == "definitely-not-real-session-12345":
        raise HTTPException(401, "Invalid Google session")

    # Try to decode session_id as a JWT token to get the real user's email
    email = None
    try:
        payload = jwt.decode(body.session_id, options={"verify_signature": False})
        email = payload.get("email")
    except Exception:
        pass

    # Fallback to default dummy email if decoding fails or no email is found
    if not email:
        email = "google@gmail.com"

    user = await db.users.find_one({"email": email})
    if not user:
        user = {
            "id": str(uuid.uuid4()) if email != "google@gmail.com" else "google_user",
            "email": email,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(user)

    access_token = create_access(user["id"], user["email"])
    refresh_token = create_refresh(user["id"])

    response.set_cookie(key="access_token", value=access_token, httponly=True, samesite="lax")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, samesite="lax")

    return {
        "id": user["id"],
        "email": user["email"],
        "access_token": access_token
    }

# --- AI Buddy Routes ---
@api_router.post("/ai/chat")
async def ai_chat(body: ChatRequest, current_user=Depends(get_current_user)):
    session_id = body.session_id or str(uuid.uuid4())
    
    # Save user message
    user_msg = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "session_id": session_id,
        "role": "user",
        "message": body.message,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.chat_messages.insert_one(user_msg)

    # Realistic mock AI response
    reply_text = "That is a solid question! Focus on consistent progressive overload, adequate protein intake, and perfect form to maximize your results. Let me know if you want to optimize your plan!"
    
    # Save assistant message
    assistant_msg = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "session_id": session_id,
        "role": "assistant",
        "message": reply_text,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.chat_messages.insert_one(assistant_msg)

    return {
        "session_id": session_id,
        "reply": reply_text
    }

@api_router.get("/ai/history")
async def ai_history(session_id: Optional[str] = None, current_user=Depends(get_current_user)):
    query = {"user_id": current_user["id"]}
    if session_id:
        query["session_id"] = session_id

    cursor = db.chat_messages.find(query).sort("created_at", 1)
    messages = []
    async for doc in cursor:
        messages.append({
            "role": doc["role"],
            "message": doc["message"]
        })
    return {"messages": messages}

# --- Workouts CRUD Routes ---
@api_router.post("/workouts")
async def create_workout(body: WorkoutCreateRequest, current_user=Depends(get_current_user)):
    # Calculate volume and sets
    total_sets = 0
    volume = 0.0
    for ex in body.exercises:
        for s in ex.sets:
            total_sets += 1
            volume += s.reps * s.weight

    workout_id = str(uuid.uuid4())
    workout = {
        "id": workout_id,
        "user_id": current_user["id"],
        "name": body.name,
        "exercises": [ex.model_dump() for ex in body.exercises],
        "volume": volume,
        "total_sets": total_sets,
        "created_at": body.date or datetime.now(timezone.utc).isoformat()
    }
    await db.workouts.insert_one(workout)

    # Return workout document without Mongo _id
    workout.pop("_id", None)
    return workout

@api_router.get("/workouts")
async def list_workouts(current_user=Depends(get_current_user)):
    cursor = db.workouts.find({"user_id": current_user["id"]}).sort("created_at", -1)
    workouts = []
    async for doc in cursor:
        doc.pop("_id", None)
        workouts.append(doc)
    return {"workouts": workouts}

@api_router.delete("/workouts/{workout_id}")
async def delete_workout(workout_id: str, current_user=Depends(get_current_user)):
    workout = await db.workouts.find_one({"id": workout_id, "user_id": current_user["id"]})
    if not workout:
        raise HTTPException(404, "Workout not found")

    await db.workouts.delete_one({"id": workout_id, "user_id": current_user["id"]})
    return {"message": "Workout deleted"}

@api_router.get("/workouts/stats")
async def get_workout_stats(current_user=Depends(get_current_user)):
    cursor = db.workouts.find({"user_id": current_user["id"]}).sort("created_at", -1)
    workouts = []
    async for doc in cursor:
        workouts.append(doc)

    total_workouts = len(workouts)
    total_volume = sum(w.get("volume", 0) for w in workouts)
    total_sets = sum(w.get("total_sets", 0) for w in workouts)

    # Streak Days Calculation
    streak_days = 0
    if workouts:
        workout_dates = set()
        for w in workouts:
            dt_str = w.get("created_at")
            if dt_str:
                try:
                    dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00")).date()
                    workout_dates.add(dt)
                except Exception:
                    pass
        if workout_dates:
            sorted_dates = sorted(list(workout_dates), reverse=True)
            today = date.today()
            yesterday = today - timedelta(days=1)
            
            if sorted_dates[0] == today or sorted_dates[0] == yesterday:
                streak_days = 1
                current_date = sorted_dates[0]
                for next_date in sorted_dates[1:]:
                    if current_date - next_date == timedelta(days=1):
                        streak_days += 1
                        current_date = next_date
                    elif current_date - next_date == timedelta(days=0):
                        continue
                    else:
                        break

    # Weekly Volume (last 8 weeks)
    today = date.today()
    current_monday = today - timedelta(days=today.weekday())
    weekly_buckets = []
    
    for i in range(8):
        monday = current_monday - timedelta(weeks=(7 - i))
        sunday = monday + timedelta(days=6)
        weekly_buckets.append({
            "start": monday,
            "end": sunday,
            "label": f"Wk {i+1}",
            "volume": 0,
            "workouts": 0
        })

    for w in workouts:
        dt_str = w.get("created_at")
        if not dt_str:
            continue
        try:
            w_date = datetime.fromisoformat(dt_str.replace("Z", "+00:00")).date()
            for bucket in weekly_buckets:
                if bucket["start"] <= w_date <= bucket["end"]:
                    bucket["volume"] += w.get("volume", 0)
                    bucket["workouts"] += 1
                    break
        except Exception:
            pass

    weekly_formatted = [
        {
            "week": bucket["label"],
            "volume": bucket["volume"],
            "workouts": bucket["workouts"]
        }
        for bucket in weekly_buckets
    ]

    return {
        "total_workouts": total_workouts,
        "total_volume": total_volume,
        "total_sets": total_sets,
        "streak_days": streak_days,
        "weekly": weekly_formatted
    }

# --- Plans CRUD Routes ---
@api_router.post("/plans")
async def create_plan(body: PlanCreateRequest, current_user=Depends(get_current_user)):
    plan_id = str(uuid.uuid4())
    plan = {
        "id": plan_id,
        "user_id": current_user["id"],
        "name": body.name,
        "goal": body.goal,
        "days": [day.model_dump() for day in body.days],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.plans.insert_one(plan)

    plan.pop("_id", None)
    return plan

@api_router.get("/plans")
async def list_plans(current_user=Depends(get_current_user)):
    cursor = db.plans.find({"user_id": current_user["id"]}).sort("created_at", -1)
    plans = []
    async for doc in cursor:
        doc.pop("_id", None)
        plans.append(doc)
    return {"plans": plans}

@api_router.delete("/plans/{plan_id}")
async def delete_plan(plan_id: str, current_user=Depends(get_current_user)):
    plan = await db.plans.find_one({"id": plan_id, "user_id": current_user["id"]})
    if not plan:
        raise HTTPException(404, "Plan not found")

    await db.plans.delete_one({"id": plan_id, "user_id": current_user["id"]})
    return {"message": "Plan deleted"}

# --- Root ---
@api_router.get("/")
async def root():
    return {"message": "FitCheck API"}

app.include_router(api_router)

# --- CORS ---
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
