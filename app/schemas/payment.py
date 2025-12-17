"""
Queska Backend - Payment Schemas
Pydantic schemas for payment processing
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, EmailStr

from app.schemas.base import BaseSchema, PaginatedResponse
from app.core.constants import PaymentStatus, PaymentMethod


# ================================================================
# COMMON SCHEMAS
# ================================================================

class PaymentMethodDetailsSchema(BaseSchema):
    """Payment method details"""
    type: str
    brand: Optional[str] = None
    last4: Optional[str] = None
    exp_month: Optional[int] = None
    exp_year: Optional[int] = None
    bank_name: Optional[str] = None
    country: Optional[str] = None
    funding: Optional[str] = None


class PaymentBreakdownSchema(BaseSchema):
    """Payment breakdown"""
    subtotal: float
    service_fee: float
    service_fee_percentage: float
    taxes: float
    tax_percentage: float
    discount: float
    discount_code: Optional[str] = None
    total: float
    currency: str


class RefundSchema(BaseSchema):
    """Refund details"""
    refund_id: str
    amount: float
    currency: str
    reason: Optional[str] = None
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None


# ================================================================
# PAYMENT INTENT SCHEMAS
# ================================================================

class CreatePaymentIntentRequest(BaseSchema):
    """Create a payment intent"""
    amount: float = Field(..., gt=0, description="Amount in currency units (e.g., dollars)")
    currency: str = Field("USD", max_length=3)
    description: Optional[str] = None
    receipt_email: Optional[EmailStr] = None
    save_payment_method: bool = False
    
    # For experience payments
    experience_id: Optional[str] = None
    booking_id: Optional[str] = None
    
    # For vendor marketplace
    vendor_id: Optional[str] = None
    platform_fee_percentage: float = Field(5.0, ge=0, le=30)


class CreatePaymentIntentResponse(BaseSchema):
    """Payment intent response"""
    success: bool
    payment_intent_id: Optional[str] = None
    client_secret: Optional[str] = None
    status: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    error: Optional[str] = None


class ConfirmPaymentRequest(BaseSchema):
    """Confirm a payment"""
    payment_intent_id: str
    payment_method_id: Optional[str] = None
    return_url: Optional[str] = None


class PaymentStatusResponse(BaseSchema):
    """Payment status"""
    payment_id: str
    payment_intent_id: Optional[str] = None
    status: str
    amount: float
    currency: str
    paid_at: Optional[datetime] = None
    receipt_url: Optional[str] = None


# ================================================================
# CHECKOUT SESSION SCHEMAS
# ================================================================

class CheckoutLineItem(BaseSchema):
    """Checkout line item"""
    name: str
    description: Optional[str] = None
    amount: float = Field(..., gt=0)
    quantity: int = Field(1, ge=1)
    image_url: Optional[str] = None


class CreateCheckoutSessionRequest(BaseSchema):
    """Create a checkout session"""
    items: List[CheckoutLineItem] = Field(..., min_length=1)
    success_url: str
    cancel_url: str
    customer_email: Optional[EmailStr] = None
    
    # Metadata
    experience_id: Optional[str] = None
    booking_id: Optional[str] = None
    
    # Options
    allow_promotion_codes: bool = True
    collect_shipping_address: bool = False
    
    # Expiration (optional, in minutes)
    expires_in_minutes: Optional[int] = Field(None, ge=30, le=1440)


class CreateCheckoutSessionResponse(BaseSchema):
    """Checkout session response"""
    success: bool
    session_id: Optional[str] = None
    checkout_url: Optional[str] = None
    expires_at: Optional[datetime] = None
    error: Optional[str] = None


class CheckoutSessionStatusResponse(BaseSchema):
    """Checkout session status"""
    session_id: str
    status: str  # open, complete, expired
    payment_status: str  # unpaid, paid, no_payment_required
    customer_email: Optional[str] = None
    amount_total: Optional[float] = None
    currency: Optional[str] = None


# ================================================================
# REFUND SCHEMAS
# ================================================================

class CreateRefundRequest(BaseSchema):
    """Create a refund"""
    payment_id: str
    amount: Optional[float] = Field(None, gt=0, description="Partial refund amount")
    reason: Optional[str] = Field(None, pattern="^(duplicate|fraudulent|requested_by_customer)$")
    note: Optional[str] = None


class RefundResponse(BaseSchema):
    """Refund response"""
    success: bool
    refund_id: Optional[str] = None
    status: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    error: Optional[str] = None


# ================================================================
# PAYMENT METHOD SCHEMAS
# ================================================================

class AddPaymentMethodRequest(BaseSchema):
    """Add a payment method"""
    payment_method_id: str  # From Stripe.js
    set_as_default: bool = False
    nickname: Optional[str] = None


class PaymentMethodResponse(BaseSchema):
    """Payment method response"""
    id: str
    type: str
    brand: Optional[str] = None
    last4: Optional[str] = None
    exp_month: Optional[int] = None
    exp_year: Optional[int] = None
    is_default: bool = False
    nickname: Optional[str] = None
    created_at: datetime


class ListPaymentMethodsResponse(BaseSchema):
    """List of payment methods"""
    payment_methods: List[PaymentMethodResponse]
    default_payment_method_id: Optional[str] = None


class SetDefaultPaymentMethodRequest(BaseSchema):
    """Set default payment method"""
    payment_method_id: str


# ================================================================
# CUSTOMER SCHEMAS
# ================================================================

class CustomerSetupResponse(BaseSchema):
    """Customer setup response"""
    customer_id: str
    setup_intent_client_secret: Optional[str] = None


# ================================================================
# SUBSCRIPTION SCHEMAS
# ================================================================

class CreateSubscriptionRequest(BaseSchema):
    """Create a subscription"""
    price_id: str
    payment_method_id: Optional[str] = None
    trial_days: Optional[int] = Field(None, ge=0, le=365)


class SubscriptionResponse(BaseSchema):
    """Subscription response"""
    subscription_id: str
    status: str
    plan_name: str
    plan_tier: str
    amount: float
    currency: str
    interval: str
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool
    trial_end: Optional[datetime] = None


class CancelSubscriptionRequest(BaseSchema):
    """Cancel subscription"""
    immediately: bool = False


class UpdateSubscriptionRequest(BaseSchema):
    """Update subscription"""
    price_id: Optional[str] = None
    cancel_at_period_end: Optional[bool] = None


# ================================================================
# WALLET SCHEMAS
# ================================================================

class WalletResponse(BaseSchema):
    """Wallet details"""
    balance: float
    currency: str
    credits: int
    reserved_balance: float
    total_deposited: float
    total_spent: float


class AddFundsRequest(BaseSchema):
    """Add funds to wallet"""
    amount: float = Field(..., gt=0, le=10000)
    payment_method_id: Optional[str] = None


class WalletTransactionResponse(BaseSchema):
    """Wallet transaction"""
    id: str
    type: str
    amount: float
    credits: int
    currency: str
    description: str
    balance_after: float
    status: str
    created_at: datetime


class PaginatedWalletTransactionsResponse(PaginatedResponse):
    """Paginated wallet transactions"""
    data: List[WalletTransactionResponse]


# ================================================================
# VENDOR/CONNECT SCHEMAS
# ================================================================

class CreateConnectAccountRequest(BaseSchema):
    """Create vendor Connect account"""
    country: str = Field("US", min_length=2, max_length=2)
    business_type: str = Field("individual", pattern="^(individual|company)$")


class ConnectAccountResponse(BaseSchema):
    """Connect account details"""
    account_id: str
    details_submitted: bool
    charges_enabled: bool
    payouts_enabled: bool
    onboarding_completed: bool


class OnboardingLinkResponse(BaseSchema):
    """Onboarding link"""
    url: str
    expires_at: datetime


class DashboardLinkResponse(BaseSchema):
    """Dashboard link for vendors"""
    url: str


class VendorPayoutResponse(BaseSchema):
    """Vendor payout"""
    id: str
    amount: float
    currency: str
    status: str
    arrival_date: Optional[datetime] = None
    destination_last4: Optional[str] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    transaction_count: int


class PaginatedPayoutsResponse(PaginatedResponse):
    """Paginated payouts"""
    data: List[VendorPayoutResponse]


# ================================================================
# PAYMENT HISTORY SCHEMAS
# ================================================================

class PaymentResponse(BaseSchema):
    """Payment record"""
    id: str
    amount: float
    currency: str
    status: str
    payment_type: str
    description: Optional[str] = None
    payment_method: Optional[PaymentMethodDetailsSchema] = None
    breakdown: Optional[PaymentBreakdownSchema] = None
    experience_id: Optional[str] = None
    booking_id: Optional[str] = None
    receipt_url: Optional[str] = None
    paid_at: Optional[datetime] = None
    created_at: datetime
    refunds: List[RefundSchema] = Field(default_factory=list)
    total_refunded: float = 0.0


class PaginatedPaymentsResponse(PaginatedResponse):
    """Paginated payments"""
    data: List[PaymentResponse]


# ================================================================
# WEBHOOK SCHEMAS
# ================================================================

class WebhookEventResponse(BaseSchema):
    """Webhook event response"""
    received: bool
    event_type: Optional[str] = None
    event_id: Optional[str] = None


# ================================================================
# PRICING SCHEMAS
# ================================================================

class SubscriptionPlanSchema(BaseSchema):
    """Subscription plan details"""
    id: str
    name: str
    tier: str
    description: str
    price_monthly: float
    price_yearly: float
    currency: str
    features: List[str]
    limits: Dict[str, Any]
    popular: bool = False


class AvailablePlansResponse(BaseSchema):
    """Available subscription plans"""
    plans: List[SubscriptionPlanSchema]


# ================================================================
# PAYMENT CONFIG SCHEMA
# ================================================================

class PaymentConfigResponse(BaseSchema):
    """Payment configuration for frontend"""
    publishable_key: str
    supported_currencies: List[str]
    default_currency: str
    min_amount: float
    max_amount: float
    platform_fee_percentage: float

