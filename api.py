"""Compatibility entry point: uvicorn api:app uses the canonical application.

Use python -m taxi normally. Both entry points create one application-owned
supervisor, preserve role checks and reject hardware motion.
"""

from taxi.api import create_app

app = create_app()
