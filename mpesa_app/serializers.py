from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from decimal import Decimal
from .models import (
    User, KYCDocument, Wallet, WalletTransaction, Agent, AgentFloat,
    Merchant, SendMoney, Withdrawal, Deposit, PayBill, BuyGoods,
    AirtimePurchase, TransactionCharge, Commission, LoanProduct, Loan,
    LoanRepayment, Notification, SMSLog, SecurityQuestion, LoginAttempt,
    AuditLog, SystemSetting, MaintenanceWindow
)


# ==================== USER & AUTHENTICATION ====================

class UserRegistrationSerializer(serializers.ModelSerializer):
    """User registration serializer"""
    password = serializers.CharField(write_only=True, required=True)
    pin = serializers.CharField(write_only=True, required=True, max_length=4, min_length=4)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'phone_number', 
                  'national_id', 'date_of_birth', 'user_type', 'password', 'pin']
        extra_kwargs = {
            'password': {'write_only': True},
            'pin': {'write_only': True}
        }
    
    def create(self, validated_data):
        pin = validated_data.pop('pin')
        password = validated_data.pop('password')
        
        user = User.objects.create(
            **validated_data,
            password=make_password(password),
            pin_hash=make_password(pin)
        )
        
        # Create wallet for user
        Wallet.objects.create(user=user)
        
        return user


class UserSerializer(serializers.ModelSerializer):
    """User detail serializer"""
    wallet_balance = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 
                  'phone_number', 'national_id', 'date_of_birth', 'user_type',
                  'is_verified', 'is_active_user', 'wallet_balance', 'created_at']
        read_only_fields = ['id', 'is_verified', 'created_at']
    
    def get_wallet_balance(self, obj):
        try:
            return str(obj.wallet.balance)
        except:
            return "0.00"


class UserUpdateSerializer(serializers.ModelSerializer):
    """User profile update"""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'date_of_birth']


class ChangePINSerializer(serializers.Serializer):
    """Change PIN serializer"""
    old_pin = serializers.CharField(required=True, max_length=4, min_length=4)
    new_pin = serializers.CharField(required=True, max_length=4, min_length=4)
    confirm_pin = serializers.CharField(required=True, max_length=4, min_length=4)
    
    def validate(self, data):
        if data['new_pin'] != data['confirm_pin']:
            raise serializers.ValidationError("New PINs do not match")
        return data


class LoginSerializer(serializers.Serializer):
    """Login serializer"""
    phone_number = serializers.CharField(required=True)
    pin = serializers.CharField(required=True, max_length=4, min_length=4)


# ==================== KYC ====================

class KYCDocumentSerializer(serializers.ModelSerializer):
    """KYC document serializer"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    verified_by_name = serializers.CharField(source='verified_by.get_full_name', read_only=True)
    
    class Meta:
        model = KYCDocument
        fields = ['id', 'user', 'user_name', 'document_type', 'document_number',
                  'document_file', 'status', 'verified_by', 'verified_by_name',
                  'verified_at', 'rejection_reason', 'created_at']
        read_only_fields = ['id', 'status', 'verified_by', 'verified_at', 'created_at']


class KYCVerificationSerializer(serializers.Serializer):
    """KYC verification by admin"""
    status = serializers.ChoiceField(choices=['APPROVED', 'REJECTED'])
    rejection_reason = serializers.CharField(required=False, allow_blank=True)


# ==================== WALLET & ACCOUNTS ====================

class WalletSerializer(serializers.ModelSerializer):
    """Wallet serializer"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)
    
    class Meta:
        model = Wallet
        fields = ['id', 'user', 'user_name', 'phone_number', 'balance', 'currency',
                  'is_active', 'daily_limit', 'monthly_limit', 'created_at', 'updated_at']
        read_only_fields = ['id', 'balance', 'created_at', 'updated_at']


class WalletTransactionSerializer(serializers.ModelSerializer):
    """Wallet transaction serializer"""
    user_name = serializers.CharField(source='wallet.user.get_full_name', read_only=True)
    
    class Meta:
        model = WalletTransaction
        fields = ['id', 'transaction_id', 'wallet', 'user_name', 'transaction_type',
                  'amount', 'balance_before', 'balance_after', 'status', 'description',
                  'reference_number', 'created_at', 'completed_at']
        read_only_fields = ['id', 'transaction_id', 'balance_before', 'balance_after',
                           'created_at', 'completed_at']


class MiniStatementSerializer(serializers.Serializer):
    """Mini statement request"""
    limit = serializers.IntegerField(default=10, min_value=1, max_value=50)


# ==================== AGENTS & MERCHANTS ====================

class AgentSerializer(serializers.ModelSerializer):
    """Agent serializer"""
    user_details = UserSerializer(source='user', read_only=True)
    super_agent_name = serializers.CharField(source='super_agent.business_name', read_only=True)
    
    class Meta:
        model = Agent
        fields = ['id', 'user', 'user_details', 'agent_number', 'agent_type',
                  'business_name', 'business_registration', 'location', 'county',
                  'sub_county', 'latitude', 'longitude', 'status', 'float_balance',
                  'commission_rate', 'super_agent', 'super_agent_name', 'created_at']
        read_only_fields = ['id', 'agent_number', 'float_balance', 'created_at']


class AgentFloatSerializer(serializers.ModelSerializer):
    """Agent float transaction serializer"""
    agent_name = serializers.CharField(source='agent.business_name', read_only=True)
    
    class Meta:
        model = AgentFloat
        fields = ['id', 'agent', 'agent_name', 'transaction_type', 'amount',
                  'balance_before', 'balance_after', 'reference', 'created_at']
        read_only_fields = ['id', 'balance_before', 'balance_after', 'created_at']


class AgentLocationSerializer(serializers.Serializer):
    """Find nearby agents"""
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    radius_km = serializers.IntegerField(default=5, min_value=1, max_value=50)


class MerchantSerializer(serializers.ModelSerializer):
    """Merchant serializer"""
    user_details = UserSerializer(source='user', read_only=True)
    
    class Meta:
        model = Merchant
        fields = ['id', 'user', 'user_details', 'merchant_type', 'business_name',
                  'business_number', 'business_registration', 'category', 'location',
                  'county', 'status', 'commission_rate', 'settlement_account', 'created_at']
        read_only_fields = ['id', 'created_at']


# ==================== TRANSACTIONS ====================

class SendMoneySerializer(serializers.ModelSerializer):
    """Send money serializer"""
    receiver_phone = serializers.CharField(write_only=True)
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    receiver_name = serializers.CharField(source='receiver.get_full_name', read_only=True)
    
    class Meta:
        model = SendMoney
        fields = ['transaction_id', 'sender', 'sender_name', 'receiver', 'receiver_name',
                  'receiver_phone', 'amount', 'charge', 'total_amount', 'status',
                  'failure_reason', 'created_at', 'completed_at']
        read_only_fields = ['transaction_id', 'sender', 'receiver', 'charge', 'total_amount',
                           'status', 'created_at', 'completed_at']


class WithdrawalSerializer(serializers.ModelSerializer):
    """Withdrawal serializer"""
    agent_number = serializers.CharField(write_only=True)
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    agent_name = serializers.CharField(source='agent.business_name', read_only=True)
    
    class Meta:
        model = Withdrawal
        fields = ['transaction_id', 'customer', 'customer_name', 'agent', 'agent_name',
                  'agent_number', 'amount', 'charge', 'total_amount', 'agent_commission',
                  'status', 'created_at', 'completed_at']
        read_only_fields = ['transaction_id', 'customer', 'agent', 'charge', 'total_amount',
                           'agent_commission', 'status', 'created_at', 'completed_at']


class DepositSerializer(serializers.ModelSerializer):
    """Deposit serializer"""
    customer_phone = serializers.CharField(write_only=True)
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    agent_name = serializers.CharField(source='agent.business_name', read_only=True)
    
    class Meta:
        model = Deposit
        fields = ['transaction_id', 'customer', 'customer_name', 'customer_phone',
                  'agent', 'agent_name', 'amount', 'agent_commission', 'status',
                  'created_at', 'completed_at']
        read_only_fields = ['transaction_id', 'agent', 'agent_commission', 'status',
                           'created_at', 'completed_at']


class PayBillSerializer(serializers.ModelSerializer):
    """PayBill serializer"""
    payer_name = serializers.CharField(source='payer.get_full_name', read_only=True)
    merchant_name = serializers.CharField(source='merchant.business_name', read_only=True)
    
    class Meta:
        model = PayBill
        fields = ['transaction_id', 'payer', 'payer_name', 'merchant', 'merchant_name',
                  'business_number', 'account_number', 'amount', 'charge', 'total_amount',
                  'status', 'created_at', 'completed_at']
        read_only_fields = ['transaction_id', 'payer', 'merchant', 'charge', 'total_amount',
                           'status', 'created_at', 'completed_at']


class BuyGoodsSerializer(serializers.ModelSerializer):
    """Buy goods serializer"""
    buyer_name = serializers.CharField(source='buyer.get_full_name', read_only=True)
    merchant_name = serializers.CharField(source='merchant.business_name', read_only=True)
    
    class Meta:
        model = BuyGoods
        fields = ['transaction_id', 'buyer', 'buyer_name', 'merchant', 'merchant_name',
                  'till_number', 'amount', 'charge', 'total_amount', 'status',
                  'created_at', 'completed_at']
        read_only_fields = ['transaction_id', 'buyer', 'merchant', 'charge', 'total_amount',
                           'status', 'created_at', 'completed_at']


class AirtimePurchaseSerializer(serializers.ModelSerializer):
    """Airtime purchase serializer"""
    buyer_name = serializers.CharField(source='buyer.get_full_name', read_only=True)
    
    class Meta:
        model = AirtimePurchase
        fields = ['transaction_id', 'buyer', 'buyer_name', 'recipient_phone',
                  'network', 'amount', 'status', 'created_at', 'completed_at']
        read_only_fields = ['transaction_id', 'buyer', 'status', 'created_at', 'completed_at']


# ==================== CHARGES & COMMISSIONS ====================

class TransactionChargeSerializer(serializers.ModelSerializer):
    """Transaction charge serializer"""
    class Meta:
        model = TransactionCharge
        fields = ['id', 'transaction_type', 'min_amount', 'max_amount', 'charge',
                  'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class CommissionSerializer(serializers.ModelSerializer):
    """Commission serializer"""
    recipient_name = serializers.CharField(source='recipient.get_full_name', read_only=True)
    
    class Meta:
        model = Commission
        fields = ['id', 'recipient', 'recipient_name', 'commission_type',
                  'transaction_id', 'amount', 'created_at']
        read_only_fields = ['id', 'created_at']


# ==================== LOANS & SAVINGS ====================

class LoanProductSerializer(serializers.ModelSerializer):
    """Loan product serializer"""
    class Meta:
        model = LoanProduct
        fields = ['id', 'name', 'description', 'min_amount', 'max_amount',
                  'interest_rate', 'duration_days', 'facilitation_fee',
                  'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class LoanApplicationSerializer(serializers.ModelSerializer):
    """Loan application serializer"""
    borrower_name = serializers.CharField(source='borrower.get_full_name', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = Loan
        fields = ['loan_id', 'borrower', 'borrower_name', 'product', 'product_name',
                  'principal_amount', 'interest_amount', 'facilitation_fee',
                  'total_amount', 'amount_paid', 'balance', 'status', 'due_date',
                  'disbursed_at', 'created_at']
        read_only_fields = ['loan_id', 'borrower', 'interest_amount', 'facilitation_fee',
                           'total_amount', 'amount_paid', 'balance', 'status',
                           'disbursed_at', 'created_at']


class LoanRepaymentSerializer(serializers.ModelSerializer):
    """Loan repayment serializer"""
    loan_id = serializers.CharField(source='loan.loan_id', read_only=True)
    
    class Meta:
        model = LoanRepayment
        fields = ['id', 'loan', 'loan_id', 'transaction_id', 'amount',
                  'balance_before', 'balance_after', 'created_at']
        read_only_fields = ['id', 'transaction_id', 'balance_before',
                           'balance_after', 'created_at']


# ==================== NOTIFICATIONS & MESSAGES ====================

class NotificationSerializer(serializers.ModelSerializer):
    """Notification serializer"""
    class Meta:
        model = Notification
        fields = ['id', 'user', 'notification_type', 'title', 'message',
                  'is_read', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']


class SMSLogSerializer(serializers.ModelSerializer):
    """SMS log serializer"""
    class Meta:
        model = SMSLog
        fields = ['id', 'recipient_phone', 'message', 'status', 'sent_at']
        read_only_fields = ['id', 'sent_at']


# ==================== SECURITY & AUDIT ====================

class SecurityQuestionSerializer(serializers.ModelSerializer):
    """Security question serializer"""
    answer = serializers.CharField(write_only=True)
    
    class Meta:
        model = SecurityQuestion
        fields = ['id', 'user', 'question', 'answer', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']
        extra_kwargs = {'answer': {'write_only': True}}
    
    def create(self, validated_data):
        answer = validated_data.pop('answer')
        validated_data['answer_hash'] = make_password(answer)
        return super().create(validated_data)


class LoginAttemptSerializer(serializers.ModelSerializer):
    """Login attempt serializer"""
    class Meta:
        model = LoginAttempt
        fields = ['id', 'phone_number', 'ip_address', 'success',
                  'failure_reason', 'attempted_at']
        read_only_fields = ['id', 'attempted_at']


class AuditLogSerializer(serializers.ModelSerializer):
    """Audit log serializer"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = ['id', 'user', 'user_name', 'action', 'model_name',
                  'object_id', 'changes', 'ip_address', 'created_at']
        read_only_fields = ['id', 'created_at']


# ==================== SETTINGS & CONFIGURATION ====================

class SystemSettingSerializer(serializers.ModelSerializer):
    """System setting serializer"""
    class Meta:
        model = SystemSetting
        fields = ['id', 'key', 'value', 'description', 'updated_at']
        read_only_fields = ['id', 'updated_at']


class MaintenanceWindowSerializer(serializers.ModelSerializer):
    """Maintenance window serializer"""
    class Meta:
        model = MaintenanceWindow
        fields = ['id', 'start_time', 'end_time', 'description',
                  'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


# ==================== DASHBOARD & REPORTS ====================

class DashboardStatsSerializer(serializers.Serializer):
    """Dashboard statistics"""
    total_users = serializers.IntegerField()
    total_transactions = serializers.IntegerField()
    total_volume = serializers.DecimalField(max_digits=15, decimal_places=2)
    active_agents = serializers.IntegerField()
    active_merchants = serializers.IntegerField()
    pending_kyc = serializers.IntegerField()


class TransactionSummarySerializer(serializers.Serializer):
    """Transaction summary"""
    date = serializers.DateField()
    transaction_count = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    transaction_type = serializers.CharField()