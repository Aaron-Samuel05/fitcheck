# FitCheck production deployment

## Vercel

This repository is configured as one Vercel project:

- React app: `/`
- FastAPI: `/api/*`
- API entrypoint: `api/index.py`
- Client-side routes such as `/app` rewrite to the React app

Vercel can deploy `api/index.py` as a FastAPI Python function and route `/api/*` to it. Keep the frontend API URL empty for this same-origin deployment.

## Required Vercel environment variables

Set these in the Vercel project for **Production** (and Preview if you want preview environments to work):

```text
MONGO_URL=<persistent MongoDB Atlas connection string>
DB_NAME=fitcheck
JWT_SECRET=<long random secret>
ACCESS_TTL_MIN=60
REFRESH_TTL_DAYS=30

EMERGENT_SESSION_URL=https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data
EMERGENT_LLM_KEY=<server-side Emergent LLM key>
FITCHECK_AI_MODEL=gemini-3-flash-preview
FREE_AI_DAILY_LIMIT=5

FRONTEND_URL=https://fitcheck-org.vercel.app
CORS_ORIGINS=https://fitcheck-org.vercel.app

STRIPE_SECRET_KEY=<Stripe secret key>
STRIPE_WEBHOOK_SECRET=<Stripe webhook signing secret>
STRIPE_PRICE_BUDDY_PRO_MONTHLY=<Stripe recurring monthly Price ID>
STRIPE_PRICE_BUDDY_PRO_YEARLY=<Stripe recurring yearly Price ID>
```

Do **not** put any of the server-side secrets in `frontend/.env` or React source code.

## Stripe

Create two recurring prices for the AI Buddy product:

- AI Buddy Pro — $9.99/month
- AI Buddy Pro — $79.99/year

Configure the Stripe webhook URL as:

```text
https://fitcheck-org.vercel.app/api/webhook/stripe
```

At minimum, send these events:

- `checkout.session.completed`
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.paid`
- `invoice.payment_failed`

The webhook must use the signing secret stored in `STRIPE_WEBHOOK_SECRET`.

## Database

Production must use a persistent MongoDB deployment such as MongoDB Atlas. The local in-memory fallback exists for development resilience only and must not be treated as production storage.

## Google login

The frontend redirects to Emergent's Google authentication broker and returns with `#session_id=...`. The Vercel API wrapper verifies that session with `EMERGENT_SESSION_URL` before creating the FitCheck JWT session.

For production, the OAuth redirect should be the deployed site's `/app` route.

## AI Buddy

Free users receive the configured daily preview allowance. AI Buddy Pro users receive unlimited AI chat while their Stripe subscription is `active` or `trialing`.

The AI key is never sent to the browser.

## Smoke test after deployment

1. Open `/` and refresh it.
2. Create an email account.
3. Refresh `/app` directly.
4. Save profile information and refresh.
5. Log a workout and verify dashboard totals change.
6. Delete a workout and verify totals recalculate.
7. Create and delete a training plan.
8. Open AI Buddy and send a message.
9. Sign out and verify `/app` no longer exposes the dashboard.
10. Test Google sign-in with a real Google account.
11. Test Stripe Checkout in test mode.
12. Confirm the Stripe webhook changes the user's plan to `buddy_pro`.
13. Return to `/app` and confirm AI Buddy Pro is active.
14. Open Manage subscription and verify Stripe Customer Portal works.
