"""
Email service — sends transactional emails via SMTP.

Configure via .env:
    SMTP_HOST     = smtp.gmail.com
    SMTP_PORT     = 587
    SMTP_USER     = you@gmail.com
    SMTP_PASSWORD = your-app-password
    SMTP_FROM     = Recording Converter <you@gmail.com>
    SMTP_TLS      = true   (STARTTLS; set false for port 465 SSL)
"""
from __future__ import annotations

import logging
import smtplib
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)
_settings = get_settings()


def _build_welcome_email(to_email: str) -> MIMEMultipart:
    """Build the HTML welcome email."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Welcome to Recording Converter 🎙"
    msg["From"]    = _settings.smtp_from or _settings.smtp_user
    msg["To"]      = to_email

    text = f"""\
Hi there!

Your Recording Converter account has been created successfully.

You can now log in at http://localhost:5173 to start converting
S3 recording URLs to presigned or CloudFront URLs in bulk.

— The Recording Converter Team
"""

    html = f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Welcome to Recording Converter</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
           background: #06070d; margin: 0; padding: 40px 20px; color: #e2e8f0; }}
    .wrap {{ max-width: 520px; margin: 0 auto; }}
    .card {{ background: #111827; border: 1px solid rgba(255,255,255,0.08);
             border-radius: 20px; padding: 40px; text-align: center; }}
    .logo {{ width: 64px; height: 64px; background: linear-gradient(135deg,#7c6ff7,#a78bfa);
             border-radius: 18px; display: inline-flex; align-items: center;
             justify-content: center; font-size: 28px; margin-bottom: 20px; }}
    h1 {{ font-size: 22px; font-weight: 700; color: #fff; margin: 0 0 8px; }}
    p  {{ font-size: 15px; color: #94a3b8; line-height: 1.7; margin: 0 0 24px; }}
    .account {{ background: rgba(124,111,247,0.1); border: 1px solid rgba(124,111,247,0.25);
                border-radius: 10px; padding: 16px; margin: 24px 0; }}
    .account-label {{ font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em;
                      color: #64748b; margin-bottom: 4px; }}
    .account-email {{ font-size: 16px; font-weight: 600; color: #a78bfa; }}
    .btn {{ display: inline-block; padding: 13px 28px;
            background: linear-gradient(135deg,#7c6ff7,#a78bfa);
            color: #fff; text-decoration: none; border-radius: 12px;
            font-size: 15px; font-weight: 600; margin-top: 8px; }}
    .footer {{ margin-top: 32px; font-size: 12px; color: #334155; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <div class="logo">🎙</div>
      <h1>Welcome aboard!</h1>
      <p>Your Recording Converter account is ready.<br/>
         Convert S3 URLs to presigned or CloudFront URLs in bulk.</p>

      <div class="account">
        <div class="account-label">Your account</div>
        <div class="account-email">{to_email}</div>
      </div>

      <p style="margin-bottom:8px">You can sign in anytime at your team's Recording Converter instance.</p>
      <a class="btn" href="http://localhost:5173">Open Recording Converter →</a>
    </div>
    <div class="footer" style="text-align:center;margin-top:20px;">
      This email was sent because an account was created with this address.<br/>
      If this wasn't you, please ignore this email.
    </div>
  </div>
</body>
</html>
"""

    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))
    return msg


def _build_login_notification_email(
    to_email: str,
    client_ip: str = "Unknown",
    user_agent: str = "Unknown",
    login_time: Optional[str] = None,
) -> MIMEMultipart:
    """Build the HTML security alert login notification email."""
    if not login_time:
        from datetime import datetime, timezone
        login_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Shorten long user agents for display
    ua_display = user_agent
    if len(ua_display) > 80:
        ua_display = ua_display[:77] + "..."

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Security Alert: New Sign-in to Recording Converter"
    msg["From"]    = _settings.smtp_from or _settings.smtp_user
    msg["To"]      = to_email

    text = f"""\
Security Notice: New Login Detected

Your Recording Converter account was just signed in to.

Account:    {to_email}
Date & Time: {login_time}
IP Address:  {client_ip}
Device/App:  {ua_display}

If this was you, no action is needed.
If you did not sign in recently, please secure your account immediately or notify your administrator.

— The Recording Converter Team
"""

    html = f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Security Alert: New Sign-in</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
           background: #06070d; margin: 0; padding: 40px 20px; color: #e2e8f0; }}
    .wrap {{ max-width: 520px; margin: 0 auto; }}
    .card {{ background: #111827; border: 1px solid rgba(255,255,255,0.08);
             border-radius: 20px; padding: 40px; text-align: left; }}
    .header {{ text-align: center; margin-bottom: 24px; }}
    .badge {{ display: inline-flex; align-items: center; gap: 6px;
              background: rgba(16,185,129,0.12); border: 1px solid rgba(16,185,129,0.28);
              color: #34d399; padding: 6px 14px; border-radius: 999px;
              font-size: 13px; font-weight: 600; margin-bottom: 12px; }}
    h1 {{ font-size: 22px; font-weight: 700; color: #fff; margin: 0 0 6px; text-align: center; }}
    p.subtitle {{ font-size: 14px; color: #94a3b8; text-align: center; margin: 0 0 24px; }}
    .info-table {{ width: 100%; border-collapse: collapse; margin: 20px 0;
                   background: rgba(255,255,255,0.02); border-radius: 12px; overflow: hidden;
                   border: 1px solid rgba(255,255,255,0.06); }}
    .info-table td {{ padding: 12px 16px; font-size: 13px; border-bottom: 1px solid rgba(255,255,255,0.04); }}
    .info-table tr:last-child td {{ border-bottom: none; }}
    .info-label {{ color: #64748b; font-weight: 500; width: 35%; }}
    .info-val {{ color: #f1f5f9; font-weight: 600; }}
    .alert-box {{ background: rgba(124,111,247,0.08); border-left: 3px solid #7c6ff7;
                  padding: 12px 16px; border-radius: 0 8px 8px 0; margin-top: 20px;
                  font-size: 13px; color: #cbd5e1; line-height: 1.6; }}
    .footer {{ margin-top: 28px; font-size: 12px; color: #475569; text-align: center; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <div class="header">
        <div class="badge">🛡 Security Notification</div>
        <h1>New Sign-in Detected</h1>
        <p class="subtitle">A successful login was just recorded for your account.</p>
      </div>

      <table class="info-table">
        <tr>
          <td class="info-label">Account</td>
          <td class="info-val">{to_email}</td>
        </tr>
        <tr>
          <td class="info-label">Timestamp</td>
          <td class="info-val">{login_time}</td>
        </tr>
        <tr>
          <td class="info-label">IP Address</td>
          <td class="info-val">{client_ip}</td>
        </tr>
        <tr>
          <td class="info-label">Device / Client</td>
          <td class="info-val" style="word-break:break-all;">{ua_display}</td>
        </tr>
      </table>

      <div class="alert-box">
        <strong>Was this you?</strong> If yes, you can safely disregard this email.<br/>
        If you did not sign in, someone else may have gained access to your account.
      </div>
    </div>
    <div class="footer">
      Recording Converter Security Team • Automated Notification
    </div>
  </div>
</body>
</html>
"""

    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))
    return msg


def _send_smtp(msg: MIMEMultipart, to_email: str) -> None:
    """Actually connect to SMTP and send. Runs in a background thread."""
    s = _settings
    if not s.smtp_user or not s.smtp_password:
        logger.warning(
            "SMTP credentials not configured — skipping email '%s' to %s. "
            "Set SMTP_USER and SMTP_PASSWORD in .env to enable emails.",
            msg.get("Subject", "Notification"),
            to_email,
        )
        return

    try:
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=10) as server:
            if s.smtp_tls:
                server.ehlo()
                server.starttls()
                server.ehlo()
            server.login(s.smtp_user, s.smtp_password)
            server.sendmail(msg["From"], [to_email], msg.as_string())
        logger.info("Email '%s' sent to %s", msg.get("Subject", "Notification"), to_email)
    except Exception as exc:
        logger.error("Failed to send email to %s: %s", to_email, exc)


def send_welcome_email(to_email: str) -> None:
    """
    Fire-and-forget welcome email in a daemon thread so it never
    blocks the HTTP response.
    """
    msg = _build_welcome_email(to_email)
    t = threading.Thread(target=_send_smtp, args=(msg, to_email), daemon=True)
    t.start()


def send_login_notification_email(
    to_email: str,
    client_ip: str = "Unknown",
    user_agent: str = "Unknown",
) -> None:
    """
    Fire-and-forget login alert email in a daemon thread so it never
    blocks the HTTP response.
    """
    msg = _build_login_notification_email(
        to_email=to_email,
        client_ip=client_ip,
        user_agent=user_agent,
    )
    t = threading.Thread(target=_send_smtp, args=(msg, to_email), daemon=True)
    t.start()
