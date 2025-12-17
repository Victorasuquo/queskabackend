"""
Queska Backend - Notification Endpoints
API endpoints for notification management
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import (
    get_current_active_user,
    get_current_active_vendor,
    get_current_active_agent,
    get_current_admin,
)
from app.core.constants import (
    NotificationCategory,
    NotificationChannel,
    NotificationStatus,
    UserType,
)
from app.models.notification import Notification, NotificationTemplate
from app.models.user import User
from app.models.vendor import Vendor
from app.models.agent import Agent
from app.schemas.notification import (
    NotificationCreate,
    NotificationFromTemplate,
    NotificationListResponse,
    NotificationPreferencesResponse,
    NotificationPreferencesUpdate,
    NotificationResponse,
    NotificationSendBatch,
    NotificationSendEmail,
    NotificationSendPush,
    NotificationSendResult,
    NotificationSendSMS,
    NotificationTemplateCreate,
    NotificationTemplateResponse,
    NotificationTemplateUpdate,
    BatchSendResult,
    DeviceTokenRegister,
    DeviceTokenResponse,
)
from app.services.notification_service import notification_service


router = APIRouter()


# === User Notification Endpoints ===

@router.get(
    "/me",
    response_model=Dict[str, Any],
    summary="Get my notifications",
    description="Get current user's in-app notifications"
)
async def get_my_notifications(
    unread_only: bool = Query(False, description="Only show unread notifications"),
    category: Optional[NotificationCategory] = Query(None, description="Filter by category"),
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    user: User = Depends(get_current_active_user)
):
    """Get notifications for current user"""
    notifications = await notification_service.get_user_notifications(
        user_id=str(user.id),
        user_type=UserType.USER,
        unread_only=unread_only,
        limit=limit,
        skip=skip
    )
    
    unread_count = await notification_service.get_unread_count(
        user_id=str(user.id),
        user_type=UserType.USER
    )
    
    return {
        "success": True,
        "notifications": [
            {
                "id": str(n.id),
                "category": n.category.value,
                "priority": n.priority.value,
                "status": n.status.value,
                "title": n.in_app_content.title if n.in_app_content else None,
                "message": n.in_app_content.message if n.in_app_content else None,
                "icon": n.in_app_content.icon if n.in_app_content else None,
                "action_url": n.in_app_content.action_url if n.in_app_content else None,
                "action_text": n.in_app_content.action_text if n.in_app_content else None,
                "image_url": n.in_app_content.image_url if n.in_app_content else None,
                "reference_type": n.reference_type,
                "reference_id": n.reference_id,
                "created_at": n.created_at.isoformat(),
                "read_at": n.read_at.isoformat() if n.read_at else None,
                "is_read": n.status == NotificationStatus.READ
            }
            for n in notifications
        ],
        "unread_count": unread_count,
        "total": len(notifications),
        "limit": limit,
        "skip": skip
    }


@router.get(
    "/me/unread-count",
    summary="Get unread notification count"
)
async def get_unread_count(
    user: User = Depends(get_current_active_user)
):
    """Get count of unread notifications"""
    count = await notification_service.get_unread_count(
        user_id=str(user.id),
        user_type=UserType.USER
    )
    
    return {
        "success": True,
        "unread_count": count
    }


@router.post(
    "/me/{notification_id}/read",
    summary="Mark notification as read"
)
async def mark_notification_read(
    notification_id: str,
    user: User = Depends(get_current_active_user)
):
    """Mark a specific notification as read"""
    success = await notification_service.mark_as_read(
        notification_id=notification_id,
        user_id=str(user.id)
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    return {
        "success": True,
        "message": "Notification marked as read"
    }


@router.post(
    "/me/read-all",
    summary="Mark all notifications as read"
)
async def mark_all_read(
    user: User = Depends(get_current_active_user)
):
    """Mark all notifications as read"""
    count = await notification_service.mark_all_as_read(
        user_id=str(user.id),
        user_type=UserType.USER
    )
    
    return {
        "success": True,
        "message": f"{count} notifications marked as read",
        "count": count
    }


@router.delete(
    "/me/{notification_id}",
    summary="Delete notification"
)
async def delete_notification(
    notification_id: str,
    user: User = Depends(get_current_active_user)
):
    """Delete a notification"""
    success = await notification_service.delete_notification(
        notification_id=notification_id,
        user_id=str(user.id)
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    return {
        "success": True,
        "message": "Notification deleted"
    }


# === Vendor Notification Endpoints ===

@router.get(
    "/vendor/me",
    response_model=Dict[str, Any],
    summary="Get vendor notifications"
)
async def get_vendor_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    vendor: Vendor = Depends(get_current_active_vendor)
):
    """Get notifications for current vendor"""
    notifications = await notification_service.get_user_notifications(
        user_id=str(vendor.id),
        user_type=UserType.VENDOR,
        unread_only=unread_only,
        limit=limit,
        skip=skip
    )
    
    unread_count = await notification_service.get_unread_count(
        user_id=str(vendor.id),
        user_type=UserType.VENDOR
    )
    
    return {
        "success": True,
        "notifications": [
            {
                "id": str(n.id),
                "category": n.category.value,
                "priority": n.priority.value,
                "status": n.status.value,
                "title": n.in_app_content.title if n.in_app_content else None,
                "message": n.in_app_content.message if n.in_app_content else None,
                "reference_type": n.reference_type,
                "reference_id": n.reference_id,
                "created_at": n.created_at.isoformat(),
                "is_read": n.status == NotificationStatus.READ
            }
            for n in notifications
        ],
        "unread_count": unread_count
    }


@router.post(
    "/vendor/me/read-all",
    summary="Mark all vendor notifications as read"
)
async def mark_vendor_all_read(
    vendor: Vendor = Depends(get_current_active_vendor)
):
    """Mark all vendor notifications as read"""
    count = await notification_service.mark_all_as_read(
        user_id=str(vendor.id),
        user_type=UserType.VENDOR
    )
    
    return {
        "success": True,
        "count": count
    }


# === Agent Notification Endpoints ===

@router.get(
    "/agent/me",
    response_model=Dict[str, Any],
    summary="Get agent notifications"
)
async def get_agent_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    agent: Agent = Depends(get_current_active_agent)
):
    """Get notifications for current agent"""
    notifications = await notification_service.get_user_notifications(
        user_id=str(agent.id),
        user_type=UserType.AGENT,
        unread_only=unread_only,
        limit=limit,
        skip=skip
    )
    
    unread_count = await notification_service.get_unread_count(
        user_id=str(agent.id),
        user_type=UserType.AGENT
    )
    
    return {
        "success": True,
        "notifications": [
            {
                "id": str(n.id),
                "category": n.category.value,
                "priority": n.priority.value,
                "status": n.status.value,
                "title": n.in_app_content.title if n.in_app_content else None,
                "message": n.in_app_content.message if n.in_app_content else None,
                "reference_type": n.reference_type,
                "reference_id": n.reference_id,
                "created_at": n.created_at.isoformat(),
                "is_read": n.status == NotificationStatus.READ
            }
            for n in notifications
        ],
        "unread_count": unread_count
    }


# === Admin Send Endpoints ===

@router.post(
    "/admin/send",
    response_model=Dict[str, Any],
    summary="Send notification (Admin)",
    description="Send notification to specific recipients"
)
async def admin_send_notification(
    data: NotificationCreate,
    admin: User = Depends(get_current_admin)
):
    """Send a notification - Admin only"""
    result = await notification_service.send(
        recipient=data.recipient.model_dump(),
        category=data.category,
        channels=data.channels,
        email_content=data.email_content.model_dump() if data.email_content else None,
        sms_content=data.sms_content.model_dump() if data.sms_content else None,
        push_content=data.push_content.model_dump() if data.push_content else None,
        in_app_content=data.in_app_content.model_dump() if data.in_app_content else None,
        priority=data.priority,
        scheduled_at=data.scheduled_at,
        reference_type=data.reference_type,
        reference_id=data.reference_id,
        check_preferences=data.check_preferences
    )
    
    return {
        "success": result.success,
        "notification_id": result.notification_id,
        "channels_attempted": result.channels_attempted,
        "channels_succeeded": result.channels_succeeded,
        "channels_failed": result.channels_failed,
        "error": result.error
    }


@router.post(
    "/admin/send/email",
    response_model=Dict[str, Any],
    summary="Send email (Admin)"
)
async def admin_send_email(
    data: NotificationSendEmail,
    admin: User = Depends(get_current_admin)
):
    """Send a quick email - Admin only"""
    from app.services.email_service import email_service
    
    if data.template_id:
        result = await email_service.send_template_email(
            to_email=data.to_email,
            template_id=data.template_id,
            template_data=data.template_data or {},
            to_name=data.to_name,
            subject=data.subject
        )
    else:
        result = await email_service.send_email(
            to_email=data.to_email,
            to_name=data.to_name,
            subject=data.subject,
            html_body=data.html_body,
            text_body=data.text_body,
            cc=data.cc,
            bcc=data.bcc
        )
    
    return {
        "success": result.success,
        "message_id": result.message_id,
        "provider": result.provider,
        "error": result.error
    }


@router.post(
    "/admin/send/sms",
    response_model=Dict[str, Any],
    summary="Send SMS (Admin)"
)
async def admin_send_sms(
    data: NotificationSendSMS,
    admin: User = Depends(get_current_admin)
):
    """Send a quick SMS - Admin only"""
    from app.services.sms_service import sms_service
    
    result = await sms_service.send_sms(
        to_phone=data.to_phone,
        message=data.message,
        sender_id=data.sender_id
    )
    
    return {
        "success": result.success,
        "message_id": result.message_id,
        "provider": result.provider,
        "segments": result.segments,
        "error": result.error
    }


@router.post(
    "/admin/send/push",
    response_model=Dict[str, Any],
    summary="Send push notification (Admin)"
)
async def admin_send_push(
    data: NotificationSendPush,
    admin: User = Depends(get_current_admin)
):
    """Send push notification - Admin only"""
    from app.services.push_service import push_service
    
    if data.topic:
        result = await push_service.send_to_topic(
            topic=data.topic,
            title=data.title,
            body=data.body,
            data=data.data,
            image_url=data.image_url
        )
    elif data.device_tokens:
        result = await push_service.send_to_devices(
            device_tokens=data.device_tokens,
            title=data.title,
            body=data.body,
            data=data.data
        )
    elif data.device_token:
        result = await push_service.send_to_device(
            device_token=data.device_token,
            title=data.title,
            body=data.body,
            data=data.data,
            image_url=data.image_url
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide device_token, device_tokens, or topic"
        )
    
    return {
        "success": result.success,
        "message_id": result.message_id,
        "provider": result.provider,
        "success_count": result.success_count,
        "failure_count": result.failure_count,
        "error": result.error
    }


@router.post(
    "/admin/send/batch",
    response_model=Dict[str, Any],
    summary="Send batch notifications (Admin)"
)
async def admin_send_batch(
    data: NotificationSendBatch,
    admin: User = Depends(get_current_admin)
):
    """Send notification to multiple recipients - Admin only"""
    results = await notification_service.send_batch(
        recipients=[r.model_dump() for r in data.recipients],
        category=data.category,
        channels=data.channels,
        email_content=data.email_content.model_dump() if data.email_content else None,
        sms_content=data.sms_content.model_dump() if data.sms_content else None,
        push_content=data.push_content.model_dump() if data.push_content else None,
        in_app_content=data.in_app_content.model_dump() if data.in_app_content else None
    )
    
    successful = sum(1 for r in results if r.success)
    
    return {
        "success": successful > 0,
        "total": len(results),
        "successful": successful,
        "failed": len(results) - successful,
        "results": [r.to_dict() for r in results]
    }


@router.post(
    "/admin/send/template",
    response_model=Dict[str, Any],
    summary="Send from template (Admin)"
)
async def admin_send_from_template(
    data: NotificationFromTemplate,
    admin: User = Depends(get_current_admin)
):
    """Send notification using a template - Admin only"""
    result = await notification_service.send_from_template(
        template_name=data.template_name,
        recipient=data.recipient.model_dump(),
        template_data=data.template_data,
        channels=data.channels
    )
    
    return {
        "success": result.success,
        "notification_id": result.notification_id,
        "channels_succeeded": result.channels_succeeded,
        "channels_failed": result.channels_failed,
        "error": result.error
    }


# === Template Management (Admin) ===

@router.get(
    "/admin/templates",
    response_model=Dict[str, Any],
    summary="List notification templates (Admin)"
)
async def list_templates(
    category: Optional[NotificationCategory] = None,
    active_only: bool = True,
    admin: User = Depends(get_current_admin)
):
    """List all notification templates - Admin only"""
    query = {}
    if category:
        query["category"] = category
    if active_only:
        query["is_active"] = True
    
    templates = await NotificationTemplate.find(query).to_list()
    
    return {
        "success": True,
        "templates": [
            {
                "id": str(t.id),
                "name": t.name,
                "category": t.category.value,
                "description": t.description,
                "variables": t.variables,
                "is_active": t.is_active,
                "created_at": t.created_at.isoformat()
            }
            for t in templates
        ]
    }


@router.post(
    "/admin/templates",
    response_model=Dict[str, Any],
    summary="Create notification template (Admin)"
)
async def create_template(
    data: NotificationTemplateCreate,
    admin: User = Depends(get_current_admin)
):
    """Create a new notification template - Admin only"""
    # Check if name exists
    existing = await NotificationTemplate.find_one({"name": data.name})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Template with this name already exists"
        )
    
    template = NotificationTemplate(**data.model_dump())
    await template.insert()
    
    return {
        "success": True,
        "message": "Template created",
        "template_id": str(template.id)
    }


@router.put(
    "/admin/templates/{template_id}",
    response_model=Dict[str, Any],
    summary="Update notification template (Admin)"
)
async def update_template(
    template_id: str,
    data: NotificationTemplateUpdate,
    admin: User = Depends(get_current_admin)
):
    """Update a notification template - Admin only"""
    template = await NotificationTemplate.get(PydanticObjectId(template_id))
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(template, key, value)
    
    template.updated_at = datetime.utcnow()
    await template.save()
    
    return {
        "success": True,
        "message": "Template updated"
    }


@router.delete(
    "/admin/templates/{template_id}",
    summary="Delete notification template (Admin)"
)
async def delete_template(
    template_id: str,
    admin: User = Depends(get_current_admin)
):
    """Delete a notification template - Admin only"""
    template = await NotificationTemplate.get(PydanticObjectId(template_id))
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    await template.delete()
    
    return {
        "success": True,
        "message": "Template deleted"
    }


# === Service Status ===

@router.get(
    "/status",
    summary="Get notification service status"
)
async def get_service_status():
    """Get status of notification services"""
    from app.services.email_service import email_service
    from app.services.sms_service import sms_service
    from app.services.push_service import push_service
    from app.core.config import settings
    
    return {
        "success": True,
        "services": {
            "email": {
                "provider": settings.EMAIL_PROVIDER,
                "mailchimp_configured": bool(settings.MAILCHIMP_API_KEY),
                "sendgrid_configured": bool(settings.SENDGRID_API_KEY),
                "smtp_configured": bool(settings.SMTP_USER and settings.SMTP_PASSWORD)
            },
            "sms": {
                "provider": settings.SMS_PROVIDER,
                "twilio_configured": bool(
                    settings.TWILIO_ACCOUNT_SID and 
                    settings.TWILIO_AUTH_TOKEN and 
                    settings.TWILIO_PHONE_NUMBER
                ),
                "termii_configured": bool(settings.TERMII_API_KEY)
            },
            "push": {
                "firebase_configured": push_service.is_configured()
            }
        }
    }

