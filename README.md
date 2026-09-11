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
