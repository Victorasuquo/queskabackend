"""
Queska Backend - Payment Models
Payment, transaction, and wallet document models
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from beanie import Document, Indexed, PydanticObjectId
from pydantic import BaseModel, Field

from app.core.constants import PaymentStatus, PaymentMethod, Currency
from app.models.base import BaseDocument


# === Embedded Models ===

class PaymentMethodDetails(BaseModel):
    """Payment method details"""
    type: str  # card, bank_transfer, wallet
    brand: Optional[str] = None  # visa, mastercard, etc.
    last4: Optional[str] = None
    exp_month: Optional[int] = None
    exp_year: Optional[int] = None
    bank_name: Optional[str] = None
    country: Optional[str] = None
    funding: Optional[str] = None  # credit, debit, prepaid


class RefundDetails(BaseModel):
    """Refund information"""
    refund_id: str
    amount: float
    currency: str
    reason: Optional[str] = None
    status: str  # pending, succeeded, failed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


class PaymentBreakdown(BaseModel):
    """Payment amount breakdown"""
    subtotal: float = 0.0
    service_fee: float = 0.0
    service_fee_percentage: float = 5.0
    taxes: float = 0.0
    tax_percentage: float = 0.0
    discount: float = 0.0
    discount_code: Optional[str] = None
    total: float = 0.0
    currency: str = "USD"
    
    # For marketplace payments
    platform_fee: float = 0.0
    vendor_amount: float = 0.0


class PaymentMetadata(BaseModel):
    """Payment metadata"""
    experience_id: Optional[str] = None
    experience_name: Optional[str] = None
    booking_id: Optional[str] = None
    order_id: Optional[str] = None
    subscription_id: Optional[str] = None
    item_count: Optional[int] = None
    item_descriptions: List[str] = Field(default_factory=list)
    customer_note: Optional[str] = None


# === Main Documents ===

class Payment(BaseDocument):
    """
    Payment transaction record.
    """
    # User info
    user_id: Indexed(str)
    user_email: Optional[str] = None
    
    # Stripe IDs
    stripe_payment_intent_id: Optional[str] = None
    stripe_checkout_session_id: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    stripe_charge_id: Optional[str] = None
    stripe_invoice_id: Optional[str] = None
    
    # Payment details
    amount: float
    currency: str = "USD"
    status: PaymentStatus = PaymentStatus.PENDING
    payment_method: PaymentMethod = PaymentMethod.STRIPE
    payment_method_details: Optional[PaymentMethodDetails] = None
    
    # Breakdown
    breakdown: Optional[PaymentBreakdown] = None
    
    # Type
    payment_type: str = "one_time"  # one_time, subscription, deposit, balance
    
    # Description
    description: Optional[str] = None
    
    # Associated records
    metadata: PaymentMetadata = Field(default_factory=PaymentMetadata)
    
    # For marketplace/Connect
    vendor_id: Optional[str] = None
    vendor_stripe_account_id: Optional[str] = None
    transfer_id: Optional[str] = None
    application_fee: Optional[float] = None
    
    # Refunds
    refunds: List[RefundDetails] = Field(default_factory=list)
    total_refunded: float = 0.0
    
    # Timestamps
    paid_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    refunded_at: Optional[datetime] = None
    
    # Error info
    failure_code: Optional[str] = None
    failure_message: Optional[str] = None
    
    # Receipt
    receipt_url: Optional[str] = None
    receipt_email: Optional[str] = None
    receipt_sent_at: Optional[datetime] = None
    
    # Internal reference
    internal_reference: Optional[str] = None
    
    class Settings:
        name = "payments"
        indexes = [
            "user_id",
            "stripe_payment_intent_id",
            "stripe_checkout_session_id",
            "status",
            "payment_type",
            "vendor_id",
            [("created_at", -1)],
        ]
    
    def mark_as_succeeded(self, charge_id: Optional[str] = None) -> None:
        """Mark payment as successful."""
        self.status = PaymentStatus.COMPLETED
        self.paid_at = datetime.utcnow()
        if charge_id:
            self.stripe_charge_id = charge_id
        self.update_timestamp()
    
    def mark_as_failed(self, code: Optional[str] = None, message: Optional[str] = None) -> None:
        """Mark payment as failed."""
        self.status = PaymentStatus.FAILED
        self.failed_at = datetime.utcnow()
        self.failure_code = code
        self.failure_message = message
        self.update_timestamp()
    
    def add_refund(self, refund: RefundDetails) -> None:
        """Add a refund to the payment."""
        self.refunds.append(refund)
        self.total_refunded += refund.amount
        
        if self.total_refunded >= self.amount:
            self.status = PaymentStatus.REFUNDED
        else:
            self.status = PaymentStatus.PARTIALLY_REFUNDED
        
        self.refunded_at = datetime.utcnow()
        self.update_timestamp()


class PaymentMethodRecord(BaseDocument):
    """
    Saved payment method for a user.
    """
    user_id: Indexed(str)
    stripe_customer_id: str
    stripe_payment_method_id: str
    
    # Details
    type: str = "card"  # card, bank_account
    details: PaymentMethodDetails
    
    # User-facing
    nickname: Optional[str] = None
    
    # Status
    is_default: bool = False
    is_active: bool = True
    
    # Last used
    last_used_at: Optional[datetime] = None
    use_count: int = 0
    
    class Settings:
        name = "payment_methods"
        indexes = [
            "user_id",
            "stripe_customer_id",
            "stripe_payment_method_id",
            "is_default",
        ]


class StripeCustomer(BaseDocument):
    """
    Stripe customer mapping for users.
    """
    user_id: Indexed(str, unique=True)
    user_type: str = "user"  # user, vendor, agent
    
    stripe_customer_id: Indexed(str, unique=True)
    email: str
    name: Optional[str] = None
    phone: Optional[str] = None
    
    # Default payment method
    default_payment_method_id: Optional[str] = None
    
    # For vendors (Connect accounts)
    stripe_connect_account_id: Optional[str] = None
    connect_account_type: Optional[str] = None  # express, standard, custom
    connect_details_submitted: bool = False
    connect_charges_enabled: bool = False
    connect_payouts_enabled: bool = False
    connect_onboarding_completed: bool = False
    
    class Settings:
        name = "stripe_customers"
        indexes = [
            "user_id",
            "stripe_customer_id",
            "stripe_connect_account_id",
        ]


class Subscription(BaseDocument):
    """
    User subscription record.
    """
    user_id: Indexed(str)
    stripe_customer_id: str
    stripe_subscription_id: Indexed(str)
    stripe_price_id: str
    stripe_product_id: Optional[str] = None
    
    # Plan details
    plan_name: str
    plan_tier: str  # free, basic, premium, enterprise
    
    # Pricing
    amount: float
    currency: str = "USD"
    interval: str = "month"  # month, year
    
    # Status
    status: str = "active"  # active, past_due, canceled, unpaid, trialing
    
    # Dates
    current_period_start: datetime
    current_period_end: datetime
    trial_start: Optional[datetime] = None
    trial_end: Optional[datetime] = None
    canceled_at: Optional[datetime] = None
    cancel_at_period_end: bool = False
    
    # Features
    features: List[str] = Field(default_factory=list)
    limits: Dict[str, Any] = Field(default_factory=dict)
    
    class Settings:
        name = "subscriptions"
        indexes = [
            "user_id",
            "stripe_subscription_id",
            "status",
            "plan_tier",
        ]


class Wallet(BaseDocument):
    """
    User wallet for credits, rewards, and balance.
    """
    user_id: Indexed(str, unique=True)
    
    # Balance
    balance: float = 0.0
    currency: str = "USD"
    
    # Credits
    credits: int = 0  # Platform credits/points
    
    # Reserved (for pending transactions)
    reserved_balance: float = 0.0
    reserved_credits: int = 0
    
    # Lifetime totals
    total_deposited: float = 0.0
    total_spent: float = 0.0
    total_refunded: float = 0.0
    total_earned: float = 0.0  # From referrals, rewards
    
    # Last activity
    last_transaction_at: Optional[datetime] = None
    
    class Settings:
        name = "wallets"
        indexes = ["user_id"]
    
    def add_balance(self, amount: float) -> None:
        """Add to balance."""
        self.balance += amount
        self.total_deposited += amount
        self.last_transaction_at = datetime.utcnow()
        self.update_timestamp()
    
    def deduct_balance(self, amount: float) -> bool:
        """Deduct from balance if sufficient."""
        if self.balance >= amount:
            self.balance -= amount
            self.total_spent += amount
            self.last_transaction_at = datetime.utcnow()
            self.update_timestamp()
            return True
        return False
    
    def add_credits(self, credits: int) -> None:
        """Add credits."""
        self.credits += credits
        self.last_transaction_at = datetime.utcnow()
        self.update_timestamp()


class WalletTransaction(BaseDocument):
    """
    Wallet transaction history.
    """
    wallet_id: Indexed(str)
    user_id: Indexed(str)
    
    # Transaction type
    type: str  # deposit, withdrawal, payment, refund, reward, credit_purchase, credit_use
    
    # Amounts
    amount: float = 0.0
    credits: int = 0
    currency: str = "USD"
    
    # Balance after transaction
    balance_after: float = 0.0
    credits_after: int = 0
    
    # Description
    description: str
    
    # Related records
    payment_id: Optional[str] = None
    experience_id: Optional[str] = None
    booking_id: Optional[str] = None
    
    # Status
    status: str = "completed"  # pending, completed, failed, reversed
    
    class Settings:
        name = "wallet_transactions"
        indexes = [
            "wallet_id",
            "user_id",
            "type",
            [("created_at", -1)],
        ]


class VendorPayout(BaseDocument):
    """
    Vendor payout record (for marketplace).
    """
    vendor_id: Indexed(str)
    stripe_connect_account_id: str
    
    # Payout details
    amount: float
    currency: str = "USD"
    status: str = "pending"  # pending, in_transit, paid, failed, canceled
    
    # Stripe IDs
    stripe_payout_id: Optional[str] = None
    stripe_transfer_id: Optional[str] = None
    
    # Arrival
    arrival_date: Optional[datetime] = None
    
    # Bank info
    destination_type: str = "bank_account"  # bank_account, card
    destination_last4: Optional[str] = None
    destination_bank_name: Optional[str] = None
    
    # Period
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    
    # Earnings breakdown
    gross_amount: float = 0.0
    platform_fees: float = 0.0
    stripe_fees: float = 0.0
    net_amount: float = 0.0
    
    # Associated payments
    payment_ids: List[str] = Field(default_factory=list)
    transaction_count: int = 0
    
    # Error info
    failure_code: Optional[str] = None
    failure_message: Optional[str] = None
    
    class Settings:
        name = "vendor_payouts"
        indexes = [
            "vendor_id",
            "stripe_connect_account_id",
            "status",
            [("created_at", -1)],
        ]

