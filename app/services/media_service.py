"""
Queska Backend - Media Service
Cloudinary integration for image/video uploads
"""

import cloudinary
import cloudinary.uploader
import cloudinary.api
from typing import Optional, Dict, Any, List
from fastapi import UploadFile, HTTPException
from loguru import logger

from app.core.config import settings


# Initialize Cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True
)


class MediaService:
    """Service for handling media uploads to Cloudinary"""
    
    # Allowed file types
    ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    ALLOWED_VIDEO_TYPES = ["video/mp4", "video/quicktime", "video/x-msvideo", "video/webm"]
    ALLOWED_DOCUMENT_TYPES = ["application/pdf", "image/jpeg", "image/png"]
    
    # Size limits (in bytes)
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_VIDEO_SIZE = 100 * 1024 * 1024  # 100MB
    
    def __init__(self):
        self.cloud_name = settings.CLOUDINARY_CLOUD_NAME
    
    async def upload_image(
        self,
        file: UploadFile,
        folder: str = "vendors",
        vendor_id: Optional[str] = None,
        transformation: Optional[Dict[str, Any]] = None,
        allow_pdf: bool = False
    ) -> Dict[str, Any]:
        """
        Upload an image to Cloudinary
        
        Args:
            file: The uploaded file
            folder: Cloudinary folder path
            vendor_id: Optional vendor ID for organizing uploads
            transformation: Optional image transformations
            allow_pdf: Whether to allow PDF uploads (for documents)
            
        Returns:
            Dict with upload result including URL
        """
        # Validate file type
        allowed_types = self.ALLOWED_IMAGE_TYPES.copy()
        if allow_pdf:
            allowed_types.append("application/pdf")
        
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
            )
        
        # Read file content
        content = await file.read()
        
        # Validate file size
        if len(content) > self.MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {self.MAX_IMAGE_SIZE // (1024*1024)}MB"
            )
        
        try:
            # Build folder path
            upload_folder = f"queska/{folder}"
            if vendor_id:
                upload_folder = f"queska/{folder}/{vendor_id}"
            
            # Default transformations for optimization
            default_transformation = {
                "quality": "auto",
                "fetch_format": "auto"
            }
            if transformation:
                default_transformation.update(transformation)
            
            # Upload to Cloudinary
            result = cloudinary.uploader.upload(
                content,
                folder=upload_folder,
                resource_type="image",
                transformation=default_transformation,
                # Generate unique filename
                use_filename=True,
                unique_filename=True
            )
            
            logger.info(f"Image uploaded successfully: {result['public_id']}")
            
            return {
                "url": result["secure_url"],
                "public_id": result["public_id"],
                "width": result.get("width"),
                "height": result.get("height"),
                "format": result.get("format"),
                "size": result.get("bytes"),
                "thumbnail_url": self._generate_thumbnail_url(result["public_id"])
            }
            
        except Exception as e:
            logger.error(f"Cloudinary upload failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload image: {str(e)}"
            )
    
    async def upload_video(
        self,
        file: UploadFile,
        folder: str = "vendors",
        vendor_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload a video to Cloudinary
        
        Args:
            file: The uploaded file
            folder: Cloudinary folder path
            vendor_id: Optional vendor ID
            
        Returns:
            Dict with upload result including URL
        """
        # Validate file type
        if file.content_type not in self.ALLOWED_VIDEO_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(self.ALLOWED_VIDEO_TYPES)}"
            )
        
        # Read file content
        content = await file.read()
        
        # Validate file size
        if len(content) > self.MAX_VIDEO_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {self.MAX_VIDEO_SIZE // (1024*1024)}MB"
            )
        
        try:
            # Build folder path
            upload_folder = f"queska/{folder}"
            if vendor_id:
                upload_folder = f"queska/{folder}/{vendor_id}"
            
            # Upload to Cloudinary
            result = cloudinary.uploader.upload(
                content,
                folder=upload_folder,
                resource_type="video",
                use_filename=True,
                unique_filename=True,
                # Generate thumbnail
                eager=[
                    {"width": 400, "height": 300, "crop": "fill", "format": "jpg"}
                ]
            )
            
            logger.info(f"Video uploaded successfully: {result['public_id']}")
            
            # Get thumbnail URL
            thumbnail_url = None
            if result.get("eager"):
                thumbnail_url = result["eager"][0].get("secure_url")
            
            return {
                "url": result["secure_url"],
                "public_id": result["public_id"],
                "duration": result.get("duration"),
                "format": result.get("format"),
                "size": result.get("bytes"),
                "thumbnail_url": thumbnail_url
            }
            
        except Exception as e:
            logger.error(f"Cloudinary video upload failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload video: {str(e)}"
            )
    
    async def upload_multiple_images(
        self,
        files: List[UploadFile],
        folder: str = "vendors",
        vendor_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Upload multiple images
        
        Args:
            files: List of uploaded files
            folder: Cloudinary folder path
            vendor_id: Optional vendor ID
            
        Returns:
            List of upload results
        """
        results = []
        for file in files:
            result = await self.upload_image(file, folder, vendor_id)
            results.append(result)
        return results
    
    async def delete_media(self, public_id: str, resource_type: str = "image") -> bool:
        """
        Delete media from Cloudinary
        
        Args:
            public_id: The Cloudinary public ID
            resource_type: 'image' or 'video'
            
        Returns:
            True if successful
        """
        try:
            result = cloudinary.uploader.destroy(public_id, resource_type=resource_type)
            return result.get("result") == "ok"
        except Exception as e:
            logger.error(f"Failed to delete media: {str(e)}")
            return False
    
    def _generate_thumbnail_url(self, public_id: str, width: int = 300, height: int = 200) -> str:
        """Generate a thumbnail URL for an image"""
        return cloudinary.CloudinaryImage(public_id).build_url(
            width=width,
            height=height,
            crop="fill",
            quality="auto",
            fetch_format="auto"
        )
    
    def get_optimized_url(
        self,
        public_id: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
        crop: str = "fill"
    ) -> str:
        """
        Get an optimized/transformed URL for an image
        
        Args:
            public_id: The Cloudinary public ID
            width: Desired width
            height: Desired height
            crop: Crop mode
            
        Returns:
            Optimized image URL
        """
        options = {
            "quality": "auto",
            "fetch_format": "auto"
        }
        if width:
            options["width"] = width
        if height:
            options["height"] = height
        if width or height:
            options["crop"] = crop
        
        return cloudinary.CloudinaryImage(public_id).build_url(**options)


# Singleton instance
media_service = MediaService()

