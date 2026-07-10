from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta
import random
import string

from app.core.email import send_email
from app.services.employee.services import db_create, utc_now
from app.models.visamodels import User, UserOTP
from app.core.config import settings
from app.core.sms import send_login_otp_sms, send_phone_verification_otp_sms



def _generate_otp(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


async def send_email_verification_otp(db: AsyncSession, user: User) -> None:
    """
    Generates a 6-digit OTP, stores it in UserOTP table, sends email.
    Expires in 10 minutes.
    """
    code = _generate_otp()
    print(code,"code")
    otp = UserOTP(
        user_id    = user.id,
        otp_code       = code,
        otp_type    = "email_verification",
        expires_at = utc_now() + timedelta(minutes=10),
        is_used       = False,
        created_by = user.id,
    )
    await db_create(db, otp)

    await send_email(
        to      = user.email,
        subject = "Verify your VisaFlow email",
        body    = f"""
Hi {user.first_name},

Your VisaFlow verification code is:

    {code}

This code expires in 10 minutes.
If you didn't create an account, please ignore this email.

– The VisaFlow Team
        """.strip(),
    )


# async def send_phone_verification_otp(db: AsyncSession, user: User) -> None:
    # """
    # Generates a 6-digit OTP, stores it in UserOTP table, sends via SMS.
    # Expires in 10 minutes. Requires user.phone to be set.
    # """
# 
    # code = _generate_otp()
    # otp = UserOTP(
        # user_id    = user.id,
        # otp_code   = code,
        # otp_type   = "phone_verification",
        # expires_at = utc_now() + timedelta(minutes=10),
        # is_used    = False,
        # created_by = user.id,
    # )
    # await db_create(db, otp)
# 
    # await send_phone_verification_otp_sms(user.phone, code, user.country_code)
# 
# 
# async def send_login_otp(db: AsyncSession, user: User, channel: str) -> None:
    # """
    # Generates a 6-digit login OTP, stores it as UserOTP(otp_type="two_factor_auth"),
    # and sends it via the requested channel.
# 
    # channel: "email" | "phone"
    # """
# 
    # code = _generate_otp()
    # otp = UserOTP(
        # user_id    = user.id,
        # otp_code   = code,
        # otp_type   = "two_factor_auth",
        # expires_at = utc_now() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
        # is_used    = False,
        # created_by = user.id,
    # )
    # await db_create(db, otp)
# 
    # if channel == "email":
        # await send_email(
            # to      = user.email,
            # subject = "Your VisaFlow login code",
            # body    = f"""
# Hi {user.first_name},
# 
# Your VisaFlow login code is:
# 
    # {code}
# 
# This code expires in {settings.OTP_EXPIRE_MINUTES} minutes.
# If you didn't request this, you can safely ignore this message.
# 
# – The VisaFlow Team
            # """.strip(),
        # )
    # elif channel == "phone":
        # await send_login_otp_sms(user.phone, code, user.country_code)
    # else:
        # raise ValueError(f"Unsupported OTP channel: {channel}")