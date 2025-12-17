"""
Queska Backend - SMS Service
Handles SMS sending via Twilio and Termii (Africa-focused backup)
"""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from app.core.config import settings


# === SMS Result ===

class SMSResult:
    """Result of an SMS send operation"""
    
    def __init__(
        self,
        success: bool,
        message_id: Optional[str] = None,
        provider: Optional[str] = None,
        error: Optional[str] = None,
        error_code: Optional[str] = None,
        segments: int = 1,
        cost: Optional[float] = None,
        response_data: Optional[Dict[str, Any]] = None
    ):
        self.success = success
        self.message_id = message_id
        self.provider = provider
        self.error = error
        self.error_code = error_code
        self.segments = segments
        self.cost = cost
        self.response_data = response_data or {}
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "message_id": self.message_id,
            "provider": self.provider,
            "error": self.error,
            "error_code": self.error_code,
            "segments": self.segments,
            "cost": self.cost,
            "response_data": self.response_data,
            "timestamp": self.timestamp.isoformat()
        }


# === SMS Message ===

class SMSMessage:
    """SMS message content"""
    
    def __init__(
        self,
        to_phone: str,
        message: str,
        sender_id: Optional[str] = None,
        is_unicode: bool = False,
        media_url: Optional[str] = None,  # For MMS
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.to_phone = self._normalize_phone(to_phone)
        self.message = message
        self.sender_id = sender_id
        self.is_unicode = is_unicode
        self.media_url = media_url
        self.metadata = metadata or {}
    
    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """Normalize phone number to E.164 format"""
        # Remove spaces, dashes, parentheses
        phone = "".join(c for c in phone if c.isdigit() or c == "+")
        
        # Ensure starts with +
        if not phone.startswith("+"):
            # Assume Nigerian number if starts with 0
            if phone.startswith("0"):
                phone = "+234" + phone[1:]
            else:
                phone = "+" + phone
        
        return phone
    
    @property
    def segment_count(self) -> int:
        """Calculate number of SMS segments"""
        if self.is_unicode:
            # Unicode: 70 chars per segment, 67 if multipart
            if len(self.message) <= 70:
                return 1
            return (len(self.message) + 66) // 67
        else:
            # GSM-7: 160 chars per segment, 153 if multipart
            if len(self.message) <= 160:
                return 1
            return (len(self.message) + 152) // 153


# === Base SMS Provider ===

class BaseSMSProvider(ABC):
    """Abstract base class for SMS providers"""
    
    @abstractmethod
    async def send(self, message: SMSMessage) -> SMSResult:
        """Send an SMS"""
        pass
    
    @abstractmethod
    async def send_batch(self, messages: List[SMSMessage]) -> List[SMSResult]:
        """Send multiple SMS messages"""
        pass
    
    @abstractmethod
    async def get_balance(self) -> Dict[str, Any]:
        """Get account balance"""
        pass
    
    @abstractmethod
    def is_configured(self) -> bool:
        """Check if provider is properly configured"""
        pass


# === Twilio Provider ===

class TwilioProvider(BaseSMSProvider):
    """Twilio SMS provider"""
    
    API_URL = "https://api.twilio.com/2010-04-01"
    
    def __init__(self):
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.from_number = settings.TWILIO_PHONE_NUMBER
        self.messaging_service_sid = settings.TWILIO_MESSAGING_SERVICE_SID
    
    def is_configured(self) -> bool:
        return bool(self.account_sid and self.auth_token and (self.from_number or self.messaging_service_sid))
    
    async def send(self, message: SMSMessage) -> SMSResult:
        """Send SMS via Twilio"""
        if not self.is_configured():
            return SMSResult(
                success=False,
                provider="twilio",
                error="Twilio credentials not configured",
                error_code="NOT_CONFIGURED"
            )
        
        # Build request data
        data = {
            "To": message.to_phone,
            "Body": message.message
        }
        
        # Use messaging service or phone number
        if self.messaging_service_sid:
            data["MessagingServiceSid"] = self.messaging_service_sid
        else:
            data["From"] = self.from_number
        
        # Add MMS media if provided
        if message.media_url:
            data["MediaUrl"] = message.media_url
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.API_URL}/Accounts/{self.account_sid}/Messages.json",
                    data=data,
                    auth=(self.account_sid, self.auth_token)
                )
                
                result_data = response.json()
                
                if response.status_code == 201:
                    return SMSResult(
                        success=True,
                        message_id=result_data.get("sid"),
                        provider="twilio",
                        segments=result_data.get("num_segments", 1),
                        response_data=result_data
                    )
                else:
                    return SMSResult(
                        success=False,
                        provider="twilio",
                        error=result_data.get("message", "Unknown error"),
                        error_code=str(result_data.get("code", response.status_code)),
                        response_data=result_data
                    )
                    
        except Exception as e:
            logger.error(f"Twilio send error: {e}")
            return SMSResult(
                success=False,
                provider="twilio",
                error=str(e),
                error_code="EXCEPTION"
            )
    
    async def send_batch(self, messages: List[SMSMessage]) -> List[SMSResult]:
        """Send multiple SMS via Twilio"""
        results = []
        for message in messages:
            result = await self.send(message)
            results.append(result)
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.1)
        return results
    
    async def get_balance(self) -> Dict[str, Any]:
        """Get Twilio account balance"""
        if not self.is_configured():
            return {"error": "Not configured"}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.API_URL}/Accounts/{self.account_sid}/Balance.json",
                    auth=(self.account_sid, self.auth_token)
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "balance": data.get("balance"),
                        "currency": data.get("currency"),
                        "provider": "twilio"
                    }
                return {"error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            return {"error": str(e)}
    
    async def lookup_phone(self, phone: str) -> Dict[str, Any]:
        """Lookup phone number details via Twilio"""
        if not self.is_configured():
            return {"error": "Not configured"}
        
        normalized = SMSMessage._normalize_phone(phone)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"https://lookups.twilio.com/v1/PhoneNumbers/{normalized}",
                    params={"Type": "carrier"},
                    auth=(self.account_sid, self.auth_token)
                )
                
                if response.status_code == 200:
                    return response.json()
                return {"error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            return {"error": str(e)}


# === Termii Provider (Africa-focused backup) ===

class TermiiProvider(BaseSMSProvider):
    """Termii SMS provider (Africa-focused)"""
    
    API_URL = "https://api.ng.termii.com/api"
    
    def __init__(self):
        self.api_key = settings.TERMII_API_KEY
        self.sender_id = settings.TERMII_SENDER_ID or "Queska"
    
    def is_configured(self) -> bool:
        return bool(self.api_key)
    
    async def send(self, message: SMSMessage) -> SMSResult:
        """Send SMS via Termii"""
        if not self.is_configured():
            return SMSResult(
                success=False,
                provider="termii",
                error="Termii API key not configured",
                error_code="NOT_CONFIGURED"
            )
        
        payload = {
            "api_key": self.api_key,
            "to": message.to_phone.lstrip("+"),
            "from": message.sender_id or self.sender_id,
            "sms": message.message,
            "type": "plain",
            "channel": "generic"
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.API_URL}/sms/send",
                    json=payload
                )
                
                result_data = response.json()
                
                if response.status_code == 200 and result_data.get("code") == "ok":
                    return SMSResult(
                        success=True,
                        message_id=result_data.get("message_id"),
                        provider="termii",
                        segments=message.segment_count,
                        response_data=result_data
                    )
                else:
                    return SMSResult(
                        success=False,
                        provider="termii",
                        error=result_data.get("message", "Unknown error"),
                        error_code=str(result_data.get("code", response.status_code)),
                        response_data=result_data
                    )
                    
        except Exception as e:
            logger.error(f"Termii send error: {e}")
            return SMSResult(
                success=False,
                provider="termii",
                error=str(e),
                error_code="EXCEPTION"
            )
    
    async def send_batch(self, messages: List[SMSMessage]) -> List[SMSResult]:
        """Send multiple SMS via Termii"""
        results = []
        for message in messages:
            result = await self.send(message)
            results.append(result)
            await asyncio.sleep(0.1)
        return results
    
    async def get_balance(self) -> Dict[str, Any]:
        """Get Termii account balance"""
        if not self.is_configured():
            return {"error": "Not configured"}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.API_URL}/get-balance",
                    params={"api_key": self.api_key}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "balance": data.get("balance"),
                        "currency": data.get("currency", "NGN"),
                        "provider": "termii"
                    }
                return {"error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            return {"error": str(e)}


# === Main SMS Service ===

class SMSService:
    """
    Main SMS service that manages providers and handles sending.
    Automatically falls back to secondary providers if primary fails.
    """
    
    def __init__(self):
        self.providers: Dict[str, BaseSMSProvider] = {
            "twilio": TwilioProvider(),
            "termii": TermiiProvider()
        }
        self.primary_provider = settings.SMS_PROVIDER
    
    def _get_provider(self, provider_name: Optional[str] = None) -> BaseSMSProvider:
        """Get SMS provider by name or return primary"""
        name = provider_name or self.primary_provider
        return self.providers.get(name, self.providers["twilio"])
    
    def _get_fallback_providers(self) -> List[BaseSMSProvider]:
        """Get list of fallback providers"""
        fallback_order = ["twilio", "termii"]
        fallbacks = []
        for name in fallback_order:
            if name != self.primary_provider:
                provider = self.providers.get(name)
                if provider and provider.is_configured():
                    fallbacks.append(provider)
        return fallbacks
    
    async def send_sms(
        self,
        to_phone: str,
        message: str,
        sender_id: Optional[str] = None,
        is_unicode: bool = False,
        use_fallback: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SMSResult:
        """
        Send an SMS with automatic fallback to secondary providers.
        
        Args:
            to_phone: Recipient phone number (any format)
            message: SMS message content
            sender_id: Custom sender ID (if supported)
            is_unicode: Whether message contains unicode characters
            use_fallback: Whether to try fallback providers on failure
            metadata: Custom metadata for tracking
            
        Returns:
            SMSResult with success status and details
        """
        sms_message = SMSMessage(
            to_phone=to_phone,
            message=message,
            sender_id=sender_id,
            is_unicode=is_unicode,
            metadata=metadata
        )
        
        # Try primary provider
        provider = self._get_provider()
        if provider.is_configured():
            result = await provider.send(sms_message)
            if result.success:
                logger.info(f"SMS sent via {result.provider} to {sms_message.to_phone}")
                return result
            logger.warning(f"Primary SMS provider failed: {result.error}")
        
        # Try fallback providers
        if use_fallback:
            for fallback in self._get_fallback_providers():
                result = await fallback.send(sms_message)
                if result.success:
                    logger.info(f"SMS sent via fallback {result.provider} to {sms_message.to_phone}")
                    return result
                logger.warning(f"Fallback provider {result.provider} failed: {result.error}")
        
        return SMSResult(
            success=False,
            error="All SMS providers failed",
            error_code="ALL_PROVIDERS_FAILED"
        )
    
    async def send_batch(
        self,
        recipients: List[str],
        message: str,
        sender_id: Optional[str] = None
    ) -> List[SMSResult]:
        """
        Send same message to multiple recipients.
        
        Args:
            recipients: List of phone numbers
            message: SMS message content
            sender_id: Custom sender ID
            
        Returns:
            List of SMSResult for each recipient
        """
        messages = [
            SMSMessage(to_phone=phone, message=message, sender_id=sender_id)
            for phone in recipients
        ]
        
        provider = self._get_provider()
        if provider.is_configured():
            return await provider.send_batch(messages)
        
        return [
            SMSResult(success=False, error="No provider configured")
            for _ in recipients
        ]
    
    async def get_balance(self, provider_name: Optional[str] = None) -> Dict[str, Any]:
        """Get account balance from provider"""
        provider = self._get_provider(provider_name)
        return await provider.get_balance()
    
    # === Convenience Methods ===
    
    async def send_verification_code(
        self,
        to_phone: str,
        code: str,
        expiry_minutes: int = 10
    ) -> SMSResult:
        """Send verification code SMS"""
        message = f"Your Queska verification code is: {code}. Valid for {expiry_minutes} minutes. Do not share this code."
        return await self.send_sms(
            to_phone=to_phone,
            message=message,
            metadata={"type": "verification", "code": code}
        )
    
    async def send_otp(
        self,
        to_phone: str,
        otp: str,
        purpose: str = "login"
    ) -> SMSResult:
        """Send OTP SMS"""
        message = f"Your Queska {purpose} OTP is: {otp}. Valid for 5 minutes. Do not share this code with anyone."
        return await self.send_sms(
            to_phone=to_phone,
            message=message,
            metadata={"type": "otp", "purpose": purpose}
        )
    
    async def send_booking_confirmation(
        self,
        to_phone: str,
        booking_id: str,
        experience_name: str,
        date: str
    ) -> SMSResult:
        """Send booking confirmation SMS"""
        message = f"Queska: Your booking #{booking_id} for {experience_name} on {date} is confirmed! Check your email for details."
        return await self.send_sms(
            to_phone=to_phone,
            message=message,
            metadata={"type": "booking", "booking_id": booking_id}
        )
    
    async def send_payment_received(
        self,
        to_phone: str,
        amount: float,
        currency: str = "NGN",
        reference: Optional[str] = None
    ) -> SMSResult:
        """Send payment received SMS"""
        message = f"Queska: Payment of {currency} {amount:,.2f} received successfully."
        if reference:
            message += f" Ref: {reference}"
        return await self.send_sms(
            to_phone=to_phone,
            message=message,
            metadata={"type": "payment", "amount": amount, "reference": reference}
        )
    
    async def send_reminder(
        self,
        to_phone: str,
        experience_name: str,
        time_until: str
    ) -> SMSResult:
        """Send experience reminder SMS"""
        message = f"Queska Reminder: Your {experience_name} starts in {time_until}. Have a great experience!"
        return await self.send_sms(
            to_phone=to_phone,
            message=message,
            metadata={"type": "reminder"}
        )
    
    async def send_alert(
        self,
        to_phone: str,
        alert_message: str,
        priority: str = "normal"
    ) -> SMSResult:
        """Send alert SMS"""
        prefix = "⚠️ " if priority == "high" else ""
        message = f"{prefix}Queska Alert: {alert_message}"
        return await self.send_sms(
            to_phone=to_phone,
            message=message,
            metadata={"type": "alert", "priority": priority}
        )


# Global service instance
sms_service = SMSService()

