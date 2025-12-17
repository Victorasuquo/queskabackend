"""
Queska Backend - Email Service
Robust email service using SendGrid with SMTP fallback
"""

import asyncio
import base64
import smtplib
from datetime import datetime
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from app.core.config import settings


class EmailResult:
    """Result of an email send operation"""
    
    def __init__(
        self,
        success: bool,
        message_id: Optional[str] = None,
        provider: str = "sendgrid",
        error: Optional[str] = None,
        error_code: Optional[str] = None,
        response_data: Optional[Dict[str, Any]] = None
    ):
        self.success = success
        self.message_id = message_id
        self.provider = provider
        self.error = error
        self.error_code = error_code
        self.response_data = response_data or {}
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "message_id": self.message_id,
            "provider": self.provider,
            "error": self.error,
            "error_code": self.error_code,
            "response_data": self.response_data,
            "timestamp": self.timestamp.isoformat()
        }


class EmailService:
    """
    Robust email service using SendGrid API.
    
    Features:
    - SendGrid v3 API integration
    - Dynamic template support
    - Attachment support
    - SMTP fallback for reliability
    - Comprehensive error handling
    - Email tracking (opens/clicks)
    """
    
    SENDGRID_API_URL = "https://api.sendgrid.com/v3"
    
    def __init__(self):
        self.api_key = settings.SENDGRID_API_KEY
        self.from_email = settings.EMAIL_FROM_ADDRESS
        self.from_name = settings.EMAIL_FROM_NAME
        self.reply_to = getattr(settings, 'EMAIL_REPLY_TO', None) or settings.EMAIL_FROM_ADDRESS
        
        # SMTP fallback settings
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.smtp_tls = settings.SMTP_TLS
    
    def is_configured(self) -> bool:
        """Check if SendGrid is configured"""
        return bool(self.api_key)
    
    def is_smtp_configured(self) -> bool:
        """Check if SMTP fallback is configured"""
        return bool(self.smtp_host and self.smtp_user and self.smtp_password)
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: Optional[str] = None,
        text_body: Optional[str] = None,
        to_name: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        reply_to: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        categories: Optional[List[str]] = None,
        custom_args: Optional[Dict[str, str]] = None,
        send_at: Optional[int] = None,
        use_smtp_fallback: bool = True
    ) -> EmailResult:
        """
        Send an email via SendGrid.
        
        Args:
            to_email: Recipient email address
            subject: Email subject line
            html_body: HTML content of the email
            text_body: Plain text content (fallback)
            to_name: Recipient's name
            from_email: Sender email (defaults to config)
            from_name: Sender name (defaults to config)
            reply_to: Reply-to email address
            cc: List of CC email addresses
            bcc: List of BCC email addresses
            attachments: List of attachments [{"filename": "...", "content": "base64...", "type": "..."}]
            categories: Tags for email analytics
            custom_args: Custom tracking arguments
            send_at: Unix timestamp for scheduled sending
            use_smtp_fallback: Whether to fall back to SMTP on failure
            
        Returns:
            EmailResult with success status and details
        """
        if not self.is_configured():
            if use_smtp_fallback and self.is_smtp_configured():
                logger.warning("SendGrid not configured, using SMTP fallback")
                return await self._send_via_smtp(
                    to_email=to_email,
                    subject=subject,
                    html_body=html_body,
                    text_body=text_body,
                    to_name=to_name,
                    from_email=from_email or self.from_email,
                    from_name=from_name or self.from_name,
                    reply_to=reply_to,
                    cc=cc,
                    bcc=bcc,
                    attachments=attachments
                )
            return EmailResult(
                success=False,
                error="SendGrid API key not configured",
                error_code="NOT_CONFIGURED"
            )
        
        # Build the SendGrid payload
        payload = self._build_payload(
            to_email=to_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            to_name=to_name,
            from_email=from_email,
            from_name=from_name,
            reply_to=reply_to,
            cc=cc,
            bcc=bcc,
            attachments=attachments,
            categories=categories,
            custom_args=custom_args,
            send_at=send_at
        )
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.SENDGRID_API_URL}/mail/send",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    }
                )
                
                # SendGrid returns 202 for successful queuing
                if response.status_code in [200, 202]:
                    message_id = response.headers.get("X-Message-Id")
                    logger.info(f"Email sent successfully to {to_email} [ID: {message_id}]")
                    return EmailResult(
                        success=True,
                        message_id=message_id,
                        provider="sendgrid"
                    )
                
                # Handle errors
                error_body = response.text
                try:
                    error_data = response.json()
                    errors = error_data.get("errors", [])
                    error_message = errors[0].get("message") if errors else error_body
                except Exception:
                    error_message = error_body
                
                logger.error(f"SendGrid error ({response.status_code}): {error_message}")
                
                # Try SMTP fallback for server errors
                if use_smtp_fallback and response.status_code >= 500 and self.is_smtp_configured():
                    logger.warning("SendGrid server error, trying SMTP fallback")
                    return await self._send_via_smtp(
                        to_email=to_email,
                        subject=subject,
                        html_body=html_body,
                        text_body=text_body,
                        to_name=to_name,
                        from_email=from_email or self.from_email,
                        from_name=from_name or self.from_name,
                        reply_to=reply_to,
                        cc=cc,
                        bcc=bcc,
                        attachments=attachments
                    )
                
                return EmailResult(
                    success=False,
                    provider="sendgrid",
                    error=error_message,
                    error_code=str(response.status_code)
                )
                
        except httpx.TimeoutException:
            logger.error("SendGrid request timed out")
            if use_smtp_fallback and self.is_smtp_configured():
                return await self._send_via_smtp(
                    to_email=to_email,
                    subject=subject,
                    html_body=html_body,
                    text_body=text_body,
                    to_name=to_name,
                    from_email=from_email or self.from_email,
                    from_name=from_name or self.from_name,
                    reply_to=reply_to,
                    cc=cc,
                    bcc=bcc,
                    attachments=attachments
                )
            return EmailResult(
                success=False,
                provider="sendgrid",
                error="Request timed out",
                error_code="TIMEOUT"
            )
            
        except Exception as e:
            logger.error(f"SendGrid exception: {e}")
            if use_smtp_fallback and self.is_smtp_configured():
                return await self._send_via_smtp(
                    to_email=to_email,
                    subject=subject,
                    html_body=html_body,
                    text_body=text_body,
                    to_name=to_name,
                    from_email=from_email or self.from_email,
                    from_name=from_name or self.from_name,
                    reply_to=reply_to,
                    cc=cc,
                    bcc=bcc,
                    attachments=attachments
                )
            return EmailResult(
                success=False,
                provider="sendgrid",
                error=str(e),
                error_code="EXCEPTION"
            )
    
    def _build_payload(
        self,
        to_email: str,
        subject: str,
        html_body: Optional[str] = None,
        text_body: Optional[str] = None,
        to_name: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        reply_to: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        categories: Optional[List[str]] = None,
        custom_args: Optional[Dict[str, str]] = None,
        send_at: Optional[int] = None
    ) -> Dict[str, Any]:
        """Build SendGrid API payload"""
        
        # Personalization (recipient info)
        personalization: Dict[str, Any] = {
            "to": [{"email": to_email}]
        }
        
        if to_name:
            personalization["to"][0]["name"] = to_name
        
        # Add CC recipients
        if cc:
            personalization["cc"] = [{"email": email} for email in cc]
        
        # Add BCC recipients
        if bcc:
            personalization["bcc"] = [{"email": email} for email in bcc]
        
        # Add custom tracking args
        if custom_args:
            personalization["custom_args"] = custom_args
        
        # Add scheduled send time
        if send_at:
            personalization["send_at"] = send_at
        
        # Build main payload
        payload: Dict[str, Any] = {
            "personalizations": [personalization],
            "from": {
                "email": from_email or self.from_email,
                "name": from_name or self.from_name
            },
            "subject": subject,
            "tracking_settings": {
                "click_tracking": {"enable": True, "enable_text": True},
                "open_tracking": {"enable": True}
            }
        }
        
        # Add reply-to
        if reply_to or self.reply_to:
            payload["reply_to"] = {"email": reply_to or self.reply_to}
        
        # Add content
        content = []
        if text_body:
            content.append({"type": "text/plain", "value": text_body})
        if html_body:
            content.append({"type": "text/html", "value": html_body})
        
        if not content:
            # Default empty content
            content.append({"type": "text/plain", "value": " "})
        
        payload["content"] = content
        
        # Add categories for analytics
        if categories:
            payload["categories"] = categories[:10]  # SendGrid max 10 categories
        
        # Add attachments
        if attachments:
            payload["attachments"] = [
                {
                    "content": att.get("content", ""),
                    "filename": att.get("filename", "attachment"),
                    "type": att.get("type", "application/octet-stream"),
                    "disposition": att.get("disposition", "attachment")
                }
                for att in attachments
            ]
        
        return payload
    
    async def send_template_email(
        self,
        to_email: str,
        template_id: str,
        template_data: Dict[str, Any],
        to_name: Optional[str] = None,
        subject: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        categories: Optional[List[str]] = None
    ) -> EmailResult:
        """
        Send email using a SendGrid Dynamic Template.
        
        Args:
            to_email: Recipient email
            template_id: SendGrid template ID (d-xxxx...)
            template_data: Data to merge into template
            to_name: Recipient name
            subject: Subject override (if template allows)
            from_email: Sender email
            from_name: Sender name
            categories: Tags for analytics
            
        Returns:
            EmailResult
        """
        if not self.is_configured():
            return EmailResult(
                success=False,
                error="SendGrid API key not configured",
                error_code="NOT_CONFIGURED"
            )
        
        # Build personalization with dynamic template data
        personalization: Dict[str, Any] = {
            "to": [{"email": to_email}],
            "dynamic_template_data": template_data
        }
        
        if to_name:
            personalization["to"][0]["name"] = to_name
        
        if subject:
            personalization["subject"] = subject
        
        # Build payload
        payload: Dict[str, Any] = {
            "personalizations": [personalization],
            "from": {
                "email": from_email or self.from_email,
                "name": from_name or self.from_name
            },
            "template_id": template_id,
            "tracking_settings": {
                "click_tracking": {"enable": True},
                "open_tracking": {"enable": True}
            }
        }
        
        if categories:
            payload["categories"] = categories[:10]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.SENDGRID_API_URL}/mail/send",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code in [200, 202]:
                    message_id = response.headers.get("X-Message-Id")
                    logger.info(f"Template email sent to {to_email} [Template: {template_id}]")
                    return EmailResult(
                        success=True,
                        message_id=message_id,
                        provider="sendgrid"
                    )
                
                error_body = response.text
                try:
                    error_data = response.json()
                    errors = error_data.get("errors", [])
                    error_message = errors[0].get("message") if errors else error_body
                except Exception:
                    error_message = error_body
                
                logger.error(f"SendGrid template error: {error_message}")
                return EmailResult(
                    success=False,
                    provider="sendgrid",
                    error=error_message,
                    error_code=str(response.status_code)
                )
                
        except Exception as e:
            logger.error(f"SendGrid template exception: {e}")
            return EmailResult(
                success=False,
                provider="sendgrid",
                error=str(e),
                error_code="EXCEPTION"
            )
    
    async def send_batch(
        self,
        recipients: List[Dict[str, Any]],
        subject: str,
        html_body: Optional[str] = None,
        text_body: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        categories: Optional[List[str]] = None
    ) -> List[EmailResult]:
        """
        Send same email to multiple recipients efficiently.
        
        Args:
            recipients: List of {"email": "...", "name": "..."} dicts
            subject: Email subject
            html_body: HTML content
            text_body: Plain text content
            from_email: Sender email
            from_name: Sender name
            categories: Tags for analytics
            
        Returns:
            List of EmailResult for each recipient
        """
        results = []
        
        # SendGrid supports up to 1000 recipients per personalization
        # But for tracking, we send individually
        for recipient in recipients:
            result = await self.send_email(
                to_email=recipient.get("email"),
                to_name=recipient.get("name"),
                subject=subject,
                html_body=html_body,
                text_body=text_body,
                from_email=from_email,
                from_name=from_name,
                categories=categories,
                use_smtp_fallback=False  # Don't fallback for batch
            )
            results.append(result)
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.05)
        
        return results
    
    async def _send_via_smtp(
        self,
        to_email: str,
        subject: str,
        html_body: Optional[str] = None,
        text_body: Optional[str] = None,
        to_name: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        reply_to: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> EmailResult:
        """Send email via SMTP as fallback"""
        try:
            # Build email message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{from_name or self.from_name} <{from_email or self.from_email}>"
            msg["To"] = f"{to_name} <{to_email}>" if to_name else to_email
            
            if reply_to:
                msg["Reply-To"] = reply_to
            
            if cc:
                msg["Cc"] = ", ".join(cc)
            
            # Add content
            if text_body:
                msg.attach(MIMEText(text_body, "plain", "utf-8"))
            if html_body:
                msg.attach(MIMEText(html_body, "html", "utf-8"))
            
            # Add attachments
            if attachments:
                for att in attachments:
                    part = MIMEBase("application", "octet-stream")
                    content = att.get("content", "")
                    if isinstance(content, str):
                        content = base64.b64decode(content)
                    part.set_payload(content)
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f'attachment; filename="{att.get("filename", "attachment")}"'
                    )
                    msg.attach(part)
            
            # Send via SMTP in thread pool
            def send_smtp():
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    if self.smtp_tls:
                        server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                    
                    all_recipients = [to_email]
                    if cc:
                        all_recipients.extend(cc)
                    if bcc:
                        all_recipients.extend(bcc)
                    
                    server.sendmail(
                        from_email or self.from_email,
                        all_recipients,
                        msg.as_string()
                    )
            
            await asyncio.get_event_loop().run_in_executor(None, send_smtp)
            
            message_id = f"smtp_{int(datetime.utcnow().timestamp())}"
            logger.info(f"Email sent via SMTP to {to_email}")
            
            return EmailResult(
                success=True,
                message_id=message_id,
                provider="smtp"
            )
            
        except Exception as e:
            logger.error(f"SMTP error: {e}")
            return EmailResult(
                success=False,
                provider="smtp",
                error=str(e),
                error_code="SMTP_ERROR"
            )
    
    # ================================================================
    # CONVENIENCE METHODS - Pre-built email templates
    # ================================================================
    
    # Queska Brand Colors - Light & Modern
    BRAND_ORANGE = "#F97316"
    BRAND_PRIMARY = "#1E3A5F"  # Deep blue - professional but not too dark
    BRAND_CYAN = "#5DD3D3"
    BRAND_LIGHT_BG = "#F8FAFC"  # Light background
    BRAND_ACCENT = "#3B82F6"  # Bright blue accent
    
    # Queska Logo URL
    QUESKA_LOGO_URL = "https://www.queska.com/assets/queska-logo-Cuza8pPL.png"
    
    def _get_email_header(self, background_color: str = None, title: str = "", show_logo: bool = True) -> str:
        """Generate consistent email header with Queska branding"""
        bg_color = background_color or "#FFFFFF"
        
        return f'''
        <tr>
            <td style="background-color: {bg_color}; padding: 32px 40px; text-align: center;">
                <!-- Queska Logo -->
                <table cellpadding="0" cellspacing="0" style="margin: 0 auto 16px auto;">
                    <tr>
                        <td>
                            <img src="{self.QUESKA_LOGO_URL}" alt="Queska" width="160" height="45" style="display: block;"/>
                        </td>
                    </tr>
                </table>
                {f'<h1 style="margin: 0; color: {self.BRAND_PRIMARY}; font-size: 24px; font-weight: 600; font-family: DM Sans, -apple-system, BlinkMacSystemFont, sans-serif;">{title}</h1>' if title else ''}
            </td>
        </tr>
        '''
    
    def _get_email_footer(self) -> str:
        """Generate consistent email footer with Queska branding"""
        return f'''
        <tr>
            <td style="background-color: #FFFFFF; padding: 30px 40px; text-align: center; border-top: 1px solid #E5E7EB;">
                <!-- Logo in footer -->
                <table cellpadding="0" cellspacing="0" style="margin: 0 auto 20px auto;">
                    <tr>
                        <td>
                            <img src="{self.QUESKA_LOGO_URL}" alt="Queska" width="120" height="34" style="display: block;"/>
                        </td>
                    </tr>
                </table>
                <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                        <td align="center" style="padding-bottom: 16px;">
                            <!-- Social Links -->
                            <a href="https://twitter.com/queska" style="display: inline-block; margin: 0 10px; text-decoration: none;">
                                <img src="https://cdn-icons-png.flaticon.com/24/733/733579.png" alt="Twitter" width="20" height="20"/>
                            </a>
                            <a href="https://instagram.com/queska" style="display: inline-block; margin: 0 10px; text-decoration: none;">
                                <img src="https://cdn-icons-png.flaticon.com/24/2111/2111463.png" alt="Instagram" width="20" height="20"/>
                            </a>
                            <a href="https://facebook.com/queska" style="display: inline-block; margin: 0 10px; text-decoration: none;">
                                <img src="https://cdn-icons-png.flaticon.com/24/733/733547.png" alt="Facebook" width="20" height="20"/>
                            </a>
                        </td>
                    </tr>
                    <tr>
                        <td align="center" style="padding-bottom: 12px;">
                            <a href="https://queska.com" style="color: {self.BRAND_ORANGE}; font-size: 14px; text-decoration: none; font-weight: 600;">www.queska.com</a>
                        </td>
                    </tr>
                    <tr>
                        <td align="center">
                            <p style="margin: 0 0 8px; color: #6B7280; font-size: 12px;">
                                Questions? Contact us at <a href="mailto:support@queska.com" style="color: {self.BRAND_ORANGE}; text-decoration: none;">support@queska.com</a>
                            </p>
                            <p style="margin: 0; color: #9CA3AF; font-size: 11px;">
                                © {datetime.utcnow().year} Queska Technologies. All rights reserved.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
        '''

    async def send_verification_email(
        self,
        to_email: str,
        to_name: str,
        verification_url: str,
        token: str
    ) -> EmailResult:
        """Send account verification email"""
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verify Your Email - Queska</title>
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
</head>
<body style="margin: 0; padding: 0; background-color: #F3F4F6; font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #F3F4F6; padding: 40px 20px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);">
                    <!-- Header with Logo -->
                    <tr>
                        <td style="background-color: #ffffff; padding: 40px 40px 20px; text-align: center;">
                            <img src="{self.QUESKA_LOGO_URL}" alt="Queska" width="160" height="45" style="display: block; margin: 0 auto;"/>
                        </td>
                    </tr>
                    
                    <!-- Title Section -->
                    <tr>
                        <td style="padding: 0 40px 30px; text-align: center;">
                            <h1 style="margin: 0; color: {self.BRAND_PRIMARY}; font-size: 26px; font-weight: 700;">Verify Your Email Address</h1>
                            <p style="margin: 12px 0 0; color: #6B7280; font-size: 15px;">Just one more step to get started!</p>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 0 40px 40px;">
                            <div style="background-color: #F9FAFB; border-radius: 12px; padding: 30px;">
                                <h2 style="margin: 0 0 16px; color: #1F2937; font-size: 18px; font-weight: 600;">Hi {to_name}! 👋</h2>
                                <p style="margin: 0 0 16px; color: #4B5563; font-size: 15px; line-height: 1.7;">
                                    Thanks for signing up for <strong style="color: {self.BRAND_ORANGE};">Queska</strong> — your all-in-one travel experience platform. We're excited to help you create unforgettable journeys!
                                </p>
                                <p style="margin: 0 0 24px; color: #4B5563; font-size: 15px; line-height: 1.7;">
                                    To get started, please verify your email address by clicking the button below:
                                </p>
                                
                                <!-- CTA Button -->
                                <table width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td align="center">
                                            <a href="{verification_url}" style="display: inline-block; background-color: {self.BRAND_ORANGE}; color: #ffffff; text-decoration: none; padding: 16px 48px; border-radius: 10px; font-size: 16px; font-weight: 600;">
                                                Verify Email Address
                                            </a>
                                        </td>
                                    </tr>
                                </table>
                            </div>
                            
                            <p style="margin: 24px 0 12px; color: #9CA3AF; font-size: 13px; text-align: center;">
                                Or copy and paste this link into your browser:
                            </p>
                            <p style="margin: 0 0 24px; word-break: break-all; background-color: #F9FAFB; padding: 12px 16px; border-radius: 8px; text-align: center;">
                                <a href="{verification_url}" style="color: {self.BRAND_ORANGE}; font-size: 12px; text-decoration: none;">{verification_url}</a>
                            </p>
                            
                            <!-- Notice Box -->
                            <div style="padding: 16px 20px; background-color: #FEF3C7; border-radius: 10px; text-align: center;">
                                <p style="margin: 0; color: #92400E; font-size: 14px;">
                                    ⏰ This verification link expires in <strong>48 hours</strong>
                                </p>
                            </div>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    {self._get_email_footer()}
                </table>
                
                <!-- Unsubscribe text -->
                <p style="margin: 24px 0 0; color: #9CA3AF; font-size: 11px; text-align: center;">
                    If you didn't create a Queska account, you can safely ignore this email.
                </p>
            </td>
        </tr>
    </table>
</body>
</html>
"""
        
        text_body = f"""
QUESKA - Verify Your Email

Hi {to_name}!

Thanks for signing up for Queska — your all-in-one travel experience platform.

To get started, please verify your email address by clicking the link below:

{verification_url}

This link expires in 48 hours.

If you didn't create a Queska account, you can safely ignore this email.

---
© {datetime.utcnow().year} Queska Technologies. All rights reserved.
queska.com | support@queska.com
"""
        
        return await self.send_email(
            to_email=to_email,
            to_name=to_name,
            subject="Verify Your Queska Account ✉️",
            html_body=html_body,
            text_body=text_body,
            categories=["verification", "transactional"]
        )
    
    async def send_password_reset_email(
        self,
        to_email: str,
        to_name: str,
        reset_url: str
    ) -> EmailResult:
        """Send password reset email"""
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reset Your Password - Queska</title>
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
</head>
<body style="margin: 0; padding: 0; background-color: #f0f4f8; font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f0f4f8; padding: 40px 20px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);">
                    <!-- Header with Logo -->
                    <tr>
                        <td style="background-color: #ffffff; padding: 40px 40px 20px; text-align: center;">
                            <img src="{self.QUESKA_LOGO_URL}" alt="Queska" width="160" height="45" style="display: block; margin: 0 auto;"/>
                        </td>
                    </tr>
                    
                    <!-- Title Section -->
                    <tr>
                        <td style="padding: 0 40px 30px; text-align: center;">
                            <h1 style="margin: 0; color: {self.BRAND_PRIMARY}; font-size: 26px; font-weight: 700;">🔒 Password Reset Request</h1>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 0 40px 40px;">
                            <div style="background-color: #F9FAFB; border-radius: 12px; padding: 30px;">
                                <h2 style="margin: 0 0 16px; color: #1F2937; font-size: 18px; font-weight: 600;">Hi {to_name},</h2>
                                <p style="margin: 0 0 16px; color: #4B5563; font-size: 15px; line-height: 1.7;">
                                    We received a request to reset the password for your <strong style="color: {self.BRAND_ORANGE};">Queska</strong> account.
                                </p>
                                <p style="margin: 0 0 24px; color: #4B5563; font-size: 15px; line-height: 1.7;">
                                    Click the button below to create a new password:
                                </p>
                                
                                <!-- CTA Button -->
                                <table width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td align="center">
                                            <a href="{reset_url}" style="display: inline-block; background-color: {self.BRAND_ORANGE}; color: #ffffff; text-decoration: none; padding: 16px 48px; border-radius: 10px; font-size: 16px; font-weight: 600;">
                                                Reset Password
                                            </a>
                                        </td>
                                    </tr>
                                </table>
                            </div>
                            
                            <p style="margin: 24px 0 12px; color: #9CA3AF; font-size: 13px; text-align: center;">
                                Or copy and paste this link into your browser:
                            </p>
                            <p style="margin: 0 0 24px; word-break: break-all; background-color: #F9FAFB; padding: 12px 16px; border-radius: 8px; text-align: center;">
                                <a href="{reset_url}" style="color: {self.BRAND_ORANGE}; font-size: 12px; text-decoration: none;">{reset_url}</a>
                            </p>
                            
                            <!-- Security Notice -->
                            <div style="padding: 16px 20px; background-color: #FEE2E2; border-radius: 10px; text-align: center;">
                                <p style="margin: 0; color: #991B1B; font-size: 14px;">
                                    ⚠️ This link expires in <strong>24 hours</strong>. If you didn't request this, ignore this email.
                                </p>
                            </div>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    {self._get_email_footer()}
                </table>
                
                <!-- Security tip -->
                <p style="margin: 24px 0 0; color: #9CA3AF; font-size: 11px; text-align: center;">
                    Never share your password or this reset link with anyone.
                </p>
            </td>
        </tr>
    </table>
</body>
</html>
"""
        
        text_body = f"""
QUESKA - Password Reset Request

Hi {to_name},

We received a request to reset your password for your Queska account.

Click here to reset your password:
{reset_url}

This link expires in 24 hours.

SECURITY NOTICE: If you didn't request this reset, please ignore this email or contact support@queska.com immediately.

---
© {datetime.utcnow().year} Queska Technologies. All rights reserved.
queska.com | support@queska.com
"""
        
        return await self.send_email(
            to_email=to_email,
            to_name=to_name,
            subject="Reset Your Queska Password 🔐",
            html_body=html_body,
            text_body=text_body,
            categories=["password-reset", "security", "transactional"]
        )
    
    async def send_booking_confirmation(
        self,
        to_email: str,
        to_name: str,
        booking_data: Dict[str, Any]
    ) -> EmailResult:
        """Send booking confirmation email"""
        booking_id = booking_data.get("booking_id", "")
        experience_name = booking_data.get("experience_name", "Your Experience")
        date = booking_data.get("date", "")
        time = booking_data.get("time", "")
        location = booking_data.get("location", "")
        total = booking_data.get("total_amount", 0)
        currency = booking_data.get("currency", "NGN")
        guests = booking_data.get("guests", 1)
        
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Booking Confirmed - Queska</title>
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
</head>
<body style="margin: 0; padding: 0; background-color: #f0f4f8; font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f0f4f8; padding: 40px 20px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 24px rgba(15, 76, 92, 0.12);">
                    <!-- Header -->
                    <tr>
                        <td style="background-color: {self.BRAND_TEAL}; padding: 40px 40px 32px; text-align: center;">
                            <table cellpadding="0" cellspacing="0" style="margin: 0 auto;">
                                <tr>
                                    <td style="padding-right: 12px;">
                                        <div style="width: 44px; height: 44px; background-color: {self.BRAND_ORANGE}; border-radius: 12px; display: inline-block;">
                                            <svg width="44" height="44" viewBox="0 0 44 44" fill="none" xmlns="http://www.w3.org/2000/svg">
                                                <path d="M22 8C14.268 8 8 14.268 8 22s6.268 14 14 14c3.866 0 7.366-1.566 9.899-4.101l-2.828-2.828C27.034 31.107 24.634 32 22 32c-5.514 0-10-4.486-10-10s4.486-10 10-10 10 4.486 10 10c0 1.326-.259 2.591-.728 3.747l3.464 3.464C35.831 27.037 36 24.572 36 22c0-7.732-6.268-14-14-14z" fill="#FFFFFF"/>
                                                <path d="M29 22l5.5-5.5 2.5 2.5-8 8-4-4 2.5-2.5 1.5 1.5z" fill="#FFFFFF"/>
                                            </svg>
                                        </div>
                                    </td>
                                    <td>
                                        <span style="color: #ffffff; font-size: 28px; font-weight: 700; letter-spacing: -0.5px;">Queska</span>
                                    </td>
                                </tr>
                            </table>
                            <h1 style="margin: 24px 0 0; color: #ffffff; font-size: 22px; font-weight: 600;">✅ Booking Confirmed!</h1>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px;">
                            <h2 style="margin: 0 0 12px; color: {self.BRAND_TEAL}; font-size: 20px; font-weight: 600;">Great news, {to_name}! 🎉</h2>
                            <p style="margin: 0 0 28px; color: #4a5568; font-size: 15px; line-height: 1.7;">
                                Your booking has been confirmed. Here are your details:
                            </p>
                            
                            <!-- Booking Card -->
                            <div style="background-color: #f7fafc; border-radius: 12px; padding: 24px; margin-bottom: 24px; border: 1px solid #e2e8f0;">
                                <h3 style="margin: 0 0 20px; color: {self.BRAND_TEAL}; font-size: 18px; font-weight: 600;">{experience_name}</h3>
                                <table width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td style="padding: 10px 0; color: #718096; font-size: 14px;">🔖 Booking ID</td>
                                        <td style="padding: 10px 0; color: {self.BRAND_TEAL}; font-size: 14px; font-weight: 600; text-align: right; font-family: monospace;">{booking_id}</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 10px 0; color: #718096; font-size: 14px;">📅 Date & Time</td>
                                        <td style="padding: 10px 0; color: #2d3748; font-size: 14px; text-align: right;">{date} {time}</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 10px 0; color: #718096; font-size: 14px;">📍 Location</td>
                                        <td style="padding: 10px 0; color: #2d3748; font-size: 14px; text-align: right;">{location}</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 10px 0; color: #718096; font-size: 14px;">👥 Guests</td>
                                        <td style="padding: 10px 0; color: #2d3748; font-size: 14px; text-align: right;">{guests}</td>
                                    </tr>
                                    <tr>
                                        <td colspan="2" style="padding-top: 16px; border-top: 2px solid #e2e8f0;"></td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 12px 0; color: #2d3748; font-size: 16px; font-weight: 600;">Total Paid</td>
                                        <td style="padding: 12px 0; color: {self.BRAND_ORANGE}; font-size: 22px; font-weight: 700; text-align: right;">{currency} {total:,.2f}</td>
                                    </tr>
                                </table>
                            </div>
                            
                            <!-- CTA Button -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 24px;">
                                <tr>
                                    <td align="center">
                                        <a href="https://queska.com/dashboard/bookings" style="display: inline-block; background-color: {self.BRAND_ORANGE}; color: #ffffff; text-decoration: none; padding: 14px 36px; border-radius: 10px; font-size: 15px; font-weight: 600; box-shadow: 0 4px 14px rgba(249, 115, 22, 0.4);">
                                            View Booking Details
                                        </a>
                                    </td>
                                </tr>
                            </table>
                            
                            <p style="margin: 0; color: #718096; font-size: 14px; text-align: center;">
                                Your experience card has been added to your dashboard. Have an amazing trip! 🌟
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    {self._get_email_footer()}
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""
        
        text_body = f"""
QUESKA - Booking Confirmed!

Hi {to_name}!

Your booking has been confirmed:

Experience: {experience_name}
Booking ID: {booking_id}
Date: {date} {time}
Location: {location}
Guests: {guests}
Total: {currency} {total:,.2f}

Have an amazing trip!

© {datetime.utcnow().year} Queska
"""
        
        return await self.send_email(
            to_email=to_email,
            to_name=to_name,
            subject=f"Booking Confirmed - {experience_name} ✅",
            html_body=html_body,
            text_body=text_body,
            categories=["booking", "confirmation", "transactional"]
        )
    
    async def send_payment_receipt(
        self,
        to_email: str,
        to_name: str,
        payment_data: Dict[str, Any]
    ) -> EmailResult:
        """Send payment receipt email"""
        amount = payment_data.get("amount", 0)
        currency = payment_data.get("currency", "NGN")
        reference = payment_data.get("reference", "")
        description = payment_data.get("description", "Payment")
        date = payment_data.get("date", datetime.utcnow().strftime("%B %d, %Y"))
        
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Payment Receipt - Queska</title>
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
</head>
<body style="margin: 0; padding: 0; background-color: #f0f4f8; font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f0f4f8; padding: 40px 20px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 24px rgba(15, 76, 92, 0.12);">
                    <!-- Header -->
                    <tr>
                        <td style="background-color: {self.BRAND_TEAL}; padding: 40px 40px 32px; text-align: center;">
                            <table cellpadding="0" cellspacing="0" style="margin: 0 auto;">
                                <tr>
                                    <td style="padding-right: 12px;">
                                        <div style="width: 44px; height: 44px; background-color: {self.BRAND_ORANGE}; border-radius: 12px; display: inline-block;">
                                            <svg width="44" height="44" viewBox="0 0 44 44" fill="none" xmlns="http://www.w3.org/2000/svg">
                                                <path d="M22 8C14.268 8 8 14.268 8 22s6.268 14 14 14c3.866 0 7.366-1.566 9.899-4.101l-2.828-2.828C27.034 31.107 24.634 32 22 32c-5.514 0-10-4.486-10-10s4.486-10 10-10 10 4.486 10 10c0 1.326-.259 2.591-.728 3.747l3.464 3.464C35.831 27.037 36 24.572 36 22c0-7.732-6.268-14-14-14z" fill="#FFFFFF"/>
                                                <path d="M29 22l5.5-5.5 2.5 2.5-8 8-4-4 2.5-2.5 1.5 1.5z" fill="#FFFFFF"/>
                                            </svg>
                                        </div>
                                    </td>
                                    <td>
                                        <span style="color: #ffffff; font-size: 28px; font-weight: 700; letter-spacing: -0.5px;">Queska</span>
                                    </td>
                                </tr>
                            </table>
                            <h1 style="margin: 24px 0 0; color: #ffffff; font-size: 22px; font-weight: 600;">💳 Payment Receipt</h1>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px;">
                            <p style="margin: 0 0 16px; color: #4a5568; font-size: 15px;">Hi {to_name},</p>
                            <p style="margin: 0 0 32px; color: #4a5568; font-size: 15px;">Your payment was successful. Here's your receipt:</p>
                            
                            <!-- Receipt Card -->
                            <div style="background-color: #f7fafc; border-radius: 12px; padding: 24px; margin-bottom: 24px; border: 1px solid #e2e8f0;">
                                <table width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td style="padding: 10px 0; color: #718096; font-size: 14px;">Reference</td>
                                        <td style="padding: 10px 0; color: {self.BRAND_TEAL}; text-align: right; font-family: monospace; font-weight: 600;">{reference}</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 10px 0; color: #718096; font-size: 14px;">Description</td>
                                        <td style="padding: 10px 0; color: #2d3748; text-align: right;">{description}</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 10px 0; color: #718096; font-size: 14px;">Date</td>
                                        <td style="padding: 10px 0; color: #2d3748; text-align: right;">{date}</td>
                                    </tr>
                                    <tr>
                                        <td colspan="2" style="padding-top: 16px; border-top: 2px solid #e2e8f0;"></td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 12px 0; color: #2d3748; font-size: 16px; font-weight: 600;">Amount Paid</td>
                                        <td style="padding: 12px 0; color: {self.BRAND_ORANGE}; font-size: 24px; font-weight: 700; text-align: right;">{currency} {amount:,.2f}</td>
                                    </tr>
                                </table>
                            </div>
                            
                            <p style="margin: 0; color: #718096; font-size: 14px; text-align: center;">Thank you for your payment! 🙏</p>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    {self._get_email_footer()}
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""
        
        return await self.send_email(
            to_email=to_email,
            to_name=to_name,
            subject=f"Payment Receipt - {currency} {amount:,.2f}",
            html_body=html_body,
            categories=["payment", "receipt", "transactional"]
        )
    
    async def send_welcome_email(
        self,
        to_email: str,
        to_name: str
    ) -> EmailResult:
        """Send welcome email after verification"""
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome to Queska!</title>
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
</head>
<body style="margin: 0; padding: 0; background-color: #F3F4F6; font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #F3F4F6; padding: 40px 20px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);">
                    <!-- Header with Logo -->
                    <tr>
                        <td style="background-color: #ffffff; padding: 40px 40px 20px; text-align: center;">
                            <img src="{self.QUESKA_LOGO_URL}" alt="Queska" width="180" height="50" style="display: block; margin: 0 auto;"/>
                        </td>
                    </tr>
                    
                    <!-- Welcome Banner -->
                    <tr>
                        <td style="padding: 0 40px 30px; text-align: center;">
                            <h1 style="margin: 0 0 8px; color: {self.BRAND_PRIMARY}; font-size: 32px; font-weight: 700;">Welcome Aboard! 🎉</h1>
                            <p style="margin: 0; color: #6B7280; font-size: 16px;">Your journey to amazing experiences starts here</p>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 0 40px 40px;">
                            <div style="background-color: #F9FAFB; border-radius: 12px; padding: 30px; margin-bottom: 24px;">
                                <h2 style="margin: 0 0 16px; color: #1F2937; font-size: 20px; font-weight: 600;">Hey {to_name}! 👋</h2>
                                <p style="margin: 0; color: #4B5563; font-size: 15px; line-height: 1.7;">
                                    Your account is now verified and ready to go! We're thrilled to have you join the <strong style="color: {self.BRAND_ORANGE};">Queska</strong> community of travelers and experience seekers.
                                </p>
                            </div>
                            
                            <h3 style="margin: 0 0 20px; color: {self.BRAND_PRIMARY}; font-size: 18px; font-weight: 600; text-align: center;">What can you do with Queska?</h3>
                            
                            <!-- Feature Grid -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 32px;">
                                <tr>
                                    <td width="50%" style="padding: 8px 8px 8px 0; vertical-align: top;">
                                        <div style="background-color: #FFF7ED; border-radius: 10px; padding: 16px; text-align: center;">
                                            <p style="margin: 0 0 8px; font-size: 28px;">🌍</p>
                                            <p style="margin: 0; color: #1F2937; font-size: 14px; font-weight: 600;">Create Experiences</p>
                                        </div>
                                    </td>
                                    <td width="50%" style="padding: 8px 0 8px 8px; vertical-align: top;">
                                        <div style="background-color: #ECFDF5; border-radius: 10px; padding: 16px; text-align: center;">
                                            <p style="margin: 0 0 8px; font-size: 28px;">🏨</p>
                                            <p style="margin: 0; color: #1F2937; font-size: 14px; font-weight: 600;">Book Hotels</p>
                                        </div>
                                    </td>
                                </tr>
                                <tr>
                                    <td width="50%" style="padding: 8px 8px 8px 0; vertical-align: top;">
                                        <div style="background-color: #EFF6FF; border-radius: 10px; padding: 16px; text-align: center;">
                                            <p style="margin: 0 0 8px; font-size: 28px;">✈️</p>
                                            <p style="margin: 0; color: #1F2937; font-size: 14px; font-weight: 600;">Search Flights</p>
                                        </div>
                                    </td>
                                    <td width="50%" style="padding: 8px 0 8px 8px; vertical-align: top;">
                                        <div style="background-color: #FDF4FF; border-radius: 10px; padding: 16px; text-align: center;">
                                            <p style="margin: 0 0 8px; font-size: 28px;">🎫</p>
                                            <p style="margin: 0; color: #1F2937; font-size: 14px; font-weight: 600;">Get Tickets</p>
                                        </div>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- CTA Button -->
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td align="center">
                                        <a href="https://queska.com/explore" style="display: inline-block; background-color: {self.BRAND_ORANGE}; color: #ffffff; text-decoration: none; padding: 18px 56px; border-radius: 10px; font-size: 16px; font-weight: 600;">
                                            Start Exploring 🚀
                                        </a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    {self._get_email_footer()}
                </table>
                
                <!-- Help text -->
                <p style="margin: 24px 0 0; color: #9CA3AF; font-size: 11px; text-align: center;">
                    Questions? Our support team is here to help at support@queska.com
                </p>
            </td>
        </tr>
    </table>
</body>
</html>
"""
        
        return await self.send_email(
            to_email=to_email,
            to_name=to_name,
            subject="Welcome to Queska - Let's Start Your Journey! 🌍",
            html_body=html_body,
            categories=["welcome", "onboarding"]
        )


# Global service instance
email_service = EmailService()
