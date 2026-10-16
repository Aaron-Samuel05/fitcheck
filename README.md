# FitCheck

FitCheck is a focused workout logger: record sessions, see your consistency, and optionally unlock AI Buddy coaching.

## Stack
- FastAPI on Vercel
- Vanilla HTML/CSS/JS frontend served by FastAPI
- MongoDB when `MONGO_URL` is configured
- Gemini REST API for AI Buddy
- Stripe Checkout for Pro
- Google OAuth + email/password authentication

## Local
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app:app --reload
```

Open `http://localhost:8000`.

## Vercel
Vercel detects the root `app.py` FastAPI application directly. No `vercel.json`, Vercel Services, Render service, or frontend build step is required.

### Environment variables
`MONGO_URL`, `DB_NAME`, `JWT_SECRET`, `FRONTEND_URL`, `COOKIE_SECURE`, `GEMINI_API_KEY`, `FITCHECK_AI_MODEL`, `STRIPE_SECRET_KEY`, `STRIPE_PRICE_ID`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`.

The app can boot without MongoDB for development, but production should use MongoDB.

## Google sign-in troubleshooting (Vercel)

FitCheck owns the Google OAuth flow: the frontend opens `/api/auth/google`, Google returns to FitCheck's callback, and FitCheck creates the session before redirecting to `/app`. The callback must not point to a third-party agent.

Set these values in the **Vercel Production** environment and redeploy:

- `FRONTEND_URL=https://fitcheck-org.vercel.app`
- `GOOGLE_REDIRECT_URI=https://fitcheck-org.vercel.app/api/auth/google/callback`
- `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` from the same Google OAuth 2.0 Web application client
- `JWT_SECRET` and `AUTH_SESSION_SECRET` as long, unique random secrets
- `MONGO_URL` pointing to the production MongoDB database

In Google Cloud Console, under **APIs & Services → Credentials → OAuth 2.0 Client ID**, add exactly
`https://fitcheck-org.vercel.app/api/auth/google/callback` to **Authorized redirect URIs** and `https://fitcheck-org.vercel.app` to **Authorized JavaScript origins**. Remove any redirect URI pointing to an Emergent domain if it is not intentionally used by another app.

After redeploying, open `https://fitcheck-org.vercel.app/api/health` and verify that `google` is `configured`, `backend_loaded` is true, and `missing_environment` does not list the required production variables. The health endpoint reports configuration presence only; it does not verify credentials with Google or MongoDB. Never put secret values in source control.

If the live site still sends users to an Emergent domain after this change, the production alias is likely serving a different/stale deployment or the Google OAuth client still has an Emergent redirect URI. Check the Vercel production deployment's Git commit and environment before changing app features.
