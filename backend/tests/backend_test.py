"""FitCheck backend auth tests."""
import os
import uuid
import requests
import pytest

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") else "https://sleek-workout-2.preview.emergentagent.com"
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


# --- Register ---
def test_register_success(session, creds):
    r = session.post(f"{API}/auth/register", json=creds)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["email"] == creds["email"]
    assert "id" in data and isinstance(data["id"], str)
    assert "created_at" in data
    # Cookies set
    assert "access_token" in session.cookies
    assert "refresh_token" in session.cookies


def test_register_duplicate(session, creds):
    r = session.post(f"{API}/auth/register", json=creds)
    assert r.status_code == 400
    assert "already registered" in r.json().get("detail", "").lower()


def test_register_short_password():
    r = requests.post(f"{API}/auth/register", json={"email": rand_email(), "password": "abc"})
    assert r.status_code == 422


def test_register_invalid_email():
    r = requests.post(f"{API}/auth/register", json={"email": "notanemail", "password": "Passw0rd!"})
    assert r.status_code == 422


# --- Me ---
def test_me_authenticated(session, creds):
    r = session.get(f"{API}/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == creds["email"]


def test_me_unauthenticated():
    r = requests.get(f"{API}/auth/me")
    assert r.status_code == 401


# --- Logout ---
def test_logout(session):
    r = session.post(f"{API}/auth/logout")
    assert r.status_code == 200
    assert r.json().get("ok") is True
    # Fresh request without cookies should be 401
    fresh = requests.get(f"{API}/auth/me")
    assert fresh.status_code == 401


# --- Login ---
def test_login_success(creds):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=creds)
    assert r.status_code == 200, r.text
    assert r.json()["email"] == creds["email"]
    assert "access_token" in s.cookies
    # me works
    me = s.get(f"{API}/auth/me")
    assert me.status_code == 200


def test_login_wrong_password(creds):
    r = requests.post(f"{API}/auth/login", json={"email": creds["email"], "password": "wrongpass"})
    assert r.status_code == 401
    assert "invalid" in r.json().get("detail", "").lower()


def test_login_unknown_user():
    r = requests.post(f"{API}/auth/login", json={"email": rand_email(), "password": "Passw0rd!"})
    assert r.status_code == 401


# --- Refresh ---
def test_refresh_token(creds):
    s = requests.Session()
    s.post(f"{API}/auth/login", json=creds)
    r = s.post(f"{API}/auth/refresh")
    assert r.status_code == 200
    assert r.json().get("ok") is True


def test_refresh_no_token():
    r = requests.post(f"{API}/auth/refresh")
    assert r.status_code == 401
