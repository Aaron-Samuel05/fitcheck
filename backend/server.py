from fastapi import Depends, FastAPI, APIRouter, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from pathlib import Path
import os
import logging
import uuid
from datetime import datetime, timezone, timedelta, date
from typing import Optional, List
import bcrypt
import jwt
import pymongo
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field
from fastapi.middleware.cors import CORSMiddleware
from emergentintegrations.llm.chat import LlmChat, UserMessage

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

JWT_ALGORITHM = "HS256"
ACCESS_TTL_MIN = int(os.environ.get("ACCESS_TTL_MIN", "60"))
REFRESH_TTL_DAYS = int(os.environ.get("REFRESH_TTL_DAYS", "30"))

mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
db_name = os.environ.get("DB_NAME", "fitcheck")

try:
    sync_client = pymongo.MongoClient(mongo_url, serverSelectionTimeoutMS=1000)
    sync_client.admin.command("ping")
    sync_client.close()
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
except Exception as e:
    logging.warning(f"MongoDB unavailable; using in-memory database: {e}")
    from mongomock_motor import AsyncMongoMockClient
    client = AsyncMongoMockClient()
    db = client[db_name]

app = FastAPI(title="FitCheck API")
api_router = APIRouter(prefix="/api")


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleExchangeRequest(BaseModel):
    session_id: str


class ProfileUpdateRequest(BaseModel):
    name: str = Field(default="", max_length=80)
    age: Optional[int] = Field(default=None, ge=13, le=100)
    height_cm: Optional[float] = Field(default=None, ge=100, le=250)
    weight_kg: Optional[float] = Field(default=None, ge=25, le=300)
    goal: str = Field(default="", max_length=120)


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
    notes: Optional[str] = None


class PlanDay(BaseModel):
    name: str
    exercises: List[str]


class PlanCreateRequest(BaseModel):
    name: str
    goal: Optional[str] = None
    days: List[PlanDay]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def get_secret() -> str:
    secret = os.environ.get("JWT_SECRET")
    if not secret:
        logging.warning("JWT_SECRET is not configured; using development secret.")
        return "dev_secret"
    return secret


def create_access(user_id: str, email: str):
    return jwt.encode(
        {
            "sub": user_id,
            "email": email,
            "type": "access",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TTL_MIN),
        },
        get_secret(),
        algorithm=JWT_ALGORITHM,
    )


def create_refresh(user_id: str):
    return jwt.encode(
        {
            "sub": user_id,
            "type": "refresh",
            "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_TTL_DAYS),
        },
        get_secret(),
        algorithm=JWT_ALGORITHM,
    )


def profile_from_user(user: dict) -> dict:
    return {
        "name": user.get("name", ""),
        "age": user.get("age"),
        "height_cm": user.get("height_cm"),
        "weight_kg": user.get("weight_kg"),
        "goal": user.get("goal", ""),
    }


async def get_current_user(request: Request):
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
    else:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(401, "Not authenticated")

    try:
        payload = jwt.decode(token, get_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(401, "Invalid token type")
        user = await db.users.find_one({"id": payload.get("sub")})
        if not user:
            raise HTTPException(404, "User not found")
        return user
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(401, "Invalid or expired token")


@api_router.get("/health")
async def health():
    return {"ok": True, "service": "fitcheck-api"}


@api_router.post("/auth/register")
async def register(body: RegisterRequest, response: Response):
    email = body.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(400, "User already exists")

    user = {
        "id": str(uuid.uuid4()),
        "email": email,
        "password_hash": hash_password(body.password),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "name": "",
        "age": None,
        "height_cm": None,
        "weight_kg": None,
        "goal": "",
    }
    await db.users.insert_one(user)

    access_token = create_access(user["id"], user["email"])
    refresh_token = create_refresh(user["id"])
    response.set_cookie("access_token", access_token, httponly=True, samesite="lax", secure=True)
    response.set_cookie("refresh_token", refresh_token, httponly=True, samesite="lax", secure=True)
    return {"id": user["id"], "email": user["email"], "access_token": access_token}


@api_router.post("/auth/login")
async def login(body: LoginRequest, response: Response):
    email = body.email.lower()
    user = await db.users.find_one({"email": email})
    if not user or "password_hash" not in user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")

    access_token = create_access(user["id"], user["email"])
    refresh_token = create_refresh(user["id"])
    response.set_cookie("access_token", access_token, httponly=True, samesite="lax", secure=True)
    response.set_cookie("refresh_token", refresh_token, httponly=True, samesite="lax", secure=True)
    return {"id": user["id"], "email": user["email"], "access_token": access_token}


@api_router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"ok": True}


@api_router.get("/auth/me")
async def get_me(current_user=Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "profile": profile_from_user(current_user),
    }


@api_router.get("/profile")
async def get_profile(current_user=Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "profile": profile_from_user(current_user),
    }


@api_router.patch("/profile")
async def update_profile(body: ProfileUpdateRequest, current_user=Depends(get_current_user)):
    values = body.model_dump()
    values["name"] = values["name"].strip()
    values["goal"] = values["goal"].strip()
    await db.users.update_one({"id": current_user["id"]}, {"$set": values})
    updated = await db.users.find_one({"id": current_user["id"]})
    return {
        "id": updated["id"],
        "email": updated["email"],
        "profile": profile_from_user(updated),
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
        user = await db.users.find_one({"id": payload.get("sub")})
        if not user:
            raise HTTPException(404, "User not found")
        access_token = create_access(user["id"], user["email"])
        response.set_cookie("access_token", access_token, httponly=True, samesite="lax", secure=True)
        return {"ok": True, "access_token": access_token}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(401, "Invalid or expired refresh token")


@api_router.post("/auth/google/exchange")
async def google_exchange(body: GoogleExchangeRequest, response: Response):
    try:
        payload = jwt.decode(body.session_id, options={"verify_signature": False})
        email = payload.get("email")
    except Exception:
        email = None

    if not email:
        raise HTTPException(401, "Google session could not be verified. Configure the Google auth provider for this deployment.")

    email = str(email).lower()
    user = await db.users.find_one({"email": email})
    if not user:
        user = {
            "id": str(uuid.uuid4()),
            "email": email,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "auth_provider": "google",
            "name": "",
            "age": None,
            "height_cm": None,
            "weight_kg": None,
            "goal": "",
        }
        await db.users.insert_one(user)

    access_token = create_access(user["id"], user["email"])
    refresh_token = create_refresh(user["id"])
    response.set_cookie("access_token", access_token, httponly=True, samesite="lax", secure=True)
    response.set_cookie("refresh_token", refresh_token, httponly=True, samesite="lax", secure=True)
    return {"id": user["id"], "email": user["email"], "access_token": access_token}


# ---------------- AI Buddy ----------------
AI_SYSTEM_PROMPT = """You are FitCheck Coach, a knowledgeable and encouraging fitness coach.
Give practical, concise answers about training, exercise selection, recovery, nutrition,
progressive overload, cardio, and healthy habits. Use the user's conversation context and
profile when available. Do not diagnose medical conditions or replace a clinician. If a
question suggests injury, serious symptoms, an eating disorder, or another medical concern,
recommend professional care. Prefer actionable advice and explain the reasoning briefly.
Never pretend that you performed an action you did not perform."""


async def generate_ai_reply(session_id: str, user_message: str, user_id: str) -> str:
    api_key = os.environ.get("EMERGENT_LLM_KEY", "").strip()
    if not api_key:
        raise HTTPException(503, "AI Buddy is not configured. Add EMERGENT_LLM_KEY to the backend environment and redeploy.")

    user = await db.users.find_one({"id": user_id})
    profile = profile_from_user(user or {})
    profile_text = ", ".join(f"{k}: {v}" for k, v in profile.items() if v not in (None, "")) or "No profile details provided"

    previous = await db.chat_messages.find(
        {"user_id": user_id, "session_id": session_id}
    ).sort("created_at", -1).to_list(12)
    previous.reverse()
    context = "\n".join(
        f"{m.get('role', 'user').upper()}: {m.get('message', '')}"
        for m in previous
    )
    prompt = (
        f"User profile: {profile_text}\n\n"
        f"Conversation so far:\n{context}\n\n"
        f"USER: {user_message}\n\nReply as FitCheck Coach."
    )

    try:
        model_name = os.environ.get("FITCHECK_AI_MODEL", "gemini-3-flash-preview")
        chat = LlmChat(
            api_key=api_key,
            session_id=f"fitcheck-{user_id}-{session_id}",
            system_message=AI_SYSTEM_PROMPT,
        ).with_model("gemini", model_name)
        result = await chat.send_message(UserMessage(text=prompt))
        reply = str(result).strip()
        if not reply:
            raise RuntimeError("The AI provider returned an empty response")
        return reply
    except HTTPException:
        raise
    except Exception as e:
        logging.exception("AI Buddy provider error")
        raise HTTPException(502, f"AI Buddy could not respond: {str(e)[:300]}")


@api_router.get("/ai/status")
async def ai_status(current_user=Depends(get_current_user)):
    key_configured = bool(os.environ.get("EMERGENT_LLM_KEY", "").strip())
    return {
        "configured": key_configured,
        "model": os.environ.get("FITCHECK_AI_MODEL", "gemini-3-flash-preview"),
    }


@api_router.post("/ai/chat")
async def ai_chat(body: ChatRequest, current_user=Depends(get_current_user)):
    session_id = body.session_id or str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    await db.chat_messages.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "session_id": session_id,
        "role": "user",
        "message": body.message,
        "created_at": now,
    })

    try:
        reply = await generate_ai_reply(session_id, body.message, current_user["id"])
    except HTTPException:
        await db.chat_messages.delete_one({"user_id": current_user["id"], "session_id": session_id, "role": "user", "created_at": now})
        raise

    await db.chat_messages.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "session_id": session_id,
        "role": "assistant",
        "message": reply,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"session_id": session_id, "reply": reply}


@api_router.get("/ai/history")
async def ai_history(session_id: Optional[str] = None, current_user=Depends(get_current_user)):
    query = {"user_id": current_user["id"]}
    if session_id:
        query["session_id"] = session_id
    cursor = db.chat_messages.find(query).sort("created_at", 1)
    messages = []
    async for doc in cursor:
        messages.append({"role": doc["role"], "message": doc["message"]})
    return {"messages": messages}


# ---------------- Workouts ----------------
@api_router.post("/workouts")
async def create_workout(body: WorkoutCreateRequest, current_user=Depends(get_current_user)):
    total_sets = sum(len(ex.sets) for ex in body.exercises)
    volume = sum(s.reps * s.weight for ex in body.exercises for s in ex.sets)
    workout = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "name": body.name,
        "exercises": [ex.model_dump() for ex in body.exercises],
        "volume": volume,
        "total_sets": total_sets,
        "date": body.date or date.today().isoformat(),
        "notes": body.notes or "",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.workouts.insert_one(workout)
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

    workout_dates = set()
    for w in workouts:
        try:
            workout_dates.add(datetime.fromisoformat(w["created_at"].replace("Z", "+00:00")).date())
        except Exception:
            pass

    streak_days = 0
    if workout_dates:
        sorted_dates = sorted(workout_dates, reverse=True)
        today = date.today()
        if sorted_dates[0] in (today, today - timedelta(days=1)):
            streak_days = 1
            current = sorted_dates[0]
            for next_date in sorted_dates[1:]:
                if current - next_date == timedelta(days=1):
                    streak_days += 1
                    current = next_date
                elif current != next_date:
                    break

    today = date.today()
    monday = today - timedelta(days=today.weekday())
    weekly = []
    for i in range(8):
        start = monday - timedelta(weeks=7 - i)
        end = start + timedelta(days=6)
        bucket = {"week": start.isoformat(), "volume": 0, "workouts": 0}
        for w in workouts:
            try:
                d = datetime.fromisoformat(w["created_at"].replace("Z", "+00:00")).date()
                if start <= d <= end:
                    bucket["volume"] += w.get("volume", 0)
                    bucket["workouts"] += 1
            except Exception:
                pass
        weekly.append(bucket)

    return {
        "total_workouts": total_workouts,
        "total_volume": total_volume,
        "total_sets": total_sets,
        "streak_days": streak_days,
        "weekly": weekly,
    }


# ---------------- Plans ----------------
@api_router.post("/plans")
async def create_plan(body: PlanCreateRequest, current_user=Depends(get_current_user)):
    plan = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "name": body.name,
        "goal": body.goal,
        "days": [day.model_dump() for day in body.days],
        "created_at": datetime.now(timezone.utc).isoformat(),
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


@api_router.get("/")
async def root():
    return {"message": "FitCheck API"}


app.include_router(api_router)

cors_origins = [x.strip() for x in os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:3000,https://fitcheck-org.vercel.app",
).split(",") if x.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_BUILD_DIR = Path(__file__).parent.parent / "frontend" / "build"
if (FRONTEND_BUILD_DIR / "static").exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_BUILD_DIR / "static")), name="static")


@app.api_route("/api/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def api_catch_all(path_name: str):
    raise HTTPException(status_code=404, detail="Not Found")


@app.get("/{path_name:path}")
async def catch_all(path_name: str):
    file_path = FRONTEND_BUILD_DIR / path_name
    if file_path.is_file():
        return FileResponse(str(file_path))
    index_path = FRONTEND_BUILD_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "Frontend build not found. Run npm run build."}


logging.basicConfig(level=logging.INFO)
