"""Explicit local/Firebase modes. No credentials or paid services are provisioned."""

import os
from urllib.parse import urlsplit


def saas_enabled() -> bool:
    mode = os.getenv("INCOME_AUTH_MODE", "local")
    if mode not in {"local", "firebase"}:
        raise RuntimeError("INCOME_AUTH_MODE must be local or firebase")
    if os.getenv("INCOME_ENV") == "production" and mode != "firebase":
        raise RuntimeError("Production requires Firebase authentication")
    return mode == "firebase"


def origin() -> str:
    value = os.environ["INCOME_APP_ORIGIN"].rstrip("/")
    parsed = urlsplit(value)
    if parsed.path or parsed.query or parsed.fragment or not parsed.hostname:
        raise RuntimeError("INCOME_APP_ORIGIN must be an exact origin")
    if parsed.scheme != "https" and not (
        os.getenv("INCOME_ENV") == "development"
        and parsed.scheme == "http"
        and parsed.hostname in {"localhost", "127.0.0.1"}
    ):
        raise RuntimeError("HTTPS required except explicit loopback development")
    return value


def secure_cookies() -> bool:
    return origin().startswith("https://")


def cookie_name(kind: str) -> str:
    return ("__Host-income_" if secure_cookies() else "income_dev_") + kind


def signup_enabled() -> bool:
    return os.getenv("INCOME_PUBLIC_SIGNUP_ENABLED") == "1"


def validate_configuration() -> None:
    if not saas_enabled():
        return
    origin()
    if not os.getenv("FIREBASE_PROJECT_ID"):
        raise RuntimeError("FIREBASE_PROJECT_ID required")
    if os.getenv("FIREBASE_AUTH_EMULATOR_HOST"):
        if os.getenv("INCOME_ENV") != "development":
            raise RuntimeError("Firebase emulator forbidden outside development")
        if not os.getenv("FIREBASE_PROJECT_ID", "").startswith("demo-"):
            raise RuntimeError("Use a demo- project with the emulator")
