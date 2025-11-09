from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.utils import timezone
from decimal import Decimal
import uuid

# ==================== USER & AUTHENTICATION ====================

class User(AbstractUser):
    """Extended user model for all system users"""
    USER_TYPES = (
        ('CUSTOMER', 'Customer'),
        ('AGENT', 'Agent'),
        ('MERCHANT', 'Merchant'),
        ('ADMIN', 'Admin'),
        ('SUPER_AGENT', 'Super Agent'),
    )
    
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='CUSTOMER')
    phone_regex = RegexValidator(regex=r'^\+?254\d{9}$', message="Phone number must be in format: '+254xxxxxxxxx'")
    phone_number = models.CharField(validators=[phone_regex], max_length=13, unique=True)
    national_id = models.CharField(max_length=20, unique=True)
    date_of_birth = models.DateField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    is_active_user = models.BooleanField(default=True)
    pin_hash = models.CharField(max_length=255)  # Hashed 4-digit PIN
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'users'


class KYCDocument(models.Model):
    """Know Your Customer documents"""
    DOCUMENT_TYPES = (
        ('NATIONAL_ID', 'National ID'),
        ('PASSPORT', 'Passport'),
        ('DRIVING_LICENSE', 'Driving License'),
        ('SELFIE', 'Selfie'),
    )
    
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='kyc_documents')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    document_number = models.CharField(max_length=50, blank=True)
    document_file = models.FileField(upload_to='kyc_documents/')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_kycs')
    verified_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'kyc_documents'


# ==================== WALLET & ACCOUNTS ====================

class Wallet(models.Model):
    """Main wallet for each user"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=3, default='KES')
    is_active = models.BooleanField(default=True)
    daily_limit = models.DecimalField(max_digits=15, decimal_places=2, default=150000.00)
    monthly_limit = models.DecimalField(max_digits=15, decimal_places=2, default=500000.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'wallets'
    
    def can_transact(self, amount):
        """Check if user can perform transaction"""
        return self.is_active and self.balance >= amount


class WalletTransaction(models.Model):
    """All wallet transactions"""
    TRANSACTION_TYPES = (
        ('DEPOSIT', 'Deposit'),
        ('WITHDRAWAL', 'Withdrawal'),
        ('TRANSFER', 'Transfer'),
        ('PAYMENT', 'Payment'),
        ('AIRTIME', 'Airtime Purchase'),
        ('PAYBILL', 'PayBill'),
        ('BUY_GOODS', 'Buy Goods'),
        ('COMMISSION', 'Commission'),
        ('REVERSAL', 'Reversal'),
        ('CHARGE', 'Transaction Charge'),
    )
    
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('REVERSED', 'Reversed'),
    )
    
    transaction_id = models.CharField(max_length=20, unique=True, db_index=True)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    balance_before = models.DecimalField(max_digits=15, decimal_places=2)
    balance_after = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    description = models.TextField()
    reference_number = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'wallet_transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at', 'wallet']),
            models.Index(fields=['transaction_id']),
        ]


# ==================== AGENTS & MERCHANTS ====================

class Agent(models.Model):
    """Agent details"""
    AGENT_TYPES = (
        ('INDEPENDENT', 'Independent Agent'),
        ('AGGREGATOR', 'Aggregator'),
    )
    
    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('SUSPENDED', 'Suspended'),
        ('DEACTIVATED', 'Deactivated'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='agent_profile')
    agent_number = models.CharField(max_length=20, unique=True)
    agent_type = models.CharField(max_length=20, choices=AGENT_TYPES)
    business_name = models.CharField(max_length=200)
    business_registration = models.CharField(max_length=50)
    location = models.CharField(max_length=200)
    county = models.CharField(max_length=50)
    sub_county = models.CharField(max_length=50)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    float_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    super_agent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='sub_agents')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'agents'


class AgentFloat(models.Model):
    """Agent float management"""
    TRANSACTION_TYPES = (
        ('PURCHASE', 'Float Purchase'),
        ('DEPOSIT', 'Customer Deposit'),
        ('WITHDRAWAL', 'Customer Withdrawal'),
        ('COMMISSION', 'Commission Earned'),
        ('TRANSFER', 'Float Transfer'),
    )
    
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='float_transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    balance_before = models.DecimalField(max_digits=15, decimal_places=2)
    balance_after = models.DecimalField(max_digits=15, decimal_places=2)
    reference = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'agent_float'
        ordering = ['-created_at']


class Merchant(models.Model):
    """Merchant/Business details"""
    MERCHANT_TYPES = (
        ('PAYBILL', 'PayBill'),
        ('TILL', 'Buy Goods (Till)'),
        ('ONLINE', 'Online Merchant'),
    )
    
    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('SUSPENDED', 'Suspended'),
        ('DEACTIVATED', 'Deactivated'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='merchant_profile')
    merchant_type = models.CharField(max_length=20, choices=MERCHANT_TYPES)
    business_name = models.CharField(max_length=200)
    business_number = models.CharField(max_length=20, unique=True)  # PayBill or Till Number
    business_registration = models.CharField(max_length=50)
    category = models.CharField(max_length=100)
    location = models.CharField(max_length=200)
    county = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    settlement_account = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'merchants'


# ==================== TRANSACTIONS ====================

class SendMoney(models.Model):
    """Send money transactions"""
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('REVERSED', 'Reversed'),
    )
    
    transaction_id = models.CharField(max_length=20, unique=True, primary_key=True)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_money')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_money')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    charge = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    sender_balance_before = models.DecimalField(max_digits=15, decimal_places=2)
    sender_balance_after = models.DecimalField(max_digits=15, decimal_places=2)
    receiver_balance_before = models.DecimalField(max_digits=15, decimal_places=2)
    receiver_balance_after = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    failure_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'send_money'
        ordering = ['-created_at']


class Withdrawal(models.Model):
    """Cash withdrawal from agent"""
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('REVERSED', 'Reversed'),
    )
    
    transaction_id = models.CharField(max_length=20, unique=True, primary_key=True)
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='withdrawals')
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='customer_withdrawals')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    charge = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    customer_balance_before = models.DecimalField(max_digits=15, decimal_places=2)
    customer_balance_after = models.DecimalField(max_digits=15, decimal_places=2)
    agent_commission = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'withdrawals'
        ordering = ['-created_at']


class Deposit(models.Model):
    """Cash deposit through agent"""
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('REVERSED', 'Reversed'),
    )
    
    transaction_id = models.CharField(max_length=20, unique=True, primary_key=True)
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='deposits')
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='customer_deposits')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    customer_balance_before = models.DecimalField(max_digits=15, decimal_places=2)
    customer_balance_after = models.DecimalField(max_digits=15, decimal_places=2)
    agent_commission = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'deposits'
        ordering = ['-created_at']


class PayBill(models.Model):
    """PayBill transactions"""
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('REVERSED', 'Reversed'),
    )
    
    transaction_id = models.CharField(max_length=20, unique=True, primary_key=True)
    payer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='paybill_payments')
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='paybill_receipts')
    business_number = models.CharField(max_length=20)
    account_number = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    charge = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    payer_balance_before = models.DecimalField(max_digits=15, decimal_places=2)
    payer_balance_after = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'paybill'
        ordering = ['-created_at']


class BuyGoods(models.Model):
    """Buy Goods and Services (Till)"""
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('REVERSED', 'Reversed'),
    )
    
    transaction_id = models.CharField(max_length=20, unique=True, primary_key=True)
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='buy_goods_payments')
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='till_receipts')
    till_number = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    charge = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    buyer_balance_before = models.DecimalField(max_digits=15, decimal_places=2)
    buyer_balance_after = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'buy_goods'
        ordering = ['-created_at']


class AirtimePurchase(models.Model):
    """Airtime purchase transactions"""
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    )
    
    NETWORKS = (
        ('SAFARICOM', 'Safaricom'),
        ('AIRTEL', 'Airtel'),
        ('TELKOM', 'Telkom'),
    )
    
    transaction_id = models.CharField(max_length=20, unique=True, primary_key=True)
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='airtime_purchases')
    recipient_phone = models.CharField(max_length=13)
    network = models.CharField(max_length=20, choices=NETWORKS)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    buyer_balance_before = models.DecimalField(max_digits=15, decimal_places=2)
    buyer_balance_after = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'airtime_purchases'
        ordering = ['-created_at']


# ==================== CHARGES & COMMISSIONS ====================

class TransactionCharge(models.Model):
    """Transaction charge structure"""
    TRANSACTION_TYPES = (
        ('SEND_MONEY', 'Send Money'),
        ('WITHDRAWAL', 'Withdrawal'),
        ('PAYBILL', 'PayBill'),
        ('BUY_GOODS', 'Buy Goods'),
    )
    
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    min_amount = models.DecimalField(max_digits=15, decimal_places=2)
    max_amount = models.DecimalField(max_digits=15, decimal_places=2)
    charge = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'transaction_charges'
        ordering = ['transaction_type', 'min_amount']


class Commission(models.Model):
    """Commission earned by agents and merchants"""
    COMMISSION_TYPES = (
        ('DEPOSIT', 'Deposit Commission'),
        ('WITHDRAWAL', 'Withdrawal Commission'),
        ('MERCHANT', 'Merchant Commission'),
    )
    
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='commissions')
    commission_type = models.CharField(max_length=20, choices=COMMISSION_TYPES)
    transaction_id = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'commissions'
        ordering = ['-created_at']


# ==================== LOANS & SAVINGS ====================

class LoanProduct(models.Model):
    """Loan products available"""
    name = models.CharField(max_length=100)
    description = models.TextField()
    min_amount = models.DecimalField(max_digits=15, decimal_places=2)
    max_amount = models.DecimalField(max_digits=15, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)  # Annual percentage
    duration_days = models.IntegerField()
    facilitation_fee = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'loan_products'


class Loan(models.Model):
    """Customer loans"""
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('DISBURSED', 'Disbursed'),
        ('ACTIVE', 'Active'),
        ('PAID', 'Fully Paid'),
        ('DEFAULTED', 'Defaulted'),
        ('REJECTED', 'Rejected'),
    )
    
    loan_id = models.CharField(max_length=20, unique=True, primary_key=True)
    borrower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='loans')
    product = models.ForeignKey(LoanProduct, on_delete=models.CASCADE)
    principal_amount = models.DecimalField(max_digits=15, decimal_places=2)
    interest_amount = models.DecimalField(max_digits=15, decimal_places=2)
    facilitation_fee = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    balance = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    due_date = models.DateField()
    disbursed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'loans'
        ordering = ['-created_at']


class LoanRepayment(models.Model):
    """Loan repayment transactions"""
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='repayments')
    transaction_id = models.CharField(max_length=20, unique=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    balance_before = models.DecimalField(max_digits=15, decimal_places=2)
    balance_after = models.DecimalField(max_digits=15, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'loan_repayments'
        ordering = ['-created_at']


# ==================== NOTIFICATIONS & MESSAGES ====================

class Notification(models.Model):
    """System notifications"""
    NOTIFICATION_TYPES = (
        ('TRANSACTION', 'Transaction'),
        ('PROMOTIONAL', 'Promotional'),
        ('SYSTEM', 'System'),
        ('LOAN', 'Loan'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']


class SMSLog(models.Model):
    """SMS messages sent"""
    recipient_phone = models.CharField(max_length=13)
    message = models.TextField()
    status = models.CharField(max_length=20)
    sent_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'sms_logs'
        ordering = ['-sent_at']


# ==================== SECURITY & AUDIT ====================

class SecurityQuestion(models.Model):
    """User security questions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='security_questions')
    question = models.CharField(max_length=200)
    answer_hash = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'security_questions'


class LoginAttempt(models.Model):
    """Track login attempts for security"""
    phone_number = models.CharField(max_length=13)
    ip_address = models.GenericIPAddressField()
    success = models.BooleanField()
    failure_reason = models.CharField(max_length=100, blank=True)
    attempted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'login_attempts'
        ordering = ['-attempted_at']


class AuditLog(models.Model):
    """Comprehensive audit trail"""
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=100)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=50)
    changes = models.JSONField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'audit_logs'
        ordering = ['-created_at']


# ==================== SETTINGS & CONFIGURATION ====================

class SystemSetting(models.Model):
    """System-wide settings"""
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'system_settings'


class MaintenanceWindow(models.Model):
    """Scheduled maintenance"""
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    description = models.TextField()
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'maintenance_windows'