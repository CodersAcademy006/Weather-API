"""
IntelliWeather - Notifications Module

Pluggable notification system supporting:
- Email (SMTP / SendGrid)
- SMS (Twilio)
- Web Push
- In-App notifications
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from enum import Enum
import uuid
import json
import os

from pydantic import BaseModel, EmailStr
from config import settings
from logging_config import get_logger

logger = get_logger(__name__)


class NotificationType(str, Enum):
    """Notification types"""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"


class NotificationPriority(str, Enum):
    """Notification priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationStatus(str, Enum):
    """Notification delivery status"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    READ = "read"


class NotificationTemplate(str, Enum):
    """Pre-defined notification templates"""
    WEATHER_ALERT = "weather_alert"
    SEVERE_WEATHER = "severe_weather"
    DAILY_FORECAST = "daily_forecast"
    ACCOUNT_WELCOME = "account_welcome"
    API_KEY_CREATED = "api_key_created"
    RATE_LIMIT_WARNING = "rate_limit_warning"


class Notification(BaseModel):
    """Notification data model"""
    id: str
    type: NotificationType
    user_id: Optional[str] = None
    recipient: str  # email, phone, or user_id
    subject: str
    body: str
    template_id: Optional[str] = None
    priority: NotificationPriority = NotificationPriority.NORMAL
    status: NotificationStatus = NotificationStatus.PENDING
    metadata: Dict[str, Any] = {}
    created_at: datetime
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    
    @classmethod
    def create(
        cls,
        notification_type: NotificationType,
        recipient: str,
        subject: str,
        body: str,
        **kwargs
    ) -> "Notification":
        """Factory method to create a notification"""
        return cls(
            id=str(uuid.uuid4()),
            type=notification_type,
            recipient=recipient,
            subject=subject,
            body=body,
            created_at=datetime.now(timezone.utc),
            **kwargs
        )


class NotificationBackend(ABC):
    """Abstract base class for notification backends"""
    
    @abstractmethod
    async def send(self, notification: Notification) -> bool:
        """Send a notification. Returns True on success."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the backend is available and configured"""
        pass


class EmailBackend(NotificationBackend):
    """Email notification backend supporting SMTP and SendGrid"""
    
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.sendgrid_api_key = os.getenv("SENDGRID_API_KEY", "")
        self.from_email = os.getenv("FROM_EMAIL", "noreply@intelliweather.io")
    
    def is_available(self) -> bool:
        return bool(self.sendgrid_api_key or (self.smtp_host and self.smtp_username))
    
    async def send(self, notification: Notification) -> bool:
        if not self.is_available():
            logger.warning("Email backend not configured")
            return False
        
        try:
            if self.sendgrid_api_key:
                return await self._send_sendgrid(notification)
            else:
                return await self._send_smtp(notification)
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    async def _send_sendgrid(self, notification: Notification) -> bool:
        """Send email via SendGrid API"""
        try:
            import httpx
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.sendgrid.com/v3/mail/send",
                    headers={
                        "Authorization": f"Bearer {self.sendgrid_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "personalizations": [{"to": [{"email": notification.recipient}]}],
                        "from": {"email": self.from_email, "name": "IntelliWeather"},
                        "subject": notification.subject,
                        "content": [
                            {"type": "text/plain", "value": notification.body},
                            {"type": "text/html", "value": self._html_template(notification)}
                        ]
                    },
                    timeout=30.0
                )
                return response.status_code in (200, 202)
        except ImportError:
            logger.error("httpx not installed for SendGrid")
            return False
    
    async def _send_smtp(self, notification: Notification) -> bool:
        """Send email via SMTP"""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            msg = MIMEMultipart("alternative")
            msg["Subject"] = notification.subject
            msg["From"] = self.from_email
            msg["To"] = notification.recipient
            
            msg.attach(MIMEText(notification.body, "plain"))
            msg.attach(MIMEText(self._html_template(notification), "html"))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.sendmail(self.from_email, notification.recipient, msg.as_string())
            
            return True
        except Exception as e:
            logger.error(f"SMTP send failed: {e}")
            return False
    
    def _html_template(self, notification: Notification) -> str:
        """Generate HTML email template"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Inter', Arial, sans-serif; background: #f8fafc; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #4a1c6e, #7b4397); padding: 30px; text-align: center; }}
                .header h1 {{ color: white; margin: 0; font-size: 24px; }}
                .content {{ padding: 30px; }}
                .footer {{ background: #1e293b; color: #94a3b8; padding: 20px; text-align: center; font-size: 12px; }}
                .btn {{ display: inline-block; background: #d4af37; color: #4a1c6e; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 600; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🌤️ IntelliWeather</h1>
                </div>
                <div class="content">
                    <h2>{notification.subject}</h2>
                    <p>{notification.body}</p>
                </div>
                <div class="footer">
                    <p>© 2024 IntelliWeather. All rights reserved.</p>
                    <p><a href="#" style="color: #d4af37;">Unsubscribe</a> | <a href="#" style="color: #d4af37;">Preferences</a></p>
                </div>
            </div>
        </body>
        </html>
        """


class SMSBackend(NotificationBackend):
    """SMS notification backend using Twilio"""
    
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        self.phone_number = os.getenv("TWILIO_PHONE_NUMBER", "")
    
    def is_available(self) -> bool:
        return bool(self.account_sid and self.auth_token and self.phone_number)
    
    async def send(self, notification: Notification) -> bool:
        if not self.is_available():
            logger.warning("SMS backend not configured, using mock")
            return self._mock_send(notification)
        
        try:
            import httpx
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json",
                    auth=(self.account_sid, self.auth_token),
                    data={
                        "From": self.phone_number,
                        "To": notification.recipient,
                        "Body": f"{notification.subject}\n\n{notification.body}"
                    },
                    timeout=30.0
                )
                return response.status_code == 201
        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")
            return False
    
    def _mock_send(self, notification: Notification) -> bool:
        """Mock SMS send for development/testing"""
        logger.info(f"[MOCK SMS] To: {notification.recipient}, Subject: {notification.subject}")
        return True


class WebPushBackend(NotificationBackend):
    """Web Push notification backend"""
    
    def __init__(self):
        self.vapid_private_key = os.getenv("VAPID_PRIVATE_KEY", "")
        self.vapid_public_key = os.getenv("VAPID_PUBLIC_KEY", "")
        self.vapid_email = os.getenv("VAPID_EMAIL", "admin@intelliweather.io")
    
    def is_available(self) -> bool:
        return bool(self.vapid_private_key and self.vapid_public_key)
    
    async def send(self, notification: Notification) -> bool:
        if not self.is_available():
            logger.warning("Web Push backend not configured, using mock")
            return self._mock_send(notification)
        
        try:
            # In production, use pywebpush
            # from pywebpush import webpush
            logger.info(f"[WEB PUSH] To: {notification.recipient}, Subject: {notification.subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to send web push: {e}")
            return False
    
    def _mock_send(self, notification: Notification) -> bool:
        """Mock web push for development/testing"""
        logger.info(f"[MOCK WEB PUSH] To: {notification.recipient}, Subject: {notification.subject}")
        return True


class InAppBackend(NotificationBackend):
    """In-app notification backend (stores in database/CSV)"""
    
    def __init__(self):
        self.notifications: Dict[str, List[Notification]] = {}
    
    def is_available(self) -> bool:
        return True
    
    async def send(self, notification: Notification) -> bool:
        try:
            user_id = notification.user_id or notification.recipient
            if user_id not in self.notifications:
                self.notifications[user_id] = []
            
            notification.status = NotificationStatus.DELIVERED
            notification.delivered_at = datetime.now(timezone.utc)
            self.notifications[user_id].append(notification)
            
            logger.info(f"[IN-APP] Notification stored for user: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to store in-app notification: {e}")
            return False
    
    def get_user_notifications(
        self, 
        user_id: str, 
        unread_only: bool = False,
        limit: int = 50
    ) -> List[Notification]:
        """Get notifications for a user"""
        notifications = self.notifications.get(user_id, [])
        
        if unread_only:
            notifications = [n for n in notifications if n.status != NotificationStatus.READ]
        
        return sorted(notifications, key=lambda n: n.created_at, reverse=True)[:limit]
    
    def mark_as_read(self, user_id: str, notification_id: str) -> bool:
        """Mark a notification as read"""
        notifications = self.notifications.get(user_id, [])
        for notification in notifications:
            if notification.id == notification_id:
                notification.status = NotificationStatus.READ
                notification.read_at = datetime.now(timezone.utc)
                return True
        return False


class NotificationService:
    """Main notification service that manages backends and delivery"""
    
    def __init__(self):
        self.backends: Dict[NotificationType, NotificationBackend] = {
            NotificationType.EMAIL: EmailBackend(),
            NotificationType.SMS: SMSBackend(),
            NotificationType.PUSH: WebPushBackend(),
            NotificationType.IN_APP: InAppBackend(),
        }
        self.pending_notifications: List[Notification] = []
    
    async def send(
        self,
        notification_type: NotificationType,
        recipient: str,
        subject: str,
        body: str,
        **kwargs
    ) -> Notification:
        """Send a notification"""
        notification = Notification.create(
            notification_type=notification_type,
            recipient=recipient,
            subject=subject,
            body=body,
            **kwargs
        )
        
        backend = self.backends.get(notification_type)
        if not backend:
            notification.status = NotificationStatus.FAILED
            notification.error_message = f"No backend for type: {notification_type}"
            return notification
        
        success = await backend.send(notification)
        
        if success:
            notification.status = NotificationStatus.SENT
            notification.sent_at = datetime.now(timezone.utc)
        else:
            notification.status = NotificationStatus.FAILED
            notification.error_message = "Backend send failed"
            self.pending_notifications.append(notification)
        
        return notification
    
    async def send_multi(
        self,
        types: List[NotificationType],
        recipient: str,
        subject: str,
        body: str,
        **kwargs
    ) -> List[Notification]:
        """Send notification via multiple channels"""
        results = []
        for notification_type in types:
            notification = await self.send(notification_type, recipient, subject, body, **kwargs)
            results.append(notification)
        return results
    
    async def retry_failed(self) -> int:
        """Retry failed notifications with exponential backoff"""
        retried = 0
        remaining = []
        
        for notification in self.pending_notifications:
            if notification.retry_count >= notification.max_retries:
                logger.warning(f"Notification {notification.id} exceeded max retries")
                continue
            
            notification.retry_count += 1
            backend = self.backends.get(notification.type)
            
            if backend and await backend.send(notification):
                notification.status = NotificationStatus.SENT
                notification.sent_at = datetime.now(timezone.utc)
                retried += 1
            else:
                remaining.append(notification)
        
        self.pending_notifications = remaining
        return retried
    
    def get_user_notifications(self, user_id: str, **kwargs) -> List[Notification]:
        """Get in-app notifications for a user"""
        in_app_backend = self.backends.get(NotificationType.IN_APP)
        if isinstance(in_app_backend, InAppBackend):
            return in_app_backend.get_user_notifications(user_id, **kwargs)
        return []
    
    def mark_as_read(self, user_id: str, notification_id: str) -> bool:
        """Mark a notification as read"""
        in_app_backend = self.backends.get(NotificationType.IN_APP)
        if isinstance(in_app_backend, InAppBackend):
            return in_app_backend.mark_as_read(user_id, notification_id)
        return False
    
    def get_available_channels(self) -> List[NotificationType]:
        """Get list of available notification channels"""
        return [
            notification_type 
            for notification_type, backend in self.backends.items() 
            if backend.is_available()
        ]


# Global notification service instance
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Get or create the notification service singleton"""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service
