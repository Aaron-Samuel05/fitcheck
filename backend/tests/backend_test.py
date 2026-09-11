"""FitCheck backend smoke/integration tests for auth, logger, plans, AI limits and billing."""
import os
import uuid
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000").rstrip("/")
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


def test_health():
    r = requests.get(f"{API}/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_root():
    r = requests.get(f"{API}/")
    assert r.status_code == 200
    assert r.json().get("message") == "FitCheck API"


def test_register_success(session, creds):
    r = session.post(f"{API}/auth/register", json=creds)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["email"] == creds["email"]
    assert data["plan"] == "free"
    assert "access_token" in session.cookies
    assert "refresh_token" in session.cookies


def test_duplicate_register(session, creds):
    assert session.post(f"{API}/auth/register", json=creds).status_code == 400


def test_me_and_profile(session, creds):
    me = session.get(f"{API}/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == creds["email"]

    updated = session.patch(f"{API}/profile", json={"name": "QA User", "age": 28, "height_cm": 180, "weight_kg": 80, "goal": "Build muscle"})
    assert updated.status_code == 200, updated.text
    assert updated.json()["profile"]["name"] == "QA User"
    assert updated.json()["profile"]["goal"] == "Build muscle"


def test_workout_create_stats_delete(session):
    payload = {
        "name": "TEST Push Day",
        "date": "2026-09-11",
        "exercises": [
            {"name": "Bench", "sets": [{"reps": 8, "weight": 60}, {"reps": 6, "weight": 65}]},
            {"name": "OHP", "sets": [{"reps": 10, "weight": 40}]},
        ],
    }
    r = session.post(f"{API}/workouts", json=payload)
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["volume"] == 1270
    assert doc["total_sets"] == 3
    assert "id" in doc and "_id" not in doc

    stats = session.get(f"{API}/workouts/stats")
    assert stats.status_code == 200
    body = stats.json()
    assert body["total_workouts"] >= 1
    assert body["total_volume"] >= 1270
    assert body["total_sets"] >= 3
    assert len(body["weekly"]) == 8

    listing = session.get(f"{API}/workouts").json()["workouts"]
    assert any(w["id"] == doc["id"] for w in listing)

    deleted = session.delete(f"{API}/workouts/{doc['id']}")
    assert deleted.status_code == 200
    assert session.delete(f"{API}/workouts/{doc['id']}").status_code == 404


def test_plans_create_delete(session):
    payload = {"name": "TEST PPL", "goal": "Hypertrophy", "days": [{"name": "Push", "exercises": ["Bench", "OHP"]}, {"name": "Pull", "exercises": ["Rows", "Pullups"]}]}
    r = session.post(f"{API}/plans", json=payload)
    assert r.status_code == 200, r.text
    plan = r.json()
    assert plan["name"] == "TEST PPL"
    assert len(plan["days"]) == 2
    assert session.get(f"{API}/plans").status_code == 200
    assert session.delete(f"{API}/plans/{plan['id']}").status_code == 200


def test_billing_plans_public():
    r = requests.get(f"{API}/billing/plans")
    assert r.status_code == 200
    ids = {p["id"] for p in r.json()["plans"]}
    assert {"free", "buddy_pro_monthly", "buddy_pro_yearly"}.issubset(ids)


def test_billing_status(session):
    r = session.get(f"{API}/billing/status")
    assert r.status_code == 200
    assert r.json()["plan"] == "free"
    assert r.json()["paid"] is False


def test_unauthenticated_guards():
    assert requests.get(f"{API}/auth/me").status_code == 401
    assert requests.get(f"{API}/profile").status_code == 401
    assert requests.get(f"{API}/workouts").status_code == 401
    assert requests.get(f"{API}/plans").status_code == 401
    assert requests.get(f"{API}/billing/status").status_code == 401


def test_logout(session):
    r = session.post(f"{API}/auth/logout")
    assert r.status_code == 200
    assert session.get(f"{API}/auth/me").status_code == 401
