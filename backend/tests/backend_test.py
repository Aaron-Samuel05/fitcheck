"""FitCheck backend tests — auth, Google exchange, payments, AI chat."""
import os
import uuid
import requests
import pytest
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://sleek-workout-2.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")


def rand_email():
    return f"qa.user+{uuid.uuid4().hex[:8]}@fitcheck.app"


@pytest.fixture(scope="module")
def mongo_db():
    c = MongoClient(MONGO_URL)
    yield c[DB_NAME]
    c.close()


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


# --- Register / login / me / logout / refresh ---
def test_register_success(session, creds):
    r = session.post(f"{API}/auth/register", json=creds)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["email"] == creds["email"]
    assert "id" in data
    assert data["is_premium"] is False
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
    assert body["is_premium"] is False


def test_me_unauthenticated():
    r = requests.get(f"{API}/auth/me")
    assert r.status_code == 401


def test_refresh_flow(creds):
    s = requests.Session()
    s.post(f"{API}/auth/login", json=creds)
    r = s.post(f"{API}/auth/refresh")
    assert r.status_code == 200
    assert r.json().get("ok") is True


def test_refresh_no_token():
    r = requests.post(f"{API}/auth/refresh")
    assert r.status_code == 401


def test_login_wrong_password(creds):
    r = requests.post(f"{API}/auth/login", json={"email": creds["email"], "password": "wrong"})
    assert r.status_code == 401


def test_login_unknown_user():
    r = requests.post(f"{API}/auth/login", json={"email": rand_email(), "password": "Passw0rd!"})
    assert r.status_code == 401


# --- Google OAuth exchange ---
def test_google_exchange_bogus_session():
    r = requests.post(f"{API}/auth/google/exchange", json={"session_id": "definitely-not-real-session-12345"})
    assert r.status_code == 401


def test_google_exchange_missing_field():
    r = requests.post(f"{API}/auth/google/exchange", json={})
    assert r.status_code == 422


# --- Payments ---
def test_payments_plans_public():
    r = requests.get(f"{API}/payments/plans")
    assert r.status_code == 200
    plans = r.json().get("plans", [])
    assert any(p["id"] == "premium_monthly" for p in plans)
    plan = next(p for p in plans if p["id"] == "premium_monthly")
    assert plan["amount"] == 9.99
    assert plan["currency"] == "usd"


def test_payments_checkout_requires_auth():
    r = requests.post(f"{API}/payments/checkout", json={"plan_id": "premium_monthly", "origin_url": BASE_URL})
    assert r.status_code == 401


def test_payments_checkout_creates_session(session, mongo_db):
    r = session.post(f"{API}/payments/checkout", json={"plan_id": "premium_monthly", "origin_url": BASE_URL})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("url", "").startswith("http")
    assert body.get("session_id")
    # Transaction persisted with status=initiated
    txn = mongo_db.payment_transactions.find_one({"session_id": body["session_id"]})
    assert txn is not None
    assert txn["status"] == "initiated"
    assert txn["payment_status"] == "unpaid"
    assert txn["amount"] == 9.99


def test_payments_checkout_invalid_plan(session):
    r = session.post(f"{API}/payments/checkout", json={"plan_id": "bogus", "origin_url": BASE_URL})
    assert r.status_code == 400


def test_payments_status_requires_auth():
    r = requests.get(f"{API}/payments/status/some_session_id")
    assert r.status_code == 401


def test_payments_status_not_found(session):
    r = session.get(f"{API}/payments/status/nonexistent_session_{uuid.uuid4().hex}")
    assert r.status_code == 404


# --- AI chat ---
def test_ai_chat_unauthenticated():
    r = requests.post(f"{API}/ai/chat", json={"message": "hi"})
    assert r.status_code == 401


def test_ai_chat_free_user_blocked(session):
    r = session.post(f"{API}/ai/chat", json={"message": "hi"})
    assert r.status_code == 402
    assert "premium" in r.json().get("detail", "").lower()


def test_ai_history_free_user_blocked(session):
    r = session.get(f"{API}/ai/history")
    assert r.status_code == 402


def test_ai_chat_premium_user(creds, mongo_db):
    """Flip is_premium directly in MongoDB, then exercise /ai/chat."""
    mongo_db.users.update_one({"email": creds["email"]}, {"$set": {"is_premium": True}})
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    lr = s.post(f"{API}/auth/login", json=creds)
    assert lr.status_code == 200
    assert lr.json()["is_premium"] is True

    r = s.post(f"{API}/ai/chat", json={"message": "Give me a 1 sentence motivational tip."}, timeout=60)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("session_id")
    assert isinstance(body.get("reply"), str) and len(body["reply"]) > 0

    # history returns persisted messages
    h = s.get(f"{API}/ai/history", params={"session_id": body["session_id"]})
    assert h.status_code == 200
    msgs = h.json().get("messages", [])
    assert len(msgs) >= 2
    roles = [m["role"] for m in msgs]
    assert "user" in roles and "assistant" in roles
