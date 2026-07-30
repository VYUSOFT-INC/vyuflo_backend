# core/sms.py
"""
SMS delivery via Twilio.
Uses MessagingServiceSid (works for India + US without a dedicated number).
Twilio SDK is sync — wrapped in asyncio.to_thread to avoid blocking event loop.
"""
import asyncio
import logging

from twilio.rest import Client

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: Client | None = None


def _get_client() -> Client:
    global _client
    if _client is None:
        _client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    return _client


def _to_e164(phone: str, country_code: str | None = None) -> str:
    """Best-effort normalization to E.164 (e.g. +919014793898)."""
    phone = phone.strip()
    if phone.startswith("+"):
        return phone
    prefix = (country_code or "").strip()
    if prefix and not prefix.startswith("+"):
        prefix = f"+{prefix}"
    return f"{prefix}{phone}" if prefix else f"+{phone}"


async def send_sms(to: str, body: str) -> None:
    """
    Sends a raw SMS via Twilio MessagingServiceSid.
    Prefers MessagingServiceSid over From number — works for India + US.
    """
    def _send() -> None:
        client  = _get_client()
        params = {
            "to":   to,
            "body": body,
        }
        # Prefer MessagingServiceSid — works globally including India
        if settings.TWILIO_MESSAGING_SERVICE_SID:
            params["messaging_service_sid"] = settings.TWILIO_MESSAGING_SERVICE_SID
        elif settings.TWILIO_FROM_NUMBER:
            params["from_"] = settings.TWILIO_FROM_NUMBER
        else:
            raise ValueError("Neither TWILIO_MESSAGING_SERVICE_SID nor TWILIO_FROM_NUMBER is set")

        client.messages.create(**params)

    await asyncio.to_thread(_send)


async def send_login_otp_sms(
    phone: str, otp_code: str, country_code: str | None = None
) -> None:
    to   = _to_e164(phone, country_code)
    body = (
        f"Your Vyuflo login code is {otp_code}. "
        f"It expires in 60 seconds. "
        "Never share this code with anyone."
    )
    await send_sms(to=to, body=body)


async def send_phone_verification_otp_sms(
    phone: str, otp_code: str, country_code: str | None = None
) -> None:
    to   = _to_e164(phone, country_code)
    body = (
        f"Your Vyuflo phone verification code is {otp_code}. "
        "It expires in 60 seconds."
    )
    await send_sms(to=to, body=body)