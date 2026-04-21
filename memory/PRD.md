# FitCheck — Product Requirements Document

## Original problem statement
Dark-mode landing page for a fitness tracking + workout planner (FitCheck). Deep charcoal + neon green (#39FF14) + white. Stripe/Vercel polish with Apple Fitness inspiration.

## User iterations
1. Landing page MVP with email/password signup stored in MongoDB, minimal sections (Hero, Features, Footer).
2. Add Contact Us (GitHub + Instagram), Premium AI Buddy subscription, animations, make every button functional.
3. Email set to aaronsamuel0205@gmail.com; add Google sign-in/sign-up; make the site user-ready.
4. **Make everything FREE — no subscription; AI Buddy is free for everyone; site's function & purpose should actually work.**

## User personas
- Fitness enthusiast logging sessions daily.
- Coached athlete following adaptive plans.
- Busy professional wanting low-friction Apple Fitness-level polish.

## Architecture
- **Frontend:** React 19, Tailwind (dark), framer-motion, lucide-react, recharts, sonner. Fonts: Outfit + Manrope. Auth modal shared via `AuthUIContext`. Routes: `/` Landing, `/app` Dashboard (auth-guarded). GoogleCallbackHandler handles `#session_id=` exchange.
- **Backend:** FastAPI + motor. bcrypt + JWT HS256 httpOnly cookies (access 15m / refresh 7d). Claude Sonnet 4.5 via `EMERGENT_LLM_KEY` (emergentintegrations). Emergent Google OAuth via `/api/auth/google/exchange`.
- **DB collections:** `users` (unique `email`), `workouts` (user_id+date), `plans` (user_id+created_at), `chat_messages` (user_id+created_at).

## What's implemented
**Landing**
- Hero with animated neon glow + pulsing "proof" headline, Features (3 cards), How it works (3 steps + neon connector), Contact (GitHub @Aaron-Samuel05, Instagram @aaron_samuel05, email aaronsamuel0205@gmail.com), Footer (social icons + "Built by @Aaron-Samuel05").
- Sign up / Log in modal with both Google OAuth and email+password. Success → navigates to `/app`.

**Dashboard (`/app`, authenticated)**
- Stats cards: workouts, total volume, total sets, streak days.
- 8-week weekly volume bar chart (recharts).
- Log Workout modal: workout name + date + multiple exercises × multiple sets (reps/weight). Auto-computes volume = Σ reps × weight.
- Recent workouts list with per-card summary and delete.
- Plans panel: name + goal + multiple days (each with free-form exercise list), save + delete.

**AI Buddy**
- Floating launcher on every page; free for any authenticated user.
- Premium-gated flow and Pricing section have been **removed**.

**Auth**
- Email+password + Emergent-managed Google OAuth. Both issue the same JWT cookies.

## Prioritized backlog
**P1**
- Split `server.py` into `routes/auth.py`, `routes/workouts.py`, `routes/plans.py`, `routes/ai.py`.
- Split `Dashboard.jsx` into `components/dashboard/*` (LogWorkoutModal, PlansPanel, WorkoutCard, StatCard, WeeklyChart).
- Rollback orphaned user message in `/api/ai/chat` when Claude call fails.
- Explicit `CORS_ORIGINS` allowlist + `secure=True` cookies in production.

**P2**
- Password reset flow + axios 401 refresh interceptor.
- Streaks UI (show best streak, per-day chart).
- Workout → Plan linkage: "Start today's plan" button that pre-fills the Log Workout modal.
- Brute-force lockout on `/auth/login`.

**P3**
- Exercise library with form cues that AI Buddy can reference.
- Personal records (PR) tracking per exercise.
- Apple Health / Google Fit import on first run.
- SEO / OG image for the landing page.

## Next tasks
1. Modularize server.py and Dashboard.jsx.
2. AI chat transactional write (rollback user turn if LLM fails).
3. Add password reset + axios refresh interceptor.
