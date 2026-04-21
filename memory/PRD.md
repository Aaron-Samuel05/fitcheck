# FitCheck — Product Requirements Document

## Original problem statement
Dark-mode landing page for a fitness tracking + workout planner (FitCheck). Deep charcoal + neon green (#39FF14) + white. Hero + 3-column Features + Footer. Stripe/Vercel polish with Apple Fitness inspiration.

## User iterations
1. Build landing page with FitCheck brand, email/password signup stored in MongoDB, minimal sections only.
2. Add Contact Us (GitHub https://github.com/Aaron-Samuel05 + Instagram https://www.instagram.com/aaron_samuel05/), Premium AI Buddy subscription, more animations, make every button functional.
3. Email aaronsamuel0205@gmail.com, add Google sign-in/sign-up, make the site user-ready.

## User personas
- Fitness enthusiast — low-friction logging, clean progress trends.
- Coached athlete — adaptive plans + weekly signal.
- Busy professional — mobile-ready, Apple Fitness polish.

## Architecture
- **Frontend:** React 19 + React Router, Tailwind (dark), framer-motion, lucide-react, sonner. Fonts: Outfit + Manrope. AuthUIContext for shared signup/login modal, PaymentReturnHandler for Stripe redirect polling, GoogleCallbackHandler for Emergent OAuth hash exchange.
- **Backend:** FastAPI + motor (async MongoDB). Auth: bcrypt + JWT (HS256) httpOnly cookies (access_token 15m, refresh_token 7d). AI: Claude Sonnet 4.5 via EMERGENT_LLM_KEY (emergentintegrations). Payments: Stripe test mode via emergentintegrations. Google OAuth via Emergent demobackend session-data endpoint.
- **DB collections:** `users` (unique `email`), `payment_transactions` (unique `session_id`), `chat_messages` (index on user_id + created_at).

## What's implemented
**2026-04-21 — Landing MVP**
- Hero + Features (3 cards) + Footer. Email/password auth with httpOnly JWT cookies. 13/13 backend + full frontend test pass.

**2026-04-21 — Premium, AI Buddy, Contact, Google Auth**
- Sections: Hero, Features, HowItWorks, Pricing (Free + Premium $9.99/mo), Contact (GitHub + Instagram + email aaronsamuel0205@gmail.com), Footer (with GitHub + Instagram icons + "Built by @Aaron-Samuel05").
- Stripe test-mode checkout (plan_id=`premium_monthly`, $9.99 USD) → flips `users.is_premium=true` via status polling + webhook.
- AI Buddy floating launcher: free users see Premium gate with Upgrade CTA; premium users chat with Claude Sonnet 4.5 (`/api/ai/chat` persists history in `chat_messages`).
- Emergent-managed Google Auth: "Continue with Google" in AuthModal → `auth.emergentagent.com` flow → `/api/auth/google/exchange` upserts user by email and issues the same JWT cookies.
- Animations: pulsing hero glow, animated "proof" neon text, staggered section reveals, AI Buddy launcher ping.
- 23/23 backend pytest + full frontend Playwright pass.

## Prioritized backlog
**P1**
- Authenticated dashboard: workout logging (sets/reps/RPE/tempo) + progress charts.
- Rollback orphaned user message in `/api/ai/chat` when Claude call fails.
- Server-side origin_url allowlist for Stripe success/cancel URLs (open-redirect hardening).
- Replace CORS `*` fallback with explicit origin list; set cookies `secure=True` via env flag for production.

**P2**
- Split `server.py` into `routes/auth.py`, `routes/payments.py`, `routes/ai.py` as surface grows.
- Password reset flow + axios 401 interceptor calling `/api/auth/refresh`.
- Brute-force lockout on `/auth/login` (5/15min via `login_attempts` collection).
- "Add password" flow for Google-only users so they can later log in with email+password.

**P3**
- Manage-billing portal via Stripe Customer Portal.
- Apple Health / Google Fit import on first-run.
- Marketing: testimonials, blog, SEO meta/OG images.

## Next tasks
1. Build authenticated dashboard (workout log + progress charts).
2. Tighten prod config (CORS allowlist, secure cookies, Stripe origin allowlist).
3. Implement password reset + 401 refresh interceptor.
