#mpesa_app/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, KYCDocumentViewSet, WalletViewSet, WalletTransactionViewSet,
    AgentViewSet, AgentFloatViewSet, MerchantViewSet, SendMoneyViewSet,
    WithdrawalViewSet, DepositViewSet, PayBillViewSet, BuyGoodsViewSet,
    AirtimePurchaseViewSet, TransactionChargeViewSet, CommissionViewSet,
    LoanProductViewSet, LoanViewSet, LoanRepaymentViewSet, NotificationViewSet,
    SMSLogViewSet, SecurityQuestionViewSet, LoginAttemptViewSet, AuditLogViewSet,
    SystemSettingViewSet, MaintenanceWindowViewSet, DashboardViewSet
)

# Create router and register viewsets
router = DefaultRouter()

# User & Authentication
router.register(r'users', UserViewSet, basename='user')
router.register(r'kyc-documents', KYCDocumentViewSet, basename='kyc-document')

# Wallet & Accounts
router.register(r'wallets', WalletViewSet, basename='wallet')
router.register(r'wallet-transactions', WalletTransactionViewSet, basename='wallet-transaction')

# Agents & Merchants
router.register(r'agents', AgentViewSet, basename='agent')
router.register(r'agent-float', AgentFloatViewSet, basename='agent-float')
router.register(r'merchants', MerchantViewSet, basename='merchant')

# Transactions
router.register(r'send-money', SendMoneyViewSet, basename='send-money')
router.register(r'withdrawals', WithdrawalViewSet, basename='withdrawal')
router.register(r'deposits', DepositViewSet, basename='deposit')
router.register(r'paybill', PayBillViewSet, basename='paybill')
router.register(r'buy-goods', BuyGoodsViewSet, basename='buy-goods')
router.register(r'airtime', AirtimePurchaseViewSet, basename='airtime')

# Charges & Commissions
router.register(r'transaction-charges', TransactionChargeViewSet, basename='transaction-charge')
router.register(r'commissions', CommissionViewSet, basename='commission')

# Loans
router.register(r'loan-products', LoanProductViewSet, basename='loan-product')
router.register(r'loans', LoanViewSet, basename='loan')
router.register(r'loan-repayments', LoanRepaymentViewSet, basename='loan-repayment')

# Notifications
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'sms-logs', SMSLogViewSet, basename='sms-log')

# Security & Audit
router.register(r'security-questions', SecurityQuestionViewSet, basename='security-question')
router.register(r'login-attempts', LoginAttemptViewSet, basename='login-attempt')
router.register(r'audit-logs', AuditLogViewSet, basename='audit-log')

# Settings
router.register(r'system-settings', SystemSettingViewSet, basename='system-setting')
router.register(r'maintenance-windows', MaintenanceWindowViewSet, basename='maintenance-window')

# Dashboard
router.register(r'dashboard', DashboardViewSet, basename='dashboard')

# URL patterns
urlpatterns = [
    path('api/', include(router.urls)),
]
