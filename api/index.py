"""Vercel entrypoint for FitCheck.

Authentication, AI, workouts, plans and billing are implemented in the clean
native FastAPI application. No external auth broker is used.
"""
from backend.clean import app
