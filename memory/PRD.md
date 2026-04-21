# FitCheck — Product Requirements Document

## Original problem statement
Create a modern, dark-mode landing page for a new fitness tracking and workout planner web app. Use a color palette of deep charcoal, neon green accents, and white text. Hero section with bold headline, subheadline, and a prominent 'Get Started Free' button. Below the hero, a Features section with a 3-column grid of cards (Log Workouts, Track Progress, Custom Plans) with sleek icons. Clean footer at the bottom. Highly polished minimalist Tailwind design similar to Stripe/Vercel with inspiration from Apple Fitness.

## User choices (explicit)
- Brand name: **FitCheck**
- 'Get Started Free' → **simple signup form (email + password) stored in MongoDB**
- Sections: **keep it minimal (Hero + Features + Footer only)**

## User personas
- **Fitness enthusiast** — wants a clean, distraction-free place to log sets/reps and see progress trends.
- **Coached athlete / program follower** — wants custom/adaptive plans and concrete weekly signal on progress.
- **Busy professional** — values speed: low-friction logging, mobile-ready, Apple Fitness-level polish.

## Architecture
- **Frontend:** React 19 + React Router, Tailwind (dark), framer-motion, lucide-react icons, sonner toasts. Fonts: Outfit (headings) + Manrope (body).
- **Backend:** FastAPI, bcrypt + PyJWT (HS256) auth in httpOnly cookies (`access_token` 15m, `refresh_token` 7d), MongoDB via motor.
- **DB:** `users` collection with unique index on `email`. UUID string `id` field (not `_id`).

## What's implemented (2026-04-21)
- Dark-mode landing page: fixed glass navbar, hero with animated headline + neon green CTA, 3-card features grid with hover neon glow, minimal footer.
- Full auth flow: register, login, logout, `/me`, `/refresh` under `/api/auth/*` with httpOnly cookies.
- Signup/Login modal with Escape + outside-click close, inline errors, loading state, sonner success toasts.
- Navbar reflects auth state (Log in + Sign up ↔ email + Log out).
- End-to-end tested: 13/13 backend pytest cases + full Playwright frontend flow passed.

## Prioritized backlog
**P1**
- Post-auth dashboard: workout logging (sets/reps/RPE), progress charts, custom plan builder.
- Server-side session refresh on 401 via axios interceptor calling `/auth/refresh`.
- Password reset (forgot/reset endpoints already outlined in playbook, not yet wired).
- CORS: replace `*` fallback with explicit preview + prod origins.

**P2**
- Brute-force lockout on `/auth/login` (5/15min via `login_attempts` collection).
- Secure cookie flag driven by env (`COOKIE_SECURE=true` in production).
- Marketing sections: pricing, testimonials, "How it works".
- SEO: meta tags, OG image, sitemap, favicon.

**P3**
- Social proof strip, blog, API docs, Apple Health import.

## Next tasks
1. Build authenticated dashboard (workout log + progress chart).
2. Add `/auth/forgot-password` and `/auth/reset-password` endpoints + email delivery.
3. Add axios response interceptor for automatic refresh on 401.
