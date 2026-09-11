from datetime import datetime, timezone
import os
import uuid

import jwt
import requests
from fastapi import FastAPI, HTTPException, Request, Response

from backend.server import (
    app as backend_app,
    db,
    create_access,
    create_refresh,
    set_auth_cookies,
    public_user,
)

# Vercel serves /api/* from this Python function. Keep the existing FastAPI app
# as the source of truth, but handle Emergent Google sessions here because the
# browser receives a session_id that must be verified with Emergent's session-data API.
app = FastAPI(title="FitCheck Vercel API")

EMERGENT_SESSION_URL = os.environ.get(
    "EMERGENT_SESSION_URL",
    "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
).strip()


@app.get("/api/health")
async def health():
    return {"ok": True, "service": "fitcheck-api", "deployment": "vercel"}


@app.post("/api/auth/google/exchange")
async def google_exchange(request: Request, response: Response):
    body = await request.json()
    session_id = str(body.get("session_id") or "").strip()
    if not session_id:
        raise HTTPException(400, "Missing session id")

    try:
        result = requests.get(
            EMERGENT_SESSION_URL,
            headers={"X-Session-ID": session_id},
            timeout=15,
        )
        result.raise_for_status()
        data = result.json()
    except Exception:
        raise HTTPException(401, "Could not verify the Google session. Please try again.")

    email = str(data.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(401, "Google did not return a valid email address.")

    user = await db.users.find_one({"email": email})
    if not user:
        user = {
            "id": str(uuid.uuid4()),
            "email": email,
            "password_hash": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "auth_provider": "google",
            "name": str(data.get("name") or "").strip(),
            "picture": data.get("picture"),
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
        await db.users.update_one(
            {"id": user["id"]},
            {"$set": {
                "auth_provider": "google",
                "name": str(data.get("name") or user.get("name") or "").strip(),
                "picture": data.get("picture") or user.get("picture"),
            }},
        )
        user = await db.users.find_one({"id": user["id"]})

    access_token = create_access(user["id"], user["email"])
    refresh_token = create_refresh(user["id"])
    set_auth_cookies(response, access_token, refresh_token)
    return public_user(user) | {"access_token": access_token}


# All other API routes use the existing backend implementation.
app.mount("/", backend_app)
