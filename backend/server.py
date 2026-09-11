"""Compatibility entrypoint for older local deployments.

The production API lives in backend.clean. Keeping this module tiny prevents
legacy authentication/AI integrations from being imported by the app.
"""
from backend.clean import *  # noqa: F401,F403
