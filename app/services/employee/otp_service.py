# app/services/employee/otp_service.py

from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta
import logging
import random
import string

from app.core.email import send_email
from app.services.employee.services import db_create, utc_now
from app.models.visamodels import User, UserOTP
from app.core.config import settings
from app.core.sms import send_login_otp_sms, send_phone_verification_otp_sms

logger = logging.getLogger(__name__)

# OTP validity — 60 seconds
OTP_EXPIRE_SECONDS = 60


def _generate_otp(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


def _twilio_configured() -> bool:
    """Returns True if Twilio credentials + at least one sender is configured."""
    has_credentials = bool(
        settings.TWILIO_ACCOUNT_SID
        and settings.TWILIO_AUTH_TOKEN
    )
    has_sender = bool(
        getattr(settings, "TWILIO_MESSAGING_SERVICE_SID", "")
        or settings.TWILIO_FROM_NUMBER
    )
    return has_credentials and has_sender


async def _try_send_sms(phone: str, code: str, country_code: str | None) -> None:
    """
    Attempts SMS delivery. Silently logs and swallows all errors.
    SMS is always secondary — email is the primary verification channel.
    Never raises — caller must never crash due to SMS failure.
    """
    if not _twilio_configured():
        logger.info("Twilio not configured — skipping SMS send")
        return
    if not phone:
        return
    try:
        await send_phone_verification_otp_sms(phone, code, country_code)
    except Exception as e:
        logger.warning("SMS send failed (non-fatal): %s", e)


# =============================================================================
# SEND EMAIL VERIFICATION OTP (signup step 2)
# One code → sent to BOTH email AND SMS (if phone exists)
# User can verify with whichever arrives first
# =============================================================================

async def send_email_verification_otp(db: AsyncSession, user: User) -> None:
    code = _generate_otp()
    logger.debug("Email verification OTP for %s: %s", user.email, code)

    await db_create(db, UserOTP(
        user_id    = user.id,
        otp_code   = code,
        otp_type   = "email_verification",
        expires_at = utc_now() + timedelta(seconds=OTP_EXPIRE_SECONDS),
        is_used    = False,
        created_by = user.id,
    ))

    # ── Email (primary — must succeed) ────────────────────────────────────────
    body_text = f"""Hi {user.first_name},

Your Vyuflo verification code is: {code}

This code expires in 60 seconds.
If you didn't create an account, ignore this email.

– The Vyuflo Team"""

    body_html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f9fafb;font-family:Inter,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f9fafb;padding:32px 0;">
    <tr><td align="center">
      <table width="480" cellpadding="0" cellspacing="0"
             style="background:#fff;border-radius:12px;overflow:hidden;
                    box-shadow:0 1px 4px rgba(0,0,0,.08);max-width:480px;width:100%;">
        <tr>
          <td style="background:#4f46e5;padding:24px 32px;text-align:center;">
            <p style="color:#fff;font-size:20px;font-weight:700;margin:0;">Vyuflo</p>
            <p style="color:#c7d2fe;font-size:13px;margin:6px 0 0;">Email Verification</p>
          </td>
        </tr>
        <tr>
          <td style="padding:32px;text-align:center;">
            <p style="font-size:15px;color:#374151;margin:0 0 8px;">
              Hi <strong>{user.first_name}</strong>, your verification code is:
            </p>
            <div style="margin:24px 0;background:#f5f3ff;border:2px dashed #a5b4fc;
                        border-radius:12px;padding:20px 0;">
              <p style="font-size:42px;font-weight:800;letter-spacing:12px;
                        color:#4f46e5;margin:0;font-family:monospace;">
                {code}
              </p>
            </div>
            <p style="font-size:13px;color:#ef4444;font-weight:600;margin:0 0 16px;">
              ⏱ This code expires in <strong>60 seconds</strong>
            </p>
            <p style="font-size:13px;color:#6b7280;margin:0;">
              Never share this code with anyone, including Vyuflo support.
            </p>
          </td>
        </tr>
        <tr>
          <td style="padding:20px 32px;border-top:1px solid #f3f4f6;text-align:center;">
            <p style="font-size:12px;color:#9ca3af;margin:0;">© Vyuflo · Do not share this code</p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

    await send_email(
        to=user.email,
        subject="Your Vyuflo verification code",
        body=body_text,
        body_html=body_html,
    )

    # ── SMS (secondary — silently skipped if Twilio not configured or fails) ──
    await _try_send_sms(user.phone, code, user.country_code)


# =============================================================================
# SEND PHONE VERIFICATION OTP (from profile settings)
# =============================================================================

async def send_phone_verification_otp(db: AsyncSession, user: User) -> None:
    """Sends phone verification OTP via SMS only. Expires in 60 seconds."""
    if not _twilio_configured():
        logger.warning("Twilio not configured — cannot send phone verification OTP")
        return

    code = _generate_otp()

    await db_create(db, UserOTP(
        user_id    = user.id,
        otp_code   = code,
        otp_type   = "phone_verification",
        expires_at = utc_now() + timedelta(seconds=OTP_EXPIRE_SECONDS),
        is_used    = False,
        created_by = user.id,
    ))

    await send_phone_verification_otp_sms(user.phone, code, user.country_code)


# =============================================================================
# SEND LOGIN OTP (passwordless login)
# channel: "email" | "phone"
# =============================================================================

async def send_login_otp(db: AsyncSession, user: User, channel: str) -> None:
    """
    Sends passwordless login OTP via email or SMS.
    Expires in 60 seconds.
    """
    if channel == "phone" and not _twilio_configured():
        logger.warning("Twilio not configured — falling back to email for login OTP")
        channel = "email"

    code = _generate_otp()

    await db_create(db, UserOTP(
        user_id    = user.id,
        otp_code   = code,
        otp_type   = "two_factor_auth",
        expires_at = utc_now() + timedelta(seconds=OTP_EXPIRE_SECONDS),
        is_used    = False,
        created_by = user.id,
    ))

    if channel == "email":
        body_text = f"""Hi {user.first_name},

Your Vyuflo login code is: {code}

Expires in 60 seconds. Never share this with anyone.

– The Vyuflo Team"""

        body_html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f9fafb;font-family:Inter,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f9fafb;padding:32px 0;">
    <tr><td align="center">
      <table width="480" cellpadding="0" cellspacing="0"
             style="background:#fff;border-radius:12px;overflow:hidden;
                    box-shadow:0 1px 4px rgba(0,0,0,.08);max-width:480px;width:100%;">
        <tr>
          <td style="background:#4f46e5;padding:24px 32px;text-align:center;">
            <p style="color:#fff;font-size:20px;font-weight:700;margin:0;">Vyuflo</p>
            <p style="color:#c7d2fe;font-size:13px;margin:6px 0 0;">Login Code</p>
          </td>
        </tr>
        <tr>
          <td style="padding:32px;text-align:center;">
            <p style="font-size:15px;color:#374151;margin:0 0 8px;">
              Hi <strong>{user.first_name}</strong>, your login code is:
            </p>
            <div style="margin:24px 0;background:#f5f3ff;border:2px dashed #a5b4fc;
                        border-radius:12px;padding:20px 0;">
              <p style="font-size:42px;font-weight:800;letter-spacing:12px;
                        color:#4f46e5;margin:0;font-family:monospace;">
                {code}
              </p>
            </div>
            <p style="font-size:13px;color:#ef4444;font-weight:600;margin:0 0 16px;">
              ⏱ Expires in <strong>60 seconds</strong>
            </p>
            <p style="font-size:13px;color:#6b7280;margin:0;">
              Never share this code with anyone, including Vyuflo support.
            </p>
          </td>
        </tr>
        <tr>
          <td style="padding:20px 32px;border-top:1px solid #f3f4f6;text-align:center;">
            <p style="font-size:12px;color:#9ca3af;margin:0;">© Vyuflo</p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

        await send_email(
            to=user.email,
            subject="Your Vyuflo login code",
            body=body_text,
            body_html=body_html,
        )

    elif channel == "phone":
        await send_login_otp_sms(user.phone, code, user.country_code)

    else:
        raise ValueError(f"Unsupported OTP channel: {channel}")