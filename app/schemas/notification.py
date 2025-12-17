"""
Queska Backend - Notification Schemas
Pydantic schemas for notification API requests and responses
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import Field

from app.core.constants import (
    NotificationCategory,
    NotificationChannel,
    NotificationPriority,
    NotificationStatus,
    UserType,
)
from app.schemas.base import BaseSchema


# === Recipient Schemas ===

class RecipientCreate(BaseSchema):
    """Recipient information for sending notifications"""
    user_id: Optional[str] = None
    user_type: Optional[UserType] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    device_token: Optional[str] = None
    name: Optional[str] = None


# === Content Schemas ===

class EmailContentCreate(BaseSchema):
    """Email content for notification"""
    subject: str
    html_body: Optional[str] = None
    text_body: Optional[str] = None
    template_id: Optional[str] = None
    template_data: Optional[Dict[str, Any]] = None
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    cc: List[str] = Field(default_factory=list)
    bcc: List[str] = Field(default_factory=list)
    reply_to: Optional[str] = None


class SMSContentCreate(BaseSchema):
    """SMS content for notification"""
    message: str
    sender_id: Optional[str] = None
    is_unicode: bool = False


class PushContentCreate(BaseSchema):
    """Push notification content"""
    title: str
    body: str
    image_url: Optional[str] = None
    icon: Optional[str] = None
    badge: Optional[int] = None
    sound: Optional[str] = "default"
    click_action: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class InAppContentCreate(BaseSchema):
    """In-app notification content"""
    title: str
    message: str
    icon: Optional[str] = None
    action_url: Optional[str] = None
    action_text: Optional[str] = None
    image_url: Optional[str] = None
    expires_at: Optional[datetime] = None


# === Create/Send Schemas ===

class NotificationCreate(BaseSchema):
    """Schema for creating/sending a notification"""
    recipient: RecipientCreate
    category: NotificationCategory
    channels: List[NotificationChannel]
    priority: NotificationPriority = NotificationPriority.NORMAL
    
    # Content for different channels
    email_content: Optional[EmailContentCreate] = None
    sms_content: Optional[SMSContentCreate] = None
    push_content: Optional[PushContentCreate] = None
    in_app_content: Optional[InAppContentCreate] = None
    
    # Scheduling
    scheduled_at: Optional[datetime] = None
    
    # Reference
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    
    # Options
    check_preferences: bool = True


class NotificationSendEmail(BaseSchema):
    """Quick email send schema"""
    to_email: str
    to_name: Optional[str] = None
    subject: str
    html_body: Optional[str] = None
    text_body: Optional[str] = None
    template_id: Optional[str] = None
    template_data: Optional[Dict[str, Any]] = None
    cc: List[str] = Field(default_factory=list)
    bcc: List[str] = Field(default_factory=list)


class NotificationSendSMS(BaseSchema):
    """Quick SMS send schema"""
    to_phone: str
    message: str
    sender_id: Optional[str] = None


class NotificationSendPush(BaseSchema):
    """Quick push notification send schema"""
    device_token: Optional[str] = None
    device_tokens: List[str] = Field(default_factory=list)
    topic: Optional[str] = None
    title: str
    body: str
    data: Optional[Dict[str, Any]] = None
    image_url: Optional[str] = None


class NotificationSendBatch(BaseSchema):
    """Batch notification send schema"""
    recipients: List[RecipientCreate]
    category: NotificationCategory
    channels: List[NotificationChannel]
    email_content: Optional[EmailContentCreate] = None
    sms_content: Optional[SMSContentCreate] = None
    push_content: Optional[PushContentCreate] = None
    in_app_content: Optional[InAppContentCreate] = None


class NotificationFromTemplate(BaseSchema):
    """Send notification from template"""
    template_name: str
    recipient: RecipientCreate
    template_data: Dict[str, Any]
    channels: Optional[List[NotificationChannel]] = None


# === Response Schemas ===

class DeliveryAttemptResponse(BaseSchema):
    """Delivery attempt response"""
    channel: str
    attempted_at: datetime
    status: str
    provider: Optional[str] = None
    provider_message_id: Optional[str] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None


class NotificationResponse(BaseSchema):
    """Notification response schema"""
    id: str
    recipient_user_id: Optional[str] = None
    category: str
    priority: str
    channels: List[str]
    status: str
    
    # Content summaries
    email_subject: Optional[str] = None
    sms_message: Optional[str] = None
    push_title: Optional[str] = None
    in_app_title: Optional[str] = None
    in_app_message: Optional[str] = None
    
    # Timestamps
    created_at: datetime
    scheduled_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    
    # Reference
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    
    # Delivery attempts
    delivery_attempts: List[DeliveryAttemptResponse] = Field(default_factory=list)


class NotificationListResponse(BaseSchema):
    """Paginated notification list response"""
    notifications: List[NotificationResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class NotificationSendResult(BaseSchema):
    """Result of sending a notification"""
    success: bool
    notification_id: Optional[str] = None
    channels_attempted: List[str] = Field(default_factory=list)
    channels_succeeded: List[str] = Field(default_factory=list)
    channels_failed: List[str] = Field(default_factory=list)
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class BatchSendResult(BaseSchema):
    """Result of batch sending"""
    total: int
    successful: int
    failed: int
    results: List[NotificationSendResult]


# === Preference Schemas ===

class NotificationPreferencesUpdate(BaseSchema):
    """Update notification preferences"""
    email_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
    in_app_enabled: Optional[bool] = None
    
    booking_notifications: Optional[bool] = None
    payment_notifications: Optional[bool] = None
    promotional_notifications: Optional[bool] = None
    newsletter: Optional[bool] = None
    security_alerts: Optional[bool] = None
    social_notifications: Optional[bool] = None
    reminder_notifications: Optional[bool] = None
    
    quiet_hours_enabled: Optional[bool] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    quiet_hours_timezone: Optional[str] = None
    
    max_emails_per_day: Optional[int] = None
    max_sms_per_day: Optional[int] = None
    max_push_per_hour: Optional[int] = None


class NotificationPreferencesResponse(BaseSchema):
    """Notification preferences response"""
    email_enabled: bool = True
    sms_enabled: bool = True
    push_enabled: bool = True
    in_app_enabled: bool = True
    
    booking_notifications: bool = True
    payment_notifications: bool = True
    promotional_notifications: bool = False
    newsletter: bool = False
    security_alerts: bool = True
    social_notifications: bool = True
    reminder_notifications: bool = True
    
    quiet_hours_enabled: bool = False
    quiet_hours_start: Optional[str] = "22:00"
    quiet_hours_end: Optional[str] = "08:00"
    quiet_hours_timezone: str = "Africa/Lagos"
    
    max_emails_per_day: int = 10
    max_sms_per_day: int = 5
    max_push_per_hour: int = 5


# === Template Schemas ===

class NotificationTemplateCreate(BaseSchema):
    """Create notification template"""
    name: str
    category: NotificationCategory
    description: Optional[str] = None
    
    email_subject: Optional[str] = None
    email_html_template: Optional[str] = None
    email_text_template: Optional[str] = None
    sms_template: Optional[str] = None
    push_title_template: Optional[str] = None
    push_body_template: Optional[str] = None
    in_app_title_template: Optional[str] = None
    in_app_message_template: Optional[str] = None
    
    mailchimp_template_id: Optional[str] = None
    sendgrid_template_id: Optional[str] = None
    
    variables: List[str] = Field(default_factory=list)


class NotificationTemplateUpdate(BaseSchema):
    """Update notification template"""
    description: Optional[str] = None
    
    email_subject: Optional[str] = None
    email_html_template: Optional[str] = None
    email_text_template: Optional[str] = None
    sms_template: Optional[str] = None
    push_title_template: Optional[str] = None
    push_body_template: Optional[str] = None
    in_app_title_template: Optional[str] = None
    in_app_message_template: Optional[str] = None
    
    mailchimp_template_id: Optional[str] = None
    sendgrid_template_id: Optional[str] = None
    
    variables: Optional[List[str]] = None
    is_active: Optional[bool] = None


class NotificationTemplateResponse(BaseSchema):
    """Notification template response"""
    id: str
    name: str
    category: str
    description: Optional[str] = None
    
    email_subject: Optional[str] = None
    email_html_template: Optional[str] = None
    email_text_template: Optional[str] = None
    sms_template: Optional[str] = None
    push_title_template: Optional[str] = None
    push_body_template: Optional[str] = None
    in_app_title_template: Optional[str] = None
    in_app_message_template: Optional[str] = None
    
    mailchimp_template_id: Optional[str] = None
    sendgrid_template_id: Optional[str] = None
    
    variables: List[str] = Field(default_factory=list)
    is_active: bool = True
    
    created_at: datetime
    updated_at: datetime


# === Stats Schemas ===

class NotificationStats(BaseSchema):
    """Notification statistics"""
    total_sent: int = 0
    total_delivered: int = 0
    total_read: int = 0
    total_failed: int = 0
    
    email_sent: int = 0
    email_delivered: int = 0
    email_failed: int = 0
    
    sms_sent: int = 0
    sms_delivered: int = 0
    sms_failed: int = 0
    
    push_sent: int = 0
    push_delivered: int = 0
    push_failed: int = 0
    
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


# === Device Token Schemas ===

class DeviceTokenRegister(BaseSchema):
    """Register device token for push notifications"""
    token: str
    platform: str  # ios, android, web
    device_name: Optional[str] = None
    device_model: Optional[str] = None
    os_version: Optional[str] = None
    app_version: Optional[str] = None


class DeviceTokenResponse(BaseSchema):
    """Device token response"""
    id: str
    token: str
    platform: str
    device_name: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    last_used_at: Optional[datetime] = None


# === Unsubscribe Schemas ===

class UnsubscribeRequest(BaseSchema):
    """Unsubscribe from notifications"""
    token: str
    channel: NotificationChannel
    category: Optional[NotificationCategory] = None


class UnsubscribeResponse(BaseSchema):
    """Unsubscribe response"""
    success: bool
    message: str
    channel: str
    category: Optional[str] = None

