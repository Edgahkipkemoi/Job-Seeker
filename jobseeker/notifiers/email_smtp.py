"""Email delivery over SMTP.

Provider-agnostic: Gmail, Brevo, Resend, SMTP2GO, Zoho, Mailgun and any other
SMTP host all work by changing SMTP_HOST / SMTP_USER / SMTP_PASSWORD in .env.
Nothing here is Gmail-specific.
"""
from __future__ import annotations

import logging
import smtplib
import ssl
from email.message import EmailMessage

from ..config import env
from ..digest import Digest

log = logging.getLogger(__name__)

NAME = "email"


def configured() -> bool:
    return bool(env("SMTP_USER") and env("SMTP_PASSWORD") and env("MAIL_TO"))


def requirements() -> str:
    return "SMTP_HOST, SMTP_USER, SMTP_PASSWORD and MAIL_TO in .env"


def _deliver(subject: str, html_body: str, text_body: str) -> bool:
    host = env("SMTP_HOST", "smtp.gmail.com")
    port = int(env("SMTP_PORT", "587") or 587)
    user, password = env("SMTP_USER"), env("SMTP_PASSWORD")
    sender = env("MAIL_FROM") or user
    recipients = [r.strip() for r in env("MAIL_TO").split(",") if r.strip()]

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    context = ssl.create_default_context()
    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, context=context, timeout=45) as smtp:
                smtp.login(user, password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=45) as smtp:
                smtp.starttls(context=context)
                smtp.login(user, password)
                smtp.send_message(msg)
    except smtplib.SMTPAuthenticationError:
        log.error("email: SMTP auth rejected by %s. Gmail needs an App Password, "
                  "not your account password; other providers need their own SMTP key.", host)
        return False
    except Exception as exc:  # noqa: BLE001
        log.error("email: send failed via %s — %s", host, exc)
        return False

    log.info("email: delivered to %s", ", ".join(recipients))
    return True


def send(digest: Digest) -> bool:
    return _deliver(digest.subject, digest.html, digest.text)


def send_test() -> bool:
    return _deliver(
        "Job Seeker — test message",
        "<p>Your job-seeker agent is wired up correctly. "
        "The first real digest arrives at 07:00.</p>",
        "Your job-seeker agent is wired up correctly.",
    )
