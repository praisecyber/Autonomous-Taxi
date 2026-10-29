"""Fail-closed settings for a single-worker service behind a trusted HTTPS proxy."""

import os
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Deployment:
    production: bool
    hosts: tuple[str, ...]

    @classmethod
    def from_environment(cls):
        mode = os.getenv("TAXI_DEPLOYMENT", "development")
        if mode not in {"development", "production"}:
            raise RuntimeError("TAXI_DEPLOYMENT must be development or production")
        hosts = tuple(
            h.strip().lower() for h in os.getenv("TAXI_ALLOWED_HOSTS", "").split(",") if h.strip()
        )
        if mode == "production":
            if os.getenv("TAXI_SECURE_COOKIES") != "1":
                raise RuntimeError("Production requires TAXI_SECURE_COOKIES=1")
            if os.getenv("TAXI_ALLOW_LEGACY_TOKEN") != "0":
                raise RuntimeError("Production requires TAXI_ALLOW_LEGACY_TOKEN=0")
            if not hosts or any(
                not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", h) for h in hosts
            ):
                raise RuntimeError(
                    "Production requires explicit TAXI_ALLOWED_HOSTS without wildcards or ports"
                )
        return cls(mode == "production", hosts)
