# core/email.py
import os

# =============================================================================
# OPTION A — SMTP (Gmail, Outlook, any mail server) — FREE, works immediately
# =============================================================================
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings
import ssl
import certifi
import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


async def send_email(to: str, subject: str, body: str) -> None:
    message = MIMEMultipart("alternative")
    message["From"]    = settings.SMTP_FROM_EMAIL
    message["To"]      = to
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))
    print("sai")

    # ✅ FIX: trusted SSL certificates
    ssl_context = ssl.create_default_context(cafile=certifi.where())

    await aiosmtplib.send(
        message,
        hostname = settings.SMTP_HOST,
        port     = settings.SMTP_PORT,
        username = settings.SMTP_USERNAME,
        password = settings.SMTP_PASSWORD,
        start_tls = True,
        tls_context = ssl_context,   # ⭐ THIS LINE FIXES YOUR ERROR
    )


async def send_invitation_email(
    to_email: str,
    invite_token: str,
    company_name: str,
    hr_name: str,
    personal_message: str | None = None,
) -> None:
    invite_link = f"{settings.FRONTEND_URL}/accept-invite?token={invite_token}"

    subject = f"Invitation to join {company_name} on VisaFlow"

    body = f"""
    Hi,

    {hr_name} has invited you to join {company_name} on VisaFlow.

    Invite link:
    {invite_link}

    {personal_message or ""}

    This invite link will expire soon.

    Thanks,
    VisaFlow Team
    """.strip()

    await send_email(
        to=to_email,
        subject=subject,
        body=body,
    )

# =============================================================================
# OPTION B — SendGrid (recommended for production)
# =============================================================================
# from sendgrid import SendGridAPIClient
# from sendgrid.helpers.mail import Mail
#
# async def send_email(to: str, subject: str, body: str) -> None:
#     message = Mail(
#         from_email = settings.SENDGRID_FROM_EMAIL,
#         to_emails  = to,
#         subject    = subject,
#         plain_text_content = body,
#     )
#     sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
#     sg.send(message)   # sendgrid is sync — wrap in asyncio.to_thread if needed


# =============================================================================
# OPTION C — Resend (simplest, modern, free tier 3000 emails/month)
# =============================================================================
# import resend
#
# async def send_email(to: str, subject: str, body: str) -> None:
#     resend.api_key = settings.RESEND_API_KEY
#     resend.Emails.send({
#         "from":    settings.RESEND_FROM_EMAIL,   # e.g. "noreply@visaflow.com"
#         "to":      to,
#         "subject": subject,
#         "text":    body,
#     })