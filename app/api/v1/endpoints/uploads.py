"""
Queska Backend - Upload Endpoints
File upload endpoints for vendors, agents, and users
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query

from app.api.deps import (
    get_current_active_vendor,
    get_current_active_agent,
    get_current_active_user
)
from app.models.vendor import Vendor, VendorMedia, VendorVerification
from app.models.agent import Agent, AgentMedia, AgentVerification
from app.models.user import User
from app.services.media_service import media_service
from app.core.constants import VerificationStatus


router = APIRouter()


# === Vendor Media Upload Endpoints ===

@router.post(
    "/vendor/logo",
    summary="Upload vendor logo",
    description="Upload a logo image for the vendor profile. Supported formats: JPEG, PNG, WebP, GIF. Max size: 10MB"
)
async def upload_vendor_logo(
    file: UploadFile = File(..., description="Logo image file"),
    vendor: Vendor = Depends(get_current_active_vendor)
):
    """Upload vendor logo image - auto-updates vendor profile"""
    result = await media_service.upload_image(
        file=file,
        folder="vendors/logos",
        vendor_id=str(vendor.id),
        transformation={"width": 500, "height": 500, "crop": "fill"}
    )
    
    # Initialize media if not exists
    if not vendor.media:
        vendor.media = VendorMedia()
    
    # Update vendor profile with new logo
    vendor.media.logo = result["url"]
    vendor.updated_at = datetime.utcnow()
    await vendor.save()
    
    return {
        "success": True,
        "message": "Logo uploaded successfully",
        "data": {
            "url": result["url"],
            "public_id": result["public_id"],
            "thumbnail_url": result["thumbnail_url"],
            "width": result.get("width"),
            "height": result.get("height")
        }
    }


@router.post(
    "/vendor/cover",
    summary="Upload vendor cover image",
    description="Upload a cover/banner image for the vendor profile. Recommended size: 1920x600. Max size: 10MB"
)
async def upload_vendor_cover(
    file: UploadFile = File(..., description="Cover image file"),
    vendor: Vendor = Depends(get_current_active_vendor)
):
    """Upload vendor cover/banner image - auto-updates vendor profile"""
    result = await media_service.upload_image(
        file=file,
        folder="vendors/covers",
        vendor_id=str(vendor.id),
        transformation={"width": 1920, "height": 600, "crop": "fill"}
    )
    
    # Initialize media if not exists
    if not vendor.media:
        vendor.media = VendorMedia()
    
    # Update vendor profile
    vendor.media.cover_image = result["url"]
    vendor.updated_at = datetime.utcnow()
    await vendor.save()
    
    return {
        "success": True,
        "message": "Cover image uploaded successfully",
        "data": {
            "url": result["url"],
            "public_id": result["public_id"],
            "thumbnail_url": result["thumbnail_url"],
            "width": result.get("width"),
            "height": result.get("height")
        }
    }


@router.post(
    "/vendor/gallery",
    summary="Upload gallery images",
    description="Upload one or more images to the vendor gallery. Max 10 images per request. Max size: 10MB each"
)
async def upload_vendor_gallery(
    files: List[UploadFile] = File(..., description="Gallery images (max 10 per request)"),
    title: Optional[str] = Query(None, description="Optional title for the images"),
    vendor: Vendor = Depends(get_current_active_vendor)
):
    """Upload multiple gallery images - auto-updates vendor profile"""
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 images per upload")
    
    results = await media_service.upload_multiple_images(
        files=files,
        folder="vendors/gallery",
        vendor_id=str(vendor.id)
    )
    
    # Initialize media if not exists
    if not vendor.media:
        vendor.media = VendorMedia()
    
    # Add to gallery
    for i, result in enumerate(results):
        vendor.media.gallery.append({
            "url": result["url"],
            "public_id": result["public_id"],
            "thumbnail_url": result["thumbnail_url"],
            "title": title or f"Image {len(vendor.media.gallery) + 1}",
            "type": "image",
            "uploaded_at": datetime.utcnow().isoformat()
        })
    
    vendor.updated_at = datetime.utcnow()
    await vendor.save()
    
    return {
        "success": True,
        "message": f"{len(results)} image(s) uploaded successfully",
        "data": results,
        "gallery_count": len(vendor.media.gallery)
    }


@router.post(
    "/vendor/video",
    summary="Upload vendor video",
    description="Upload a promotional or tour video. Supported formats: MP4, WebM, MOV. Max size: 100MB"
)
async def upload_vendor_video(
    file: UploadFile = File(..., description="Video file"),
    title: Optional[str] = Query(None, description="Video title"),
    vendor: Vendor = Depends(get_current_active_vendor)
):
    """Upload vendor video - auto-updates vendor profile"""
    result = await media_service.upload_video(
        file=file,
        folder="vendors/videos",
        vendor_id=str(vendor.id)
    )
    
    # Initialize media if not exists
    if not vendor.media:
        vendor.media = VendorMedia()
    
    # Add to videos
    vendor.media.videos.append({
        "url": result["url"],
        "public_id": result["public_id"],
        "thumbnail_url": result["thumbnail_url"],
        "title": title or f"Video {len(vendor.media.videos) + 1}",
        "duration": result.get("duration"),
        "type": "video",
        "uploaded_at": datetime.utcnow().isoformat()
    })
    
    vendor.updated_at = datetime.utcnow()
    await vendor.save()
    
    return {
        "success": True,
        "message": "Video uploaded successfully",
        "data": result,
        "video_count": len(vendor.media.videos)
    }


@router.delete(
    "/vendor/gallery/{index}",
    summary="Delete gallery image",
    description="Delete a specific image from the gallery by index"
)
async def delete_gallery_image(
    index: int,
    vendor: Vendor = Depends(get_current_active_vendor)
):
    """Delete a gallery image by index"""
    if not vendor.media or not vendor.media.gallery:
        raise HTTPException(status_code=404, detail="No gallery images found")
    
    if index < 0 or index >= len(vendor.media.gallery):
        raise HTTPException(status_code=404, detail="Image index out of range")
    
    # Get the image to delete
    image = vendor.media.gallery[index]
    
    # Delete from Cloudinary
    if image.get("public_id"):
        await media_service.delete_media(image["public_id"], "image")
    
    # Remove from gallery
    vendor.media.gallery.pop(index)
    vendor.updated_at = datetime.utcnow()
    await vendor.save()
    
    return {
        "success": True,
        "message": "Image deleted successfully",
        "gallery_count": len(vendor.media.gallery)
    }


@router.delete(
    "/vendor/video/{index}",
    summary="Delete vendor video",
    description="Delete a specific video by index"
)
async def delete_vendor_video(
    index: int,
    vendor: Vendor = Depends(get_current_active_vendor)
):
    """Delete a video by index"""
    if not vendor.media or not vendor.media.videos:
        raise HTTPException(status_code=404, detail="No videos found")
    
    if index < 0 or index >= len(vendor.media.videos):
        raise HTTPException(status_code=404, detail="Video index out of range")
    
    # Get the video to delete
    video = vendor.media.videos[index]
    
    # Delete from Cloudinary
    if video.get("public_id"):
        await media_service.delete_media(video["public_id"], "video")
    
    # Remove from videos
    vendor.media.videos.pop(index)
    vendor.updated_at = datetime.utcnow()
    await vendor.save()
    
    return {
        "success": True,
        "message": "Video deleted successfully",
        "video_count": len(vendor.media.videos)
    }


# === Vendor Verification Document Uploads ===

@router.post(
    "/vendor/verification/business-registration",
    summary="Upload business registration document",
    description="Upload CAC certificate or business registration document. Supported: PDF, JPEG, PNG. Max: 10MB"
)
async def upload_business_registration(
    file: UploadFile = File(..., description="Business registration document"),
    vendor: Vendor = Depends(get_current_active_vendor)
):
    """Upload business registration document for verification"""
    result = await media_service.upload_image(
        file=file,
        folder="vendors/verification/business",
        vendor_id=str(vendor.id),
        allow_pdf=True
    )
    
    # Initialize verification if not exists
    if not vendor.verification:
        vendor.verification = VendorVerification()
    
    vendor.verification.business_registration = result["url"]
    vendor.updated_at = datetime.utcnow()
    await vendor.save()
    
    return {
        "success": True,
        "message": "Business registration document uploaded",
        "document_type": "business_registration",
        "url": result["url"]
    }


@router.post(
    "/vendor/verification/tax-certificate",
    summary="Upload tax certificate",
    description="Upload TIN certificate or tax registration document. Supported: PDF, JPEG, PNG. Max: 10MB"
)
async def upload_tax_certificate(
    file: UploadFile = File(..., description="Tax certificate"),
    vendor: Vendor = Depends(get_current_active_vendor)
):
    """Upload tax certificate for verification"""
    result = await media_service.upload_image(
        file=file,
        folder="vendors/verification/tax",
        vendor_id=str(vendor.id),
        allow_pdf=True
    )
    
    if not vendor.verification:
        vendor.verification = VendorVerification()
    
    vendor.verification.tax_certificate = result["url"]
    vendor.updated_at = datetime.utcnow()
    await vendor.save()
    
    return {
        "success": True,
        "message": "Tax certificate uploaded",
        "document_type": "tax_certificate",
        "url": result["url"]
    }


@router.post(
    "/vendor/verification/license",
    summary="Upload business license",
    description="Upload operating license or permit. Supported: PDF, JPEG, PNG. Max: 10MB"
)
async def upload_license_document(
    file: UploadFile = File(..., description="License document"),
    vendor: Vendor = Depends(get_current_active_vendor)
):
    """Upload business license for verification"""
    result = await media_service.upload_image(
        file=file,
        folder="vendors/verification/license",
        vendor_id=str(vendor.id),
        allow_pdf=True
    )
    
    if not vendor.verification:
        vendor.verification = VendorVerification()
    
    vendor.verification.license_document = result["url"]
    vendor.updated_at = datetime.utcnow()
    await vendor.save()
    
    return {
        "success": True,
        "message": "License document uploaded",
        "document_type": "license_document",
        "url": result["url"]
    }


@router.post(
    "/vendor/verification/identity",
    summary="Upload identity document",
    description="Upload government-issued ID (passport, driver's license, national ID). Supported: PDF, JPEG, PNG. Max: 10MB"
)
async def upload_identity_document(
    file: UploadFile = File(..., description="Identity document"),
    vendor: Vendor = Depends(get_current_active_vendor)
):
    """Upload identity document for verification"""
    result = await media_service.upload_image(
        file=file,
        folder="vendors/verification/identity",
        vendor_id=str(vendor.id),
        allow_pdf=True
    )
    
    if not vendor.verification:
        vendor.verification = VendorVerification()
    
    vendor.verification.identity_document = result["url"]
    vendor.updated_at = datetime.utcnow()
    await vendor.save()
    
    return {
        "success": True,
        "message": "Identity document uploaded",
        "document_type": "identity_document",
        "url": result["url"]
    }


@router.post(
    "/vendor/verification/address-proof",
    summary="Upload proof of address",
    description="Upload utility bill or bank statement (not older than 3 months). Supported: PDF, JPEG, PNG. Max: 10MB"
)
async def upload_proof_of_address(
    file: UploadFile = File(..., description="Proof of address document"),
    vendor: Vendor = Depends(get_current_active_vendor)
):
    """Upload proof of address for verification"""
    result = await media_service.upload_image(
        file=file,
        folder="vendors/verification/address",
        vendor_id=str(vendor.id),
        allow_pdf=True
    )
    
    if not vendor.verification:
        vendor.verification = VendorVerification()
    
    vendor.verification.proof_of_address = result["url"]
    vendor.updated_at = datetime.utcnow()
    await vendor.save()
    
    return {
        "success": True,
        "message": "Proof of address uploaded",
        "document_type": "proof_of_address",
        "url": result["url"]
    }


@router.post(
    "/vendor/verification/submit",
    summary="Submit verification for review",
    description="Submit all uploaded documents for admin review"
)
async def submit_verification_for_review(
    vendor: Vendor = Depends(get_current_active_vendor)
):
    """Submit uploaded verification documents for review"""
    if not vendor.verification:
        raise HTTPException(
            status_code=400,
            detail="No verification documents uploaded. Please upload at least one document."
        )
    
    # Check if at least basic documents are uploaded
    if not vendor.verification.business_registration and not vendor.verification.identity_document:
        raise HTTPException(
            status_code=400,
            detail="Please upload at least business registration or identity document"
        )
    
    # Update verification status
    vendor.verification.status = VerificationStatus.UNDER_REVIEW
    vendor.verification.submitted_at = datetime.utcnow()
    vendor.updated_at = datetime.utcnow()
    await vendor.save()
    
    return {
        "success": True,
        "message": "Verification documents submitted for review",
        "status": vendor.verification.status.value,
        "submitted_at": vendor.verification.submitted_at.isoformat(),
        "documents": {
            "business_registration": bool(vendor.verification.business_registration),
            "tax_certificate": bool(vendor.verification.tax_certificate),
            "license_document": bool(vendor.verification.license_document),
            "identity_document": bool(vendor.verification.identity_document),
            "proof_of_address": bool(vendor.verification.proof_of_address)
        }
    }


@router.get(
    "/vendor/verification/status",
    summary="Get verification status",
    description="Get current verification status and uploaded documents"
)
async def get_verification_upload_status(
    vendor: Vendor = Depends(get_current_active_vendor)
):
    """Get verification documents upload status"""
    if not vendor.verification:
        return {
            "status": "not_started",
            "documents": {
                "business_registration": None,
                "tax_certificate": None,
                "license_document": None,
                "identity_document": None,
                "proof_of_address": None
            },
            "submitted_at": None,
            "reviewed_at": None,
            "rejection_reason": None
        }
    
    return {
        "status": vendor.verification.status.value,
        "documents": {
            "business_registration": vendor.verification.business_registration,
            "tax_certificate": vendor.verification.tax_certificate,
            "license_document": vendor.verification.license_document,
            "identity_document": vendor.verification.identity_document,
            "proof_of_address": vendor.verification.proof_of_address
        },
        "submitted_at": vendor.verification.submitted_at.isoformat() if vendor.verification.submitted_at else None,
        "reviewed_at": vendor.verification.reviewed_at.isoformat() if vendor.verification.reviewed_at else None,
        "rejection_reason": vendor.verification.rejection_reason
    }


# === User Upload Endpoints ===

@router.post(
    "/user/avatar",
    summary="Upload user avatar",
    description="Upload a profile picture for the user. Auto-cropped to face. Max: 10MB"
)
async def upload_user_avatar(
    file: UploadFile = File(..., description="Avatar image file"),
    user: User = Depends(get_current_active_user)
):
    """Upload user avatar - auto-updates user profile"""
    result = await media_service.upload_image(
        file=file,
        folder="users/avatars",
        vendor_id=str(user.id),
        transformation={"width": 400, "height": 400, "crop": "fill", "gravity": "face"}
    )
    
    # Update user profile
    user.avatar = result["url"]
    user.updated_at = datetime.utcnow()
    await user.save()
    
    return {
        "success": True,
        "message": "Avatar uploaded successfully",
        "data": {
            "url": result["url"],
            "thumbnail_url": result["thumbnail_url"]
        }
    }


@router.post(
    "/user/cover",
    summary="Upload user cover image",
    description="Upload a cover/banner image for the user profile"
)
async def upload_user_cover(
    file: UploadFile = File(..., description="Cover image file"),
    user: User = Depends(get_current_active_user)
):
    """Upload user cover image"""
    result = await media_service.upload_image(
        file=file,
        folder="users/covers",
        vendor_id=str(user.id),
        transformation={"width": 1200, "height": 400, "crop": "fill"}
    )
    
    # Update user profile
    user.cover_image = result["url"]
    user.updated_at = datetime.utcnow()
    await user.save()
    
    return {
        "success": True,
        "message": "Cover image uploaded successfully",
        "data": {
            "url": result["url"],
            "thumbnail_url": result["thumbnail_url"]
        }
    }


# === Agent Media Upload Endpoints ===

@router.post(
    "/agent/profile-photo",
    summary="Upload agent profile photo",
    description="Upload a profile photo for the agent. Supported formats: JPEG, PNG, WebP. Max size: 10MB"
)
async def upload_agent_profile_photo(
    file: UploadFile = File(..., description="Profile photo file"),
    agent: Agent = Depends(get_current_active_agent)
):
    """Upload agent profile photo - auto-updates agent profile"""
    result = await media_service.upload_image(
        file=file,
        folder="agents/profile",
        vendor_id=str(agent.id),
        transformation={"width": 500, "height": 500, "crop": "fill", "gravity": "face"}
    )
    
    # Initialize media if not exists
    if not agent.media:
        agent.media = AgentMedia()
    
    # Update agent profile with new photo
    agent.media.profile_photo = result["url"]
    agent.media.profile_photo_public_id = result["public_id"]
    agent.updated_at = datetime.utcnow()
    await agent.save()
    
    return {
        "success": True,
        "message": "Profile photo uploaded successfully",
        "data": {
            "url": result["url"],
            "public_id": result["public_id"],
            "thumbnail_url": result["thumbnail_url"]
        }
    }


@router.post(
    "/agent/cover",
    summary="Upload agent cover image",
    description="Upload a cover/banner image for the agent profile. Recommended size: 1920x600. Max size: 10MB"
)
async def upload_agent_cover(
    file: UploadFile = File(..., description="Cover image file"),
    agent: Agent = Depends(get_current_active_agent)
):
    """Upload agent cover/banner image - auto-updates agent profile"""
    result = await media_service.upload_image(
        file=file,
        folder="agents/covers",
        vendor_id=str(agent.id),
        transformation={"width": 1920, "height": 600, "crop": "fill"}
    )
    
    # Initialize media if not exists
    if not agent.media:
        agent.media = AgentMedia()
    
    # Update agent profile
    agent.media.cover_image = result["url"]
    agent.media.cover_image_public_id = result["public_id"]
    agent.updated_at = datetime.utcnow()
    await agent.save()
    
    return {
        "success": True,
        "message": "Cover image uploaded successfully",
        "data": {
            "url": result["url"],
            "public_id": result["public_id"],
            "thumbnail_url": result["thumbnail_url"]
        }
    }


@router.post(
    "/agent/gallery",
    summary="Upload agent gallery images",
    description="Upload one or more images to the agent gallery. Max 10 images per request. Max size: 10MB each"
)
async def upload_agent_gallery(
    files: List[UploadFile] = File(..., description="Gallery images (max 10 per request)"),
    title: Optional[str] = Query(None, description="Optional title for the images"),
    agent: Agent = Depends(get_current_active_agent)
):
    """Upload multiple gallery images - auto-updates agent profile"""
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 images per upload")
    
    results = await media_service.upload_multiple_images(
        files=files,
        folder="agents/gallery",
        vendor_id=str(agent.id)
    )
    
    # Initialize media if not exists
    if not agent.media:
        agent.media = AgentMedia()
    
    # Add to gallery
    for i, result in enumerate(results):
        agent.media.gallery.append({
            "url": result["url"],
            "public_id": result["public_id"],
            "thumbnail_url": result["thumbnail_url"],
            "title": title or f"Image {len(agent.media.gallery) + 1}",
            "type": "image",
            "uploaded_at": datetime.utcnow().isoformat()
        })
    
    agent.updated_at = datetime.utcnow()
    await agent.save()
    
    return {
        "success": True,
        "message": f"{len(results)} image(s) uploaded successfully",
        "data": results,
        "gallery_count": len(agent.media.gallery)
    }


@router.post(
    "/agent/portfolio",
    summary="Upload agent portfolio item",
    description="Upload portfolio images showcasing past work/trips. Max 10 images per request."
)
async def upload_agent_portfolio(
    files: List[UploadFile] = File(..., description="Portfolio images"),
    title: Optional[str] = Query(None, description="Portfolio item title"),
    description: Optional[str] = Query(None, description="Portfolio item description"),
    agent: Agent = Depends(get_current_active_agent)
):
    """Upload portfolio images - auto-updates agent profile"""
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 images per upload")
    
    results = await media_service.upload_multiple_images(
        files=files,
        folder="agents/portfolio",
        vendor_id=str(agent.id)
    )
    
    # Initialize media if not exists
    if not agent.media:
        agent.media = AgentMedia()
    
    # Add to portfolio
    portfolio_item = {
        "title": title or f"Portfolio {len(agent.media.portfolio) + 1}",
        "description": description,
        "images": [
            {
                "url": result["url"],
                "public_id": result["public_id"],
                "thumbnail_url": result["thumbnail_url"]
            }
            for result in results
        ],
        "uploaded_at": datetime.utcnow().isoformat()
    }
    agent.media.portfolio.append(portfolio_item)
    
    agent.updated_at = datetime.utcnow()
    await agent.save()
    
    return {
        "success": True,
        "message": f"Portfolio item with {len(results)} image(s) uploaded",
        "data": portfolio_item,
        "portfolio_count": len(agent.media.portfolio)
    }


@router.delete(
    "/agent/gallery/{index}",
    summary="Delete agent gallery image",
    description="Delete a specific image from the gallery by index"
)
async def delete_agent_gallery_image(
    index: int,
    agent: Agent = Depends(get_current_active_agent)
):
    """Delete a gallery image by index"""
    if not agent.media or not agent.media.gallery:
        raise HTTPException(status_code=404, detail="No gallery images found")
    
    if index < 0 or index >= len(agent.media.gallery):
        raise HTTPException(status_code=404, detail="Image index out of range")
    
    # Get the image to delete
    image = agent.media.gallery[index]
    
    # Delete from Cloudinary
    if image.get("public_id"):
        await media_service.delete_media(image["public_id"], "image")
    
    # Remove from gallery
    agent.media.gallery.pop(index)
    agent.updated_at = datetime.utcnow()
    await agent.save()
    
    return {
        "success": True,
        "message": "Image deleted successfully",
        "gallery_count": len(agent.media.gallery)
    }


@router.delete(
    "/agent/portfolio/{index}",
    summary="Delete agent portfolio item",
    description="Delete a portfolio item by index"
)
async def delete_agent_portfolio(
    index: int,
    agent: Agent = Depends(get_current_active_agent)
):
    """Delete a portfolio item by index"""
    if not agent.media or not agent.media.portfolio:
        raise HTTPException(status_code=404, detail="No portfolio items found")
    
    if index < 0 or index >= len(agent.media.portfolio):
        raise HTTPException(status_code=404, detail="Portfolio index out of range")
    
    # Get the portfolio item
    portfolio_item = agent.media.portfolio[index]
    
    # Delete all images from Cloudinary
    for image in portfolio_item.get("images", []):
        if image.get("public_id"):
            await media_service.delete_media(image["public_id"], "image")
    
    # Remove from portfolio
    agent.media.portfolio.pop(index)
    agent.updated_at = datetime.utcnow()
    await agent.save()
    
    return {
        "success": True,
        "message": "Portfolio item deleted successfully",
        "portfolio_count": len(agent.media.portfolio)
    }


# === Agent Verification Document Uploads ===

@router.post(
    "/agent/verification/identity",
    summary="Upload agent identity document",
    description="Upload government-issued ID (passport, driver's license, national ID). Supported: PDF, JPEG, PNG. Max: 10MB"
)
async def upload_agent_identity(
    file: UploadFile = File(..., description="Identity document"),
    agent: Agent = Depends(get_current_active_agent)
):
    """Upload identity document for agent verification"""
    result = await media_service.upload_image(
        file=file,
        folder="agents/verification/identity",
        vendor_id=str(agent.id),
        allow_pdf=True
    )
    
    # Initialize verification if not exists
    if not agent.verification:
        agent.verification = AgentVerification()
    
    agent.verification.identity_document = result["url"]
    agent.updated_at = datetime.utcnow()
    await agent.save()
    
    return {
        "success": True,
        "message": "Identity document uploaded",
        "document_type": "identity_document",
        "url": result["url"]
    }


@router.post(
    "/agent/verification/license",
    summary="Upload agent license",
    description="Upload travel agent license or IATA certificate. Supported: PDF, JPEG, PNG. Max: 10MB"
)
async def upload_agent_license(
    file: UploadFile = File(..., description="License document"),
    agent: Agent = Depends(get_current_active_agent)
):
    """Upload agent license for verification"""
    result = await media_service.upload_image(
        file=file,
        folder="agents/verification/license",
        vendor_id=str(agent.id),
        allow_pdf=True
    )
    
    if not agent.verification:
        agent.verification = AgentVerification()
    
    agent.verification.license_document = result["url"]
    agent.updated_at = datetime.utcnow()
    await agent.save()
    
    return {
        "success": True,
        "message": "License document uploaded",
        "document_type": "license_document",
        "url": result["url"]
    }


@router.post(
    "/agent/verification/certification",
    summary="Upload agent certification",
    description="Upload professional certifications (IATA, tourism board, etc). Supported: PDF, JPEG, PNG. Max: 10MB"
)
async def upload_agent_certification(
    file: UploadFile = File(..., description="Certification document"),
    agent: Agent = Depends(get_current_active_agent)
):
    """Upload certification for agent verification"""
    result = await media_service.upload_image(
        file=file,
        folder="agents/verification/certification",
        vendor_id=str(agent.id),
        allow_pdf=True
    )
    
    if not agent.verification:
        agent.verification = AgentVerification()
    
    agent.verification.certification = result["url"]
    agent.updated_at = datetime.utcnow()
    await agent.save()
    
    return {
        "success": True,
        "message": "Certification uploaded",
        "document_type": "certification",
        "url": result["url"]
    }


@router.post(
    "/agent/verification/address-proof",
    summary="Upload agent proof of address",
    description="Upload utility bill or bank statement (not older than 3 months). Supported: PDF, JPEG, PNG. Max: 10MB"
)
async def upload_agent_address_proof(
    file: UploadFile = File(..., description="Proof of address document"),
    agent: Agent = Depends(get_current_active_agent)
):
    """Upload proof of address for agent verification"""
    result = await media_service.upload_image(
        file=file,
        folder="agents/verification/address",
        vendor_id=str(agent.id),
        allow_pdf=True
    )
    
    if not agent.verification:
        agent.verification = AgentVerification()
    
    agent.verification.proof_of_address = result["url"]
    agent.updated_at = datetime.utcnow()
    await agent.save()
    
    return {
        "success": True,
        "message": "Proof of address uploaded",
        "document_type": "proof_of_address",
        "url": result["url"]
    }


@router.post(
    "/agent/verification/agency-registration",
    summary="Upload agency registration",
    description="Upload agency/company registration document. Supported: PDF, JPEG, PNG. Max: 10MB"
)
async def upload_agent_agency_registration(
    file: UploadFile = File(..., description="Agency registration document"),
    agent: Agent = Depends(get_current_active_agent)
):
    """Upload agency registration for agent verification"""
    result = await media_service.upload_image(
        file=file,
        folder="agents/verification/agency",
        vendor_id=str(agent.id),
        allow_pdf=True
    )
    
    if not agent.verification:
        agent.verification = AgentVerification()
    
    agent.verification.agency_registration = result["url"]
    agent.updated_at = datetime.utcnow()
    await agent.save()
    
    return {
        "success": True,
        "message": "Agency registration uploaded",
        "document_type": "agency_registration",
        "url": result["url"]
    }


@router.post(
    "/agent/verification/submit",
    summary="Submit agent verification for review",
    description="Submit all uploaded documents for admin review"
)
async def submit_agent_verification_for_review(
    agent: Agent = Depends(get_current_active_agent)
):
    """Submit uploaded verification documents for review"""
    if not agent.verification:
        raise HTTPException(
            status_code=400,
            detail="No verification documents uploaded. Please upload at least one document."
        )
    
    # Check if at least identity document is uploaded
    if not agent.verification.identity_document:
        raise HTTPException(
            status_code=400,
            detail="Please upload at least your identity document"
        )
    
    # Update verification status
    agent.verification.status = VerificationStatus.UNDER_REVIEW
    agent.verification.submitted_at = datetime.utcnow()
    agent.updated_at = datetime.utcnow()
    await agent.save()
    
    return {
        "success": True,
        "message": "Verification documents submitted for review",
        "status": agent.verification.status.value,
        "submitted_at": agent.verification.submitted_at.isoformat(),
        "documents": {
            "identity_document": bool(agent.verification.identity_document),
            "license_document": bool(agent.verification.license_document),
            "certification": bool(agent.verification.certification),
            "proof_of_address": bool(agent.verification.proof_of_address),
            "agency_registration": bool(agent.verification.agency_registration)
        }
    }


@router.get(
    "/agent/verification/status",
    summary="Get agent verification status",
    description="Get current verification status and uploaded documents"
)
async def get_agent_verification_upload_status(
    agent: Agent = Depends(get_current_active_agent)
):
    """Get verification documents upload status for agent"""
    if not agent.verification:
        return {
            "status": "not_started",
            "documents": {
                "identity_document": None,
                "license_document": None,
                "certification": None,
                "proof_of_address": None,
                "agency_registration": None
            },
            "submitted_at": None,
            "reviewed_at": None,
            "rejection_reason": None
        }
    
    return {
        "status": agent.verification.status.value,
        "documents": {
            "identity_document": agent.verification.identity_document,
            "license_document": agent.verification.license_document,
            "certification": agent.verification.certification,
            "proof_of_address": agent.verification.proof_of_address,
            "agency_registration": agent.verification.agency_registration
        },
        "submitted_at": agent.verification.submitted_at.isoformat() if agent.verification.submitted_at else None,
        "reviewed_at": agent.verification.reviewed_at.isoformat() if agent.verification.reviewed_at else None,
        "rejection_reason": agent.verification.rejection_reason
    }
