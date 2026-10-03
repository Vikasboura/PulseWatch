import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def dispatch_notification(
    channel_type: str,
    channel_config: Dict[str, Any],
    subject: str,
    message: str,
    event_status: str = "triggered"
) -> bool:
    """
    Dispatches alert notifications to configured channels (Email or Slack webhook).
    Returns True if sent successfully, False otherwise.
    """
    try:
        if channel_type == "slack":
            webhook_url = channel_config.get("webhook_url")
            if not webhook_url:
                logger.warning("Slack notification failed: Missing webhook_url in channel_config")
                return False
            return send_slack_notification(webhook_url, subject, message, event_status)

        elif channel_type == "email":
            recipient = channel_config.get("email")
            if not recipient:
                logger.warning("Email notification failed: Missing recipient email in channel_config")
                return False
            return send_email_notification(recipient, subject, message)

        else:
            logger.warning(f"Unknown notification channel type: {channel_type}")
            return False

    except Exception as e:
        logger.error(f"Error dispatching notification via {channel_type}: {e}", exc_info=True)
        return False


def send_slack_notification(webhook_url: str, subject: str, message: str, event_status: str) -> bool:
    color = "#E53E3E" if event_status == "triggered" else "#38A169"
    status_emoji = "🚨" if event_status == "triggered" else "✅"

    payload = {
        "text": f"{status_emoji} *PulseWatch Alert: {subject}*",
        "attachments": [
            {
                "color": color,
                "text": message,
                "fields": [
                    {"title": "Status", "value": event_status.upper(), "short": True},
                ],
            }
        ],
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(webhook_url, json=payload)
            if resp.status_code == 200:
                logger.info(f"Successfully posted Slack alert to {webhook_url[:30]}...")
                return True
            else:
                logger.error(f"Slack webhook returned HTTP {resp.status_code}: {resp.text}")
                return False
    except Exception as e:
        logger.error(f"Failed to post to Slack webhook: {e}")
        return False


def send_email_notification(recipient: str, subject: str, body: str) -> bool:
    if not settings.SMTP_HOST:
        logger.info(f"[DEV MODE] SMTP_HOST not configured. Mocking email to {recipient}: {subject}")
        return True

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[PulseWatch] {subject}"
    msg["From"] = settings.SMTP_FROM_EMAIL
    msg["To"] = recipient

    part = MIMEText(body, "plain")
    msg.attach(part)

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10.0) as server:
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM_EMAIL, [recipient], msg.as_string())
        logger.info(f"Successfully sent alert email to {recipient}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {recipient}: {e}")
        return False
