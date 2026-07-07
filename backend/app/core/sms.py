# core/sms.py
"""
SMS delivery for phone OTPs — Twilio.

Twilio's Python SDK is synchronous, so calls are pushed to a thread with
asyncio.to_thread to avoid blocking the event loop, matching the async
style of core/email.py.
"""
import asyncio

from twilio.rest import Client

from app.core.config import settings

_client: Client | None = None


def _get_client() -> Client:
    global _client
    if _client is None:
        _client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    return _client


def _to_e164(phone: str, country_code: str | None = None) -> str:
    """
    Best-effort normalization to E.164 (e.g. +14155551234).
    Assumes `phone` is already digits-only or has a leading '+'.
    """
    phone = phone.strip()
    if phone.startswith("+"):
        return phone
    prefix = (country_code or "").strip()
    if prefix and not prefix.startswith("+"):
        prefix = f"+{prefix}"
    return f"{prefix}{phone}" if prefix else f"+{phone}"


async def send_sms(to: str, body: str) -> None:
    """
    Sends a raw SMS via Twilio.
    `to` must already be E.164 formatted (+countrycode number).
    """
    def _send() -> None:
        client = _get_client()
        client.messages.create(
            to=to,
            from_=settings.TWILIO_FROM_NUMBER,
            body=body,
        )

    await asyncio.to_thread(_send)


async def send_login_otp_sms(phone: str, otp_code: str, country_code: str | None = None) -> None:
    """Sends the passwordless-login OTP code to a phone number."""
    to = _to_e164(phone, country_code)
    body = (
        f"Your VisaFlow login code is {otp_code}. "
        f"It expires in {settings.OTP_EXPIRE_MINUTES} minutes. "
        "Never share this code with anyone."
    )
    await send_sms(to=to, body=body)


async def send_phone_verification_otp_sms(phone: str, otp_code: str, country_code: str | None = None) -> None:
    """Sends the signup phone-verification OTP code."""
    to = _to_e164(phone, country_code)
    body = (
        f"Your VisaFlow phone verification code is {otp_code}. "
        f"It expires in {settings.OTP_EXPIRE_MINUTES} minutes."
    )
    await send_sms(to=to, body=body)
