import django_filters
from django.db.models import Q
from .models import (
    User, WalletTransaction, SendMoney, Withdrawal, Deposit,
    PayBill, BuyGoods, Agent, Merchant, Loan, Commission
)


class UserFilter(django_filters.FilterSet):
    """Filter for User model"""
    search = django_filters.CharFilter(method='search_users')
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = User
        fields = ['user_type', 'is_verified', 'is_active_user']
    
    def search_users(self, queryset, name, value):
        return queryset.filter(
            Q(username__icontains=value) |
            Q(email__icontains=value) |
            Q(phone_number__icontains=value) |
            Q(first_name__icontains=value) |
            Q(last_name__icontains=value)
        )


class WalletTransactionFilter(django_filters.FilterSet):
    """Filter for WalletTransaction model"""
    amount_min = django_filters.NumberFilter(field_name='amount', lookup_expr='gte')
    amount_max = django_filters.NumberFilter(field_name='amount', lookup_expr='lte')
    date_from = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    date_to = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = WalletTransaction
        fields = ['transaction_type', 'status']


class SendMoneyFilter(django_filters.FilterSet):
    """Filter for SendMoney transactions"""
    amount_min = django_filters.NumberFilter(field_name='amount', lookup_expr='gte')
    amount_max = django_filters.NumberFilter(field_name='amount', lookup_expr='lte')
    date_from = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    date_to = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = SendMoney
        fields = ['status']


class WithdrawalFilter(django_filters.FilterSet):
    """Filter for Withdrawal transactions"""
    amount_min = django_filters.NumberFilter(field_name='amount', lookup_expr='gte')
    amount_max = django_filters.NumberFilter(field_name='amount', lookup_expr='lte')
    date_from = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    date_to = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = Withdrawal
        fields = ['status', 'agent']


class DepositFilter(django_filters.FilterSet):
    """Filter for Deposit transactions"""
    amount_min = django_filters.NumberFilter(field_name='amount', lookup_expr='gte')
    amount_max = django_filters.NumberFilter(field_name='amount', lookup_expr='lte')
    date_from = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    date_to = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = Deposit
        fields = ['status', 'agent']


class PayBillFilter(django_filters.FilterSet):
    """Filter for PayBill transactions"""
    amount_min = django_filters.NumberFilter(field_name='amount', lookup_expr='gte')
    amount_max = django_filters.NumberFilter(field_name='amount', lookup_expr='lte')
    date_from = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    date_to = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    business_number = django_filters.CharFilter(lookup_expr='icontains')
    
    class Meta:
        model = PayBill
        fields = ['status', 'merchant']


class BuyGoodsFilter(django_filters.FilterSet):
    """Filter for BuyGoods transactions"""
    amount_min = django_filters.NumberFilter(field_name='amount', lookup_expr='gte')
    amount_max = django_filters.NumberFilter(field_name='amount', lookup_expr='lte')
    date_from = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    date_to = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    till_number = django_filters.CharFilter(lookup_expr='icontains')
    
    class Meta:
        model = BuyGoods
        fields = ['status', 'merchant']


class AgentFilter(django_filters.FilterSet):
    """Filter for Agent model"""
    search = django_filters.CharFilter(method='search_agents')
    
    class Meta:
        model = Agent
        fields = ['status', 'agent_type', 'county', 'sub_county']
    
    def search_agents(self, queryset, name, value):
        return queryset.filter(
            Q(business_name__icontains=value) |
            Q(agent_number__icontains=value) |
            Q(location__icontains=value)
        )


class MerchantFilter(django_filters.FilterSet):
    """Filter for Merchant model"""
    search = django_filters.CharFilter(method='search_merchants')
    
    class Meta:
        model = Merchant
        fields = ['status', 'merchant_type', 'category', 'county']
    
    def search_merchants(self, queryset, name, value):
        return queryset.filter(
            Q(business_name__icontains=value) |
            Q(business_number__icontains=value) |
            Q(location__icontains=value)
        )


class LoanFilter(django_filters.FilterSet):
    """Filter for Loan model"""
    amount_min = django_filters.NumberFilter(field_name='principal_amount', lookup_expr='gte')
    amount_max = django_filters.NumberFilter(field_name='principal_amount', lookup_expr='lte')
    date_from = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    date_to = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = Loan
        fields = ['status', 'product']


class CommissionFilter(django_filters.FilterSet):
    """Filter for Commission model"""
    date_from = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    date_to = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = Commission
        fields = ['commission_type', 'recipient']