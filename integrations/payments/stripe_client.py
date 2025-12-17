"""
Queska Backend - Stripe Integration
Comprehensive Stripe payment processing client
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import stripe
from loguru import logger

from app.core.config import settings


class StripeClient:
    """
    Stripe Payment Processing Client
    
    Provides:
    - Customer management
    - Payment methods (cards, bank transfers)
    - Payment intents (one-time payments)
    - Checkout sessions
    - Subscriptions
    - Refunds
    - Payouts (for vendors)
    - Connect (marketplace payments)
    - Webhook handling
    """
    
    def __init__(self):
        self.api_key = settings.STRIPE_SECRET_KEY
        self.publishable_key = settings.STRIPE_PUBLISHABLE_KEY
        self.webhook_secret = settings.STRIPE_WEBHOOK_SECRET
        self.default_currency = settings.STRIPE_CURRENCY.lower()
        
        # Initialize Stripe
        stripe.api_key = self.api_key
        stripe.api_version = "2023-10-16"
    
    def is_configured(self) -> bool:
        return bool(self.api_key and self.publishable_key)
    
    # ================================================================
    # CUSTOMERS
    # ================================================================
    
    async def create_customer(
        self,
        email: str,
        name: Optional[str] = None,
        phone: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Create a Stripe customer.
        
        Args:
            email: Customer email
            name: Customer name
            phone: Customer phone
            metadata: Additional metadata (user_id, etc.)
            
        Returns:
            Stripe customer object
        """
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                phone=phone,
                metadata=metadata or {}
            )
            
            logger.info(f"Created Stripe customer: {customer.id}")
            
            return {
                "success": True,
                "customer_id": customer.id,
                "email": customer.email,
                "customer": customer
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe customer creation error: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_customer(self, customer_id: str) -> Dict[str, Any]:
        """Retrieve a customer by ID."""
        try:
            customer = stripe.Customer.retrieve(customer_id)
            return {"success": True, "customer": customer}
        except stripe.error.StripeError as e:
            logger.error(f"Stripe get customer error: {e}")
            return {"success": False, "error": str(e)}
    
    async def update_customer(
        self,
        customer_id: str,
        email: Optional[str] = None,
        name: Optional[str] = None,
        phone: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Update a customer."""
        try:
            update_data = {}
            if email:
                update_data["email"] = email
            if name:
                update_data["name"] = name
            if phone:
                update_data["phone"] = phone
            if metadata:
                update_data["metadata"] = metadata
            
            customer = stripe.Customer.modify(customer_id, **update_data)
            return {"success": True, "customer": customer}
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe update customer error: {e}")
            return {"success": False, "error": str(e)}
    
    async def delete_customer(self, customer_id: str) -> Dict[str, Any]:
        """Delete a customer."""
        try:
            deleted = stripe.Customer.delete(customer_id)
            return {"success": True, "deleted": deleted.deleted}
        except stripe.error.StripeError as e:
            logger.error(f"Stripe delete customer error: {e}")
            return {"success": False, "error": str(e)}
    
    # ================================================================
    # PAYMENT METHODS
    # ================================================================
    
    async def attach_payment_method(
        self,
        payment_method_id: str,
        customer_id: str
    ) -> Dict[str, Any]:
        """Attach a payment method to a customer."""
        try:
            payment_method = stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer_id
            )
            
            return {
                "success": True,
                "payment_method_id": payment_method.id,
                "payment_method": payment_method
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe attach payment method error: {e}")
            return {"success": False, "error": str(e)}
    
    async def list_payment_methods(
        self,
        customer_id: str,
        type: str = "card"
    ) -> Dict[str, Any]:
        """List payment methods for a customer."""
        try:
            payment_methods = stripe.PaymentMethod.list(
                customer=customer_id,
                type=type
            )
            
            return {
                "success": True,
                "payment_methods": [
                    self._parse_payment_method(pm)
                    for pm in payment_methods.data
                ]
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe list payment methods error: {e}")
            return {"success": False, "error": str(e)}
    
    async def detach_payment_method(
        self,
        payment_method_id: str
    ) -> Dict[str, Any]:
        """Detach a payment method from a customer."""
        try:
            payment_method = stripe.PaymentMethod.detach(payment_method_id)
            return {"success": True, "payment_method_id": payment_method.id}
        except stripe.error.StripeError as e:
            logger.error(f"Stripe detach payment method error: {e}")
            return {"success": False, "error": str(e)}
    
    async def set_default_payment_method(
        self,
        customer_id: str,
        payment_method_id: str
    ) -> Dict[str, Any]:
        """Set default payment method for a customer."""
        try:
            customer = stripe.Customer.modify(
                customer_id,
                invoice_settings={
                    "default_payment_method": payment_method_id
                }
            )
            return {"success": True, "customer": customer}
        except stripe.error.StripeError as e:
            logger.error(f"Stripe set default payment method error: {e}")
            return {"success": False, "error": str(e)}
    
    def _parse_payment_method(self, pm: stripe.PaymentMethod) -> Dict[str, Any]:
        """Parse payment method into simplified format."""
        data = {
            "id": pm.id,
            "type": pm.type,
            "created": datetime.fromtimestamp(pm.created).isoformat(),
        }
        
        if pm.type == "card":
            card = pm.card
            data["card"] = {
                "brand": card.brand,
                "last4": card.last4,
                "exp_month": card.exp_month,
                "exp_year": card.exp_year,
                "funding": card.funding,
                "country": card.country,
            }
        
        return data
    
    # ================================================================
    # PAYMENT INTENTS (One-time Payments)
    # ================================================================
    
    async def create_payment_intent(
        self,
        amount: int,  # Amount in cents
        currency: str = None,
        customer_id: Optional[str] = None,
        payment_method_id: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        receipt_email: Optional[str] = None,
        capture_method: str = "automatic",  # automatic, manual
        confirm: bool = False,
        return_url: Optional[str] = None,
        setup_future_usage: Optional[str] = None,  # off_session, on_session
        application_fee_amount: Optional[int] = None,
        transfer_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a payment intent for a one-time payment.
        
        Args:
            amount: Amount in smallest currency unit (cents for USD)
            currency: Currency code (default from settings)
            customer_id: Stripe customer ID
            payment_method_id: Attached payment method ID
            description: Payment description
            metadata: Custom metadata (order_id, experience_id, etc.)
            receipt_email: Email for receipt
            capture_method: automatic or manual (hold funds)
            confirm: Confirm immediately
            return_url: Return URL for redirect-based payments
            setup_future_usage: Save for future use
            application_fee_amount: Platform fee (for Connect)
            transfer_data: Transfer destination (for Connect)
            
        Returns:
            Payment intent with client_secret
        """
        try:
            params = {
                "amount": amount,
                "currency": currency or self.default_currency,
                "capture_method": capture_method,
                "automatic_payment_methods": {"enabled": True},
            }
            
            if customer_id:
                params["customer"] = customer_id
            if payment_method_id:
                params["payment_method"] = payment_method_id
            if description:
                params["description"] = description
            if metadata:
                params["metadata"] = metadata
            if receipt_email:
                params["receipt_email"] = receipt_email
            if confirm:
                params["confirm"] = True
                if return_url:
                    params["return_url"] = return_url
            if setup_future_usage:
                params["setup_future_usage"] = setup_future_usage
            if application_fee_amount:
                params["application_fee_amount"] = application_fee_amount
            if transfer_data:
                params["transfer_data"] = transfer_data
            
            intent = stripe.PaymentIntent.create(**params)
            
            logger.info(f"Created payment intent: {intent.id} for amount {amount}")
            
            return {
                "success": True,
                "payment_intent_id": intent.id,
                "client_secret": intent.client_secret,
                "status": intent.status,
                "amount": intent.amount,
                "currency": intent.currency,
                "payment_intent": intent
            }
            
        except stripe.error.CardError as e:
            logger.error(f"Stripe card error: {e}")
            return {
                "success": False,
                "error": e.user_message,
                "code": e.code,
                "decline_code": e.error.decline_code if e.error else None
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe payment intent error: {e}")
            return {"success": False, "error": str(e)}
    
    async def retrieve_payment_intent(
        self,
        payment_intent_id: str
    ) -> Dict[str, Any]:
        """Retrieve a payment intent."""
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            return {
                "success": True,
                "payment_intent_id": intent.id,
                "status": intent.status,
                "amount": intent.amount,
                "currency": intent.currency,
                "payment_method": intent.payment_method,
                "payment_intent": intent
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe retrieve payment intent error: {e}")
            return {"success": False, "error": str(e)}
    
    async def confirm_payment_intent(
        self,
        payment_intent_id: str,
        payment_method_id: Optional[str] = None,
        return_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Confirm a payment intent."""
        try:
            params = {}
            if payment_method_id:
                params["payment_method"] = payment_method_id
            if return_url:
                params["return_url"] = return_url
            
            intent = stripe.PaymentIntent.confirm(payment_intent_id, **params)
            
            return {
                "success": True,
                "payment_intent_id": intent.id,
                "status": intent.status,
                "payment_intent": intent
            }
            
        except stripe.error.CardError as e:
            logger.error(f"Stripe card error on confirm: {e}")
            return {
                "success": False,
                "error": e.user_message,
                "code": e.code
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe confirm payment intent error: {e}")
            return {"success": False, "error": str(e)}
    
    async def capture_payment_intent(
        self,
        payment_intent_id: str,
        amount_to_capture: Optional[int] = None
    ) -> Dict[str, Any]:
        """Capture a previously authorized payment."""
        try:
            params = {}
            if amount_to_capture:
                params["amount_to_capture"] = amount_to_capture
            
            intent = stripe.PaymentIntent.capture(payment_intent_id, **params)
            
            return {
                "success": True,
                "payment_intent_id": intent.id,
                "status": intent.status,
                "amount_captured": intent.amount_received
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe capture payment intent error: {e}")
            return {"success": False, "error": str(e)}
    
    async def cancel_payment_intent(
        self,
        payment_intent_id: str,
        cancellation_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Cancel a payment intent."""
        try:
            params = {}
            if cancellation_reason:
                params["cancellation_reason"] = cancellation_reason
            
            intent = stripe.PaymentIntent.cancel(payment_intent_id, **params)
            
            return {
                "success": True,
                "payment_intent_id": intent.id,
                "status": intent.status
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe cancel payment intent error: {e}")
            return {"success": False, "error": str(e)}
    
    # ================================================================
    # CHECKOUT SESSIONS
    # ================================================================
    
    async def create_checkout_session(
        self,
        line_items: List[Dict[str, Any]],
        success_url: str,
        cancel_url: str,
        mode: str = "payment",  # payment, subscription, setup
        customer_id: Optional[str] = None,
        customer_email: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        allow_promotion_codes: bool = True,
        billing_address_collection: str = "auto",
        shipping_address_collection: Optional[Dict[str, Any]] = None,
        payment_method_types: Optional[List[str]] = None,
        expires_at: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Create a Stripe Checkout session.
        
        Args:
            line_items: Items to purchase
                [{"price_data": {"currency": "usd", "product_data": {"name": "..."}, "unit_amount": 1000}, "quantity": 1}]
            success_url: Redirect URL on success
            cancel_url: Redirect URL on cancel
            mode: Session mode
            customer_id: Existing customer ID
            customer_email: Customer email (if no customer_id)
            metadata: Custom metadata
            allow_promotion_codes: Allow discount codes
            billing_address_collection: auto or required
            shipping_address_collection: Shipping options
            payment_method_types: Limit payment methods
            expires_at: Session expiration timestamp
            
        Returns:
            Checkout session with URL
        """
        try:
            params = {
                "line_items": line_items,
                "mode": mode,
                "success_url": success_url,
                "cancel_url": cancel_url,
                "allow_promotion_codes": allow_promotion_codes,
                "billing_address_collection": billing_address_collection,
            }
            
            if customer_id:
                params["customer"] = customer_id
            elif customer_email:
                params["customer_email"] = customer_email
            
            if metadata:
                params["metadata"] = metadata
            if shipping_address_collection:
                params["shipping_address_collection"] = shipping_address_collection
            if payment_method_types:
                params["payment_method_types"] = payment_method_types
            if expires_at:
                params["expires_at"] = expires_at
            
            session = stripe.checkout.Session.create(**params)
            
            logger.info(f"Created checkout session: {session.id}")
            
            return {
                "success": True,
                "session_id": session.id,
                "url": session.url,
                "expires_at": datetime.fromtimestamp(session.expires_at).isoformat() if session.expires_at else None,
                "session": session
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe checkout session error: {e}")
            return {"success": False, "error": str(e)}
    
    async def retrieve_checkout_session(
        self,
        session_id: str,
        expand: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Retrieve a checkout session."""
        try:
            params = {}
            if expand:
                params["expand"] = expand
            
            session = stripe.checkout.Session.retrieve(session_id, **params)
            
            return {
                "success": True,
                "session_id": session.id,
                "status": session.status,
                "payment_status": session.payment_status,
                "customer": session.customer,
                "amount_total": session.amount_total,
                "currency": session.currency,
                "payment_intent": session.payment_intent,
                "session": session
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe retrieve checkout session error: {e}")
            return {"success": False, "error": str(e)}
    
    async def expire_checkout_session(self, session_id: str) -> Dict[str, Any]:
        """Expire a checkout session."""
        try:
            session = stripe.checkout.Session.expire(session_id)
            return {"success": True, "status": session.status}
        except stripe.error.StripeError as e:
            logger.error(f"Stripe expire checkout session error: {e}")
            return {"success": False, "error": str(e)}
    
    # ================================================================
    # REFUNDS
    # ================================================================
    
    async def create_refund(
        self,
        payment_intent_id: Optional[str] = None,
        charge_id: Optional[str] = None,
        amount: Optional[int] = None,  # Partial refund amount
        reason: Optional[str] = None,  # duplicate, fraudulent, requested_by_customer
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Create a refund.
        
        Args:
            payment_intent_id: Payment intent to refund
            charge_id: Or charge ID to refund
            amount: Amount to refund (partial) or None for full
            reason: Refund reason
            metadata: Custom metadata
            
        Returns:
            Refund object
        """
        try:
            params = {}
            if payment_intent_id:
                params["payment_intent"] = payment_intent_id
            elif charge_id:
                params["charge"] = charge_id
            else:
                return {"success": False, "error": "payment_intent_id or charge_id required"}
            
            if amount:
                params["amount"] = amount
            if reason:
                params["reason"] = reason
            if metadata:
                params["metadata"] = metadata
            
            refund = stripe.Refund.create(**params)
            
            logger.info(f"Created refund: {refund.id}")
            
            return {
                "success": True,
                "refund_id": refund.id,
                "status": refund.status,
                "amount": refund.amount,
                "currency": refund.currency,
                "refund": refund
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe refund error: {e}")
            return {"success": False, "error": str(e)}
    
    async def retrieve_refund(self, refund_id: str) -> Dict[str, Any]:
        """Retrieve a refund."""
        try:
            refund = stripe.Refund.retrieve(refund_id)
            return {"success": True, "refund": refund}
        except stripe.error.StripeError as e:
            logger.error(f"Stripe retrieve refund error: {e}")
            return {"success": False, "error": str(e)}
    
    async def list_refunds(
        self,
        payment_intent_id: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """List refunds."""
        try:
            params = {"limit": limit}
            if payment_intent_id:
                params["payment_intent"] = payment_intent_id
            
            refunds = stripe.Refund.list(**params)
            return {"success": True, "refunds": refunds.data}
        except stripe.error.StripeError as e:
            logger.error(f"Stripe list refunds error: {e}")
            return {"success": False, "error": str(e)}
    
    # ================================================================
    # SUBSCRIPTIONS
    # ================================================================
    
    async def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        payment_method_id: Optional[str] = None,
        trial_period_days: Optional[int] = None,
        metadata: Optional[Dict[str, str]] = None,
        cancel_at_period_end: bool = False
    ) -> Dict[str, Any]:
        """Create a subscription."""
        try:
            params = {
                "customer": customer_id,
                "items": [{"price": price_id}],
            }
            
            if payment_method_id:
                params["default_payment_method"] = payment_method_id
            if trial_period_days:
                params["trial_period_days"] = trial_period_days
            if metadata:
                params["metadata"] = metadata
            if cancel_at_period_end:
                params["cancel_at_period_end"] = cancel_at_period_end
            
            subscription = stripe.Subscription.create(**params)
            
            logger.info(f"Created subscription: {subscription.id}")
            
            return {
                "success": True,
                "subscription_id": subscription.id,
                "status": subscription.status,
                "current_period_start": datetime.fromtimestamp(subscription.current_period_start).isoformat(),
                "current_period_end": datetime.fromtimestamp(subscription.current_period_end).isoformat(),
                "subscription": subscription
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe subscription error: {e}")
            return {"success": False, "error": str(e)}
    
    async def retrieve_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Retrieve a subscription."""
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            return {"success": True, "subscription": subscription}
        except stripe.error.StripeError as e:
            logger.error(f"Stripe retrieve subscription error: {e}")
            return {"success": False, "error": str(e)}
    
    async def update_subscription(
        self,
        subscription_id: str,
        price_id: Optional[str] = None,
        cancel_at_period_end: Optional[bool] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Update a subscription."""
        try:
            params = {}
            if price_id:
                params["items"] = [{"price": price_id}]
            if cancel_at_period_end is not None:
                params["cancel_at_period_end"] = cancel_at_period_end
            if metadata:
                params["metadata"] = metadata
            
            subscription = stripe.Subscription.modify(subscription_id, **params)
            return {"success": True, "subscription": subscription}
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe update subscription error: {e}")
            return {"success": False, "error": str(e)}
    
    async def cancel_subscription(
        self,
        subscription_id: str,
        immediately: bool = False
    ) -> Dict[str, Any]:
        """Cancel a subscription."""
        try:
            if immediately:
                subscription = stripe.Subscription.delete(subscription_id)
            else:
                subscription = stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
            
            return {
                "success": True,
                "subscription_id": subscription.id,
                "status": subscription.status,
                "cancel_at_period_end": subscription.cancel_at_period_end
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe cancel subscription error: {e}")
            return {"success": False, "error": str(e)}
    
    # ================================================================
    # PRODUCTS & PRICES
    # ================================================================
    
    async def create_product(
        self,
        name: str,
        description: Optional[str] = None,
        images: Optional[List[str]] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Create a product."""
        try:
            params = {"name": name}
            if description:
                params["description"] = description
            if images:
                params["images"] = images
            if metadata:
                params["metadata"] = metadata
            
            product = stripe.Product.create(**params)
            return {"success": True, "product_id": product.id, "product": product}
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe create product error: {e}")
            return {"success": False, "error": str(e)}
    
    async def create_price(
        self,
        product_id: str,
        unit_amount: int,
        currency: str = None,
        recurring: Optional[Dict[str, Any]] = None,  # {"interval": "month"}
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Create a price for a product."""
        try:
            params = {
                "product": product_id,
                "unit_amount": unit_amount,
                "currency": currency or self.default_currency,
            }
            if recurring:
                params["recurring"] = recurring
            if metadata:
                params["metadata"] = metadata
            
            price = stripe.Price.create(**params)
            return {"success": True, "price_id": price.id, "price": price}
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe create price error: {e}")
            return {"success": False, "error": str(e)}
    
    # ================================================================
    # STRIPE CONNECT (Marketplace)
    # ================================================================
    
    async def create_connect_account(
        self,
        email: str,
        country: str = "US",
        type: str = "express",  # express, standard, custom
        business_type: str = "individual",
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Create a Stripe Connect account for vendors.
        
        Args:
            email: Vendor email
            country: Country code
            type: Account type (express recommended)
            business_type: individual or company
            metadata: vendor_id, etc.
            
        Returns:
            Connect account
        """
        try:
            params = {
                "type": type,
                "email": email,
                "country": country,
                "capabilities": {
                    "card_payments": {"requested": True},
                    "transfers": {"requested": True},
                },
            }
            
            if type == "custom":
                params["business_type"] = business_type
            
            if metadata:
                params["metadata"] = metadata
            
            account = stripe.Account.create(**params)
            
            logger.info(f"Created Connect account: {account.id}")
            
            return {
                "success": True,
                "account_id": account.id,
                "account": account
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe Connect account error: {e}")
            return {"success": False, "error": str(e)}
    
    async def create_account_link(
        self,
        account_id: str,
        refresh_url: str,
        return_url: str,
        type: str = "account_onboarding"
    ) -> Dict[str, Any]:
        """Create an account link for onboarding."""
        try:
            link = stripe.AccountLink.create(
                account=account_id,
                refresh_url=refresh_url,
                return_url=return_url,
                type=type
            )
            
            return {
                "success": True,
                "url": link.url,
                "expires_at": datetime.fromtimestamp(link.expires_at).isoformat()
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe account link error: {e}")
            return {"success": False, "error": str(e)}
    
    async def create_login_link(self, account_id: str) -> Dict[str, Any]:
        """Create a login link for Express dashboard."""
        try:
            link = stripe.Account.create_login_link(account_id)
            return {"success": True, "url": link.url}
        except stripe.error.StripeError as e:
            logger.error(f"Stripe login link error: {e}")
            return {"success": False, "error": str(e)}
    
    async def retrieve_connect_account(self, account_id: str) -> Dict[str, Any]:
        """Retrieve a Connect account."""
        try:
            account = stripe.Account.retrieve(account_id)
            return {
                "success": True,
                "account_id": account.id,
                "details_submitted": account.details_submitted,
                "payouts_enabled": account.payouts_enabled,
                "charges_enabled": account.charges_enabled,
                "account": account
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe retrieve Connect account error: {e}")
            return {"success": False, "error": str(e)}
    
    async def create_transfer(
        self,
        amount: int,
        destination_account_id: str,
        currency: str = None,
        source_transaction: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Transfer funds to a connected account.
        
        Args:
            amount: Amount in cents
            destination_account_id: Connect account ID
            currency: Currency code
            source_transaction: Charge to transfer from
            description: Transfer description
            metadata: Custom metadata
            
        Returns:
            Transfer object
        """
        try:
            params = {
                "amount": amount,
                "currency": currency or self.default_currency,
                "destination": destination_account_id,
            }
            
            if source_transaction:
                params["source_transaction"] = source_transaction
            if description:
                params["description"] = description
            if metadata:
                params["metadata"] = metadata
            
            transfer = stripe.Transfer.create(**params)
            
            logger.info(f"Created transfer: {transfer.id} to {destination_account_id}")
            
            return {
                "success": True,
                "transfer_id": transfer.id,
                "amount": transfer.amount,
                "transfer": transfer
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe transfer error: {e}")
            return {"success": False, "error": str(e)}
    
    # ================================================================
    # WEBHOOKS
    # ================================================================
    
    def construct_webhook_event(
        self,
        payload: bytes,
        signature: str
    ) -> Tuple[bool, Any]:
        """
        Construct and verify a webhook event.
        
        Args:
            payload: Raw request body
            signature: Stripe-Signature header
            
        Returns:
            Tuple of (success, event_or_error)
        """
        try:
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                self.webhook_secret
            )
            return True, event
            
        except ValueError as e:
            logger.error(f"Invalid webhook payload: {e}")
            return False, str(e)
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid webhook signature: {e}")
            return False, str(e)
    
    # ================================================================
    # UTILITY METHODS
    # ================================================================
    
    def convert_to_cents(self, amount: float, currency: str = "usd") -> int:
        """Convert amount to cents (smallest currency unit)."""
        # Most currencies use 100 subunits
        zero_decimal_currencies = ["JPY", "KRW", "VND"]
        
        if currency.upper() in zero_decimal_currencies:
            return int(amount)
        return int(amount * 100)
    
    def convert_from_cents(self, amount: int, currency: str = "usd") -> float:
        """Convert cents to decimal amount."""
        zero_decimal_currencies = ["JPY", "KRW", "VND"]
        
        if currency.upper() in zero_decimal_currencies:
            return float(amount)
        return amount / 100.0
    
    def get_publishable_key(self) -> str:
        """Get the publishable key for frontend."""
        return self.publishable_key
    
    async def get_balance(self) -> Dict[str, Any]:
        """Get Stripe account balance."""
        try:
            balance = stripe.Balance.retrieve()
            return {
                "success": True,
                "available": [
                    {"amount": b.amount, "currency": b.currency}
                    for b in balance.available
                ],
                "pending": [
                    {"amount": b.amount, "currency": b.currency}
                    for b in balance.pending
                ]
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe balance error: {e}")
            return {"success": False, "error": str(e)}


# Global client instance
stripe_client = StripeClient()

