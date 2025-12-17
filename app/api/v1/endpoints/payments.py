"""
Queska Backend - Payment Endpoints
API routes for payment processing, subscriptions, and vendor payouts
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status

from app.api.deps import get_current_active_user, get_current_verified_vendor
from app.core.exceptions import NotFoundError, ValidationError, PaymentError
from app.models.user import User
from app.models.vendor import Vendor
from app.schemas.base import SuccessResponse
from app.schemas.payment import (
    # Payment Intent
    CreatePaymentIntentRequest,
    CreatePaymentIntentResponse,
    ConfirmPaymentRequest,
    PaymentStatusResponse,
    # Checkout
    CreateCheckoutSessionRequest,
    CreateCheckoutSessionResponse,
    CheckoutSessionStatusResponse,
    CheckoutLineItem,
    # Refunds
    CreateRefundRequest,
    RefundResponse,
    # Payment Methods
    AddPaymentMethodRequest,
    PaymentMethodResponse,
    ListPaymentMethodsResponse,
    SetDefaultPaymentMethodRequest,
    # Subscriptions
    CreateSubscriptionRequest,
    SubscriptionResponse,
    CancelSubscriptionRequest,
    UpdateSubscriptionRequest,
    AvailablePlansResponse,
    SubscriptionPlanSchema,
    # Wallet
    WalletResponse,
    AddFundsRequest,
    WalletTransactionResponse,
    PaginatedWalletTransactionsResponse,
    # Connect (Vendors)
    CreateConnectAccountRequest,
    ConnectAccountResponse,
    OnboardingLinkResponse,
    DashboardLinkResponse,
    VendorPayoutResponse,
    PaginatedPayoutsResponse,
    # History
    PaymentResponse,
    PaginatedPaymentsResponse,
    PaymentBreakdownSchema,
    PaymentMethodDetailsSchema,
    RefundSchema,
    # Config
    PaymentConfigResponse,
    # Webhook
    WebhookEventResponse,
    CustomerSetupResponse,
)
from app.services.payment_service import payment_service
from integrations.payments.stripe_client import stripe_client

router = APIRouter()


# ================================================================
# CONFIGURATION
# ================================================================

@router.get(
    "/config",
    response_model=PaymentConfigResponse,
    summary="Get payment configuration",
    description="Get Stripe publishable key and payment settings",
)
async def get_payment_config():
    """Get payment configuration for frontend."""
    return PaymentConfigResponse(
        publishable_key=payment_service.get_publishable_key(),
        supported_currencies=["USD", "EUR", "GBP", "NGN"],
        default_currency="USD",
        min_amount=1.0,
        max_amount=50000.0,
        platform_fee_percentage=5.0
    )


# ================================================================
# CUSTOMER SETUP
# ================================================================

@router.post(
    "/setup",
    response_model=CustomerSetupResponse,
    summary="Setup payment customer",
    description="Create or get Stripe customer for the current user",
)
async def setup_payment_customer(
    current_user: User = Depends(get_current_active_user)
):
    """Setup Stripe customer for payments."""
    customer = await payment_service.get_or_create_stripe_customer(
        user_id=str(current_user.id),
        email=current_user.email,
        name=f"{current_user.first_name} {current_user.last_name}".strip() or None,
        phone=current_user.phone,
        user_type="user"
    )
    
    return CustomerSetupResponse(
        customer_id=customer.stripe_customer_id,
        setup_intent_client_secret=None  # Can add SetupIntent if needed
    )


# ================================================================
# PAYMENT INTENTS
# ================================================================

@router.post(
    "/intents",
    response_model=CreatePaymentIntentResponse,
    summary="Create payment intent",
    description="Create a payment intent for one-time payment",
)
async def create_payment_intent(
    data: CreatePaymentIntentRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a payment intent for processing payment.
    
    Returns client_secret for Stripe.js to complete payment.
    """
    try:
        result = await payment_service.create_payment_intent(
            user_id=str(current_user.id),
            amount=data.amount,
            currency=data.currency,
            description=data.description,
            receipt_email=data.receipt_email or current_user.email,
            experience_id=data.experience_id,
            booking_id=data.booking_id,
            vendor_id=data.vendor_id,
            platform_fee_percentage=data.platform_fee_percentage,
            save_payment_method=data.save_payment_method,
        )
        
        return CreatePaymentIntentResponse(
            success=True,
            payment_intent_id=result.get("payment_intent_id"),
            client_secret=result.get("client_secret"),
            status=result.get("status"),
            amount=result.get("amount"),
            currency=result.get("currency"),
        )
        
    except PaymentError as e:
        return CreatePaymentIntentResponse(success=False, error=str(e))
    except ValidationError as e:
        return CreatePaymentIntentResponse(success=False, error=str(e))


@router.post(
    "/intents/{payment_intent_id}/confirm",
    response_model=CreatePaymentIntentResponse,
    summary="Confirm payment intent",
)
async def confirm_payment_intent(
    payment_intent_id: str,
    data: ConfirmPaymentRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Confirm a payment intent with payment method."""
    try:
        result = await payment_service.confirm_payment(
            payment_intent_id=payment_intent_id,
            payment_method_id=data.payment_method_id,
            return_url=data.return_url
        )
        
        return CreatePaymentIntentResponse(
            success=result.get("success", False),
            payment_intent_id=result.get("payment_intent_id"),
            status=result.get("status"),
            error=result.get("error"),
        )
        
    except PaymentError as e:
        return CreatePaymentIntentResponse(success=False, error=str(e))


@router.get(
    "/status/{payment_id}",
    response_model=PaymentStatusResponse,
    summary="Get payment status",
)
async def get_payment_status(
    payment_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get the status of a payment."""
    try:
        result = await payment_service.get_payment_status(
            payment_id=payment_id,
            user_id=str(current_user.id)
        )
        
        return PaymentStatusResponse(
            payment_id=result["payment_id"],
            payment_intent_id=result.get("payment_intent_id"),
            status=result["status"],
            amount=result["amount"],
            currency=result["currency"],
            paid_at=result.get("paid_at"),
            receipt_url=result.get("receipt_url"),
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ================================================================
# CHECKOUT SESSIONS
# ================================================================

@router.post(
    "/checkout",
    response_model=CreateCheckoutSessionResponse,
    summary="Create checkout session",
    description="Create a Stripe Checkout session for payment",
)
async def create_checkout_session(
    data: CreateCheckoutSessionRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a Stripe Checkout session.
    
    Redirects user to Stripe's hosted checkout page.
    """
    try:
        result = await payment_service.create_checkout_session(
            user_id=str(current_user.id),
            items=data.items,
            success_url=data.success_url,
            cancel_url=data.cancel_url,
            customer_email=data.customer_email or current_user.email,
            experience_id=data.experience_id,
            booking_id=data.booking_id,
            allow_promotion_codes=data.allow_promotion_codes,
            collect_shipping=data.collect_shipping_address,
            expires_in_minutes=data.expires_in_minutes,
        )
        
        return CreateCheckoutSessionResponse(
            success=True,
            session_id=result.get("session_id"),
            checkout_url=result.get("checkout_url"),
            expires_at=result.get("expires_at"),
        )
        
    except PaymentError as e:
        return CreateCheckoutSessionResponse(success=False, error=str(e))


@router.get(
    "/checkout/{session_id}",
    response_model=CheckoutSessionStatusResponse,
    summary="Get checkout session status",
)
async def get_checkout_session_status(
    session_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get the status of a checkout session."""
    try:
        result = await payment_service.get_checkout_session_status(session_id)
        
        return CheckoutSessionStatusResponse(
            session_id=result["session_id"],
            status=result["status"],
            payment_status=result["payment_status"],
            customer_email=result.get("customer_email"),
            amount_total=result.get("amount_total"),
            currency=result.get("currency"),
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ================================================================
# PAYMENT METHODS
# ================================================================

@router.post(
    "/methods",
    response_model=PaymentMethodResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add payment method",
)
async def add_payment_method(
    data: AddPaymentMethodRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Add a payment method to user's account."""
    try:
        pm = await payment_service.add_payment_method(
            user_id=str(current_user.id),
            payment_method_id=data.payment_method_id,
            set_as_default=data.set_as_default,
            nickname=data.nickname
        )
        
        return PaymentMethodResponse(
            id=pm.stripe_payment_method_id,
            type=pm.type,
            brand=pm.details.brand,
            last4=pm.details.last4,
            exp_month=pm.details.exp_month,
            exp_year=pm.details.exp_year,
            is_default=pm.is_default,
            nickname=pm.nickname,
            created_at=pm.created_at,
        )
        
    except PaymentError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/methods",
    response_model=ListPaymentMethodsResponse,
    summary="List payment methods",
)
async def list_payment_methods(
    current_user: User = Depends(get_current_active_user)
):
    """List user's saved payment methods."""
    methods, default_id = await payment_service.list_payment_methods(
        user_id=str(current_user.id)
    )
    
    return ListPaymentMethodsResponse(
        payment_methods=[
            PaymentMethodResponse(
                id=pm.stripe_payment_method_id,
                type=pm.type,
                brand=pm.details.brand,
                last4=pm.details.last4,
                exp_month=pm.details.exp_month,
                exp_year=pm.details.exp_year,
                is_default=pm.is_default,
                nickname=pm.nickname,
                created_at=pm.created_at,
            )
            for pm in methods
        ],
        default_payment_method_id=default_id,
    )


@router.delete(
    "/methods/{payment_method_id}",
    response_model=SuccessResponse,
    summary="Remove payment method",
)
async def remove_payment_method(
    payment_method_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Remove a payment method."""
    try:
        await payment_service.remove_payment_method(
            user_id=str(current_user.id),
            payment_method_id=payment_method_id
        )
        return SuccessResponse(message="Payment method removed")
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PaymentError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put(
    "/methods/default",
    response_model=SuccessResponse,
    summary="Set default payment method",
)
async def set_default_payment_method(
    data: SetDefaultPaymentMethodRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Set default payment method."""
    try:
        await payment_service.set_default_payment_method(
            user_id=str(current_user.id),
            payment_method_id=data.payment_method_id
        )
        return SuccessResponse(message="Default payment method updated")
    except PaymentError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ================================================================
# REFUNDS
# ================================================================

@router.post(
    "/refunds",
    response_model=RefundResponse,
    summary="Create refund",
    description="Request a refund for a payment",
)
async def create_refund(
    data: CreateRefundRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Create a refund for a payment."""
    try:
        result = await payment_service.create_refund(
            payment_id=data.payment_id,
            user_id=str(current_user.id),
            amount=data.amount,
            reason=data.reason,
            note=data.note,
        )
        
        return RefundResponse(
            success=True,
            refund_id=result.get("refund_id"),
            status=result.get("status"),
            amount=result.get("amount"),
            currency=result.get("currency"),
        )
        
    except NotFoundError as e:
        return RefundResponse(success=False, error=str(e))
    except ValidationError as e:
        return RefundResponse(success=False, error=str(e))
    except PaymentError as e:
        return RefundResponse(success=False, error=str(e))


# ================================================================
# SUBSCRIPTIONS
# ================================================================

@router.get(
    "/subscriptions/plans",
    response_model=AvailablePlansResponse,
    summary="Get available plans",
)
async def get_available_plans():
    """Get available subscription plans."""
    plans = [
        SubscriptionPlanSchema(
            id="free",
            name="Free",
            tier="free",
            description="Basic features for casual travelers",
            price_monthly=0,
            price_yearly=0,
            currency="USD",
            features=[
                "Up to 3 experiences per month",
                "Basic itinerary planning",
                "Community support",
            ],
            limits={"experiences_per_month": 3, "saved_places": 10},
            popular=False,
        ),
        SubscriptionPlanSchema(
            id="basic",
            name="Basic",
            tier="basic",
            description="Perfect for regular travelers",
            price_monthly=9.99,
            price_yearly=99.99,
            currency="USD",
            features=[
                "Up to 10 experiences per month",
                "AI-powered recommendations",
                "Priority support",
                "No booking fees",
            ],
            limits={"experiences_per_month": 10, "saved_places": 50},
            popular=False,
        ),
        SubscriptionPlanSchema(
            id="premium",
            name="Premium",
            tier="premium",
            description="For the avid traveler",
            price_monthly=19.99,
            price_yearly=199.99,
            currency="USD",
            features=[
                "Unlimited experiences",
                "AI travel agent access",
                "Exclusive deals and discounts",
                "Concierge support",
                "Premium vendor access",
            ],
            limits={"experiences_per_month": -1, "saved_places": -1},
            popular=True,
        ),
    ]
    
    return AvailablePlansResponse(plans=plans)


@router.post(
    "/subscriptions",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create subscription",
)
async def create_subscription(
    data: CreateSubscriptionRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Subscribe to a plan."""
    try:
        subscription = await payment_service.create_subscription(
            user_id=str(current_user.id),
            price_id=data.price_id,
            payment_method_id=data.payment_method_id,
            trial_days=data.trial_days,
        )
        
        return SubscriptionResponse(
            subscription_id=subscription.stripe_subscription_id,
            status=subscription.status,
            plan_name=subscription.plan_name,
            plan_tier=subscription.plan_tier,
            amount=subscription.amount,
            currency=subscription.currency,
            interval=subscription.interval,
            current_period_start=subscription.current_period_start,
            current_period_end=subscription.current_period_end,
            cancel_at_period_end=subscription.cancel_at_period_end,
            trial_end=subscription.trial_end,
        )
        
    except PaymentError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/subscriptions/{subscription_id}",
    response_model=SuccessResponse,
    summary="Cancel subscription",
)
async def cancel_subscription(
    subscription_id: str,
    data: CancelSubscriptionRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Cancel a subscription."""
    try:
        await payment_service.cancel_subscription(
            user_id=str(current_user.id),
            subscription_id=subscription_id,
            immediately=data.immediately,
        )
        
        message = "Subscription cancelled"
        if not data.immediately:
            message = "Subscription will be cancelled at end of billing period"
        
        return SuccessResponse(message=message)
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PaymentError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ================================================================
# WALLET
# ================================================================

@router.get(
    "/wallet",
    response_model=WalletResponse,
    summary="Get wallet",
)
async def get_wallet(
    current_user: User = Depends(get_current_active_user)
):
    """Get user's wallet balance and details."""
    wallet = await payment_service.get_or_create_wallet(str(current_user.id))
    
    return WalletResponse(
        balance=wallet.balance,
        currency=wallet.currency,
        credits=wallet.credits,
        reserved_balance=wallet.reserved_balance,
        total_deposited=wallet.total_deposited,
        total_spent=wallet.total_spent,
    )


@router.post(
    "/wallet/deposit",
    response_model=CreatePaymentIntentResponse,
    summary="Add funds to wallet",
)
async def add_wallet_funds(
    data: AddFundsRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Add funds to wallet."""
    try:
        result = await payment_service.add_wallet_funds(
            user_id=str(current_user.id),
            amount=data.amount,
            payment_method_id=data.payment_method_id,
        )
        
        return CreatePaymentIntentResponse(
            success=True,
            payment_intent_id=result.get("payment_intent_id"),
            client_secret=result.get("client_secret"),
            status=result.get("status"),
            amount=result.get("amount"),
            currency=result.get("currency"),
        )
        
    except PaymentError as e:
        return CreatePaymentIntentResponse(success=False, error=str(e))


@router.get(
    "/wallet/transactions",
    response_model=PaginatedWalletTransactionsResponse,
    summary="Get wallet transactions",
)
async def get_wallet_transactions(
    current_user: User = Depends(get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """Get wallet transaction history."""
    transactions, total = await payment_service.get_wallet_transactions(
        user_id=str(current_user.id),
        skip=skip,
        limit=limit,
    )
    
    return PaginatedWalletTransactionsResponse(
        data=[
            WalletTransactionResponse(
                id=str(t.id),
                type=t.type,
                amount=t.amount,
                credits=t.credits,
                currency=t.currency,
                description=t.description,
                balance_after=t.balance_after,
                status=t.status,
                created_at=t.created_at,
            )
            for t in transactions
        ],
        total=total,
        skip=skip,
        limit=limit,
    )


# ================================================================
# PAYMENT HISTORY
# ================================================================

@router.get(
    "/history",
    response_model=PaginatedPaymentsResponse,
    summary="Get payment history",
)
async def get_payment_history(
    current_user: User = Depends(get_current_active_user),
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """Get user's payment history."""
    payments, total = await payment_service.get_user_payments(
        user_id=str(current_user.id),
        status=status_filter,
        skip=skip,
        limit=limit,
    )
    
    return PaginatedPaymentsResponse(
        data=[
            PaymentResponse(
                id=str(p.id),
                amount=p.amount,
                currency=p.currency,
                status=p.status.value,
                payment_type=p.payment_type,
                description=p.description,
                payment_method=PaymentMethodDetailsSchema(
                    type=p.payment_method_details.type,
                    brand=p.payment_method_details.brand,
                    last4=p.payment_method_details.last4,
                ) if p.payment_method_details else None,
                breakdown=PaymentBreakdownSchema(
                    subtotal=p.breakdown.subtotal,
                    service_fee=p.breakdown.service_fee,
                    service_fee_percentage=p.breakdown.service_fee_percentage,
                    taxes=p.breakdown.taxes,
                    tax_percentage=p.breakdown.tax_percentage,
                    discount=p.breakdown.discount,
                    discount_code=p.breakdown.discount_code,
                    total=p.breakdown.total,
                    currency=p.breakdown.currency,
                ) if p.breakdown else None,
                experience_id=p.metadata.experience_id if p.metadata else None,
                booking_id=p.metadata.booking_id if p.metadata else None,
                receipt_url=p.receipt_url,
                paid_at=p.paid_at,
                created_at=p.created_at,
                refunds=[
                    RefundSchema(
                        refund_id=r.refund_id,
                        amount=r.amount,
                        currency=r.currency,
                        reason=r.reason,
                        status=r.status,
                        created_at=r.created_at,
                        completed_at=r.completed_at,
                    )
                    for r in p.refunds
                ],
                total_refunded=p.total_refunded,
            )
            for p in payments
        ],
        total=total,
        skip=skip,
        limit=limit,
    )


# ================================================================
# VENDOR CONNECT
# ================================================================

@router.post(
    "/connect/account",
    response_model=ConnectAccountResponse,
    summary="Create vendor Connect account",
)
async def create_vendor_connect_account(
    data: CreateConnectAccountRequest,
    current_vendor: Vendor = Depends(get_current_verified_vendor)
):
    """Create Stripe Connect account for vendor payouts."""
    try:
        result = await payment_service.create_connect_account(
            vendor_id=str(current_vendor.id),
            email=current_vendor.email,
            country=data.country,
            business_type=data.business_type,
        )
        
        status_result = await payment_service.get_connect_account_status(
            vendor_id=str(current_vendor.id)
        )
        
        return ConnectAccountResponse(
            account_id=result.get("account_id"),
            details_submitted=status_result.get("details_submitted", False),
            charges_enabled=status_result.get("charges_enabled", False),
            payouts_enabled=status_result.get("payouts_enabled", False),
            onboarding_completed=status_result.get("details_submitted", False),
        )
        
    except PaymentError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/connect/account",
    response_model=ConnectAccountResponse,
    summary="Get vendor Connect account status",
)
async def get_vendor_connect_status(
    current_vendor: Vendor = Depends(get_current_verified_vendor)
):
    """Get vendor's Stripe Connect account status."""
    result = await payment_service.get_connect_account_status(
        vendor_id=str(current_vendor.id)
    )
    
    if not result.get("configured"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connect account not found. Please create one first."
        )
    
    return ConnectAccountResponse(
        account_id=result.get("account_id"),
        details_submitted=result.get("details_submitted", False),
        charges_enabled=result.get("charges_enabled", False),
        payouts_enabled=result.get("payouts_enabled", False),
        onboarding_completed=result.get("details_submitted", False),
    )


@router.get(
    "/connect/onboarding-link",
    response_model=OnboardingLinkResponse,
    summary="Get onboarding link",
)
async def get_onboarding_link(
    refresh_url: str = Query(..., description="URL to redirect if link expires"),
    return_url: str = Query(..., description="URL to redirect after onboarding"),
    current_vendor: Vendor = Depends(get_current_verified_vendor)
):
    """Get Stripe Connect onboarding link."""
    try:
        result = await payment_service.get_connect_onboarding_link(
            vendor_id=str(current_vendor.id),
            refresh_url=refresh_url,
            return_url=return_url,
        )
        
        return OnboardingLinkResponse(
            url=result["url"],
            expires_at=datetime.fromisoformat(result["expires_at"]),
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PaymentError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/connect/dashboard-link",
    response_model=DashboardLinkResponse,
    summary="Get vendor dashboard link",
)
async def get_vendor_dashboard_link(
    current_vendor: Vendor = Depends(get_current_verified_vendor)
):
    """Get link to Stripe Express Dashboard."""
    try:
        result = await payment_service.get_connect_dashboard_link(
            vendor_id=str(current_vendor.id)
        )
        
        return DashboardLinkResponse(url=result["url"])
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PaymentError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ================================================================
# WEBHOOKS
# ================================================================

@router.post(
    "/webhooks/stripe",
    response_model=WebhookEventResponse,
    summary="Stripe webhook handler",
    include_in_schema=False,  # Hide from docs
)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature")
):
    """Handle Stripe webhook events."""
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")
    
    # Get raw body
    payload = await request.body()
    
    # Verify and construct event
    success, result = stripe_client.construct_webhook_event(
        payload=payload,
        signature=stripe_signature
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=f"Invalid webhook: {result}")
    
    event = result
    
    # Handle the event
    try:
        handler_result = await payment_service.handle_webhook_event(event)
        
        return WebhookEventResponse(
            received=True,
            event_type=event.type,
            event_id=event.id,
        )
        
    except Exception as e:
        logger.error(f"Webhook handling error: {e}")
        # Still return 200 to acknowledge receipt
        return WebhookEventResponse(
            received=True,
            event_type=event.type,
            event_id=event.id,
        )


# ================================================================
# SERVICE STATUS
# ================================================================

@router.get(
    "/status",
    response_model=Dict[str, Any],
    summary="Get payment service status",
)
async def get_payment_service_status():
    """Get status of payment services."""
    return await payment_service.get_service_status()

