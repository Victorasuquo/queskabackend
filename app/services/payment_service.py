"""
Queska Backend - Payment Service
Business logic for payment processing with Stripe
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from beanie import PydanticObjectId
from loguru import logger

from app.core.config import settings
from app.core.constants import PaymentStatus, PaymentMethod
from app.core.exceptions import NotFoundError, ValidationError, PaymentError
from app.models.payment import (
    Payment,
    PaymentMethodRecord,
    StripeCustomer,
    Subscription,
    Wallet,
    WalletTransaction,
    VendorPayout,
    PaymentMethodDetails,
    PaymentBreakdown,
    PaymentMetadata,
    RefundDetails,
)
from app.models.user import User
from app.schemas.payment import (
    CreatePaymentIntentRequest,
    CheckoutLineItem,
    CreateRefundRequest,
    AddPaymentMethodRequest,
)
from integrations.payments.stripe_client import stripe_client


class PaymentService:
    """
    Payment service handling:
    - Payment intents
    - Checkout sessions
    - Payment methods
    - Refunds
    - Subscriptions
    - Wallet operations
    - Vendor payouts (Connect)
    """
    
    def __init__(self):
        self.stripe = stripe_client
    
    # ================================================================
    # CUSTOMER MANAGEMENT
    # ================================================================
    
    async def get_or_create_stripe_customer(
        self,
        user_id: str,
        email: str,
        name: Optional[str] = None,
        phone: Optional[str] = None,
        user_type: str = "user"
    ) -> StripeCustomer:
        """
        Get existing or create new Stripe customer.
        """
        # Check if customer exists
        existing = await StripeCustomer.find_one({
            "user_id": user_id,
            "is_deleted": False
        })
        
        if existing:
            return existing
        
        # Create new Stripe customer
        result = await self.stripe.create_customer(
            email=email,
            name=name,
            phone=phone,
            metadata={
                "user_id": user_id,
                "user_type": user_type,
                "platform": "queska"
            }
        )
        
        if not result.get("success"):
            raise PaymentError(f"Failed to create Stripe customer: {result.get('error')}")
        
        # Save to database
        customer = StripeCustomer(
            user_id=user_id,
            user_type=user_type,
            stripe_customer_id=result["customer_id"],
            email=email,
            name=name,
            phone=phone
        )
        await customer.insert()
        
        logger.info(f"Created Stripe customer {result['customer_id']} for user {user_id}")
        
        return customer
    
    async def get_stripe_customer(self, user_id: str) -> Optional[StripeCustomer]:
        """Get Stripe customer by user ID."""
        return await StripeCustomer.find_one({
            "user_id": user_id,
            "is_deleted": False
        })
    
    # ================================================================
    # PAYMENT INTENTS
    # ================================================================
    
    async def create_payment_intent(
        self,
        user_id: str,
        amount: float,
        currency: str = "USD",
        description: Optional[str] = None,
        receipt_email: Optional[str] = None,
        experience_id: Optional[str] = None,
        booking_id: Optional[str] = None,
        vendor_id: Optional[str] = None,
        platform_fee_percentage: float = 5.0,
        save_payment_method: bool = False,
    ) -> Dict[str, Any]:
        """
        Create a payment intent for one-time payment.
        """
        # Get or create customer
        customer = await self.get_stripe_customer(user_id)
        if not customer:
            raise ValidationError("Customer not found. Please setup payment first.")
        
        # Convert amount to cents
        amount_cents = self.stripe.convert_to_cents(amount, currency)
        
        # Build metadata
        metadata = {
            "user_id": user_id,
            "platform": "queska",
        }
        if experience_id:
            metadata["experience_id"] = experience_id
        if booking_id:
            metadata["booking_id"] = booking_id
        
        # Handle marketplace payments (with vendor)
        transfer_data = None
        application_fee = None
        
        if vendor_id:
            vendor_customer = await StripeCustomer.find_one({
                "user_id": vendor_id,
                "stripe_connect_account_id": {"$exists": True}
            })
            
            if vendor_customer and vendor_customer.stripe_connect_account_id:
                application_fee = int(amount_cents * (platform_fee_percentage / 100))
                transfer_data = {
                    "destination": vendor_customer.stripe_connect_account_id
                }
                metadata["vendor_id"] = vendor_id
        
        # Create payment intent
        result = await self.stripe.create_payment_intent(
            amount=amount_cents,
            currency=currency.lower(),
            customer_id=customer.stripe_customer_id,
            description=description,
            metadata=metadata,
            receipt_email=receipt_email,
            setup_future_usage="off_session" if save_payment_method else None,
            application_fee_amount=application_fee,
            transfer_data=transfer_data,
        )
        
        if not result.get("success"):
            raise PaymentError(f"Failed to create payment intent: {result.get('error')}")
        
        # Create payment record
        payment = Payment(
            user_id=user_id,
            user_email=receipt_email,
            stripe_payment_intent_id=result["payment_intent_id"],
            stripe_customer_id=customer.stripe_customer_id,
            amount=amount,
            currency=currency.upper(),
            status=PaymentStatus.PENDING,
            payment_method=PaymentMethod.STRIPE,
            description=description,
            metadata=PaymentMetadata(
                experience_id=experience_id,
                booking_id=booking_id,
            ),
            vendor_id=vendor_id,
            application_fee=self.stripe.convert_from_cents(application_fee, currency) if application_fee else None,
        )
        await payment.insert()
        
        logger.info(f"Created payment intent {result['payment_intent_id']} for {amount} {currency}")
        
        return {
            "success": True,
            "payment_id": str(payment.id),
            "payment_intent_id": result["payment_intent_id"],
            "client_secret": result["client_secret"],
            "status": result["status"],
            "amount": amount,
            "currency": currency.upper(),
        }
    
    async def get_payment_status(
        self,
        payment_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Get payment status."""
        payment = await Payment.find_one({
            "_id": PydanticObjectId(payment_id),
            "user_id": user_id,
            "is_deleted": False
        })
        
        if not payment:
            raise NotFoundError("Payment not found")
        
        # Sync with Stripe if pending
        if payment.status == PaymentStatus.PENDING and payment.stripe_payment_intent_id:
            result = await self.stripe.retrieve_payment_intent(payment.stripe_payment_intent_id)
            if result.get("success"):
                stripe_status = result.get("status")
                if stripe_status == "succeeded":
                    payment.mark_as_succeeded()
                    await payment.save()
                elif stripe_status in ["canceled", "requires_payment_method"]:
                    payment.status = PaymentStatus.FAILED
                    await payment.save()
        
        return {
            "payment_id": str(payment.id),
            "payment_intent_id": payment.stripe_payment_intent_id,
            "status": payment.status.value,
            "amount": payment.amount,
            "currency": payment.currency,
            "paid_at": payment.paid_at,
            "receipt_url": payment.receipt_url,
        }
    
    async def confirm_payment(
        self,
        payment_intent_id: str,
        payment_method_id: Optional[str] = None,
        return_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Confirm a payment intent."""
        result = await self.stripe.confirm_payment_intent(
            payment_intent_id=payment_intent_id,
            payment_method_id=payment_method_id,
            return_url=return_url
        )
        
        if not result.get("success"):
            raise PaymentError(f"Payment confirmation failed: {result.get('error')}")
        
        return result
    
    # ================================================================
    # CHECKOUT SESSIONS
    # ================================================================
    
    async def create_checkout_session(
        self,
        user_id: str,
        items: List[CheckoutLineItem],
        success_url: str,
        cancel_url: str,
        customer_email: Optional[str] = None,
        experience_id: Optional[str] = None,
        booking_id: Optional[str] = None,
        allow_promotion_codes: bool = True,
        collect_shipping: bool = False,
        expires_in_minutes: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create a Stripe Checkout session."""
        # Get customer
        customer = await self.get_stripe_customer(user_id)
        
        # Build line items for Stripe
        line_items = []
        total_amount = 0
        
        for item in items:
            amount_cents = self.stripe.convert_to_cents(item.amount, "usd")
            total_amount += amount_cents * item.quantity
            
            line_item = {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": item.name,
                    },
                    "unit_amount": amount_cents,
                },
                "quantity": item.quantity,
            }
            
            if item.description:
                line_item["price_data"]["product_data"]["description"] = item.description
            if item.image_url:
                line_item["price_data"]["product_data"]["images"] = [item.image_url]
            
            line_items.append(line_item)
        
        # Build metadata
        metadata = {
            "user_id": user_id,
            "platform": "queska",
        }
        if experience_id:
            metadata["experience_id"] = experience_id
        if booking_id:
            metadata["booking_id"] = booking_id
        
        # Calculate expiration
        expires_at = None
        if expires_in_minutes:
            expires_at = int((datetime.utcnow() + timedelta(minutes=expires_in_minutes)).timestamp())
        
        # Create session
        result = await self.stripe.create_checkout_session(
            line_items=line_items,
            success_url=success_url,
            cancel_url=cancel_url,
            customer_id=customer.stripe_customer_id if customer else None,
            customer_email=customer_email if not customer else None,
            metadata=metadata,
            allow_promotion_codes=allow_promotion_codes,
            shipping_address_collection={"allowed_countries": ["US", "CA", "GB", "NG", "GH", "KE", "ZA"]} if collect_shipping else None,
            expires_at=expires_at,
        )
        
        if not result.get("success"):
            raise PaymentError(f"Failed to create checkout session: {result.get('error')}")
        
        # Create payment record
        payment = Payment(
            user_id=user_id,
            user_email=customer_email,
            stripe_checkout_session_id=result["session_id"],
            stripe_customer_id=customer.stripe_customer_id if customer else None,
            amount=self.stripe.convert_from_cents(total_amount, "usd"),
            currency="USD",
            status=PaymentStatus.PENDING,
            payment_method=PaymentMethod.STRIPE,
            payment_type="checkout",
            metadata=PaymentMetadata(
                experience_id=experience_id,
                booking_id=booking_id,
                item_descriptions=[item.name for item in items],
                item_count=len(items),
            ),
        )
        await payment.insert()
        
        return {
            "success": True,
            "payment_id": str(payment.id),
            "session_id": result["session_id"],
            "checkout_url": result["url"],
            "expires_at": result.get("expires_at"),
        }
    
    async def get_checkout_session_status(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """Get checkout session status."""
        result = await self.stripe.retrieve_checkout_session(session_id)
        
        if not result.get("success"):
            raise NotFoundError("Checkout session not found")
        
        return {
            "session_id": result["session_id"],
            "status": result["status"],
            "payment_status": result["payment_status"],
            "customer_email": result.get("customer"),
            "amount_total": self.stripe.convert_from_cents(result.get("amount_total", 0), result.get("currency", "usd")),
            "currency": result.get("currency", "").upper(),
        }
    
    # ================================================================
    # REFUNDS
    # ================================================================
    
    async def create_refund(
        self,
        payment_id: str,
        user_id: str,
        amount: Optional[float] = None,
        reason: Optional[str] = None,
        note: Optional[str] = None,
        is_admin: bool = False
    ) -> Dict[str, Any]:
        """Create a refund for a payment."""
        # Get payment
        query = {"_id": PydanticObjectId(payment_id), "is_deleted": False}
        if not is_admin:
            query["user_id"] = user_id
        
        payment = await Payment.find_one(query)
        
        if not payment:
            raise NotFoundError("Payment not found")
        
        if payment.status not in [PaymentStatus.COMPLETED, PaymentStatus.PARTIALLY_REFUNDED]:
            raise ValidationError("Payment cannot be refunded")
        
        # Calculate refund amount
        refund_amount = amount if amount else payment.amount - payment.total_refunded
        
        if refund_amount <= 0:
            raise ValidationError("Invalid refund amount")
        
        if refund_amount > (payment.amount - payment.total_refunded):
            raise ValidationError("Refund amount exceeds available balance")
        
        # Create Stripe refund
        amount_cents = self.stripe.convert_to_cents(refund_amount, payment.currency) if amount else None
        
        result = await self.stripe.create_refund(
            payment_intent_id=payment.stripe_payment_intent_id,
            amount=amount_cents,
            reason=reason,
            metadata={
                "payment_id": str(payment.id),
                "user_id": user_id,
                "note": note or "",
            }
        )
        
        if not result.get("success"):
            raise PaymentError(f"Refund failed: {result.get('error')}")
        
        # Update payment record
        refund_details = RefundDetails(
            refund_id=result["refund_id"],
            amount=refund_amount,
            currency=payment.currency,
            reason=reason,
            status=result["status"],
        )
        payment.add_refund(refund_details)
        await payment.save()
        
        logger.info(f"Created refund {result['refund_id']} for payment {payment_id}")
        
        return {
            "success": True,
            "refund_id": result["refund_id"],
            "status": result["status"],
            "amount": refund_amount,
            "currency": payment.currency,
        }
    
    # ================================================================
    # PAYMENT METHODS
    # ================================================================
    
    async def add_payment_method(
        self,
        user_id: str,
        payment_method_id: str,
        set_as_default: bool = False,
        nickname: Optional[str] = None
    ) -> PaymentMethodRecord:
        """Add a payment method to user's account."""
        customer = await self.get_stripe_customer(user_id)
        if not customer:
            raise ValidationError("Customer not found")
        
        # Attach to Stripe customer
        result = await self.stripe.attach_payment_method(
            payment_method_id=payment_method_id,
            customer_id=customer.stripe_customer_id
        )
        
        if not result.get("success"):
            raise PaymentError(f"Failed to add payment method: {result.get('error')}")
        
        pm = result["payment_method"]
        
        # Set as default if requested
        if set_as_default:
            await self.stripe.set_default_payment_method(
                customer_id=customer.stripe_customer_id,
                payment_method_id=payment_method_id
            )
            
            # Update other methods to not be default
            await PaymentMethodRecord.find({
                "user_id": user_id,
                "is_default": True,
                "is_deleted": False
            }).update({"$set": {"is_default": False}})
        
        # Build details
        details = PaymentMethodDetails(
            type=pm.type,
            brand=pm.card.brand if pm.type == "card" else None,
            last4=pm.card.last4 if pm.type == "card" else None,
            exp_month=pm.card.exp_month if pm.type == "card" else None,
            exp_year=pm.card.exp_year if pm.type == "card" else None,
            country=pm.card.country if pm.type == "card" else None,
            funding=pm.card.funding if pm.type == "card" else None,
        )
        
        # Save record
        pm_record = PaymentMethodRecord(
            user_id=user_id,
            stripe_customer_id=customer.stripe_customer_id,
            stripe_payment_method_id=payment_method_id,
            type=pm.type,
            details=details,
            nickname=nickname,
            is_default=set_as_default,
        )
        await pm_record.insert()
        
        return pm_record
    
    async def list_payment_methods(
        self,
        user_id: str
    ) -> Tuple[List[PaymentMethodRecord], Optional[str]]:
        """List user's payment methods."""
        methods = await PaymentMethodRecord.find({
            "user_id": user_id,
            "is_active": True,
            "is_deleted": False
        }).sort("-is_default", "-created_at").to_list()
        
        default_id = None
        for m in methods:
            if m.is_default:
                default_id = m.stripe_payment_method_id
                break
        
        return methods, default_id
    
    async def remove_payment_method(
        self,
        user_id: str,
        payment_method_id: str
    ) -> bool:
        """Remove a payment method."""
        record = await PaymentMethodRecord.find_one({
            "user_id": user_id,
            "stripe_payment_method_id": payment_method_id,
            "is_deleted": False
        })
        
        if not record:
            raise NotFoundError("Payment method not found")
        
        # Detach from Stripe
        result = await self.stripe.detach_payment_method(payment_method_id)
        
        if not result.get("success"):
            raise PaymentError(f"Failed to remove payment method: {result.get('error')}")
        
        # Soft delete record
        await record.soft_delete()
        
        return True
    
    async def set_default_payment_method(
        self,
        user_id: str,
        payment_method_id: str
    ) -> bool:
        """Set default payment method."""
        customer = await self.get_stripe_customer(user_id)
        if not customer:
            raise ValidationError("Customer not found")
        
        # Update Stripe
        result = await self.stripe.set_default_payment_method(
            customer_id=customer.stripe_customer_id,
            payment_method_id=payment_method_id
        )
        
        if not result.get("success"):
            raise PaymentError(f"Failed to set default: {result.get('error')}")
        
        # Update database
        await PaymentMethodRecord.find({
            "user_id": user_id,
            "is_deleted": False
        }).update({"$set": {"is_default": False}})
        
        await PaymentMethodRecord.find_one({
            "user_id": user_id,
            "stripe_payment_method_id": payment_method_id,
            "is_deleted": False
        }).update({"$set": {"is_default": True}})
        
        return True
    
    # ================================================================
    # SUBSCRIPTIONS
    # ================================================================
    
    async def create_subscription(
        self,
        user_id: str,
        price_id: str,
        payment_method_id: Optional[str] = None,
        trial_days: Optional[int] = None
    ) -> Subscription:
        """Create a subscription for a user."""
        customer = await self.get_stripe_customer(user_id)
        if not customer:
            raise ValidationError("Customer not found")
        
        result = await self.stripe.create_subscription(
            customer_id=customer.stripe_customer_id,
            price_id=price_id,
            payment_method_id=payment_method_id,
            trial_period_days=trial_days,
            metadata={"user_id": user_id}
        )
        
        if not result.get("success"):
            raise PaymentError(f"Subscription failed: {result.get('error')}")
        
        sub = result["subscription"]
        
        # Create subscription record
        subscription = Subscription(
            user_id=user_id,
            stripe_customer_id=customer.stripe_customer_id,
            stripe_subscription_id=sub.id,
            stripe_price_id=price_id,
            plan_name=sub.items.data[0].price.product if sub.items.data else "Unknown",
            plan_tier="premium",  # Determine from price
            amount=self.stripe.convert_from_cents(sub.items.data[0].price.unit_amount, sub.currency),
            currency=sub.currency.upper(),
            interval=sub.items.data[0].price.recurring.interval,
            status=sub.status,
            current_period_start=datetime.fromtimestamp(sub.current_period_start),
            current_period_end=datetime.fromtimestamp(sub.current_period_end),
            trial_end=datetime.fromtimestamp(sub.trial_end) if sub.trial_end else None,
        )
        await subscription.insert()
        
        return subscription
    
    async def cancel_subscription(
        self,
        user_id: str,
        subscription_id: str,
        immediately: bool = False
    ) -> Dict[str, Any]:
        """Cancel a subscription."""
        subscription = await Subscription.find_one({
            "user_id": user_id,
            "stripe_subscription_id": subscription_id,
            "is_deleted": False
        })
        
        if not subscription:
            raise NotFoundError("Subscription not found")
        
        result = await self.stripe.cancel_subscription(
            subscription_id=subscription_id,
            immediately=immediately
        )
        
        if not result.get("success"):
            raise PaymentError(f"Cancellation failed: {result.get('error')}")
        
        subscription.status = result["status"]
        subscription.cancel_at_period_end = result.get("cancel_at_period_end", False)
        subscription.canceled_at = datetime.utcnow()
        await subscription.save()
        
        return result
    
    # ================================================================
    # WALLET
    # ================================================================
    
    async def get_or_create_wallet(self, user_id: str) -> Wallet:
        """Get or create user wallet."""
        wallet = await Wallet.find_one({
            "user_id": user_id,
            "is_deleted": False
        })
        
        if not wallet:
            wallet = Wallet(user_id=user_id)
            await wallet.insert()
        
        return wallet
    
    async def add_wallet_funds(
        self,
        user_id: str,
        amount: float,
        payment_method_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add funds to wallet."""
        # Create payment intent for wallet deposit
        result = await self.create_payment_intent(
            user_id=user_id,
            amount=amount,
            description="Wallet deposit",
        )
        
        if not result.get("success"):
            raise PaymentError("Failed to create wallet deposit")
        
        return result
    
    async def process_wallet_deposit(
        self,
        user_id: str,
        amount: float,
        payment_id: str
    ) -> Wallet:
        """Process completed wallet deposit."""
        wallet = await self.get_or_create_wallet(user_id)
        wallet.add_balance(amount)
        await wallet.save()
        
        # Create transaction
        transaction = WalletTransaction(
            wallet_id=str(wallet.id),
            user_id=user_id,
            type="deposit",
            amount=amount,
            currency=wallet.currency,
            balance_after=wallet.balance,
            description="Wallet deposit",
            payment_id=payment_id,
        )
        await transaction.insert()
        
        return wallet
    
    async def get_wallet_transactions(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[WalletTransaction], int]:
        """Get wallet transactions."""
        query = {"user_id": user_id}
        
        total = await WalletTransaction.find(query).count()
        transactions = await WalletTransaction.find(query)\
            .sort("-created_at")\
            .skip(skip)\
            .limit(limit)\
            .to_list()
        
        return transactions, total
    
    # ================================================================
    # VENDOR CONNECT
    # ================================================================
    
    async def create_connect_account(
        self,
        vendor_id: str,
        email: str,
        country: str = "US",
        business_type: str = "individual"
    ) -> Dict[str, Any]:
        """Create Stripe Connect account for vendor."""
        # Check if already exists
        customer = await StripeCustomer.find_one({
            "user_id": vendor_id,
            "stripe_connect_account_id": {"$exists": True}
        })
        
        if customer and customer.stripe_connect_account_id:
            return {
                "success": True,
                "account_id": customer.stripe_connect_account_id,
                "already_exists": True
            }
        
        # Create Connect account
        result = await self.stripe.create_connect_account(
            email=email,
            country=country,
            type="express",
            business_type=business_type,
            metadata={"vendor_id": vendor_id}
        )
        
        if not result.get("success"):
            raise PaymentError(f"Failed to create Connect account: {result.get('error')}")
        
        # Get or create customer record
        if not customer:
            customer = await self.get_or_create_stripe_customer(
                user_id=vendor_id,
                email=email,
                user_type="vendor"
            )
        
        # Update with Connect info
        customer.stripe_connect_account_id = result["account_id"]
        customer.connect_account_type = "express"
        await customer.save()
        
        return {
            "success": True,
            "account_id": result["account_id"],
        }
    
    async def get_connect_onboarding_link(
        self,
        vendor_id: str,
        refresh_url: str,
        return_url: str
    ) -> Dict[str, Any]:
        """Get onboarding link for vendor."""
        customer = await StripeCustomer.find_one({
            "user_id": vendor_id,
            "stripe_connect_account_id": {"$exists": True}
        })
        
        if not customer or not customer.stripe_connect_account_id:
            raise NotFoundError("Connect account not found")
        
        result = await self.stripe.create_account_link(
            account_id=customer.stripe_connect_account_id,
            refresh_url=refresh_url,
            return_url=return_url
        )
        
        if not result.get("success"):
            raise PaymentError(f"Failed to create onboarding link: {result.get('error')}")
        
        return result
    
    async def get_connect_dashboard_link(
        self,
        vendor_id: str
    ) -> Dict[str, Any]:
        """Get Express dashboard link for vendor."""
        customer = await StripeCustomer.find_one({
            "user_id": vendor_id,
            "stripe_connect_account_id": {"$exists": True}
        })
        
        if not customer or not customer.stripe_connect_account_id:
            raise NotFoundError("Connect account not found")
        
        result = await self.stripe.create_login_link(customer.stripe_connect_account_id)
        
        if not result.get("success"):
            raise PaymentError(f"Failed to create dashboard link: {result.get('error')}")
        
        return result
    
    async def get_connect_account_status(
        self,
        vendor_id: str
    ) -> Dict[str, Any]:
        """Get Connect account status."""
        customer = await StripeCustomer.find_one({
            "user_id": vendor_id,
            "stripe_connect_account_id": {"$exists": True}
        })
        
        if not customer or not customer.stripe_connect_account_id:
            return {
                "configured": False,
                "account_id": None,
            }
        
        result = await self.stripe.retrieve_connect_account(customer.stripe_connect_account_id)
        
        if result.get("success"):
            # Update local record
            customer.connect_details_submitted = result.get("details_submitted", False)
            customer.connect_charges_enabled = result.get("charges_enabled", False)
            customer.connect_payouts_enabled = result.get("payouts_enabled", False)
            customer.connect_onboarding_completed = result.get("details_submitted", False)
            await customer.save()
        
        return {
            "configured": True,
            "account_id": customer.stripe_connect_account_id,
            "details_submitted": result.get("details_submitted", False),
            "charges_enabled": result.get("charges_enabled", False),
            "payouts_enabled": result.get("payouts_enabled", False),
        }
    
    # ================================================================
    # PAYMENT HISTORY
    # ================================================================
    
    async def get_user_payments(
        self,
        user_id: str,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[Payment], int]:
        """Get user's payment history."""
        query = {"user_id": user_id, "is_deleted": False}
        
        if status:
            query["status"] = status
        
        total = await Payment.find(query).count()
        payments = await Payment.find(query)\
            .sort("-created_at")\
            .skip(skip)\
            .limit(limit)\
            .to_list()
        
        return payments, total
    
    # ================================================================
    # WEBHOOK HANDLING
    # ================================================================
    
    async def handle_webhook_event(self, event: Any) -> Dict[str, Any]:
        """Handle Stripe webhook event."""
        event_type = event.type
        data = event.data.object
        
        logger.info(f"Processing webhook: {event_type}")
        
        handlers = {
            "payment_intent.succeeded": self._handle_payment_succeeded,
            "payment_intent.payment_failed": self._handle_payment_failed,
            "checkout.session.completed": self._handle_checkout_completed,
            "customer.subscription.created": self._handle_subscription_created,
            "customer.subscription.updated": self._handle_subscription_updated,
            "customer.subscription.deleted": self._handle_subscription_deleted,
            "invoice.payment_succeeded": self._handle_invoice_paid,
            "invoice.payment_failed": self._handle_invoice_failed,
            "charge.refunded": self._handle_charge_refunded,
            "account.updated": self._handle_connect_account_updated,
        }
        
        handler = handlers.get(event_type)
        if handler:
            return await handler(data)
        
        return {"handled": False, "event_type": event_type}
    
    async def _handle_payment_succeeded(self, data: Any) -> Dict[str, Any]:
        """Handle successful payment."""
        payment = await Payment.find_one({
            "stripe_payment_intent_id": data.id,
            "is_deleted": False
        })
        
        if payment:
            payment.mark_as_succeeded(charge_id=data.latest_charge)
            payment.receipt_url = getattr(data, "receipt_url", None)
            await payment.save()
            
            # Handle wallet deposit
            if payment.payment_type == "wallet_deposit":
                await self.process_wallet_deposit(
                    user_id=payment.user_id,
                    amount=payment.amount,
                    payment_id=str(payment.id)
                )
        
        return {"handled": True, "payment_id": str(payment.id) if payment else None}
    
    async def _handle_payment_failed(self, data: Any) -> Dict[str, Any]:
        """Handle failed payment."""
        payment = await Payment.find_one({
            "stripe_payment_intent_id": data.id,
            "is_deleted": False
        })
        
        if payment:
            error = data.last_payment_error
            payment.mark_as_failed(
                code=error.code if error else None,
                message=error.message if error else "Payment failed"
            )
            await payment.save()
        
        return {"handled": True, "payment_id": str(payment.id) if payment else None}
    
    async def _handle_checkout_completed(self, data: Any) -> Dict[str, Any]:
        """Handle completed checkout session."""
        payment = await Payment.find_one({
            "stripe_checkout_session_id": data.id,
            "is_deleted": False
        })
        
        if payment:
            payment.status = PaymentStatus.COMPLETED
            payment.paid_at = datetime.utcnow()
            payment.stripe_payment_intent_id = data.payment_intent
            await payment.save()
        
        return {"handled": True, "payment_id": str(payment.id) if payment else None}
    
    async def _handle_subscription_created(self, data: Any) -> Dict[str, Any]:
        """Handle new subscription."""
        # Subscription already created in create_subscription method
        return {"handled": True, "subscription_id": data.id}
    
    async def _handle_subscription_updated(self, data: Any) -> Dict[str, Any]:
        """Handle subscription update."""
        subscription = await Subscription.find_one({
            "stripe_subscription_id": data.id,
            "is_deleted": False
        })
        
        if subscription:
            subscription.status = data.status
            subscription.current_period_start = datetime.fromtimestamp(data.current_period_start)
            subscription.current_period_end = datetime.fromtimestamp(data.current_period_end)
            subscription.cancel_at_period_end = data.cancel_at_period_end
            await subscription.save()
        
        return {"handled": True, "subscription_id": data.id}
    
    async def _handle_subscription_deleted(self, data: Any) -> Dict[str, Any]:
        """Handle subscription cancellation."""
        subscription = await Subscription.find_one({
            "stripe_subscription_id": data.id,
            "is_deleted": False
        })
        
        if subscription:
            subscription.status = "canceled"
            subscription.canceled_at = datetime.utcnow()
            await subscription.save()
        
        return {"handled": True, "subscription_id": data.id}
    
    async def _handle_invoice_paid(self, data: Any) -> Dict[str, Any]:
        """Handle paid invoice."""
        return {"handled": True, "invoice_id": data.id}
    
    async def _handle_invoice_failed(self, data: Any) -> Dict[str, Any]:
        """Handle failed invoice."""
        return {"handled": True, "invoice_id": data.id}
    
    async def _handle_charge_refunded(self, data: Any) -> Dict[str, Any]:
        """Handle refund event."""
        return {"handled": True, "charge_id": data.id}
    
    async def _handle_connect_account_updated(self, data: Any) -> Dict[str, Any]:
        """Handle Connect account update."""
        customer = await StripeCustomer.find_one({
            "stripe_connect_account_id": data.id
        })
        
        if customer:
            customer.connect_details_submitted = data.details_submitted
            customer.connect_charges_enabled = data.charges_enabled
            customer.connect_payouts_enabled = data.payouts_enabled
            await customer.save()
        
        return {"handled": True, "account_id": data.id}
    
    # ================================================================
    # UTILITIES
    # ================================================================
    
    def get_publishable_key(self) -> str:
        """Get Stripe publishable key for frontend."""
        return self.stripe.get_publishable_key()
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get payment service status."""
        balance = await self.stripe.get_balance()
        
        return {
            "stripe_configured": self.stripe.is_configured(),
            "balance": balance if balance.get("success") else None,
        }


# Global service instance
payment_service = PaymentService()

