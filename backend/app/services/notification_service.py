import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional
from fastapi import WebSocket
from app.core.config import get_settings

settings = get_settings()


class WebSocketNotificationManager:
    """Manages active in-app WebSocket connections for real-time alerts"""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)


ws_manager = WebSocketNotificationManager()


def send_email_alert(
    to_email: str,
    subject: str,
    body_text: str,
    body_html: Optional[str] = None
) -> bool:
    """
    Sends email notification via SMTP to MailHog local inbox (localhost:1025).
    """
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[{settings.APP_NAME}] {subject}"
        msg["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
        msg["To"] = to_email

        msg.attach(MIMEText(body_text, "plain"))
        if body_html:
            msg.attach(MIMEText(body_html, "html"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=3) as server:
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.EMAILS_FROM_EMAIL, [to_email], msg.as_string())
        return True
    except Exception:
        # Fallback gracefully if MailHog is not currently active
        return False
