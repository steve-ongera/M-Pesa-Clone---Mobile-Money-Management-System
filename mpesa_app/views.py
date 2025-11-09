from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password, make_password
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from decimal import Decimal
import uuid
from datetime import datetime, timedelta

from .models import (
    User, KYCDocument, Wallet, WalletTransaction, Agent, AgentFloat,
    Merchant, SendMoney, Withdrawal, Deposit, PayBill, BuyGoods,
    AirtimePurchase, TransactionCharge, Commission, LoanProduct, Loan,
    LoanRepayment, Notification, SMSLog, SecurityQuestion, LoginAttempt,
    AuditLog, SystemSetting, MaintenanceWindow
)

from .serializers import (
    UserRegistrationSerializer, UserSerializer, UserUpdateSerializer,
    ChangePINSerializer, LoginSerializer, KYCDocumentSerializer,
    KYCVerificationSerializer, WalletSerializer, WalletTransactionSerializer,
    MiniStatementSerializer, AgentSerializer, AgentFloatSerializer,
    AgentLocationSerializer, MerchantSerializer, SendMoneySerializer,
    WithdrawalSerializer, DepositSerializer, PayBillSerializer,
    BuyGoodsSerializer, AirtimePurchaseSerializer, TransactionChargeSerializer,
    CommissionSerializer, LoanProductSerializer, LoanApplicationSerializer,
    LoanRepaymentSerializer, NotificationSerializer, SMSLogSerializer,
    SecurityQuestionSerializer, LoginAttemptSerializer, AuditLogSerializer,
    SystemSettingSerializer, MaintenanceWindowSerializer, DashboardStatsSerializer
)


# ==================== HELPER FUNCTIONS ====================

def generate_transaction_id(prefix='TXN'):
    """Generate unique transaction ID"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    return f"{prefix}{timestamp}{uuid.uuid4().hex[:6].upper()}"


def get_transaction_charge(transaction_type, amount):
    """Get transaction charge based on amount"""
    try:
        charge = TransactionCharge.objects.get(
            transaction_type=transaction_type,
            min_amount__lte=amount,
            max_amount__gte=amount,
            is_active=True
        )
        return charge.charge
    except TransactionCharge.DoesNotExist:
        return Decimal('0.00')


# ==================== USER & AUTHENTICATION ====================

class UserViewSet(viewsets.ModelViewSet):
    """User management viewset"""
    queryset = User.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['username', 'email', 'phone_number', 'first_name', 'last_name']
    filterset_fields = ['user_type', 'is_verified', 'is_active_user']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserRegistrationSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer
    
    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return [IsAuthenticated()]
    
    @action(detail=False, methods=['post'])
    def login(self, request):
        """User login with phone and PIN"""
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        phone_number = serializer.validated_data['phone_number']
        pin = serializer.validated_data['pin']
        
        try:
            user = User.objects.get(phone_number=phone_number)
            
            # Check PIN
            if check_password(pin, user.pin_hash):
                # Log successful login
                LoginAttempt.objects.create(
                    phone_number=phone_number,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    success=True
                )
                
                return Response({
                    'message': 'Login successful',
                    'user': UserSerializer(user).data
                })
            else:
                # Log failed login
                LoginAttempt.objects.create(
                    phone_number=phone_number,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    success=False,
                    failure_reason='Invalid PIN'
                )
                return Response(
                    {'error': 'Invalid PIN'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'])
    def change_pin(self, request):
        """Change user PIN"""
        serializer = ChangePINSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        old_pin = serializer.validated_data['old_pin']
        new_pin = serializer.validated_data['new_pin']
        
        if check_password(old_pin, user.pin_hash):
            user.pin_hash = make_password(new_pin)
            user.save()
            return Response({'message': 'PIN changed successfully'})
        
        return Response(
            {'error': 'Invalid old PIN'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=False, methods=['get'])
    def profile(self, request):
        """Get current user profile"""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def balance(self, request):
        """Get wallet balance"""
        wallet = request.user.wallet
        return Response({
            'balance': str(wallet.balance),
            'currency': wallet.currency,
            'is_active': wallet.is_active
        })


# ==================== KYC ====================

class KYCDocumentViewSet(viewsets.ModelViewSet):
    """KYC document management"""
    queryset = KYCDocument.objects.all()
    serializer_class = KYCDocumentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'document_type', 'user']
    
    def get_queryset(self):
        if self.request.user.user_type == 'ADMIN':
            return KYCDocument.objects.all()
        return KYCDocument.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def verify(self, request, pk=None):
        """Verify or reject KYC document"""
        kyc_doc = self.get_object()
        serializer = KYCVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        kyc_doc.status = serializer.validated_data['status']
        kyc_doc.verified_by = request.user
        kyc_doc.verified_at = timezone.now()
        
        if serializer.validated_data['status'] == 'REJECTED':
            kyc_doc.rejection_reason = serializer.validated_data.get('rejection_reason', '')
        
        kyc_doc.save()
        
        # Update user verification status if all documents approved
        user = kyc_doc.user
        all_approved = not user.kyc_documents.exclude(status='APPROVED').exists()
        if all_approved:
            user.is_verified = True
            user.save()
        
        return Response({'message': 'KYC document updated successfully'})


# ==================== WALLET & TRANSACTIONS ====================

class WalletViewSet(viewsets.ReadOnlyModelViewSet):
    """Wallet viewset"""
    queryset = Wallet.objects.all()
    serializer_class = WalletSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.user_type == 'ADMIN':
            return Wallet.objects.all()
        return Wallet.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def my_wallet(self, request):
        """Get current user's wallet"""
        wallet = request.user.wallet
        return Response(WalletSerializer(wallet).data)


class WalletTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """Wallet transaction history"""
    queryset = WalletTransaction.objects.all()
    serializer_class = WalletTransactionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['transaction_type', 'status']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        if self.request.user.user_type == 'ADMIN':
            return WalletTransaction.objects.all()
        return WalletTransaction.objects.filter(wallet__user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def mini_statement(self, request):
        """Get recent transactions (mini statement)"""
        limit = int(request.query_params.get('limit', 10))
        transactions = self.get_queryset()[:limit]
        serializer = self.get_serializer(transactions, many=True)
        return Response(serializer.data)


# ==================== AGENTS ====================

class AgentViewSet(viewsets.ModelViewSet):
    """Agent management"""
    queryset = Agent.objects.all()
    serializer_class = AgentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['business_name', 'agent_number', 'location', 'county']
    filterset_fields = ['status', 'agent_type', 'county']
    
    @action(detail=False, methods=['post'])
    def find_nearby(self, request):
        """Find nearby agents"""
        serializer = AgentLocationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Simple distance calculation (you may want to use a proper geospatial query)
        agents = Agent.objects.filter(
            status='ACTIVE',
            latitude__isnull=False,
            longitude__isnull=False
        )
        
        return Response(AgentSerializer(agents, many=True).data)
    
    @action(detail=True, methods=['get'])
    def float_history(self, request, pk=None):
        """Get agent float transaction history"""
        agent = self.get_object()
        float_txns = agent.float_transactions.all()[:50]
        return Response(AgentFloatSerializer(float_txns, many=True).data)


class AgentFloatViewSet(viewsets.ReadOnlyModelViewSet):
    """Agent float transactions"""
    queryset = AgentFloat.objects.all()
    serializer_class = AgentFloatSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['agent', 'transaction_type']


# ==================== MERCHANTS ====================

class MerchantViewSet(viewsets.ModelViewSet):
    """Merchant management"""
    queryset = Merchant.objects.all()
    serializer_class = MerchantSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['business_name', 'business_number', 'category']
    filterset_fields = ['status', 'merchant_type', 'category', 'county']
    
    @action(detail=True, methods=['get'])
    def transactions(self, request, pk=None):
        """Get merchant transaction history"""
        merchant = self.get_object()
        
        paybills = merchant.paybill_receipts.all()[:50]
        till_payments = merchant.till_receipts.all()[:50]
        
        return Response({
            'paybill_transactions': PayBillSerializer(paybills, many=True).data,
            'till_transactions': BuyGoodsSerializer(till_payments, many=True).data
        })


# ==================== SEND MONEY ====================

class SendMoneyViewSet(viewsets.ModelViewSet):
    """Send money transactions"""
    queryset = SendMoney.objects.all()
    serializer_class = SendMoneySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status']
    
    def get_queryset(self):
        if self.request.user.user_type == 'ADMIN':
            return SendMoney.objects.all()
        return SendMoney.objects.filter(
            Q(sender=self.request.user) | Q(receiver=self.request.user)
        )
    
    def create(self, request):
        """Send money to another user"""
        receiver_phone = request.data.get('receiver_phone')
        amount = Decimal(request.data.get('amount', '0'))
        
        # Validate receiver
        try:
            receiver = User.objects.get(phone_number=receiver_phone)
        except User.DoesNotExist:
            return Response(
                {'error': 'Receiver not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check sender wallet
        sender = request.user
        sender_wallet = sender.wallet
        
        # Calculate charge
        charge = get_transaction_charge('SEND_MONEY', amount)
        total_amount = amount + charge
        
        if not sender_wallet.can_transact(total_amount):
            return Response(
                {'error': 'Insufficient balance'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create transaction
        transaction_id = generate_transaction_id('SM')
        
        # Deduct from sender
        sender_balance_before = sender_wallet.balance
        sender_wallet.balance -= total_amount
        sender_wallet.save()
        sender_balance_after = sender_wallet.balance
        
        # Add to receiver
        receiver_wallet = receiver.wallet
        receiver_balance_before = receiver_wallet.balance
        receiver_wallet.balance += amount
        receiver_wallet.save()
        receiver_balance_after = receiver_wallet.balance
        
        # Create send money record
        send_money = SendMoney.objects.create(
            transaction_id=transaction_id,
            sender=sender,
            receiver=receiver,
            amount=amount,
            charge=charge,
            total_amount=total_amount,
            sender_balance_before=sender_balance_before,
            sender_balance_after=sender_balance_after,
            receiver_balance_before=receiver_balance_before,
            receiver_balance_after=receiver_balance_after,
            status='COMPLETED',
            completed_at=timezone.now()
        )
        
        # Create wallet transactions
        WalletTransaction.objects.create(
            transaction_id=transaction_id,
            wallet=sender_wallet,
            transaction_type='TRANSFER',
            amount=total_amount,
            balance_before=sender_balance_before,
            balance_after=sender_balance_after,
            status='COMPLETED',
            description=f'Sent to {receiver.phone_number}',
            completed_at=timezone.now()
        )
        
        WalletTransaction.objects.create(
            transaction_id=transaction_id,
            wallet=receiver_wallet,
            transaction_type='TRANSFER',
            amount=amount,
            balance_before=receiver_balance_before,
            balance_after=receiver_balance_after,
            status='COMPLETED',
            description=f'Received from {sender.phone_number}',
            completed_at=timezone.now()
        )
        
        return Response(
            SendMoneySerializer(send_money).data,
            status=status.HTTP_201_CREATED
        )


# ==================== WITHDRAWAL ====================

class WithdrawalViewSet(viewsets.ModelViewSet):
    """Withdrawal transactions"""
    queryset = Withdrawal.objects.all()
    serializer_class = WithdrawalSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status']
    
    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'ADMIN':
            return Withdrawal.objects.all()
        elif user.user_type in ['AGENT', 'SUPER_AGENT']:
            return Withdrawal.objects.filter(agent__user=user)
        return Withdrawal.objects.filter(customer=user)
    
    def create(self, request):
        """Withdraw cash from agent"""
        agent_number = request.data.get('agent_number')
        amount = Decimal(request.data.get('amount', '0'))
        
        # Validate agent
        try:
            agent = Agent.objects.get(agent_number=agent_number, status='ACTIVE')
        except Agent.DoesNotExist:
            return Response(
                {'error': 'Agent not found or inactive'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check agent float
        if agent.float_balance < amount:
            return Response(
                {'error': 'Agent has insufficient float'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        customer = request.user
        customer_wallet = customer.wallet
        
        # Calculate charge and commission
        charge = get_transaction_charge('WITHDRAWAL', amount)
        total_amount = amount + charge
        commission = charge * Decimal('0.3')  # 30% commission
        
        if not customer_wallet.can_transact(total_amount):
            return Response(
                {'error': 'Insufficient balance'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        transaction_id = generate_transaction_id('WD')
        
        # Deduct from customer
        customer_balance_before = customer_wallet.balance
        customer_wallet.balance -= total_amount
        customer_wallet.save()
        customer_balance_after = customer_wallet.balance
        
        # Update agent float
        agent.float_balance -= amount
        agent.save()
        
        # Create withdrawal record
        withdrawal = Withdrawal.objects.create(
            transaction_id=transaction_id,
            customer=customer,
            agent=agent,
            amount=amount,
            charge=charge,
            total_amount=total_amount,
            customer_balance_before=customer_balance_before,
            customer_balance_after=customer_balance_after,
            agent_commission=commission,
            status='COMPLETED',
            completed_at=timezone.now()
        )
        
        # Create wallet transaction
        WalletTransaction.objects.create(
            transaction_id=transaction_id,
            wallet=customer_wallet,
            transaction_type='WITHDRAWAL',
            amount=total_amount,
            balance_before=customer_balance_before,
            balance_after=customer_balance_after,
            status='COMPLETED',
            description=f'Withdrawal at {agent.business_name}',
            completed_at=timezone.now()
        )
        
        # Record commission
        Commission.objects.create(
            recipient=agent.user,
            commission_type='WITHDRAWAL',
            transaction_id=transaction_id,
            amount=commission
        )
        
        return Response(
            WithdrawalSerializer(withdrawal).data,
            status=status.HTTP_201_CREATED
        )


# ==================== DEPOSIT ====================

class DepositViewSet(viewsets.ModelViewSet):
    """Deposit transactions"""
    queryset = Deposit.objects.all()
    serializer_class = DepositSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status']
    
    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'ADMIN':
            return Deposit.objects.all()
        elif user.user_type in ['AGENT', 'SUPER_AGENT']:
            return Deposit.objects.filter(agent__user=user)
        return Deposit.objects.filter(customer=user)
    
    def create(self, request):
        """Deposit cash through agent (Agent initiated)"""
        customer_phone = request.data.get('customer_phone')
        amount = Decimal(request.data.get('amount', '0'))
        
        # Must be agent
        if request.user.user_type not in ['AGENT', 'SUPER_AGENT']:
            return Response(
                {'error': 'Only agents can perform deposits'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        agent = request.user.agent_profile
        
        # Validate customer
        try:
            customer = User.objects.get(phone_number=customer_phone)
        except User.DoesNotExist:
            return Response(
                {'error': 'Customer not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check agent float
        if agent.float_balance < amount:
            return Response(
                {'error': 'Insufficient float'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        customer_wallet = customer.wallet
        commission = amount * agent.commission_rate / 100
        
        transaction_id = generate_transaction_id('DP')
        
        # Add to customer
        customer_balance_before = customer_wallet.balance
        customer_wallet.balance += amount
        customer_wallet.save()
        customer_balance_after = customer_wallet.balance
        
        # Update agent float
        agent.float_balance -= amount
        agent.save()
        
        # Create deposit record
        deposit = Deposit.objects.create(
            transaction_id=transaction_id,
            customer=customer,
            agent=agent,
            amount=amount,
            customer_balance_before=customer_balance_before,
            customer_balance_after=customer_balance_after,
            agent_commission=commission,
            status='COMPLETED',
            completed_at=timezone.now()
        )
        
        # Create wallet transaction
        WalletTransaction.objects.create(
            transaction_id=transaction_id,
            wallet=customer_wallet,
            transaction_type='DEPOSIT',
            amount=amount,
            balance_before=customer_balance_before,
            balance_after=customer_balance_after,
            status='COMPLETED',
            description=f'Deposit at {agent.business_name}',
            completed_at=timezone.now()
        )
        
        # Record commission
        Commission.objects.create(
            recipient=agent.user,
            commission_type='DEPOSIT',
            transaction_id=transaction_id,
            amount=commission
        )
        
        return Response(
            DepositSerializer(deposit).data,
            status=status.HTTP_201_CREATED
        )


# ==================== PAYBILL ====================

class PayBillViewSet(viewsets.ModelViewSet):
    """PayBill transactions"""
    queryset = PayBill.objects.all()
    serializer_class = PayBillSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status']
    
    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'ADMIN':
            return PayBill.objects.all()
        elif user.user_type == 'MERCHANT':
            return PayBill.objects.filter(merchant__user=user)
        return PayBill.objects.filter(payer=user)
    
    def create(self, request):
        """Pay bill to merchant"""
        business_number = request.data.get('business_number')
        account_number = request.data.get('account_number')
        amount = Decimal(request.data.get('amount', '0'))
        
        # Validate merchant
        try:
            merchant = Merchant.objects.get(
                business_number=business_number,
                merchant_type='PAYBILL',
                status='ACTIVE'
            )
        except Merchant.DoesNotExist:
            return Response(
                {'error': 'PayBill number not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        payer = request.user
        payer_wallet = payer.wallet
        
        # Calculate charge
        charge = get_transaction_charge('PAYBILL', amount)
        total_amount = amount + charge
        
        if not payer_wallet.can_transact(total_amount):
            return Response(
                {'error': 'Insufficient balance'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        transaction_id = generate_transaction_id('PB')
        
        # Deduct from payer
        payer_balance_before = payer_wallet.balance
        payer_wallet.balance -= total_amount
        payer_wallet.save()
        payer_balance_after = payer_wallet.balance
        
        # Add to merchant (to their wallet)
        merchant_wallet = merchant.user.wallet
        merchant_wallet.balance += amount
        merchant_wallet.save()
        
        # Create paybill record
        paybill = PayBill.objects.create(
            transaction_id=transaction_id,
            payer=payer,
            merchant=merchant,
            business_number=business_number,
            account_number=account_number,
            amount=amount,
            charge=charge,
            total_amount=total_amount,
            payer_balance_before=payer_balance_before,
            payer_balance_after=payer_balance_after,
            status='COMPLETED',
            completed_at=timezone.now()
        )
        
        # Create wallet transaction
        WalletTransaction.objects.create(
            transaction_id=transaction_id,
            wallet=payer_wallet,
            transaction_type='PAYBILL',
            amount=total_amount,
            balance_before=payer_balance_before,
            balance_after=payer_balance_after,
            status='COMPLETED',
            description=f'PayBill to {merchant.business_name} - Acc: {account_number}',
            reference_number=account_number,
            completed_at=timezone.now()
        )
        
        return Response(
            PayBillSerializer(paybill).data,
            status=status.HTTP_201_CREATED
        )


# ==================== BUY GOODS ====================

class BuyGoodsViewSet(viewsets.ModelViewSet):
    """Buy Goods transactions"""
    queryset = BuyGoods.objects.all()
    serializer_class = BuyGoodsSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status']
    
    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'ADMIN':
            return BuyGoods.objects.all()
        elif user.user_type == 'MERCHANT':
            return BuyGoods.objects.filter(merchant__user=user)
        return BuyGoods.objects.filter(buyer=user)
    
    def create(self, request):
        """Buy goods from merchant till"""
        till_number = request.data.get('till_number')
        amount = Decimal(request.data.get('amount', '0'))
        
        # Validate merchant
        try:
            merchant = Merchant.objects.get(
                business_number=till_number,
                merchant_type='TILL',
                status='ACTIVE'
            )
        except Merchant.DoesNotExist:
            return Response(
                {'error': 'Till number not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        buyer = request.user
        buyer_wallet = buyer.wallet
        
        # Calculate charge
        charge = get_transaction_charge('BUY_GOODS', amount)
        total_amount = amount + charge
        
        if not buyer_wallet.can_transact(total_amount):
            return Response(
                {'error': 'Insufficient balance'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        transaction_id = generate_transaction_id('BG')
        
        # Deduct from buyer
        buyer_balance_before = buyer_wallet.balance
        buyer_wallet.balance -= total_amount
        buyer_wallet.save()
        buyer_balance_after = buyer_wallet.balance
        
        # Add to merchant
        merchant_wallet = merchant.user.wallet
        merchant_wallet.balance += amount
        merchant_wallet.save()
        
        # Create buy goods record
        buy_goods = BuyGoods.objects.create(
            transaction_id=transaction_id,
            buyer=buyer,
            merchant=merchant,
            till_number=till_number,
            amount=amount,
            charge=charge,
            total_amount=total_amount,
            buyer_balance_before=buyer_balance_before,
            buyer_balance_after=buyer_balance_after,
            status='COMPLETED',
            completed_at=timezone.now()
        )
        
        # Create wallet transaction
        WalletTransaction.objects.create(
            transaction_id=transaction_id,
            wallet=buyer_wallet,
            transaction_type='BUY_GOODS',
            amount=total_amount,
            balance_before=buyer_balance_before,
            balance_after=buyer_balance_after,
            status='COMPLETED',
            description=f'Buy Goods at {merchant.business_name}',
            reference_number=till_number,
            completed_at=timezone.now()
        )
        
        return Response(
            BuyGoodsSerializer(buy_goods).data,
            status=status.HTTP_201_CREATED
        )


# ==================== AIRTIME ====================

class AirtimePurchaseViewSet(viewsets.ModelViewSet):
    """Airtime purchase transactions"""
    queryset = AirtimePurchase.objects.all()
    serializer_class = AirtimePurchaseSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'network']
    
    def get_queryset(self):
        if self.request.user.user_type == 'ADMIN':
            return AirtimePurchase.objects.all()
        return AirtimePurchase.objects.filter(buyer=self.request.user)
    
    def create(self, request):
        """Purchase airtime"""
        recipient_phone = request.data.get('recipient_phone')
        network = request.data.get('network')
        amount = Decimal(request.data.get('amount', '0'))
        
        buyer = request.user
        buyer_wallet = buyer.wallet
        
        if not buyer_wallet.can_transact(amount):
            return Response(
                {'error': 'Insufficient balance'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        transaction_id = generate_transaction_id('AT')
        
        # Deduct from buyer
        buyer_balance_before = buyer_wallet.balance
        buyer_wallet.balance -= amount
        buyer_wallet.save()
        buyer_balance_after = buyer_wallet.balance
        
        # Create airtime purchase record
        airtime = AirtimePurchase.objects.create(
            transaction_id=transaction_id,
            buyer=buyer,
            recipient_phone=recipient_phone,
            network=network,
            amount=amount,
            buyer_balance_before=buyer_balance_before,
            buyer_balance_after=buyer_balance_after,
            status='COMPLETED',
            completed_at=timezone.now()
        )
        
        # Create wallet transaction
        WalletTransaction.objects.create(
            transaction_id=transaction_id,
            wallet=buyer_wallet,
            transaction_type='AIRTIME',
            amount=amount,
            balance_before=buyer_balance_before,
            balance_after=buyer_balance_after,
            status='COMPLETED',
            description=f'Airtime {network} for {recipient_phone}',
            completed_at=timezone.now()
        )
        
        return Response(
            AirtimePurchaseSerializer(airtime).data,
            status=status.HTTP_201_CREATED
        )


# ==================== CHARGES & COMMISSIONS ====================

class TransactionChargeViewSet(viewsets.ModelViewSet):
    """Transaction charge management"""
    queryset = TransactionCharge.objects.all()
    serializer_class = TransactionChargeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['transaction_type', 'is_active']
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAdminUser()]
    
    @action(detail=False, methods=['get'])
    def calculate_charge(self, request):
        """Calculate charge for a transaction"""
        transaction_type = request.query_params.get('transaction_type')
        amount = Decimal(request.query_params.get('amount', '0'))
        
        charge = get_transaction_charge(transaction_type, amount)
        return Response({
            'amount': str(amount),
            'charge': str(charge),
            'total': str(amount + charge)
        })


class CommissionViewSet(viewsets.ReadOnlyModelViewSet):
    """Commission records"""
    queryset = Commission.objects.all()
    serializer_class = CommissionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['commission_type', 'recipient']
    
    def get_queryset(self):
        if self.request.user.user_type == 'ADMIN':
            return Commission.objects.all()
        return Commission.objects.filter(recipient=self.request.user)
    
    @action(detail=False, methods=['get'])
    def total_earned(self, request):
        """Get total commission earned"""
        total = self.get_queryset().aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        return Response({
            'total_commission': str(total),
            'currency': 'KES'
        })


# ==================== LOANS ====================

class LoanProductViewSet(viewsets.ModelViewSet):
    """Loan product management"""
    queryset = LoanProduct.objects.filter(is_active=True)
    serializer_class = LoanProductSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAdminUser()]
    
    @action(detail=True, methods=['post'])
    def calculate_repayment(self, request, pk=None):
        """Calculate loan repayment amount"""
        product = self.get_object()
        principal = Decimal(request.data.get('amount', '0'))
        
        if principal < product.min_amount or principal > product.max_amount:
            return Response(
                {'error': f'Amount must be between {product.min_amount} and {product.max_amount}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Calculate interest
        daily_rate = product.interest_rate / 365 / 100
        interest = principal * Decimal(str(daily_rate)) * product.duration_days
        total = principal + interest + product.facilitation_fee
        
        return Response({
            'principal': str(principal),
            'interest': str(interest.quantize(Decimal('0.01'))),
            'facilitation_fee': str(product.facilitation_fee),
            'total_repayable': str(total.quantize(Decimal('0.01'))),
            'duration_days': product.duration_days
        })


class LoanViewSet(viewsets.ModelViewSet):
    """Loan management"""
    queryset = Loan.objects.all()
    serializer_class = LoanApplicationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status']
    
    def get_queryset(self):
        if self.request.user.user_type == 'ADMIN':
            return Loan.objects.all()
        return Loan.objects.filter(borrower=self.request.user)
    
    def create(self, request):
        """Apply for a loan"""
        product_id = request.data.get('product')
        principal_amount = Decimal(request.data.get('principal_amount', '0'))
        
        try:
            product = LoanProduct.objects.get(id=product_id, is_active=True)
        except LoanProduct.DoesNotExist:
            return Response(
                {'error': 'Loan product not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Validate amount
        if principal_amount < product.min_amount or principal_amount > product.max_amount:
            return Response(
                {'error': f'Amount must be between {product.min_amount} and {product.max_amount}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user has active loan
        active_loans = Loan.objects.filter(
            borrower=request.user,
            status__in=['ACTIVE', 'DISBURSED', 'APPROVED']
        )
        if active_loans.exists():
            return Response(
                {'error': 'You have an active loan. Please repay it first.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Calculate loan details
        daily_rate = product.interest_rate / 365 / 100
        interest_amount = principal_amount * Decimal(str(daily_rate)) * product.duration_days
        total_amount = principal_amount + interest_amount + product.facilitation_fee
        due_date = timezone.now().date() + timedelta(days=product.duration_days)
        
        loan_id = generate_transaction_id('LN')
        
        loan = Loan.objects.create(
            loan_id=loan_id,
            borrower=request.user,
            product=product,
            principal_amount=principal_amount,
            interest_amount=interest_amount.quantize(Decimal('0.01')),
            facilitation_fee=product.facilitation_fee,
            total_amount=total_amount.quantize(Decimal('0.01')),
            balance=total_amount.quantize(Decimal('0.01')),
            due_date=due_date,
            status='PENDING'
        )
        
        return Response(
            LoanApplicationSerializer(loan).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def approve(self, request, pk=None):
        """Approve loan and disburse funds"""
        loan = self.get_object()
        
        if loan.status != 'PENDING':
            return Response(
                {'error': 'Loan is not pending'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Disburse to borrower wallet
        wallet = loan.borrower.wallet
        balance_before = wallet.balance
        wallet.balance += loan.principal_amount
        wallet.save()
        
        loan.status = 'DISBURSED'
        loan.disbursed_at = timezone.now()
        loan.save()
        
        # Create wallet transaction
        WalletTransaction.objects.create(
            transaction_id=loan.loan_id,
            wallet=wallet,
            transaction_type='DEPOSIT',
            amount=loan.principal_amount,
            balance_before=balance_before,
            balance_after=wallet.balance,
            status='COMPLETED',
            description=f'Loan disbursement - {loan.loan_id}',
            completed_at=timezone.now()
        )
        
        return Response({'message': 'Loan approved and disbursed'})
    
    @action(detail=True, methods=['post'])
    def repay(self, request, pk=None):
        """Make loan repayment"""
        loan = self.get_object()
        amount = Decimal(request.data.get('amount', '0'))
        
        if loan.status not in ['ACTIVE', 'DISBURSED']:
            return Response(
                {'error': 'Loan is not active'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if amount > loan.balance:
            amount = loan.balance
        
        wallet = request.user.wallet
        if not wallet.can_transact(amount):
            return Response(
                {'error': 'Insufficient balance'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        transaction_id = generate_transaction_id('LR')
        
        # Deduct from wallet
        balance_before = wallet.balance
        wallet.balance -= amount
        wallet.save()
        
        # Update loan
        balance_before_loan = loan.balance
        loan.amount_paid += amount
        loan.balance -= amount
        
        if loan.balance == 0:
            loan.status = 'PAID'
        else:
            loan.status = 'ACTIVE'
        
        loan.save()
        
        # Create repayment record
        repayment = LoanRepayment.objects.create(
            loan=loan,
            transaction_id=transaction_id,
            amount=amount,
            balance_before=balance_before_loan,
            balance_after=loan.balance
        )
        
        # Create wallet transaction
        WalletTransaction.objects.create(
            transaction_id=transaction_id,
            wallet=wallet,
            transaction_type='PAYMENT',
            amount=amount,
            balance_before=balance_before,
            balance_after=wallet.balance,
            status='COMPLETED',
            description=f'Loan repayment - {loan.loan_id}',
            completed_at=timezone.now()
        )
        
        return Response(LoanRepaymentSerializer(repayment).data)


class LoanRepaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """Loan repayment history"""
    queryset = LoanRepayment.objects.all()
    serializer_class = LoanRepaymentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.user_type == 'ADMIN':
            return LoanRepayment.objects.all()
        return LoanRepayment.objects.filter(loan__borrower=self.request.user)


# ==================== NOTIFICATIONS ====================

class NotificationViewSet(viewsets.ModelViewSet):
    """Notification management"""
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['notification_type', 'is_read']
    
    def get_queryset(self):
        if self.request.user.user_type == 'ADMIN':
            return Notification.objects.all()
        return Notification.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark notification as read"""
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'message': 'Notification marked as read'})
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read"""
        self.get_queryset().update(is_read=True)
        return Response({'message': 'All notifications marked as read'})
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get unread notification count"""
        count = self.get_queryset().filter(is_read=False).count()
        return Response({'unread_count': count})


# ==================== SECURITY ====================

class SecurityQuestionViewSet(viewsets.ModelViewSet):
    """Security question management"""
    queryset = SecurityQuestion.objects.all()
    serializer_class = SecurityQuestionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return SecurityQuestion.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class LoginAttemptViewSet(viewsets.ReadOnlyModelViewSet):
    """Login attempt logs"""
    queryset = LoginAttempt.objects.all()
    serializer_class = LoginAttemptSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['success', 'phone_number']


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Audit log viewer"""
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['action', 'model_name', 'object_id']
    filterset_fields = ['model_name', 'action']


# ==================== SYSTEM SETTINGS ====================

class SystemSettingViewSet(viewsets.ModelViewSet):
    """System settings management"""
    queryset = SystemSetting.objects.all()
    serializer_class = SystemSettingSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [filters.SearchFilter]
    search_fields = ['key', 'description']


class MaintenanceWindowViewSet(viewsets.ModelViewSet):
    """Maintenance window management"""
    queryset = MaintenanceWindow.objects.all()
    serializer_class = MaintenanceWindowSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active']


# ==================== DASHBOARD & REPORTS ====================

class DashboardViewSet(viewsets.ViewSet):
    """Dashboard statistics and reports"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get dashboard statistics"""
        user = request.user
        
        if user.user_type == 'ADMIN':
            stats = {
                'total_users': User.objects.count(),
                'total_transactions': WalletTransaction.objects.count(),
                'total_volume': WalletTransaction.objects.filter(
                    status='COMPLETED'
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00'),
                'active_agents': Agent.objects.filter(status='ACTIVE').count(),
                'active_merchants': Merchant.objects.filter(status='ACTIVE').count(),
                'pending_kyc': KYCDocument.objects.filter(status='PENDING').count(),
            }
        else:
            # User-specific stats
            wallet = user.wallet
            stats = {
                'balance': str(wallet.balance),
                'total_sent': SendMoney.objects.filter(
                    sender=user, status='COMPLETED'
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00'),
                'total_received': SendMoney.objects.filter(
                    receiver=user, status='COMPLETED'
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00'),
                'transaction_count': WalletTransaction.objects.filter(
                    wallet=wallet
                ).count(),
            }
        
        return Response(stats)
    
    @action(detail=False, methods=['get'])
    def transaction_summary(self, request):
        """Get transaction summary by date"""
        days = int(request.query_params.get('days', 7))
        start_date = timezone.now().date() - timedelta(days=days)
        
        summary = WalletTransaction.objects.filter(
            created_at__date__gte=start_date,
            status='COMPLETED'
        ).values('transaction_type', 'created_at__date').annotate(
            count=Count('id'),
            total=Sum('amount')
        ).order_by('-created_at__date')
        
        return Response(list(summary))
    
    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def revenue_report(self, request):
        """Get revenue report"""
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now().date() - timedelta(days=days)
        
        charges = WalletTransaction.objects.filter(
            created_at__date__gte=start_date,
            transaction_type='CHARGE',
            status='COMPLETED'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        commissions = Commission.objects.filter(
            created_at__date__gte=start_date
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        return Response({
            'period_days': days,
            'total_charges': str(charges),
            'total_commissions': str(commissions),
            'net_revenue': str(charges - commissions)
        })


class SMSLogViewSet(viewsets.ReadOnlyModelViewSet):
    """SMS log viewer"""
    queryset = SMSLog.objects.all()
    serializer_class = SMSLogSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['recipient_phone']
    filterset_fields = ['status']