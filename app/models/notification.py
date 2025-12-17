"""
Queska Backend - Notification Model
MongoDB document model for notifications using Beanie ODM
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from beanie import Indexed, PydanticObjectId
from pydantic import BaseModel, Field

from app.core.constants import (
    NotificationChannel,
    NotificationCategory,
    NotificationPriority,
    NotificationStatus,
    UserType,
)
from app.models.base import BaseDocument


# === Embedded Models ===

class NotificationRecipient(BaseModel):
    """Notification recipient details"""
    user_id: Optional[str] = None
    user_type: Optional[UserType] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    device_token: Optional[str] = None  # For push notifications
    name: Optional[str] = None


class DeliveryAttempt(BaseModel):
    """Record of a delivery attempt"""
    channel: NotificationChannel
    attempted_at: datetime = Field(default_factory=datetime.utcnow)
    status: NotificationStatus = NotificationStatus.PENDING
    provider: Optional[str] = None  # twilio, mailchimp, firebase, etc.
    provider_message_id: Optional[str] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    response_data: Optional[Dict[str, Any]] = None


class EmailContent(BaseModel):
    """Email-specific content"""
    subject: str
    html_body: Optional[str] = None
    text_body: Optional[str] = None
    template_id: Optional[str] = None  # Mailchimp/SendGrid template ID
    template_data: Optional[Dict[str, Any]] = None
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    cc: List[str] = Field(default_factory=list)
    bcc: List[str] = Field(default_factory=list)
    reply_to: Optional[str] = None
    headers: Optional[Dict[str, str]] = None


class SMSContent(BaseModel):
    """SMS-specific content"""
    message: str
    sender_id: Optional[str] = None
    is_unicode: bool = False
    segments: int = 1


class PushContent(BaseModel):
    """Push notification content"""
    title: str
    body: str
    image_url: Optional[str] = None
    icon: Optional[str] = None
    badge: Optional[int] = None
    sound: Optional[str] = "default"
    click_action: Optional[str] = None
    data: Optional[Dict[str, Any]] = None  # Custom data payload
    android_config: Optional[Dict[str, Any]] = None
    ios_config: Optional[Dict[str, Any]] = None
    web_config: Optional[Dict[str, Any]] = None


class InAppContent(BaseModel):
    """In-app notification content"""
    title: str
    message: str
    icon: Optional[str] = None
    action_url: Optional[str] = None
    action_text: Optional[str] = None
    image_url: Optional[str] = None
    expires_at: Optional[datetime] = None


# === Main Notification Document ===

class Notification(BaseDocument):
    """
    Notification document for storing all types of notifications.
    Supports email, SMS, push, and in-app notifications.
    """
    
    # Recipient information
    recipient: NotificationRecipient
    
    # Notification details
    category: NotificationCategory
    priority: NotificationPriority = NotificationPriority.NORMAL
    channels: List[NotificationChannel] = Field(default_factory=list)
    
    # Content for different channels
    email_content: Optional[EmailContent] = None
    sms_content: Optional[SMSContent] = None
    push_content: Optional[PushContent] = None
    in_app_content: Optional[InAppContent] = None
    
    # Status tracking (indexed via Settings.indexes)
    status: NotificationStatus = NotificationStatus.PENDING
    delivery_attempts: List[DeliveryAttempt] = Field(default_factory=list)
    
    # Scheduling
    scheduled_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    
    # Reference to related entities
    reference_type: Optional[str] = None  # booking, experience, payment, etc.
    reference_id: Optional[str] = None
    
    # Retry handling
    retry_count: int = 0
    max_retries: int = 3
    next_retry_at: Optional[datetime] = None
    
    # User preferences check
    preferences_checked: bool = False
    
    # Tracking
    opened: bool = False
    clicked: bool = False
    click_count: int = 0
    
    # Batch processing
    batch_id: Optional[str] = None
    
    class Settings:
        name = "notifications"
        indexes = [
            "recipient.user_id",
            "category",
            "status",
            "scheduled_at",
            "created_at",
        ]
    
    def mark_as_sent(self, channel: NotificationChannel, provider_message_id: Optional[str] = None):
        """Mark notification as sent"""
        self.status = NotificationStatus.SENT
        self.sent_at = datetime.utcnow()
        self.delivery_attempts.append(
            DeliveryAttempt(
                channel=channel,
                status=NotificationStatus.SENT,
                provider_message_id=provider_message_id
            )
        )
    
    def mark_as_delivered(self):
        """Mark notification as delivered"""
        self.status = NotificationStatus.DELIVERED
        self.delivered_at = datetime.utcnow()
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.status = NotificationStatus.READ
        self.read_at = datetime.utcnow()
    
    def mark_as_failed(self, channel: NotificationChannel, error_message: str, error_code: Optional[str] = None):
        """Mark notification as failed"""
        self.retry_count += 1
        if self.retry_count >= self.max_retries:
            self.status = NotificationStatus.FAILED
            self.failed_at = datetime.utcnow()
        else:
            self.status = NotificationStatus.PENDING
            # Schedule retry with exponential backoff
            from datetime import timedelta
            delay = 60 * (2 ** self.retry_count)  # 60s, 120s, 240s...
            self.next_retry_at = datetime.utcnow() + timedelta(seconds=delay)
        
        self.delivery_attempts.append(
            DeliveryAttempt(
                channel=channel,
                status=NotificationStatus.FAILED,
                error_message=error_message,
                error_code=error_code
            )
        )


# === User Notification Preferences ===

class NotificationPreferences(BaseModel):
    """User notification preferences (embedded in User model)"""
    
    # Channel preferences
    email_enabled: bool = True
    sms_enabled: bool = True
    push_enabled: bool = True
    in_app_enabled: bool = True
    
    # Category preferences
    booking_notifications: bool = True
    payment_notifications: bool = True
    promotional_notifications: bool = False
    newsletter: bool = False
    security_alerts: bool = True
    social_notifications: bool = True
    reminder_notifications: bool = True
    
    # Quiet hours
    quiet_hours_enabled: bool = False
    quiet_hours_start: Optional[str] = "22:00"  # HH:MM format
    quiet_hours_end: Optional[str] = "08:00"
    quiet_hours_timezone: str = "Africa/Lagos"
    
    # Frequency limits
    max_emails_per_day: int = 10
    max_sms_per_day: int = 5
    max_push_per_hour: int = 5
    
    # Unsubscribe tokens
    email_unsubscribe_token: Optional[str] = None
    sms_unsubscribe_token: Optional[str] = None


# === Notification Template ===

class NotificationTemplate(BaseDocument):
    """Reusable notification templates"""
    
    name: Indexed(str, unique=True)
    category: NotificationCategory
    description: Optional[str] = None
    
    # Template content
    email_subject: Optional[str] = None
    email_html_template: Optional[str] = None
    email_text_template: Optional[str] = None
    sms_template: Optional[str] = None
    push_title_template: Optional[str] = None
    push_body_template: Optional[str] = None
    in_app_title_template: Optional[str] = None
    in_app_message_template: Optional[str] = None
    
    # External template IDs
    mailchimp_template_id: Optional[str] = None
    sendgrid_template_id: Optional[str] = None
    
    # Template variables (for documentation)
    variables: List[str] = Field(default_factory=list)
    
    # Status
    is_active: bool = True
    
    class Settings:
        name = "notification_templates"
        indexes = ["name", "category", "is_active"]

