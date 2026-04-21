"""FitCheck backend tests (iteration 3) — Stripe/premium REMOVED, workouts+plans CRUD, AI ungated."""
import os
import uuid
import requests
import pytest

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL",
    "https://sleek-workout-2.preview.emergentagent.com",
).rstrip("/")
API = f"{BASE_URL}/api"


def rand_email():
    return f"qa.user+{uuid.uuid4().hex[:8]}@fitcheck.app"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def creds():
    return {"email": rand_email(), "password": "Passw0rd!"}


# --- Health ---
def test_root():
    r = requests.get(f"{API}/")
    assert r.status_code == 200
    assert r.json().get("message") == "FitCheck API"


# --- Auth register / login / me / refresh ---
def test_register_success(session, creds):
    r = session.post(f"{API}/auth/register", json=creds)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["email"] == creds["email"]
    assert "id" in data
    # is_premium field must be REMOVED
    assert "is_premium" not in data, f"is_premium should no longer be in response: {data}"
    assert "access_token" in session.cookies
    assert "refresh_token" in session.cookies


def test_register_duplicate(session, creds):
    r = session.post(f"{API}/auth/register", json=creds)
    assert r.status_code == 400


def test_register_short_password():
    r = requests.post(f"{API}/auth/register", json={"email": rand_email(), "password": "abc"})
    assert r.status_code == 422


def test_register_invalid_email():
    r = requests.post(f"{API}/auth/register", json={"email": "notanemail", "password": "Passw0rd!"})
    assert r.status_code == 422


def test_me_authenticated(session, creds):
    r = session.get(f"{API}/auth/me")
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == creds["email"]
    assert "is_premium" not in body, f"is_premium field should be removed: {body}"


def test_me_unauthenticated():
    r = requests.get(f"{API}/auth/me")
    assert r.status_code == 401


def test_refresh_flow(creds):
    s = requests.Session()
    s.post(f"{API}/auth/login", json=creds)
    r = s.post(f"{API}/auth/refresh")
    assert r.status_code == 200
    assert r.json().get("ok") is True


def test_login_wrong_password(creds):
    r = requests.post(f"{API}/auth/login", json={"email": creds["email"], "password": "wrong"})
    assert r.status_code == 401


# --- Google exchange ---
def test_google_exchange_bogus_session():
    r = requests.post(f"{API}/auth/google/exchange", json={"session_id": "definitely-not-real-session-12345"})
    assert r.status_code == 401


def test_google_exchange_missing_field():
    r = requests.post(f"{API}/auth/google/exchange", json={})
    assert r.status_code == 422


# --- Stripe/Payments endpoints must be REMOVED (404) ---
def test_payments_plans_removed():
    r = requests.get(f"{API}/payments/plans")
    assert r.status_code == 404, f"/api/payments/plans should be removed; got {r.status_code}"


def test_payments_checkout_removed():
    r = requests.post(
        f"{API}/payments/checkout",
        json={"plan_id": "premium_monthly", "origin_url": BASE_URL},
    )
    assert r.status_code == 404


def test_payments_status_removed():
    r = requests.get(f"{API}/payments/status/whatever")
    assert r.status_code == 404


def test_webhook_stripe_removed():
    r = requests.post(f"{API}/webhook/stripe", data="{}")
    assert r.status_code == 404


# --- AI chat is now FREE for any authenticated user ---
def test_ai_chat_unauthenticated():
    r = requests.post(f"{API}/ai/chat", json={"message": "hi"})
    assert r.status_code == 401


def test_ai_history_unauthenticated():
    r = requests.get(f"{API}/ai/history")
    assert r.status_code == 401


def test_ai_chat_free_user_allowed(session):
    r = session.post(
        f"{API}/ai/chat",
        json={"message": "Give me a 1 sentence motivational tip."},
        timeout=60,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("session_id")
    assert isinstance(body.get("reply"), str) and len(body["reply"]) > 0


def test_ai_history_free_user_allowed(session):
    r = session.get(f"{API}/ai/history")
    assert r.status_code == 200
    msgs = r.json().get("messages", [])
    assert isinstance(msgs, list)
    assert len(msgs) >= 2  # user + assistant from prev test
    roles = {m["role"] for m in msgs}
    assert "user" in roles and "assistant" in roles


# --- Workouts CRUD ---
def test_workouts_require_auth():
    assert requests.get(f"{API}/workouts").status_code == 401
    assert requests.post(f"{API}/workouts", json={"name": "x"}).status_code == 401
    assert requests.get(f"{API}/workouts/stats").status_code == 401
    assert requests.delete(f"{API}/workouts/anything").status_code == 401


def test_create_workout_computes_volume(session):
    payload = {
        "name": "TEST_Push Day",
        "exercises": [
            {"name": "Bench", "sets": [{"reps": 8, "weight": 60}, {"reps": 6, "weight": 65}]},
            {"name": "OHP", "sets": [{"reps": 10, "weight": 40}]},
        ],
    }
    r = session.post(f"{API}/workouts", json=payload)
    assert r.status_code == 200, r.text
    doc = r.json()
    # 8*60 + 6*65 + 10*40 = 1270
    assert doc["volume"] == 1270
    assert doc["total_sets"] == 3
    assert doc["name"] == "TEST_Push Day"
    assert "id" in doc
    assert "_id" not in doc

    # GET list — newest first, contains our doc
    gl = session.get(f"{API}/workouts")
    assert gl.status_code == 200
    workouts = gl.json()["workouts"]
    assert any(w["id"] == doc["id"] for w in workouts)
    return doc["id"]


def test_workout_stats_shape_and_streak(session):
    r = session.get(f"{API}/workouts/stats")
    assert r.status_code == 200
    s = r.json()
    for k in ("total_workouts", "total_volume", "total_sets", "streak_days", "weekly"):
        assert k in s, f"missing {k}"
    assert s["total_workouts"] >= 1
    assert s["total_volume"] >= 1270
    assert s["total_sets"] >= 3
    assert s["streak_days"] == 1  # workout logged today
    assert isinstance(s["weekly"], list)
    assert len(s["weekly"]) == 8
    for w in s["weekly"]:
        assert "week" in w and "volume" in w and "workouts" in w
    # Current (most recent / last) bucket should include today's workout
    assert s["weekly"][-1]["workouts"] >= 1
    assert s["weekly"][-1]["volume"] >= 1270


def test_delete_workout_and_foreign_404(session):
    # Create a workout specifically for deletion
    r = session.post(f"{API}/workouts", json={"name": "TEST_delete_me", "exercises": []})
    wid = r.json()["id"]

    # Delete succeeds
    d = session.delete(f"{API}/workouts/{wid}")
    assert d.status_code == 200

    # Second delete → 404
    d2 = session.delete(f"{API}/workouts/{wid}")
    assert d2.status_code == 404

    # Foreign id → 404
    d3 = session.delete(f"{API}/workouts/{uuid.uuid4()}")
    assert d3.status_code == 404


# --- Plans CRUD ---
def test_plans_require_auth():
    assert requests.get(f"{API}/plans").status_code == 401
    assert requests.post(f"{API}/plans", json={"name": "x"}).status_code == 401
    assert requests.delete(f"{API}/plans/any").status_code == 401


def test_create_and_list_plan(session):
    payload = {
        "name": "TEST_PPL",
        "goal": "Hypertrophy",
        "days": [
            {"name": "Push", "exercises": ["Bench", "OHP", "Triceps"]},
            {"name": "Pull", "exercises": ["Row", "Pullup"]},
        ],
    }
    r = session.post(f"{API}/plans", json=payload)
    assert r.status_code == 200, r.text
    p = r.json()
    assert p["name"] == "TEST_PPL"
    assert len(p["days"]) == 2
    assert p["days"][0]["exercises"] == ["Bench", "OHP", "Triceps"]
    assert "id" in p and "_id" not in p

    lst = session.get(f"{API}/plans").json()["plans"]
    assert lst[0]["id"] == p["id"]  # newest first
    return p["id"]


def test_delete_plan_and_foreign_404(session):
    r = session.post(f"{API}/plans", json={"name": "TEST_delete_plan", "days": []})
    pid = r.json()["id"]
    d = session.delete(f"{API}/plans/{pid}")
    assert d.status_code == 200
    d2 = session.delete(f"{API}/plans/{pid}")
    assert d2.status_code == 404
    d3 = session.delete(f"{API}/plans/{uuid.uuid4()}")
    assert d3.status_code == 404


# --- Cross-user isolation: a new user cannot delete another user's workout ---
def test_foreign_user_cannot_delete_workout(session):
    # session user creates a workout
    r = session.post(f"{API}/workouts", json={"name": "TEST_owned", "exercises": []})
    wid = r.json()["id"]

    # new user, separate cookies
    s2 = requests.Session()
    s2.headers.update({"Content-Type": "application/json"})
    s2.post(f"{API}/auth/register", json={"email": rand_email(), "password": "Passw0rd!"})
    d = s2.delete(f"{API}/workouts/{wid}")
    assert d.status_code == 404

    # owner can still delete
    assert session.delete(f"{API}/workouts/{wid}").status_code == 200


def test_logout(session):
    r = session.post(f"{API}/auth/logout")
    assert r.status_code == 200
    # After logout, /me should be 401
    r2 = session.get(f"{API}/auth/me")
    assert r2.status_code == 401
