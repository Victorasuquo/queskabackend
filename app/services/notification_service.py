"""
Queska Backend - Notification Service
Main notification orchestration service that coordinates email, SMS, push, and in-app notifications
"""

import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from beanie import PydanticObjectId
from loguru import logger

from app.core.config import settings
from app.core.constants import (
    NotificationCategory,
    NotificationChannel,
    NotificationPriority,
    NotificationStatus,
    UserType,
)
from app.models.notification import (
    DeliveryAttempt,
    EmailContent,
    InAppContent,
    Notification,
    NotificationPreferences,
    NotificationRecipient,
    NotificationTemplate,
    PushContent,
    SMSContent,
)
from app.services.email_service import email_service, EmailResult
from app.services.sms_service import sms_service, SMSResult
from app.services.push_service import push_service, PushResult


# === Notification Result ===

class NotificationResult:
    """Result of sending a notification across channels"""
    
    def __init__(
        self,
        notification_id: Optional[str] = None,
        channels_attempted: Optional[List[str]] = None,
        channels_succeeded: Optional[List[str]] = None,
        channels_failed: Optional[List[str]] = None,
        email_result: Optional[EmailResult] = None,
        sms_result: Optional[SMSResult] = None,
        push_result: Optional[PushResult] = None,
        error: Optional[str] = None
    ):
        self.notification_id = notification_id
        self.channels_attempted = channels_attempted or []
        self.channels_succeeded = channels_succeeded or []
        self.channels_failed = channels_failed or []
        self.email_result = email_result
        self.sms_result = sms_result
        self.push_result = push_result
        self.error = error
        self.timestamp = datetime.utcnow()
    
    @property
    def success(self) -> bool:
        return len(self.channels_succeeded) > 0
    
    @property
    def partial_success(self) -> bool:
        return len(self.channels_succeeded) > 0 and len(self.channels_failed) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "notification_id": self.notification_id,
            "success": self.success,
            "partial_success": self.partial_success,
            "channels_attempted": self.channels_attempted,
            "channels_succeeded": self.channels_succeeded,
            "channels_failed": self.channels_failed,
            "email_result": self.email_result.to_dict() if self.email_result else None,
            "sms_result": self.sms_result.to_dict() if self.sms_result else None,
            "push_result": self.push_result.to_dict() if self.push_result else None,
            "error": self.error,
            "timestamp": self.timestamp.isoformat()
        }


# === Main Notification Service ===

class NotificationService:
    """
    Main notification service that orchestrates sending across all channels.
    Handles user preferences, templating, and delivery tracking.
    """
    
    def __init__(self):
        self.email = email_service
        self.sms = sms_service
        self.push = push_service
    
    # === Core Send Methods ===
    
    async def send(
        self,
        recipient: Union[Dict[str, Any], NotificationRecipient],
        category: NotificationCategory,
        channels: List[NotificationChannel],
        email_content: Optional[Dict[str, Any]] = None,
        sms_content: Optional[Dict[str, Any]] = None,
        push_content: Optional[Dict[str, Any]] = None,
        in_app_content: Optional[Dict[str, Any]] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        scheduled_at: Optional[datetime] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[str] = None,
        check_preferences: bool = True,
        save_notification: bool = True
    ) -> NotificationResult:
        """
        Send a notification across multiple channels.
        
        Args:
            recipient: Recipient information (user_id, email, phone, device_token)
            category: Notification category for preferences filtering
            channels: List of channels to attempt
            email_content: Email-specific content
            sms_content: SMS-specific content
            push_content: Push notification content
            in_app_content: In-app notification content
            priority: Notification priority
            scheduled_at: Schedule for later delivery
            reference_type: Related entity type (booking, payment, etc.)
            reference_id: Related entity ID
            check_preferences: Whether to check user notification preferences
            save_notification: Whether to save notification to database
            
        Returns:
            NotificationResult with delivery status for each channel
        """
        # Normalize recipient
        if isinstance(recipient, dict):
            recipient = NotificationRecipient(**recipient)
        
        # Create notification record
        notification = Notification(
            recipient=recipient,
            category=category,
            priority=priority,
            channels=channels,
            scheduled_at=scheduled_at,
            reference_type=reference_type,
            reference_id=reference_id,
        )
        
        # Add content for each channel
        if email_content:
            notification.email_content = EmailContent(**email_content)
        if sms_content:
            notification.sms_content = SMSContent(**sms_content)
        if push_content:
            notification.push_content = PushContent(**push_content)
        if in_app_content:
            notification.in_app_content = InAppContent(**in_app_content)
        
        # Check if scheduled for later
        if scheduled_at and scheduled_at > datetime.utcnow():
            notification.status = NotificationStatus.PENDING
            if save_notification:
                await notification.insert()
            return NotificationResult(
                notification_id=str(notification.id),
                channels_attempted=[],
                error=f"Scheduled for {scheduled_at.isoformat()}"
            )
        
        # Check user preferences if requested
        if check_preferences and recipient.user_id:
            channels = await self._filter_by_preferences(
                recipient.user_id,
                recipient.user_type,
                channels,
                category
            )
        
        # Save notification
        if save_notification:
            await notification.insert()
        
        # Send across channels
        result = await self._send_to_channels(notification, channels)
        
        # Update notification status
        if result.success:
            notification.status = NotificationStatus.SENT
            notification.sent_at = datetime.utcnow()
        elif result.partial_success:
            notification.status = NotificationStatus.SENT
            notification.sent_at = datetime.utcnow()
        else:
            notification.status = NotificationStatus.FAILED
            notification.failed_at = datetime.utcnow()
        
        if save_notification:
            await notification.save()
        
        result.notification_id = str(notification.id)
        return result
    
    async def _send_to_channels(
        self,
        notification: Notification,
        channels: List[NotificationChannel]
    ) -> NotificationResult:
        """Send notification to all specified channels"""
        result = NotificationResult()
        result.channels_attempted = [c.value for c in channels]
        
        for channel in channels:
            try:
                if channel == NotificationChannel.EMAIL:
                    if notification.email_content and notification.recipient.email:
                        email_result = await self._send_email(notification)
                        result.email_result = email_result
                        if email_result.success:
                            result.channels_succeeded.append(channel.value)
                            notification.delivery_attempts.append(
                                DeliveryAttempt(
                                    channel=channel,
                                    status=NotificationStatus.SENT,
                                    provider=email_result.provider,
                                    provider_message_id=email_result.message_id
                                )
                            )
                        else:
                            result.channels_failed.append(channel.value)
                            notification.delivery_attempts.append(
                                DeliveryAttempt(
                                    channel=channel,
                                    status=NotificationStatus.FAILED,
                                    provider=email_result.provider,
                                    error_message=email_result.error,
                                    error_code=email_result.error_code
                                )
                            )
                
                elif channel == NotificationChannel.SMS:
                    if notification.sms_content and notification.recipient.phone:
                        sms_result = await self._send_sms(notification)
                        result.sms_result = sms_result
                        if sms_result.success:
                            result.channels_succeeded.append(channel.value)
                            notification.delivery_attempts.append(
                                DeliveryAttempt(
                                    channel=channel,
                                    status=NotificationStatus.SENT,
                                    provider=sms_result.provider,
                                    provider_message_id=sms_result.message_id
                                )
                            )
                        else:
                            result.channels_failed.append(channel.value)
                            notification.delivery_attempts.append(
                                DeliveryAttempt(
                                    channel=channel,
                                    status=NotificationStatus.FAILED,
                                    provider=sms_result.provider,
                                    error_message=sms_result.error,
                                    error_code=sms_result.error_code
                                )
                            )
                
                elif channel == NotificationChannel.PUSH:
                    if notification.push_content and notification.recipient.device_token:
                        push_result = await self._send_push(notification)
                        result.push_result = push_result
                        if push_result.success:
                            result.channels_succeeded.append(channel.value)
                            notification.delivery_attempts.append(
                                DeliveryAttempt(
                                    channel=channel,
                                    status=NotificationStatus.SENT,
                                    provider=push_result.provider,
                                    provider_message_id=push_result.message_id
                                )
                            )
                        else:
                            result.channels_failed.append(channel.value)
                            notification.delivery_attempts.append(
                                DeliveryAttempt(
                                    channel=channel,
                                    status=NotificationStatus.FAILED,
                                    provider=push_result.provider,
                                    error_message=push_result.error,
                                    error_code=push_result.error_code
                                )
                            )
                
                elif channel == NotificationChannel.IN_APP:
                    if notification.in_app_content:
                        # In-app notifications are stored directly - no external sending
                        result.channels_succeeded.append(channel.value)
                        notification.delivery_attempts.append(
                            DeliveryAttempt(
                                channel=channel,
                                status=NotificationStatus.DELIVERED,
                                provider="in_app"
                            )
                        )
                
            except Exception as e:
                logger.error(f"Error sending to {channel.value}: {e}")
                result.channels_failed.append(channel.value)
                notification.delivery_attempts.append(
                    DeliveryAttempt(
                        channel=channel,
                        status=NotificationStatus.FAILED,
                        error_message=str(e),
                        error_code="EXCEPTION"
                    )
                )
        
        return result
    
    async def _send_email(self, notification: Notification) -> EmailResult:
        """Send email notification"""
        content = notification.email_content
        recipient = notification.recipient
        
        # Use template if specified
        if content.template_id:
            return await self.email.send_template_email(
                to_email=recipient.email,
                template_id=content.template_id,
                template_data=content.template_data or {},
                to_name=recipient.name,
                subject=content.subject
            )
        
        # Send raw email
        return await self.email.send_email(
            to_email=recipient.email,
            to_name=recipient.name,
            subject=content.subject,
            html_body=content.html_body,
            text_body=content.text_body,
            cc=content.cc,
            bcc=content.bcc,
            reply_to=content.reply_to,
            attachments=content.attachments
        )
    
    async def _send_sms(self, notification: Notification) -> SMSResult:
        """Send SMS notification"""
        content = notification.sms_content
        recipient = notification.recipient
        
        return await self.sms.send_sms(
            to_phone=recipient.phone,
            message=content.message,
            sender_id=content.sender_id,
            is_unicode=content.is_unicode
        )
    
    async def _send_push(self, notification: Notification) -> PushResult:
        """Send push notification"""
        content = notification.push_content
        recipient = notification.recipient
        
        return await self.push.send_to_device(
            device_token=recipient.device_token,
            title=content.title,
            body=content.body,
            data=content.data,
            image_url=content.image_url,
            click_action=content.click_action,
            badge=content.badge,
            sound=content.sound
        )
    
    async def _filter_by_preferences(
        self,
        user_id: str,
        user_type: Optional[UserType],
        channels: List[NotificationChannel],
        category: NotificationCategory
    ) -> List[NotificationChannel]:
        """Filter channels based on user notification preferences"""
        # TODO: Fetch user preferences from database
        # For now, return all channels
        return channels
    
    # === Convenience Methods ===
    
    async def send_verification_email(
        self,
        to_email: str,
        to_name: str,
        verification_url: str,
        user_id: Optional[str] = None
    ) -> NotificationResult:
        """Send account verification email"""
        email_result = await self.email.send_verification_email(
            to_email=to_email,
            to_name=to_name,
            verification_url=verification_url,
            token=secrets.token_urlsafe(32)
        )
        
        return NotificationResult(
            channels_attempted=[NotificationChannel.EMAIL.value],
            channels_succeeded=[NotificationChannel.EMAIL.value] if email_result.success else [],
            channels_failed=[] if email_result.success else [NotificationChannel.EMAIL.value],
            email_result=email_result
        )
    
    async def send_password_reset(
        self,
        to_email: str,
        to_name: str,
        reset_url: str,
        user_id: Optional[str] = None
    ) -> NotificationResult:
        """Send password reset email"""
        email_result = await self.email.send_password_reset_email(
            to_email=to_email,
            to_name=to_name,
            reset_url=reset_url
        )
        
        return NotificationResult(
            channels_attempted=[NotificationChannel.EMAIL.value],
            channels_succeeded=[NotificationChannel.EMAIL.value] if email_result.success else [],
            channels_failed=[] if email_result.success else [NotificationChannel.EMAIL.value],
            email_result=email_result
        )
    
    async def send_otp(
        self,
        to_phone: str,
        otp: str,
        purpose: str = "verification",
        user_id: Optional[str] = None
    ) -> NotificationResult:
        """Send OTP via SMS"""
        sms_result = await self.sms.send_otp(
            to_phone=to_phone,
            otp=otp,
            purpose=purpose
        )
        
        return NotificationResult(
            channels_attempted=[NotificationChannel.SMS.value],
            channels_succeeded=[NotificationChannel.SMS.value] if sms_result.success else [],
            channels_failed=[] if sms_result.success else [NotificationChannel.SMS.value],
            sms_result=sms_result
        )
    
    async def send_booking_confirmation(
        self,
        recipient: Dict[str, Any],
        booking_data: Dict[str, Any],
        channels: Optional[List[NotificationChannel]] = None
    ) -> NotificationResult:
        """Send booking confirmation across channels"""
        if channels is None:
            channels = [
                NotificationChannel.EMAIL,
                NotificationChannel.SMS,
                NotificationChannel.PUSH,
                NotificationChannel.IN_APP
            ]
        
        booking_id = booking_data.get("booking_id", "")
        experience_name = booking_data.get("experience_name", "Your Experience")
        date = booking_data.get("date", "")
        total = booking_data.get("total_amount", 0)
        currency = booking_data.get("currency", "NGN")
        
        return await self.send(
            recipient=recipient,
            category=NotificationCategory.BOOKING_CONFIRMATION,
            channels=channels,
            email_content={
                "subject": f"Booking Confirmed - {experience_name}",
                "html_body": f"""
                    <h2>Your booking is confirmed!</h2>
                    <p>Booking ID: {booking_id}</p>
                    <p>Experience: {experience_name}</p>
                    <p>Date: {date}</p>
                    <p>Total: {currency} {total:,.2f}</p>
                """,
                "text_body": f"Booking {booking_id} confirmed for {experience_name} on {date}. Total: {currency} {total:,.2f}"
            },
            sms_content={
                "message": f"Queska: Booking #{booking_id} confirmed for {experience_name} on {date}. Total: {currency} {total:,.2f}"
            },
            push_content={
                "title": "Booking Confirmed! ✅",
                "body": f"Your booking for {experience_name} is confirmed!",
                "data": {"type": "booking", "booking_id": booking_id}
            },
            in_app_content={
                "title": "Booking Confirmed",
                "message": f"Your booking for {experience_name} on {date} has been confirmed.",
                "action_url": f"/bookings/{booking_id}",
                "action_text": "View Booking"
            },
            reference_type="booking",
            reference_id=booking_id
        )
    
    async def send_payment_notification(
        self,
        recipient: Dict[str, Any],
        payment_data: Dict[str, Any],
        status: str = "success",
        channels: Optional[List[NotificationChannel]] = None
    ) -> NotificationResult:
        """Send payment notification"""
        if channels is None:
            channels = [NotificationChannel.EMAIL, NotificationChannel.PUSH, NotificationChannel.IN_APP]
        
        amount = payment_data.get("amount", 0)
        currency = payment_data.get("currency", "NGN")
        reference = payment_data.get("reference", "")
        
        if status == "success":
            category = NotificationCategory.PAYMENT_RECEIVED
            subject = "Payment Successful"
            title = "Payment Successful 💳"
            body = f"Your payment of {currency} {amount:,.2f} was successful."
        else:
            category = NotificationCategory.PAYMENT_FAILED
            subject = "Payment Failed"
            title = "Payment Failed"
            body = f"Your payment of {currency} {amount:,.2f} could not be processed."
        
        return await self.send(
            recipient=recipient,
            category=category,
            channels=channels,
            email_content={
                "subject": subject,
                "html_body": f"<h2>{title}</h2><p>{body}</p><p>Reference: {reference}</p>",
                "text_body": f"{body} Reference: {reference}"
            },
            push_content={
                "title": title,
                "body": body,
                "data": {"type": "payment", "status": status, "reference": reference}
            },
            in_app_content={
                "title": title,
                "message": body,
                "action_url": "/payments",
                "action_text": "View Payments"
            },
            reference_type="payment",
            reference_id=reference
        )
    
    async def send_vendor_notification(
        self,
        vendor_id: str,
        vendor_email: str,
        vendor_phone: Optional[str],
        vendor_device_token: Optional[str],
        category: NotificationCategory,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        channels: Optional[List[NotificationChannel]] = None
    ) -> NotificationResult:
        """Send notification to a vendor"""
        if channels is None:
            channels = [NotificationChannel.EMAIL, NotificationChannel.IN_APP]
            if vendor_device_token:
                channels.append(NotificationChannel.PUSH)
        
        return await self.send(
            recipient={
                "user_id": vendor_id,
                "user_type": UserType.VENDOR,
                "email": vendor_email,
                "phone": vendor_phone,
                "device_token": vendor_device_token
            },
            category=category,
            channels=channels,
            email_content={
                "subject": title,
                "html_body": f"<h2>{title}</h2><p>{message}</p>",
                "text_body": f"{title}\n\n{message}"
            },
            push_content={
                "title": title,
                "body": message,
                "data": data or {}
            },
            in_app_content={
                "title": title,
                "message": message
            }
        )
    
    # === In-App Notification Methods ===
    
    async def get_user_notifications(
        self,
        user_id: str,
        user_type: Optional[UserType] = None,
        unread_only: bool = False,
        limit: int = 20,
        skip: int = 0
    ) -> List[Notification]:
        """Get notifications for a user"""
        query = {
            "recipient.user_id": user_id,
            "is_deleted": False,
            "channels": NotificationChannel.IN_APP
        }
        
        if user_type:
            query["recipient.user_type"] = user_type
        
        if unread_only:
            query["status"] = {"$ne": NotificationStatus.READ}
        
        notifications = await Notification.find(query).sort(
            [("-created_at", -1)]
        ).skip(skip).limit(limit).to_list()
        
        return notifications
    
    async def get_unread_count(
        self,
        user_id: str,
        user_type: Optional[UserType] = None
    ) -> int:
        """Get count of unread notifications"""
        query = {
            "recipient.user_id": user_id,
            "is_deleted": False,
            "channels": NotificationChannel.IN_APP,
            "status": {"$ne": NotificationStatus.READ}
        }
        
        if user_type:
            query["recipient.user_type"] = user_type
        
        return await Notification.find(query).count()
    
    async def mark_as_read(
        self,
        notification_id: str,
        user_id: str
    ) -> bool:
        """Mark a notification as read"""
        notification = await Notification.get(PydanticObjectId(notification_id))
        
        if not notification or notification.recipient.user_id != user_id:
            return False
        
        notification.mark_as_read()
        await notification.save()
        return True
    
    async def mark_all_as_read(
        self,
        user_id: str,
        user_type: Optional[UserType] = None
    ) -> int:
        """Mark all notifications as read for a user"""
        query = {
            "recipient.user_id": user_id,
            "is_deleted": False,
            "status": {"$ne": NotificationStatus.READ}
        }
        
        if user_type:
            query["recipient.user_type"] = user_type
        
        result = await Notification.find(query).update_many(
            {"$set": {
                "status": NotificationStatus.READ,
                "read_at": datetime.utcnow()
            }}
        )
        
        return result.modified_count if hasattr(result, 'modified_count') else 0
    
    async def delete_notification(
        self,
        notification_id: str,
        user_id: str
    ) -> bool:
        """Soft delete a notification"""
        notification = await Notification.get(PydanticObjectId(notification_id))
        
        if not notification or notification.recipient.user_id != user_id:
            return False
        
        await notification.soft_delete()
        return True
    
    # === Template Methods ===
    
    async def send_from_template(
        self,
        template_name: str,
        recipient: Dict[str, Any],
        template_data: Dict[str, Any],
        channels: Optional[List[NotificationChannel]] = None
    ) -> NotificationResult:
        """Send notification using a template"""
        # Fetch template
        template = await NotificationTemplate.find_one(
            {"name": template_name, "is_active": True}
        )
        
        if not template:
            return NotificationResult(error=f"Template '{template_name}' not found")
        
        if channels is None:
            channels = [NotificationChannel.EMAIL, NotificationChannel.IN_APP]
        
        # Render template content
        def render(template_str: Optional[str]) -> Optional[str]:
            if not template_str:
                return None
            try:
                return template_str.format(**template_data)
            except KeyError as e:
                logger.warning(f"Missing template variable: {e}")
                return template_str
        
        # Build content for each channel
        email_content = None
        if template.email_subject or template.email_html_template:
            email_content = {
                "subject": render(template.email_subject) or "Notification",
                "html_body": render(template.email_html_template),
                "text_body": render(template.email_text_template)
            }
            
            # Use external template if specified
            if template.mailchimp_template_id:
                email_content["template_id"] = template.mailchimp_template_id
                email_content["template_data"] = template_data
        
        sms_content = None
        if template.sms_template:
            sms_content = {"message": render(template.sms_template)}
        
        push_content = None
        if template.push_title_template or template.push_body_template:
            push_content = {
                "title": render(template.push_title_template) or "Notification",
                "body": render(template.push_body_template) or ""
            }
        
        in_app_content = None
        if template.in_app_title_template or template.in_app_message_template:
            in_app_content = {
                "title": render(template.in_app_title_template) or "Notification",
                "message": render(template.in_app_message_template) or ""
            }
        
        return await self.send(
            recipient=recipient,
            category=template.category,
            channels=channels,
            email_content=email_content,
            sms_content=sms_content,
            push_content=push_content,
            in_app_content=in_app_content
        )
    
    # === Batch Methods ===
    
    async def send_batch(
        self,
        recipients: List[Dict[str, Any]],
        category: NotificationCategory,
        channels: List[NotificationChannel],
        email_content: Optional[Dict[str, Any]] = None,
        sms_content: Optional[Dict[str, Any]] = None,
        push_content: Optional[Dict[str, Any]] = None,
        in_app_content: Optional[Dict[str, Any]] = None
    ) -> List[NotificationResult]:
        """Send notification to multiple recipients"""
        batch_id = secrets.token_hex(16)
        results = []
        
        for recipient in recipients:
            result = await self.send(
                recipient=recipient,
                category=category,
                channels=channels,
                email_content=email_content,
                sms_content=sms_content,
                push_content=push_content,
                in_app_content=in_app_content
            )
            results.append(result)
        
        logger.info(
            f"Batch {batch_id}: Sent to {len(recipients)} recipients, "
            f"{sum(1 for r in results if r.success)} successful"
        )
        
        return results
    
    async def send_to_topic(
        self,
        topic: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        image_url: Optional[str] = None
    ) -> PushResult:
        """Send push notification to a topic"""
        return await self.push.send_to_topic(
            topic=topic,
            title=title,
            body=body,
            data=data,
            image_url=image_url
        )


# Global service instance
notification_service = NotificationService()

