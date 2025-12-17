"""
Queska Backend - Custom Exceptions
Centralized exception classes for consistent error handling
"""

from typing import Any, Dict, Optional


class AppException(Exception):
    """
    Base application exception.
    All custom exceptions should inherit from this.
    """
    
    def __init__(
        self,
        message: str = "An error occurred",
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


# === Authentication Errors ===

class AuthenticationError(AppException):
    """Authentication failed"""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=401,
            error_code="AUTHENTICATION_ERROR",
            details=details
        )


class InvalidCredentialsError(AppException):
    """Invalid login credentials"""
    
    def __init__(
        self,
        message: str = "Invalid email or password",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=401,
            error_code="INVALID_CREDENTIALS",
            details=details
        )


class TokenExpiredError(AppException):
    """Token has expired"""
    
    def __init__(
        self,
        message: str = "Token has expired",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=401,
            error_code="TOKEN_EXPIRED",
            details=details
        )


class InvalidTokenError(AppException):
    """Token is invalid"""
    
    def __init__(
        self,
        message: str = "Invalid token",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=401,
            error_code="INVALID_TOKEN",
            details=details
        )


# === Authorization Errors ===

class ForbiddenError(AppException):
    """Access forbidden"""
    
    def __init__(
        self,
        message: str = "Access forbidden",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=403,
            error_code="FORBIDDEN",
            details=details
        )


class PermissionDeniedError(AppException):
    """Permission denied for this action"""
    
    def __init__(
        self,
        message: str = "Permission denied",
        required_permission: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if required_permission:
            message = f"Permission denied. Required: {required_permission}"
        super().__init__(
            message=message,
            status_code=403,
            error_code="PERMISSION_DENIED",
            details=details
        )


class AccountSuspendedError(AppException):
    """Account has been suspended"""
    
    def __init__(
        self,
        message: str = "Your account has been suspended",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=403,
            error_code="ACCOUNT_SUSPENDED",
            details=details
        )


class AccountNotVerifiedError(AppException):
    """Account not verified"""
    
    def __init__(
        self,
        message: str = "Please verify your account",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=403,
            error_code="ACCOUNT_NOT_VERIFIED",
            details=details
        )


# === Not Found Errors ===

class NotFoundError(AppException):
    """Resource not found"""
    
    def __init__(
        self,
        resource: str = "Resource",
        identifier: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        message = f"{resource} not found"
        if identifier:
            message = f"{resource} with ID '{identifier}' not found"
        super().__init__(
            message=message,
            status_code=404,
            error_code="NOT_FOUND",
            details=details
        )


class UserNotFoundError(NotFoundError):
    """User not found"""
    
    def __init__(self, identifier: Optional[str] = None):
        super().__init__("User", identifier)


class VendorNotFoundError(NotFoundError):
    """Vendor not found"""
    
    def __init__(self, identifier: Optional[str] = None):
        super().__init__("Vendor", identifier)


class AgentNotFoundError(NotFoundError):
    """Agent not found"""
    
    def __init__(self, identifier: Optional[str] = None):
        super().__init__("Agent", identifier)


class ExperienceNotFoundError(NotFoundError):
    """Experience not found"""
    
    def __init__(self, identifier: Optional[str] = None):
        super().__init__("Experience", identifier)


class BookingNotFoundError(NotFoundError):
    """Booking not found"""
    
    def __init__(self, identifier: Optional[str] = None):
        super().__init__("Booking", identifier)


# === Validation Errors ===

class ValidationError(AppException):
    """Validation error"""
    
    def __init__(
        self,
        message: str = "Validation error",
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if field:
            message = f"Validation error for field '{field}': {message}"
        super().__init__(
            message=message,
            status_code=422,
            error_code="VALIDATION_ERROR",
            details=details
        )


class InvalidInputError(ValidationError):
    """Invalid input provided"""
    
    def __init__(
        self,
        message: str = "Invalid input",
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, field, details)


# === Conflict Errors ===

class ConflictError(AppException):
    """Resource conflict"""
    
    def __init__(
        self,
        message: str = "Resource conflict",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=409,
            error_code="CONFLICT",
            details=details
        )


class AlreadyExistsError(ConflictError):
    """Resource already exists"""
    
    def __init__(
        self,
        resource: str = "Resource",
        field: Optional[str] = None,
        value: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if field and value:
            message = f"{resource} with {field} '{value}' already exists"
        else:
            message = f"{resource} already exists"
        super().__init__(message, details)


class DuplicateEmailError(AlreadyExistsError):
    """Email already registered"""
    
    def __init__(self, email: str):
        super().__init__("User", "email", email)


# === Payment Errors ===

class PaymentError(AppException):
    """Payment processing error"""
    
    def __init__(
        self,
        message: str = "Payment processing failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=402,
            error_code="PAYMENT_ERROR",
            details=details
        )


class InsufficientFundsError(PaymentError):
    """Insufficient funds for transaction"""
    
    def __init__(
        self,
        message: str = "Insufficient funds",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details)


# === Booking Errors ===

class BookingError(AppException):
    """Booking operation error"""
    
    def __init__(
        self,
        message: str = "Booking operation failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=400,
            error_code="BOOKING_ERROR",
            details=details
        )


class BookingUnavailableError(BookingError):
    """Booking not available"""
    
    def __init__(
        self,
        message: str = "This booking is no longer available",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details)


class BookingExpiredError(BookingError):
    """Booking has expired"""
    
    def __init__(
        self,
        message: str = "Booking has expired",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details)


# === Rate Limit Errors ===

class RateLimitError(AppException):
    """Rate limit exceeded"""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if retry_after:
            message = f"{message}. Retry after {retry_after} seconds"
        super().__init__(
            message=message,
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            details=details
        )


# === External Service Errors ===

class ExternalServiceError(AppException):
    """External service error"""
    
    def __init__(
        self,
        service: str = "External service",
        message: str = "External service error",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"{service}: {message}",
            status_code=502,
            error_code="EXTERNAL_SERVICE_ERROR",
            details=details
        )


class StripeError(ExternalServiceError):
    """Stripe API error"""
    
    def __init__(
        self,
        message: str = "Payment service error",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__("Stripe", message, details)


class MapboxError(ExternalServiceError):
    """Mapbox API error"""
    
    def __init__(
        self,
        message: str = "Location service error",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__("Mapbox", message, details)


# === File Errors ===

class FileError(AppException):
    """File operation error"""
    
    def __init__(
        self,
        message: str = "File operation failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=400,
            error_code="FILE_ERROR",
            details=details
        )


class FileTooLargeError(FileError):
    """File exceeds size limit"""
    
    def __init__(
        self,
        max_size: int,
        details: Optional[Dict[str, Any]] = None
    ):
        max_mb = max_size / (1024 * 1024)
        super().__init__(
            f"File exceeds maximum size of {max_mb:.1f}MB",
            details
        )


class InvalidFileTypeError(FileError):
    """Invalid file type"""
    
    def __init__(
        self,
        allowed_types: list,
        details: Optional[Dict[str, Any]] = None
    ):
        types_str = ", ".join(allowed_types)
        super().__init__(
            f"Invalid file type. Allowed types: {types_str}",
            details
        )


# === Database Errors ===

class DatabaseError(AppException):
    """Database operation error"""
    
    def __init__(
        self,
        message: str = "Database operation failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=500,
            error_code="DATABASE_ERROR",
            details=details
        )


class ConnectionError(DatabaseError):
    """Database connection error"""
    
    def __init__(
        self,
        message: str = "Could not connect to database",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details)


# === Business Logic Errors ===

class VendorError(AppException):
    """Vendor-related business logic error"""
    
    def __init__(
        self,
        message: str = "Vendor operation failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=400,
            error_code="VENDOR_ERROR",
            details=details
        )


class AgentError(AppException):
    """Agent-related business logic error"""
    
    def __init__(
        self,
        message: str = "Agent operation failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=400,
            error_code="AGENT_ERROR",
            details=details
        )


class UserError(AppException):
    """User-related business logic error"""
    
    def __init__(
        self,
        message: str = "User operation failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=400,
            error_code="USER_ERROR",
            details=details
        )


class ExperienceError(AppException):
    """Experience-related business logic error"""
    
    def __init__(
        self,
        message: str = "Experience operation failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=400,
            error_code="EXPERIENCE_ERROR",
            details=details
        )


class ServiceUnavailableError(AppException):
    """Service temporarily unavailable"""
    
    def __init__(
        self,
        service: str = "Service",
        message: str = "temporarily unavailable",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"{service} is {message}",
            status_code=503,
            error_code="SERVICE_UNAVAILABLE",
            details=details
        )
