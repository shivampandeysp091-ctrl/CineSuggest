"""
services/email.py
-----------------
Email delivery via Resend REST API.
Sends OTP verification emails for new user registration.

Secrets are loaded from backend/.env and are never logged or exposed.
"""
import logging
import os

import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

logger = logging.getLogger("services.email")

_RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
_EMAIL_FROM     = os.getenv("EMAIL_FROM", "CineSuggest <noreply@cinesuggest.app>")
_RESEND_URL     = "https://api.resend.com/emails"


def send_otp_email(to_email: str, otp: str, username: str) -> bool:
    """
    Send a 6-digit OTP verification email via Resend.

    Returns True on success, False on failure.
    The OTP value is placed only in the email body — it is never logged.
    """
    if not _RESEND_API_KEY:
        logger.error(
            "RESEND_API_KEY is not configured in backend/.env — "
            "set it to enable email verification."
        )
        return False

    html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#0a0a0a;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr>
      <td align="center" style="padding:40px 16px;">
        <table width="480" cellpadding="0" cellspacing="0"
               style="background:#111111;border-radius:12px;overflow:hidden;">

          <!-- Header -->
          <tr>
            <td style="background:#1a1a1a;padding:24px 32px;border-bottom:3px solid #e50914;">
              <span style="font-size:24px;font-weight:700;color:#ffffff;">
                🎬 CineSuggest
              </span>
              <p style="margin:4px 0 0;color:#aaaaaa;font-size:13px;">
                AI-Powered Movie Recommendations
              </p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:32px;">
              <h2 style="color:#ffffff;font-size:20px;margin:0 0 12px;">
                Verify your email address
              </h2>
              <p style="color:#cccccc;font-size:15px;line-height:1.6;margin:0 0 24px;">
                Hi <strong style="color:#ffffff;">{username}</strong>, welcome to CineSuggest!
                Enter the code below to activate your account.
                This code expires in <strong style="color:#e50914;">15 minutes</strong>.
              </p>

              <!-- OTP Box -->
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="center"
                      style="background:#1a1a1a;border:2px solid #e50914;
                             border-radius:10px;padding:28px 16px;">
                    <p style="color:#aaaaaa;font-size:12px;
                               letter-spacing:2px;margin:0 0 10px;
                               text-transform:uppercase;">
                      Your verification code
                    </p>
                    <span style="font-size:44px;font-weight:700;
                                  letter-spacing:14px;color:#ffffff;
                                  font-family:'Courier New',monospace;">
                      {otp}
                    </span>
                  </td>
                </tr>
              </table>

              <p style="color:#888888;font-size:13px;margin:24px 0 0;line-height:1.5;">
                If you did not create a CineSuggest account, you can safely ignore
                this email. Do not share this code with anyone.
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background:#0f0f0f;padding:16px 32px;text-align:center;">
              <p style="color:#555555;font-size:12px;margin:0;">
                © 2025 CineSuggest AI. All rights reserved.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    try:
        resp = requests.post(
            _RESEND_URL,
            headers={
                "Authorization": f"Bearer {_RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from":    _EMAIL_FROM,
                "to":      [to_email],
                "subject": "Your CineSuggest verification code",
                "html":    html_body,
            },
            timeout=10,
        )
        if resp.status_code in (200, 201):
            logger.info("Verification email queued for %s", to_email)
            return True
        logger.error(
            "Resend API returned HTTP %s for recipient %s",
            resp.status_code, to_email,
        )
        return False
    except requests.exceptions.Timeout:
        logger.error("Resend API timed out for %s", to_email)
        return False
    except Exception as exc:
        logger.error("Email delivery failed: %s", exc)
        return False
