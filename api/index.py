"""Vercel entrypoint for FitCheck."""

import sys
from pathlib import Path

# Vercel invokes this file as a standalone Python function. Ensure the
# repository root is on sys.path before importing the backend package.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.clean import app  # noqa: E402

__all__ = ["app"]
