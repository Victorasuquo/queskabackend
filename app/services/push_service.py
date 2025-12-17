"""
Queska Backend - Push Notification Service
Handles push notifications via Firebase Cloud Messaging (FCM)
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from app.core.config import settings


# === Push Result ===

class PushResult:
    """Result of a push notification send operation"""
    
    def __init__(
        self,
        success: bool,
        message_id: Optional[str] = None,
        provider: str = "firebase",
        error: Optional[str] = None,
        error_code: Optional[str] = None,
        success_count: int = 0,
        failure_count: int = 0,
        response_data: Optional[Dict[str, Any]] = None
    ):
        self.success = success
        self.message_id = message_id
        self.provider = provider
        self.error = error
        self.error_code = error_code
        self.success_count = success_count
        self.failure_count = failure_count
        self.response_data = response_data or {}
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "message_id": self.message_id,
            "provider": self.provider,
            "error": self.error,
            "error_code": self.error_code,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "response_data": self.response_data,
            "timestamp": self.timestamp.isoformat()
        }


# === Push Message ===

class PushMessage:
    """Push notification message content"""
    
    def __init__(
        self,
        device_token: Optional[str] = None,
        device_tokens: Optional[List[str]] = None,
        topic: Optional[str] = None,
        condition: Optional[str] = None,
        title: str = "",
        body: str = "",
        image_url: Optional[str] = None,
        icon: Optional[str] = None,
        badge: Optional[int] = None,
        sound: Optional[str] = "default",
        click_action: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        android_config: Optional[Dict[str, Any]] = None,
        ios_config: Optional[Dict[str, Any]] = None,
        web_config: Optional[Dict[str, Any]] = None,
        priority: str = "high",  # high, normal
        ttl: int = 86400,  # Time to live in seconds (default 24 hours)
        collapse_key: Optional[str] = None,
        mutable_content: bool = True,
        content_available: bool = True
    ):
        self.device_token = device_token
        self.device_tokens = device_tokens or []
        self.topic = topic
        self.condition = condition
        self.title = title
        self.body = body
        self.image_url = image_url
        self.icon = icon
        self.badge = badge
        self.sound = sound
        self.click_action = click_action
        self.data = data or {}
        self.android_config = android_config
        self.ios_config = ios_config
        self.web_config = web_config
        self.priority = priority
        self.ttl = ttl
        self.collapse_key = collapse_key
        self.mutable_content = mutable_content
        self.content_available = content_available
    
    @property
    def target_type(self) -> str:
        """Determine the target type"""
        if self.device_token:
            return "token"
        elif len(self.device_tokens) > 0:
            return "multicast"
        elif self.topic:
            return "topic"
        elif self.condition:
            return "condition"
        return "unknown"


# === Firebase Cloud Messaging Service ===

class FirebaseCloudMessaging:
    """Firebase Cloud Messaging (FCM) provider"""
    
    FCM_V1_URL = "https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
    FCM_LEGACY_URL = "https://fcm.googleapis.com/fcm/send"
    
    def __init__(self):
        self.credentials_path = settings.FIREBASE_CREDENTIALS_PATH
        self.project_id = settings.FIREBASE_PROJECT_ID
        self._access_token = None
        self._token_expiry = None
    
    def is_configured(self) -> bool:
        """Check if Firebase is configured"""
        return bool(self.credentials_path or self.project_id)
    
    async def _get_access_token(self) -> Optional[str]:
        """Get OAuth2 access token for FCM v1 API"""
        if not self.credentials_path:
            return None
        
        # Check if token is still valid
        if self._access_token and self._token_expiry:
            if datetime.utcnow() < self._token_expiry:
                return self._access_token
        
        try:
            # Load service account credentials
            with open(self.credentials_path, 'r') as f:
                creds = json.load(f)
            
            # Use google-auth library if available
            try:
                from google.oauth2 import service_account
                from google.auth.transport.requests import Request
                
                credentials = service_account.Credentials.from_service_account_info(
                    creds,
                    scopes=['https://www.googleapis.com/auth/firebase.messaging']
                )
                credentials.refresh(Request())
                
                self._access_token = credentials.token
                self._token_expiry = credentials.expiry
                
                return self._access_token
                
            except ImportError:
                logger.warning("google-auth library not installed, using legacy API")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get Firebase access token: {e}")
            return None
    
    async def send(self, message: PushMessage) -> PushResult:
        """Send push notification via FCM"""
        if not self.is_configured():
            return PushResult(
                success=False,
                error="Firebase not configured",
                error_code="NOT_CONFIGURED"
            )
        
        # Build notification payload
        notification = {
            "title": message.title,
            "body": message.body
        }
        
        if message.image_url:
            notification["image"] = message.image_url
        
        # Build message payload
        fcm_message: Dict[str, Any] = {
            "notification": notification,
            "data": {k: str(v) for k, v in message.data.items()}  # FCM data must be strings
        }
        
        # Add target
        if message.target_type == "token":
            fcm_message["token"] = message.device_token
        elif message.target_type == "topic":
            fcm_message["topic"] = message.topic
        elif message.target_type == "condition":
            fcm_message["condition"] = message.condition
        
        # Add Android config
        android_config = message.android_config or {}
        fcm_message["android"] = {
            "priority": message.priority,
            "ttl": f"{message.ttl}s",
            "notification": {
                "icon": message.icon or "ic_notification",
                "sound": message.sound,
                "click_action": message.click_action,
                **android_config.get("notification", {})
            },
            **{k: v for k, v in android_config.items() if k != "notification"}
        }
        
        if message.collapse_key:
            fcm_message["android"]["collapse_key"] = message.collapse_key
        
        # Add iOS (APNs) config
        ios_config = message.ios_config or {}
        apns_payload = {
            "aps": {
                "alert": {
                    "title": message.title,
                    "body": message.body
                },
                "sound": message.sound,
                "mutable-content": 1 if message.mutable_content else 0,
                "content-available": 1 if message.content_available else 0,
                **ios_config.get("aps", {})
            }
        }
        
        if message.badge is not None:
            apns_payload["aps"]["badge"] = message.badge
        
        fcm_message["apns"] = {
            "payload": apns_payload,
            "headers": {
                "apns-priority": "10" if message.priority == "high" else "5",
                "apns-expiration": str(int(datetime.utcnow().timestamp()) + message.ttl)
            },
            **{k: v for k, v in ios_config.items() if k not in ["aps", "payload"]}
        }
        
        # Add webpush config
        web_config = message.web_config or {}
        fcm_message["webpush"] = {
            "notification": {
                "title": message.title,
                "body": message.body,
                "icon": message.icon,
                "image": message.image_url,
                **web_config.get("notification", {})
            },
            "fcm_options": {
                "link": message.click_action
            },
            **{k: v for k, v in web_config.items() if k != "notification"}
        }
        
        # Try FCM v1 API first
        access_token = await self._get_access_token()
        
        if access_token and self.project_id:
            return await self._send_v1(fcm_message, access_token)
        
        # Fallback to legacy API
        return await self._send_legacy(message, fcm_message)
    
    async def _send_v1(self, fcm_message: Dict[str, Any], access_token: str) -> PushResult:
        """Send via FCM HTTP v1 API"""
        url = self.FCM_V1_URL.format(project_id=self.project_id)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    json={"message": fcm_message},
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    }
                )
                
                result_data = response.json()
                
                if response.status_code == 200:
                    return PushResult(
                        success=True,
                        message_id=result_data.get("name"),
                        success_count=1,
                        response_data=result_data
                    )
                else:
                    error = result_data.get("error", {})
                    return PushResult(
                        success=False,
                        error=error.get("message", "Unknown error"),
                        error_code=error.get("code", str(response.status_code)),
                        failure_count=1,
                        response_data=result_data
                    )
                    
        except Exception as e:
            logger.error(f"FCM v1 send error: {e}")
            return PushResult(
                success=False,
                error=str(e),
                error_code="EXCEPTION",
                failure_count=1
            )
    
    async def _send_legacy(self, message: PushMessage, fcm_message: Dict[str, Any]) -> PushResult:
        """Send via legacy FCM HTTP API (requires server key)"""
        # Legacy API requires server key from Firebase console
        logger.warning("Legacy FCM API not fully implemented - use Firebase Admin SDK")
        return PushResult(
            success=False,
            error="Legacy API not available - configure Firebase credentials",
            error_code="LEGACY_NOT_SUPPORTED"
        )
    
    async def send_multicast(self, message: PushMessage) -> PushResult:
        """Send to multiple device tokens"""
        if not message.device_tokens:
            return PushResult(
                success=False,
                error="No device tokens provided",
                error_code="NO_TOKENS"
            )
        
        # FCM has a limit of 500 tokens per multicast
        results = []
        success_count = 0
        failure_count = 0
        
        for i in range(0, len(message.device_tokens), 500):
            batch = message.device_tokens[i:i+500]
            
            for token in batch:
                single_message = PushMessage(
                    device_token=token,
                    title=message.title,
                    body=message.body,
                    image_url=message.image_url,
                    icon=message.icon,
                    badge=message.badge,
                    sound=message.sound,
                    click_action=message.click_action,
                    data=message.data,
                    android_config=message.android_config,
                    ios_config=message.ios_config,
                    web_config=message.web_config,
                    priority=message.priority,
                    ttl=message.ttl
                )
                
                result = await self.send(single_message)
                results.append(result)
                
                if result.success:
                    success_count += 1
                else:
                    failure_count += 1
        
        return PushResult(
            success=success_count > 0,
            success_count=success_count,
            failure_count=failure_count,
            response_data={"results": [r.to_dict() for r in results]}
        )
    
    async def send_to_topic(self, message: PushMessage) -> PushResult:
        """Send to a topic"""
        if not message.topic:
            return PushResult(
                success=False,
                error="No topic specified",
                error_code="NO_TOPIC"
            )
        
        return await self.send(message)
    
    async def subscribe_to_topic(
        self,
        device_tokens: List[str],
        topic: str
    ) -> Dict[str, Any]:
        """Subscribe devices to a topic"""
        if not self.is_configured():
            return {"error": "Firebase not configured"}
        
        access_token = await self._get_access_token()
        if not access_token:
            return {"error": "Could not get access token"}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"https://iid.googleapis.com/iid/v1:batchAdd",
                    json={
                        "to": f"/topics/{topic}",
                        "registration_tokens": device_tokens
                    },
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    }
                )
                
                return response.json()
                
        except Exception as e:
            return {"error": str(e)}
    
    async def unsubscribe_from_topic(
        self,
        device_tokens: List[str],
        topic: str
    ) -> Dict[str, Any]:
        """Unsubscribe devices from a topic"""
        if not self.is_configured():
            return {"error": "Firebase not configured"}
        
        access_token = await self._get_access_token()
        if not access_token:
            return {"error": "Could not get access token"}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"https://iid.googleapis.com/iid/v1:batchRemove",
                    json={
                        "to": f"/topics/{topic}",
                        "registration_tokens": device_tokens
                    },
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    }
                )
                
                return response.json()
                
        except Exception as e:
            return {"error": str(e)}


# === Main Push Service ===

class PushService:
    """
    Main push notification service.
    Handles sending push notifications via Firebase Cloud Messaging.
    """
    
    def __init__(self):
        self.fcm = FirebaseCloudMessaging()
    
    def is_configured(self) -> bool:
        """Check if push service is configured"""
        return self.fcm.is_configured()
    
    async def send_to_device(
        self,
        device_token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        image_url: Optional[str] = None,
        click_action: Optional[str] = None,
        badge: Optional[int] = None,
        sound: str = "default",
        priority: str = "high"
    ) -> PushResult:
        """
        Send push notification to a single device.
        
        Args:
            device_token: FCM device token
            title: Notification title
            body: Notification body
            data: Custom data payload
            image_url: Image URL for rich notification
            click_action: Action on notification click
            badge: Badge count (iOS)
            sound: Notification sound
            priority: Delivery priority (high/normal)
            
        Returns:
            PushResult with success status
        """
        message = PushMessage(
            device_token=device_token,
            title=title,
            body=body,
            data=data,
            image_url=image_url,
            click_action=click_action,
            badge=badge,
            sound=sound,
            priority=priority
        )
        
        result = await self.fcm.send(message)
        
        if result.success:
            logger.info(f"Push sent to device: {device_token[:20]}...")
        else:
            logger.warning(f"Push failed: {result.error}")
        
        return result
    
    async def send_to_devices(
        self,
        device_tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> PushResult:
        """
        Send push notification to multiple devices.
        
        Args:
            device_tokens: List of FCM device tokens
            title: Notification title
            body: Notification body
            data: Custom data payload
            **kwargs: Additional PushMessage parameters
            
        Returns:
            PushResult with success/failure counts
        """
        message = PushMessage(
            device_tokens=device_tokens,
            title=title,
            body=body,
            data=data,
            **kwargs
        )
        
        result = await self.fcm.send_multicast(message)
        
        logger.info(
            f"Push multicast: {result.success_count} sent, {result.failure_count} failed"
        )
        
        return result
    
    async def send_to_topic(
        self,
        topic: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> PushResult:
        """
        Send push notification to a topic.
        
        Args:
            topic: Topic name (without /topics/ prefix)
            title: Notification title
            body: Notification body
            data: Custom data payload
            
        Returns:
            PushResult
        """
        message = PushMessage(
            topic=topic,
            title=title,
            body=body,
            data=data,
            **kwargs
        )
        
        result = await self.fcm.send_to_topic(message)
        
        if result.success:
            logger.info(f"Push sent to topic: {topic}")
        else:
            logger.warning(f"Push to topic {topic} failed: {result.error}")
        
        return result
    
    async def subscribe_to_topic(
        self,
        device_tokens: List[str],
        topic: str
    ) -> Dict[str, Any]:
        """Subscribe devices to a topic"""
        return await self.fcm.subscribe_to_topic(device_tokens, topic)
    
    async def unsubscribe_from_topic(
        self,
        device_tokens: List[str],
        topic: str
    ) -> Dict[str, Any]:
        """Unsubscribe devices from a topic"""
        return await self.fcm.unsubscribe_from_topic(device_tokens, topic)
    
    # === Convenience Methods ===
    
    async def send_booking_notification(
        self,
        device_token: str,
        booking_id: str,
        experience_name: str,
        status: str = "confirmed"
    ) -> PushResult:
        """Send booking status notification"""
        titles = {
            "confirmed": "Booking Confirmed! ✅",
            "cancelled": "Booking Cancelled",
            "modified": "Booking Updated",
            "reminder": "Upcoming Experience 🎉"
        }
        
        bodies = {
            "confirmed": f"Your booking for {experience_name} is confirmed!",
            "cancelled": f"Your booking for {experience_name} has been cancelled.",
            "modified": f"Your booking for {experience_name} has been updated.",
            "reminder": f"Don't forget! {experience_name} is coming up soon."
        }
        
        return await self.send_to_device(
            device_token=device_token,
            title=titles.get(status, "Booking Update"),
            body=bodies.get(status, f"Update for {experience_name}"),
            data={
                "type": "booking",
                "booking_id": booking_id,
                "status": status
            },
            click_action=f"/bookings/{booking_id}"
        )
    
    async def send_payment_notification(
        self,
        device_token: str,
        amount: float,
        currency: str = "NGN",
        status: str = "success"
    ) -> PushResult:
        """Send payment notification"""
        if status == "success":
            title = "Payment Successful 💳"
            body = f"Your payment of {currency} {amount:,.2f} was successful."
        else:
            title = "Payment Failed"
            body = f"Your payment of {currency} {amount:,.2f} could not be processed."
        
        return await self.send_to_device(
            device_token=device_token,
            title=title,
            body=body,
            data={
                "type": "payment",
                "status": status,
                "amount": str(amount),
                "currency": currency
            }
        )
    
    async def send_message_notification(
        self,
        device_token: str,
        sender_name: str,
        message_preview: str,
        conversation_id: str
    ) -> PushResult:
        """Send new message notification"""
        return await self.send_to_device(
            device_token=device_token,
            title=f"New message from {sender_name}",
            body=message_preview[:100] + "..." if len(message_preview) > 100 else message_preview,
            data={
                "type": "message",
                "conversation_id": conversation_id,
                "sender_name": sender_name
            },
            click_action=f"/messages/{conversation_id}"
        )
    
    async def send_promo_notification(
        self,
        topic: str,
        title: str,
        body: str,
        promo_code: Optional[str] = None,
        image_url: Optional[str] = None
    ) -> PushResult:
        """Send promotional notification to topic"""
        data = {"type": "promo"}
        if promo_code:
            data["promo_code"] = promo_code
        
        return await self.send_to_topic(
            topic=topic,
            title=title,
            body=body,
            data=data,
            image_url=image_url
        )


# Global service instance
push_service = PushService()

