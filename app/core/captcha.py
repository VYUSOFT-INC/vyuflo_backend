# app/core/captcha.py — NEW FILE
#
# Cloudflare Turnstile server-side verification. Needs TURNSTILE_SECRET_KEY
# set in .env — get this from the Cloudflare dashboard (Turnstile is free).
#
# NOTE: TURNSTILE_SITE_KEY (the PUBLIC key) is a separate value the
# FRONTEND needs — that one is not a secret and goes in your frontend's
# env (e.g. VITE_TURNSTILE_SITE_KEY), not here.

import httpx
from app.core.config import settings

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


async def verify_captcha(token: str | None) -> bool:
    """
    Returns True only if the token is present AND Cloudflare confirms it's
    valid. Fails closed — missing/invalid token, misconfigured secret, or
    a network error all return False (never silently let a request through).
    """
    if not token:
        return False
    if not settings.TURNSTILE_SECRET_KEY:
        # Misconfigured — fail closed rather than accidentally disabling
        # CAPTCHA entirely because someone forgot to set the env var.
        return False

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(
                TURNSTILE_VERIFY_URL,
                data={"secret": settings.TURNSTILE_SECRET_KEY, "response": token},
            )
        return bool(res.json().get("success", False))
    except Exception:
        return False