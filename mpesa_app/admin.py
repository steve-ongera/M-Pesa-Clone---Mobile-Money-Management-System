from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.db.models import Sum, Count
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import *

# ==================== USER MANAGEMENT ====================

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'phone_number', 'user_type', 'is_verified', 'is_active_user', 'created_at')
    list_filter = ('user_type', 'is_verified', 'is_active_user', 'created_at')
    search_fields = ('username', 'phone_number', 'email', 'national_id', 'first_name', 'last_name')
    ordering = ('-created_at',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('user_type', 'phone_number', 'national_id', 'date_of_birth', 
                      'is_verified', 'is_active_user', 'pin_hash')
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Additional Info', {
            'fields': ('user_type', 'phone_number', 'national_id', 'date_of_birth', 
                      'is_verified', 'is_active_user', 'pin_hash')
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('wallet')


@admin.register(KYCDocument)
class KYCDocumentAdmin(admin.ModelAdmin):
    list_display = ('user', 'document_type', 'status', 'document_number', 'created_at', 'verified_at')
    list_filter = ('status', 'document_type', 'created_at')
    search_fields = ('user__phone_number', 'user__username', 'document_number')
    readonly_fields = ('created_at', 'verified_at')
    actions = ['approve_documents', 'reject_documents']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'document_type', 'document_number')
        }),
        ('Document', {
            'fields': ('document_file', 'status')
        }),
        ('Verification', {
            'fields': ('verified_by', 'verified_at', 'rejection_reason')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )
    
    def approve_documents(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='APPROVED', verified_by=request.user, verified_at=timezone.now())
        self.message_user(request, f"{queryset.count()} documents approved successfully.")
    approve_documents.short_description = "Approve selected documents"
    
    def reject_documents(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='REJECTED', verified_by=request.user, verified_at=timezone.now())
        self.message_user(request, f"{queryset.count()} documents rejected.")
    reject_documents.short_description = "Reject selected documents"


# ==================== WALLET MANAGEMENT ====================

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance_display', 'currency', 'is_active', 'daily_limit', 'created_at')
    list_filter = ('is_active', 'currency', 'created_at')
    search_fields = ('user__phone_number', 'user__username')
    readonly_fields = ('created_at', 'updated_at', 'transaction_summary')
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Balance & Limits', {
            'fields': ('balance', 'currency', 'daily_limit', 'monthly_limit', 'is_active')
        }),
        ('Statistics', {
            'fields': ('transaction_summary',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def balance_display(self, obj):
        color = 'green' if obj.balance > 0 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {:,.2f}</span>',
            color, obj.currency, obj.balance
        )
    balance_display.short_description = 'Balance'
    
    def transaction_summary(self, obj):
        if obj.pk:
            total_transactions = obj.transactions.count()
            total_in = obj.transactions.filter(
                transaction_type__in=['DEPOSIT', 'TRANSFER']
            ).aggregate(Sum('amount'))['amount__sum'] or 0
            total_out = obj.transactions.filter(
                transaction_type__in=['WITHDRAWAL', 'PAYMENT']
            ).aggregate(Sum('amount'))['amount__sum'] or 0
            
            return format_html(
                '<strong>Total Transactions:</strong> {}<br>'
                '<strong>Total In:</strong> KES {:,.2f}<br>'
                '<strong>Total Out:</strong> KES {:,.2f}',
                total_transactions, total_in, total_out
            )
        return "Save wallet to see statistics"
    transaction_summary.short_description = 'Transaction Summary'


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'wallet_user', 'transaction_type', 'amount_display', 
                   'status', 'created_at')
    list_filter = ('transaction_type', 'status', 'created_at')
    search_fields = ('transaction_id', 'wallet__user__phone_number', 'reference_number')
    readonly_fields = ('transaction_id', 'created_at', 'completed_at', 'balance_before', 'balance_after')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Transaction Details', {
            'fields': ('transaction_id', 'wallet', 'transaction_type', 'amount', 'status')
        }),
        ('Balance Information', {
            'fields': ('balance_before', 'balance_after')
        }),
        ('Additional Info', {
            'fields': ('description', 'reference_number')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'completed_at')
        }),
    )
    
    def wallet_user(self, obj):
        return obj.wallet.user.phone_number
    wallet_user.short_description = 'User'
    
    def amount_display(self, obj):
        return format_html('<strong>KES {:,.2f}</strong>', obj.amount)
    amount_display.short_description = 'Amount'


# ==================== AGENT MANAGEMENT ====================

@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ('agent_number', 'business_name', 'user_phone', 'agent_type', 
                   'float_balance_display', 'status', 'location')
    list_filter = ('agent_type', 'status', 'county', 'created_at')
    search_fields = ('agent_number', 'business_name', 'user__phone_number', 'business_registration')
    readonly_fields = ('created_at', 'updated_at', 'agent_statistics')
    
    fieldsets = (
        ('Agent Information', {
            'fields': ('user', 'agent_number', 'agent_type', 'status')
        }),
        ('Business Details', {
            'fields': ('business_name', 'business_registration')
        }),
        ('Location', {
            'fields': ('location', 'county', 'sub_county', 'latitude', 'longitude')
        }),
        ('Financial', {
            'fields': ('float_balance', 'commission_rate', 'super_agent')
        }),
        ('Statistics', {
            'fields': ('agent_statistics',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def user_phone(self, obj):
        return obj.user.phone_number
    user_phone.short_description = 'Phone Number'
    
    def float_balance_display(self, obj):
        return format_html(
            '<span style="color: blue; font-weight: bold;">KES {:,.2f}</span>',
            obj.float_balance
        )
    float_balance_display.short_description = 'Float Balance'
    
    def agent_statistics(self, obj):
        if obj.pk:
            total_deposits = obj.customer_deposits.filter(status='COMPLETED').count()
            total_withdrawals = obj.customer_withdrawals.filter(status='COMPLETED').count()
            total_commission = obj.user.commissions.aggregate(Sum('amount'))['amount__sum'] or 0
            
            return format_html(
                '<strong>Total Deposits:</strong> {}<br>'
                '<strong>Total Withdrawals:</strong> {}<br>'
                '<strong>Total Commission Earned:</strong> KES {:,.2f}',
                total_deposits, total_withdrawals, total_commission
            )
        return "Save agent to see statistics"
    agent_statistics.short_description = 'Agent Statistics'


@admin.register(AgentFloat)
class AgentFloatAdmin(admin.ModelAdmin):
    list_display = ('agent_business', 'transaction_type', 'amount', 'balance_after', 'created_at')
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('agent__agent_number', 'agent__business_name', 'reference')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    
    def agent_business(self, obj):
        return obj.agent.business_name
    agent_business.short_description = 'Agent'


# ==================== MERCHANT MANAGEMENT ====================

@admin.register(Merchant)
class MerchantAdmin(admin.ModelAdmin):
    list_display = ('business_number', 'business_name', 'merchant_type', 'category', 
                   'status', 'commission_rate', 'created_at')
    list_filter = ('merchant_type', 'status', 'category', 'county', 'created_at')
    search_fields = ('business_number', 'business_name', 'business_registration', 'user__phone_number')
    readonly_fields = ('created_at', 'updated_at', 'merchant_statistics')
    
    fieldsets = (
        ('Merchant Information', {
            'fields': ('user', 'merchant_type', 'business_number', 'status')
        }),
        ('Business Details', {
            'fields': ('business_name', 'business_registration', 'category')
        }),
        ('Location', {
            'fields': ('location', 'county')
        }),
        ('Financial', {
            'fields': ('commission_rate', 'settlement_account')
        }),
        ('Statistics', {
            'fields': ('merchant_statistics',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def merchant_statistics(self, obj):
        if obj.pk:
            if obj.merchant_type == 'PAYBILL':
                total_transactions = obj.paybill_receipts.filter(status='COMPLETED').count()
                total_amount = obj.paybill_receipts.filter(status='COMPLETED').aggregate(
                    Sum('amount'))['amount__sum'] or 0
            else:
                total_transactions = obj.till_receipts.filter(status='COMPLETED').count()
                total_amount = obj.till_receipts.filter(status='COMPLETED').aggregate(
                    Sum('amount'))['amount__sum'] or 0
            
            return format_html(
                '<strong>Total Transactions:</strong> {}<br>'
                '<strong>Total Amount Received:</strong> KES {:,.2f}',
                total_transactions, total_amount
            )
        return "Save merchant to see statistics"
    merchant_statistics.short_description = 'Merchant Statistics'


# ==================== TRANSACTION MANAGEMENT ====================

@admin.register(SendMoney)
class SendMoneyAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'sender_phone', 'receiver_phone', 'amount_display', 
                   'charge', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('transaction_id', 'sender__phone_number', 'receiver__phone_number')
    readonly_fields = ('transaction_id', 'created_at', 'completed_at', 'sender_balance_before', 
                      'sender_balance_after', 'receiver_balance_before', 'receiver_balance_after')
    date_hierarchy = 'created_at'
    
    def sender_phone(self, obj):
        return obj.sender.phone_number
    sender_phone.short_description = 'Sender'
    
    def receiver_phone(self, obj):
        return obj.receiver.phone_number
    receiver_phone.short_description = 'Receiver'
    
    def amount_display(self, obj):
        return format_html('<strong>KES {:,.2f}</strong>', obj.amount)
    amount_display.short_description = 'Amount'


@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'customer_phone', 'agent_name', 'amount_display', 
                   'charge', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('transaction_id', 'customer__phone_number', 'agent__agent_number')
    readonly_fields = ('transaction_id', 'created_at', 'completed_at')
    date_hierarchy = 'created_at'
    
    def customer_phone(self, obj):
        return obj.customer.phone_number
    customer_phone.short_description = 'Customer'
    
    def agent_name(self, obj):
        return obj.agent.business_name
    agent_name.short_description = 'Agent'
    
    def amount_display(self, obj):
        return format_html('<strong>KES {:,.2f}</strong>', obj.amount)
    amount_display.short_description = 'Amount'


@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'customer_phone', 'agent_name', 'amount_display', 
                   'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('transaction_id', 'customer__phone_number', 'agent__agent_number')
    readonly_fields = ('transaction_id', 'created_at', 'completed_at')
    date_hierarchy = 'created_at'
    
    def customer_phone(self, obj):
        return obj.customer.phone_number
    customer_phone.short_description = 'Customer'
    
    def agent_name(self, obj):
        return obj.agent.business_name
    agent_name.short_description = 'Agent'
    
    def amount_display(self, obj):
        return format_html('<strong>KES {:,.2f}</strong>', obj.amount)
    amount_display.short_description = 'Amount'


@admin.register(PayBill)
class PayBillAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'payer_phone', 'business_number', 'account_number', 
                   'amount_display', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('transaction_id', 'payer__phone_number', 'business_number', 'account_number')
    readonly_fields = ('transaction_id', 'created_at', 'completed_at')
    date_hierarchy = 'created_at'
    
    def payer_phone(self, obj):
        return obj.payer.phone_number
    payer_phone.short_description = 'Payer'
    
    def amount_display(self, obj):
        return format_html('<strong>KES {:,.2f}</strong>', obj.amount)
    amount_display.short_description = 'Amount'


@admin.register(BuyGoods)
class BuyGoodsAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'buyer_phone', 'till_number', 'amount_display', 
                   'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('transaction_id', 'buyer__phone_number', 'till_number')
    readonly_fields = ('transaction_id', 'created_at', 'completed_at')
    date_hierarchy = 'created_at'
    
    def buyer_phone(self, obj):
        return obj.buyer.phone_number
    buyer_phone.short_description = 'Buyer'
    
    def amount_display(self, obj):
        return format_html('<strong>KES {:,.2f}</strong>', obj.amount)
    amount_display.short_description = 'Amount'


@admin.register(AirtimePurchase)
class AirtimePurchaseAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'buyer_phone', 'recipient_phone', 'network', 
                   'amount_display', 'status', 'created_at')
    list_filter = ('network', 'status', 'created_at')
    search_fields = ('transaction_id', 'buyer__phone_number', 'recipient_phone')
    readonly_fields = ('transaction_id', 'created_at', 'completed_at')
    date_hierarchy = 'created_at'
    
    def buyer_phone(self, obj):
        return obj.buyer.phone_number
    buyer_phone.short_description = 'Buyer'
    
    def amount_display(self, obj):
        return format_html('<strong>KES {:,.2f}</strong>', obj.amount)
    amount_display.short_description = 'Amount'


# ==================== CHARGES & COMMISSIONS ====================

@admin.register(TransactionCharge)
class TransactionChargeAdmin(admin.ModelAdmin):
    list_display = ('transaction_type', 'amount_range', 'charge', 'is_active', 'updated_at')
    list_filter = ('transaction_type', 'is_active', 'created_at')
    search_fields = ('transaction_type',)
    ordering = ('transaction_type', 'min_amount')
    
    def amount_range(self, obj):
        return f"KES {obj.min_amount:,.2f} - {obj.max_amount:,.2f}"
    amount_range.short_description = 'Amount Range'


@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    list_display = ('recipient_phone', 'commission_type', 'transaction_id', 'amount_display', 'created_at')
    list_filter = ('commission_type', 'created_at')
    search_fields = ('recipient__phone_number', 'transaction_id')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    
    def recipient_phone(self, obj):
        return obj.recipient.phone_number
    recipient_phone.short_description = 'Recipient'
    
    def amount_display(self, obj):
        return format_html('<strong>KES {:,.2f}</strong>', obj.amount)
    amount_display.short_description = 'Amount'


# ==================== LOANS ====================

@admin.register(LoanProduct)
class LoanProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'amount_range', 'interest_rate', 'duration_days', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name',)
    
    def amount_range(self, obj):
        return f"KES {obj.min_amount:,.2f} - {obj.max_amount:,.2f}"
    amount_range.short_description = 'Loan Range'


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ('loan_id', 'borrower_phone', 'principal_amount', 'total_amount', 
                   'balance', 'status', 'due_date')
    list_filter = ('status', 'created_at', 'due_date')
    search_fields = ('loan_id', 'borrower__phone_number')
    readonly_fields = ('loan_id', 'created_at', 'disbursed_at')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Loan Information', {
            'fields': ('loan_id', 'borrower', 'product', 'status')
        }),
        ('Amounts', {
            'fields': ('principal_amount', 'interest_amount', 'facilitation_fee', 
                      'total_amount', 'amount_paid', 'balance')
        }),
        ('Dates', {
            'fields': ('due_date', 'disbursed_at', 'created_at')
        }),
    )
    
    def borrower_phone(self, obj):
        return obj.borrower.phone_number
    borrower_phone.short_description = 'Borrower'


@admin.register(LoanRepayment)
class LoanRepaymentAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'loan_id_display', 'amount', 'balance_after', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('transaction_id', 'loan__loan_id')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    
    def loan_id_display(self, obj):
        return obj.loan.loan_id
    loan_id_display.short_description = 'Loan ID'


# ==================== NOTIFICATIONS ====================

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user_phone', 'notification_type', 'title', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('user__phone_number', 'title', 'message')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    actions = ['mark_as_read']
    
    def user_phone(self, obj):
        return obj.user.phone_number
    user_phone.short_description = 'User'
    
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
        self.message_user(request, f"{queryset.count()} notifications marked as read.")
    mark_as_read.short_description = "Mark selected as read"


@admin.register(SMSLog)
class SMSLogAdmin(admin.ModelAdmin):
    list_display = ('recipient_phone', 'message_preview', 'status', 'sent_at')
    list_filter = ('status', 'sent_at')
    search_fields = ('recipient_phone', 'message')
    readonly_fields = ('sent_at',)
    date_hierarchy = 'sent_at'
    
    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message'


# ==================== SECURITY ====================

@admin.register(SecurityQuestion)
class SecurityQuestionAdmin(admin.ModelAdmin):
    list_display = ('user_phone', 'question', 'created_at')
    search_fields = ('user__phone_number', 'question')
    readonly_fields = ('created_at', 'answer_hash')
    
    def user_phone(self, obj):
        return obj.user.phone_number
    user_phone.short_description = 'User'


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'ip_address', 'success', 'failure_reason', 'attempted_at')
    list_filter = ('success', 'attempted_at')
    search_fields = ('phone_number', 'ip_address')
    readonly_fields = ('attempted_at',)
    date_hierarchy = 'attempted_at'


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('user_display', 'action', 'model_name', 'object_id', 'created_at')
    list_filter = ('action', 'model_name', 'created_at')
    search_fields = ('user__phone_number', 'action', 'model_name', 'object_id')
    readonly_fields = ('created_at', 'changes')
    date_hierarchy = 'created_at'
    
    def user_display(self, obj):
        return obj.user.phone_number if obj.user else 'System'
    user_display.short_description = 'User'


# ==================== SETTINGS ====================

@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ('key', 'value_preview', 'updated_at')
    search_fields = ('key', 'description')
    readonly_fields = ('updated_at',)
    
    def value_preview(self, obj):
        return obj.value[:50] + '...' if len(obj.value) > 50 else obj.value
    value_preview.short_description = 'Value'


@admin.register(MaintenanceWindow)
class MaintenanceWindowAdmin(admin.ModelAdmin):
    list_display = ('description', 'start_time', 'end_time', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Schedule', {
            'fields': ('start_time', 'end_time', 'is_active')
        }),
        ('Details', {
            'fields': ('description',)
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )