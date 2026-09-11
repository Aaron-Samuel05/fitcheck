from pathlib import Path
import re

ROOT = Path('.')

# ---------------- backend ----------------
p = ROOT / 'backend/server.py'
s = p.read_text()

s = s.replace(
    'from fastapi.responses import FileResponse',
    'from fastapi.responses import FileResponse, RedirectResponse',
    1,
)
s = s.replace(
    '''from fastapi.middleware.cors import CORSMiddleware
from emergentintegrations.llm.chat import LlmChat, UserMessage''',
    '''from fastapi.middleware.cors import CORSMiddleware
from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware''',
    1,
)
s = s.replace(
    '''REFRESH_TTL_DAYS = int(os.environ.get("REFRESH_TTL_DAYS", "30"))
FREE_AI_DAILY_LIMIT''',
    '''REFRESH_TTL_DAYS = int(os.environ.get("REFRESH_TTL_DAYS", "30"))
AUTH_VERSION = "2026-09-11-auth-v2"
FREE_AI_DAILY_LIMIT''',
    1,
)
s = re.sub(
    r'''\nclass GoogleExchangeRequest\(BaseModel\):\n    session_id: str\n\n''',
    '\n',
    s,
    count=1,
)

old_app = '''app = FastAPI(title="FitCheck API")
api_router = APIRouter(prefix="/api")'''
new_app = '''app = FastAPI(title="FitCheck API")

auth_session_secret = os.environ.get("AUTH_SESSION_SECRET") or os.environ.get("JWT_SECRET", "fitcheck-development-secret")
app.add_middleware(
    SessionMiddleware,
    secret_key=auth_session_secret,
    same_site="lax",
    https_only=os.environ.get("COOKIE_SECURE", "true").lower() == "true",
)

oauth = OAuth()
oauth.register(
    name="google",
    client_id=os.environ.get("GOOGLE_CLIENT_ID", ""),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET", ""),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile", "code_challenge_method": "S256"},
)

api_router = APIRouter(prefix="/api")'''
if old_app not in s:
    raise SystemExit('FastAPI bootstrap not found')
s = s.replace(old_app, new_app, 1)

s = s.replace(
    '''            "type": "access",
            "exp":''',
    '''            "type": "access",
            "ver": AUTH_VERSION,
            "exp":''',
    1,
)
s = s.replace(
    '''            "type": "refresh",
            "exp":''',
    '''            "type": "refresh",
            "ver": AUTH_VERSION,
            "exp":''',
    1,
)
s = s.replace(
    '''        if payload.get("type") != "access":
            raise HTTPException(401, "Invalid token type")''',
    '''        if payload.get("type") != "access" or payload.get("ver") != AUTH_VERSION:
            raise HTTPException(401, "Session expired. Please sign in again.")''',
    1,
)
s = s.replace(
    '''        if payload.get("type") != "refresh":
            raise HTTPException(401, "Invalid token type")''',
    '''        if payload.get("type") != "refresh" or payload.get("ver") != AUTH_VERSION:
            raise HTTPException(401, "Session expired. Please sign in again.")''',
    1,
)

google_pattern = re.compile(
    r'''\n@api_router\.post\("/auth/google/exchange"\).*?\n\n# ---------------- AI Buddy ----------------''',
    re.S,
)
google_match = google_pattern.search(s)
if not google_match:
    raise SystemExit('Old Emergent Google auth route not found')

google_block = '''
@api_router.get("/auth/google", name="google_login")
async def google_login(request: Request):
    if not os.environ.get("GOOGLE_CLIENT_ID") or not os.environ.get("GOOGLE_CLIENT_SECRET"):
        raise HTTPException(503, "Google authentication is not configured on this deployment.")
    redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI", "").strip() or str(request.url_for("google_callback"))
    return await oauth.google.authorize_redirect(request, redirect_uri)


@api_router.get("/auth/google/callback", name="google_callback")
async def google_callback(request: Request):
    frontend_url = os.environ.get("FRONTEND_URL", "").strip().rstrip("/")
    if not frontend_url:
        raise HTTPException(503, "FRONTEND_URL is not configured.")
    try:
        token = await oauth.google.authorize_access_token(request)
        google_user = token.get("userinfo") or await oauth.google.userinfo(token=token)
        google_sub = str(google_user.get("sub", "")).strip()
        email = str(google_user.get("email", "")).strip().lower()
        verified = google_user.get("email_verified")
        name = str(google_user.get("name", "")).strip()
        if not google_sub or not email or verified is False:
            raise ValueError("Google did not return a verified account")

        user = await db.users.find_one({"$or": [{"google_sub": google_sub}, {"email": email}]})
        if not user:
            user = {
                "id": str(uuid.uuid4()),
                "email": email,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "auth_provider": "google",
                "google_sub": google_sub,
                "name": name,
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
            updates = {"google_sub": google_sub, "auth_provider": "google"}
            if not user.get("name") and name:
                updates["name"] = name
            await db.users.update_one({"id": user["id"]}, {"$set": updates})
            user = await db.users.find_one({"id": user["id"]})

        access_token = create_access(user["id"], user["email"])
        refresh_token = create_refresh(user["id"])
        response = RedirectResponse(url=f"{frontend_url}/app?google=success", status_code=302)
        set_auth_cookies(response, access_token, refresh_token)
        return response
    except HTTPException:
        raise
    except Exception:
        logging.exception("Google OAuth callback failed")
        return RedirectResponse(url=f"{frontend_url}/?google=error", status_code=302)


# ---------------- AI Buddy ----------------'''
s = s[:google_match.start()] + google_block + s[google_match.end():]

ai_pattern = re.compile(
    r'''async def generate_ai_reply\(session_id: str, user_message: str, user_id: str\) -> str:.*?\n\n@api_router\.get\("/ai/status"\)''',
    re.S,
)
ai_match = ai_pattern.search(s)
if not ai_match:
    raise SystemExit('Old Emergent AI implementation not found')

ai_block = '''async def generate_ai_reply(session_id: str, user_message: str, user_id: str) -> str:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(503, "AI Buddy is not configured. Add GEMINI_API_KEY to the backend environment and redeploy.")

    user = await db.users.find_one({"id": user_id})
    profile = profile_from_user(user or {})
    profile_text = ", ".join(f"{k}: {v}" for k, v in profile.items() if v not in (None, "")) or "No profile details provided"
    previous = await db.chat_messages.find({"user_id": user_id, "session_id": session_id}).sort("created_at", -1).to_list(12)
    previous.reverse()
    context = chr(10).join(f"{m.get('role', 'user').upper()}: {m.get('message', '')}" for m in previous)
    prompt = f"User profile: {profile_text}{chr(10)}{chr(10)}Conversation so far:{chr(10)}{context}{chr(10)}{chr(10)}USER: {user_message}{chr(10)}{chr(10)}Reply as FitCheck Coach."

    model_name = os.environ.get("FITCHECK_AI_MODEL", "gemini-3.6-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
    payload = {
        "system_instruction": {"parts": [{"text": AI_SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
    }
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(url, headers={"x-goog-api-key": api_key, "Content-Type": "application/json"}, json=payload)
        if response.status_code >= 400:
            logging.error("Gemini API error %s: %s", response.status_code, response.text[:500])
            raise HTTPException(502, "AI Buddy is temporarily unavailable. Please try again.")
        data = response.json()
        reply = str(data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")).strip()
        if not reply:
            raise HTTPException(502, "AI Buddy returned an empty response. Please try again.")
        return reply
    except HTTPException:
        raise
    except Exception:
        logging.exception("Gemini AI provider error")
        raise HTTPException(502, "AI Buddy is temporarily unavailable. Please try again.")


@api_router.get("/ai/status")'''
s = s[:ai_match.start()] + ai_block + s[ai_match.end():]
s = s.replace(
    'key_configured = bool(os.environ.get("EMERGENT_LLM_KEY", "").strip())',
    'key_configured = bool(os.environ.get("GEMINI_API_KEY", "").strip())',
    1,
)

cookie_pattern = re.compile(
r'''def set_auth_cookies\(response: Response, access_token: str, refresh_token: str\):.*?\n\n''',
    re.S,
)
cookie_match = cookie_pattern.search(s)
if not cookie_match:
    raise SystemExit('Cookie helper not found')
cookie_block = '''def set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    secure = os.environ.get("COOKIE_SECURE", "true").lower() == "true"
    samesite = "none" if secure else "lax"
    response.set_cookie("access_token", access_token, httponly=True, samesite=samesite, secure=secure, path="/")
    response.set_cookie("refresh_token", refresh_token, httponly=True, samesite=samesite, secure=secure, path="/api/auth")

'''
s = s[:cookie_match.start()] + cookie_block + s[cookie_match.end():]
s = s.replace(
    '        response.set_cookie("access_token", access_token, httponly=True, samesite="lax", secure=True, path="/")',
    '''        secure = os.environ.get("COOKIE_SECURE", "true").lower() == "true"
        samesite = "none" if secure else "lax"
        response.set_cookie("access_token", access_token, httponly=True, samesite=samesite, secure=secure, path="/")''',
    1,
)
p.write_text(s)

# ---------------- frontend ----------------
p = ROOT / 'frontend/src/components/AuthModal.jsx'
s = p.read_text()
if 'import { API } from "@/lib/api";' not in s:
    s = s.replace('import { toast } from "sonner";', 'import { toast } from "sonner";\nimport { API } from "@/lib/api";', 1)
s = re.sub(
    r'''function startGoogleAuth\(\) \{.*?\n\}''',
    '''function startGoogleAuth() {
  window.location.assign(`${API}/auth/google`);
}''',
    s,
    count=1,
    flags=re.S,
)
p.write_text(s)

p = ROOT / 'frontend/src/components/GoogleCallbackHandler.jsx'
p.write_text('''import { useEffect, useRef } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";

export default function GoogleCallbackHandler() {
  const { refresh } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const processed = useRef(false);

  useEffect(() => {
    if (processed.current) return;
    const status = new URLSearchParams(location.search).get("google");
    if (!status) return;
    processed.current = true;

    if (status === "error") {
      toast.error("Google sign-in failed. Please try again.");
      navigate("/", { replace: true });
      return;
    }

    (async () => {
      try {
        const me = await refresh?.();
        if (!me) throw new Error("Google session could not be loaded.");
        toast.success("Signed in with Google.");
        navigate("/app", { replace: true });
      } catch (e) {
        toast.error(e.message || "Google sign-in failed.");
        navigate("/", { replace: true });
      }
    })();
  }, [location.search, refresh, navigate]);

  return null;
}
''')

p = ROOT / 'frontend/src/context/AuthContext.jsx'
s = p.read_text()
old = '''    const hasSessionId = new URLSearchParams(window.location.hash.replace(/^#/, "")).has("session_id");
    const token = localStorage.getItem("token");

    if (hasSessionId) return;

    if (!token || token === "undefined" || token === "null") {
      localStorage.removeItem("token");
      setUser(false);
      return;
    }

    fetchMe();'''
new = '''    const googleCallback = new URLSearchParams(window.location.search).get("google") === "success";
    const token = localStorage.getItem("token");

    if (!token || token === "undefined" || token === "null") {
      fetchMe().then((result) => {
        if (!result && !googleCallback) setUser(false);
      });
      return;
    }

    fetchMe();'''
if old not in s:
    raise SystemExit('AuthContext bootstrap not found')
p.write_text(s.replace(old, new, 1))

# ---------------- config/dependencies ----------------
p = ROOT / 'backend/.env.example'
s = p.read_text()
s = s.replace('EMERGENT_LLM_KEY=\nFITCHECK_AI_MODEL=gemini-3-flash-preview', 'GEMINI_API_KEY=\nFITCHECK_AI_MODEL=gemini-3.6-flash')
if 'GOOGLE_CLIENT_ID=' not in s:
    s += '\n# Google OAuth\nGOOGLE_CLIENT_ID=\nGOOGLE_CLIENT_SECRET=\nGOOGLE_REDIRECT_URI=https://YOUR-BACKEND-DOMAIN/api/auth/google/callback\nAUTH_SESSION_SECRET=\nCOOKIE_SECURE=true\nFRONTEND_URL=https://fitcheck-org.vercel.app\n'
p.write_text(s)

p = ROOT / 'backend/requirements.txt'
lines = [x for x in p.read_text().splitlines() if not x.startswith('emergentintegrations==')]
if not any(x.lower().startswith('authlib') for x in lines):
    lines.append('authlib>=1.7.0')
if not any(x.lower().startswith('itsdangerous') for x in lines):
    lines.append('itsdangerous>=2.2.0')
p.write_text(chr(10).join(lines) + chr(10))

# Make sure the old provider is actually gone from the source/config we touched.
for path in [
    ROOT / 'backend/server.py',
    ROOT / 'backend/.env.example',
    ROOT / 'backend/requirements.txt',
    ROOT / 'frontend/src/components/AuthModal.jsx',
    ROOT / 'frontend/src/components/GoogleCallbackHandler.jsx',
]:
    text = path.read_text()
    if 'auth.emergentagent.com' in text or 'EMERGENT_LLM_KEY' in text or 'emergentintegrations' in text:
        raise SystemExit(f'Emergent reference remains in {path}')

print('FitCheck auth migration completed')
