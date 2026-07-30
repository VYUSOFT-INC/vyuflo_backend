# core/email.py
import ssl
import certifi
import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.core.config import settings


async def send_email(
    to:        str,
    subject:   str,
    body:      str,            # plain text — always required (fallback)
    body_html: str | None = None,  # HTML — shown by default in modern clients
) -> None:
    message = MIMEMultipart("alternative")
    message["From"]    = settings.SMTP_FROM_EMAIL
    message["To"]      = to
    message["Subject"] = subject

    # Plain text first — email clients pick the last matching part,
    # so plain text must come before HTML per RFC 2046
    message.attach(MIMEText(body, "plain"))

    if body_html:
        message.attach(MIMEText(body_html, "html"))

    ssl_context = ssl.create_default_context(cafile=certifi.where())

    await aiosmtplib.send(
        message,
        hostname    = settings.SMTP_HOST,
        port        = settings.SMTP_PORT,
        username    = settings.SMTP_USERNAME,
        password    = settings.SMTP_PASSWORD,
        start_tls   = True,
        tls_context = ssl_context,
    )


async def send_invitation_email(
    to_email:         str,
    invite_token:     str,
    company_name:     str,
    hr_name:          str,
    personal_message: str | None = None,
    logo_url:         str | None = None,   # ← NEW: HR company logo
) -> None:
    invite_link = f"{settings.FRONTEND_URL}/accept-invite?token={invite_token}"
    subject     = f"Invitation to join {company_name} on Vyuflo"

    body = f"""Hi,

{hr_name} has invited you to join {company_name} on Vyuflo.

Invite link:
{invite_link}

{personal_message or ""}

This invite link will expire soon.

Thanks,
Vyuflo Team""".strip()

    # HTML version with company logo
    logo_img = (
        f'<img src="{logo_url}" alt="{company_name}" height="40" '
        f'style="max-height:40px;object-fit:contain;">'
        if logo_url else company_name
    )
    body_html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f9fafb;font-family:Inter,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f9fafb;padding:32px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0"
             style="background:#fff;border-radius:12px;overflow:hidden;
                    box-shadow:0 1px 4px rgba(0,0,0,.08);max-width:600px;width:100%;">
        <tr>
          <td style="background:#4f46e5;padding:24px 32px;text-align:center;">
            {logo_img}
            <p style="color:#c7d2fe;margin:8px 0 0;font-size:13px;">{company_name}</p>
          </td>
        </tr>
        <tr>
          <td style="padding:32px;">
            <p style="font-size:15px;color:#111827;line-height:1.6;">
              Hi,<br><br>
              <strong>{hr_name}</strong> has invited you to join
              <strong>{company_name}</strong> on Vyuflo.<br><br>
              <a href="{invite_link}"
                 style="display:inline-block;background:#4f46e5;color:#fff;
                        padding:12px 24px;border-radius:8px;text-decoration:none;
                        font-weight:600;font-size:14px;">
                Accept Invitation
              </a><br><br>
              {f"<em>{personal_message}</em><br><br>" if personal_message else ""}
              This invite link will expire soon.
            </p>
          </td>
        </tr>
        <tr>
          <td style="padding:20px 32px;border-top:1px solid #f3f4f6;text-align:center;">
            <p style="font-size:12px;color:#9ca3af;margin:0;">
              Sent by {company_name} via
              <a href="{settings.FRONTEND_URL}" style="color:#4f46e5;text-decoration:none;">Vyuflo</a>
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

    await send_email(to=to_email, subject=subject, body=body, body_html=body_html)