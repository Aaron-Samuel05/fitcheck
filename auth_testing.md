# FitCheck Auth + Features Testing Playbook

## Setup
- Backend: FastAPI at `$REACT_APP_BACKEND_URL/api` (supervisor on 0.0.0.0:8001)
- DB: MongoDB via `MONGO_URL`, DB `DB_NAME`
- Auth: bcrypt email+password + Emergent-managed Google OAuth (both issue the SAME JWT httpOnly cookies: `access_token` 15m, `refresh_token` 7d)
- Premium: Stripe test-mode (`STRIPE_API_KEY=sk_test_emergent`) — one plan `premium_monthly` at $9.99 USD
- AI Buddy: Claude Sonnet 4.5 via `EMERGENT_LLM_KEY`, gated behind `is_premium=true`

## Backend endpoints
- `POST /api/auth/register` { email, password }
- `POST /api/auth/login` { email, password }
- `POST /api/auth/logout`
- `GET  /api/auth/me` → includes `is_premium`
- `POST /api/auth/refresh`
- `POST /api/auth/google/exchange` { session_id } — Emergent Google OAuth exchange
- `GET  /api/payments/plans`
- `POST /api/payments/checkout` { plan_id, origin_url } (auth required) → { url, session_id }
- `GET  /api/payments/status/{session_id}` (auth required) → marks user `is_premium=true` when Stripe confirms payment
- `POST /api/webhook/stripe`
- `POST /api/ai/chat` { message, session_id? } (auth + premium required)
- `GET  /api/ai/history?session_id=...` (auth + premium required)

## Backend API tests (curl)

```
API_URL=$(grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d '=' -f2)

# Register → cookies set
curl -c /tmp/c.txt -s -X POST "$API_URL/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"qa+'"$RANDOM"'@fitcheck.app","password":"Passw0rd!"}'

# /me returns is_premium=false
curl -b /tmp/c.txt -s "$API_URL/api/auth/me"

# AI chat while free → 402 Premium required
curl -b /tmp/c.txt -s -o /dev/null -w "%{http_code}\n" \
  -X POST "$API_URL/api/ai/chat" \
  -H "Content-Type: application/json" \
  -d '{"message":"hi"}'

# Google exchange with a bogus session → 401
curl -s -o /dev/null -w "%{http_code}\n" \
  -X POST "$API_URL/api/auth/google/exchange" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"definitely-not-real"}'

# Stripe: create checkout
curl -b /tmp/c.txt -s -X POST "$API_URL/api/payments/checkout" \
  -H "Content-Type: application/json" \
  -d '{"plan_id":"premium_monthly","origin_url":"'"$API_URL"'"}'
```

Testing Stripe end-to-end payment completion requires using a Stripe test card in the browser. For agent-only tests, validate that `POST /api/payments/checkout` returns a `url` + `session_id` and that the `payment_transactions` collection has a doc with `status=initiated`.

## Frontend flow

1. Landing renders Hero, Features, How it works, Pricing, Contact, Footer. Nav anchors all scroll correctly.
2. Contact section shows GitHub (@Aaron-Samuel05), Instagram (@aaron_samuel05), and email `aaronsamuel0205@gmail.com` as three cards — all clickable.
3. "Get Started Free" opens signup modal. Modal now has "Sign up with Google" (top) and email/password form (below).
4. Email signup creates a user, navbar updates to show email + Log out.
5. "Continue with Google" redirects to `https://auth.emergentagent.com/?redirect=<origin>/` — verify the redirect URL is built from `window.location.origin` (not hardcoded).
6. Floating AI Buddy launcher appears bottom-right. Click → if not signed in, opens signup modal. If signed in but free, panel shows "AI Buddy is Premium" + "Upgrade to Premium" CTA that scrolls to Pricing.
7. Pricing section: Premium card "Upgrade to Premium" → calls `/api/payments/checkout`, redirects to Stripe Checkout.
8. Return from Stripe (`?payment=success&session_id=...`) triggers polling of `/api/payments/status/{id}`; once paid, toast fires, `is_premium=true`, navbar shows a **Premium** badge, AI Buddy chat becomes usable.
9. Logout clears cookies and resets the UI to signed-out.

## Google-auth-only user notes
- Emergent Google Auth returns `email, name, picture, session_token`. Our `/api/auth/google/exchange` endpoint upserts by email and issues the SAME JWT cookies as email/password auth, so all downstream endpoints work identically.
- A Google-only user has no `password_hash`, so classic `/auth/login` with that email will fail (401) — expected.
