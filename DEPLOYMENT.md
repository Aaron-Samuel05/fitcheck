# FitCheck production deployment

FitCheck is deployed as **one FastAPI Vercel application**. The FastAPI app is the only server entrypoint and serves the compiled React frontend plus `/api/*` routes from the same origin.

## Architecture

- Root entrypoint: `app.py`
- React source: `frontend/`
- React production build: `frontend/build/`
- API: `backend/clean.py`
- Same-origin API URL: `/api/*`
- Vercel Python version: 3.12

The root `pyproject.toml` tells Vercel to build the React app with `cd frontend && npm install && npm run build`, then run `app:app`.

## Required Vercel environment variables

Set these in Vercel Production:

```text
MONGO_URL=<persistent MongoDB Atlas connection string>
DB_NAME=fitcheck
JWT_SECRET=<long random secret>
ACCESS_TTL_MIN=60
REFRESH_TTL_DAYS=30
AUTH_SESSION_SECRET=<long random session secret>
COOKIE_SECURE=true

GOOGLE_CLIENT_ID=<Google OAuth client id>
GOOGLE_CLIENT_SECRET=<Google OAuth client secret>
GOOGLE_REDIRECT_URI=https://fitcheck-org.vercel.app/api/auth/google/callback

GEMINI_API_KEY=<server-side Gemini key>
FITCHECK_AI_MODEL=gemini-2.5-flash
FREE_AI_DAILY_LIMIT=5

FRONTEND_URL=https://fitcheck-org.vercel.app
CORS_ORIGINS=https://fitcheck-org.vercel.app

STRIPE_SECRET_KEY=<Stripe secret key>
STRIPE_WEBHOOK_SECRET=<Stripe webhook signing secret>
STRIPE_PRICE_BUDDY_PRO_MONTHLY=<Stripe recurring monthly Price ID>
STRIPE_PRICE_BUDDY_PRO_YEARLY=<Stripe recurring yearly Price ID>
```

Never commit production secrets and never expose server-side keys in React source.

## Smoke test

1. Open `/`.
2. Create an email account.
3. Refresh `/app` directly.
4. Save profile information and refresh.
5. Log a workout and verify dashboard totals change.
6. Delete a workout and verify totals recalculate.
7. Create and delete a training plan.
8. Open AI Buddy and send a message.
9. Sign out and verify `/app` is protected.
10. Test Google sign-in.
11. Test Stripe Checkout in test mode.
12. Confirm the Stripe webhook updates the subscription state.
13. Test the Manage Subscription flow.
