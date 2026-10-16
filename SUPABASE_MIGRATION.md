# Supabase migration notes

## Audit snapshot (2026-10-16)

The current application is a React frontend served from the root FastAPI app, with API routes delegated to `backend.clean`. The backend currently uses MongoDB/Motor with an in-memory mock fallback, custom JWT access/refresh cookies, Authlib Google OIDC, Gemini REST, and Stripe subscriptions.

Preserve these API contracts while migrating:
- `/api/auth/register`, `/login`, `/me`, `/refresh`, `/logout`, Google sign-in
- `/api/profile`
- `/api/workouts`, `/api/workouts/stats`
- `/api/plans`
- `/api/ai/status`, `/api/ai/chat`, `/api/ai/history`
- `/api/billing/plans`, `/status`, `/checkout`, `/portal`, `/api/webhook/stripe`

## Target architecture

- Supabase Auth owns identities, password verification, OAuth and session refresh.
- Supabase Postgres owns profiles, workouts, training plans and AI chat history.
- FastAPI remains the trusted server for Gemini calls, Stripe checkout/portal creation, and Stripe webhook signature verification.
- The Supabase service-role key is server-only; never place it in React build variables or commit it.
- Client-visible tables use Row Level Security. Stripe webhook events are server-only and processed idempotently.

## Schema

Apply `supabase/migrations/202610160001_initial_schema.sql` in the Supabase SQL Editor or through the Supabase CLI.

## Required deployment configuration after code integration

Frontend:
- `REACT_APP_SUPABASE_URL`
- `REACT_APP_SUPABASE_ANON_KEY` (public/anon key only)

Backend (server-only):
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `FRONTEND_URL=https://fitcheck-org.vercel.app`
- Existing Stripe secrets and price IDs
- Existing Gemini key/model if AI Buddy is enabled

Supabase Auth provider configuration:
- Enable Email/password and Google providers.
- Add `https://fitcheck-org.vercel.app` as an allowed redirect URL.
- Configure Google OAuth credentials in the Supabase provider settings; Google still requires a client ID and secret.

## Data and billing migration safety

Do not delete the MongoDB database or change the Stripe webhook endpoint while migrating. Existing MongoDB user IDs are UUID strings, but existing password hashes cannot be imported as usable Supabase Auth passwords through a normal schema copy. Existing users need a deliberate account-linking/password-reset plan. Stripe customer/subscription IDs and current entitlement state must be carried over to `profiles`; webhook event IDs should be persisted to avoid duplicate processing.

## Current status

This is the schema and migration plan only. Application code has not yet been switched to Supabase, no data has been copied, and no deployment has been verified.
