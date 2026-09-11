# FitCheck deployment

The application is served by the root `app.py` FastAPI entrypoint. The original FitCheck React frontend remains under `frontend/` so its visual design is unchanged. Vercel serves the committed `frontend/build` through FastAPI and proxies `/api/*` to the original backend app.

Required production variables are documented in `backend/.env.example`.
