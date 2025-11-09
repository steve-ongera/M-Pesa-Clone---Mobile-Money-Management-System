from rest_framework import permissions


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object or admins to access it.
    """
    
    def has_object_permission(self, request, view, obj):
        # Admin can access everything
        if request.user.user_type == 'ADMIN':
            return True
        
        # Check if object has a user field
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        # Check if object is the user itself
        if obj == request.user:
            return True
        
        return False


class IsAgent(permissions.BasePermission):
    """
    Permission to only allow agents to perform certain actions.
    """
    
    def has_permission(self, request, view):
        return request.user.user_type in ['AGENT', 'SUPER_AGENT']


class IsMerchant(permissions.BasePermission):
    """
    Permission to only allow merchants to perform certain actions.
    """
    
    def has_permission(self, request, view):
        return request.user.user_type == 'MERCHANT'


class IsVerifiedUser(permissions.BasePermission):
    """
    Permission to only allow verified users.
    """
    
    def has_permission(self, request, view):
        return request.user.is_verified


class IsActiveWallet(permissions.BasePermission):
    """
    Permission to check if user's wallet is active.
    """
    
    def has_permission(self, request, view):
        try:
            return request.user.wallet.is_active
        except:
            return False


class CanPerformTransaction(permissions.BasePermission):
    """
    Permission to check if user can perform transactions.
    """
    
    def has_permission(self, request, view):
        # Check if user is verified
        if not request.user.is_verified:
            return False
        
        # Check if wallet is active
        try:
            if not request.user.wallet.is_active:
                return False
        except:
            return False
        
        return True


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow admins to edit, but allow read for authenticated users.
    """
    
    def has_permission(self, request, view):
        # Read permissions are allowed for authenticated users
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        
        # Write permissions are only allowed for admins
        return request.user.user_type == 'ADMIN'


class IsAgentOwner(permissions.BasePermission):
    """
    Permission to check if user is the agent owner.
    """
    
    def has_object_permission(self, request, view, obj):
        if request.user.user_type == 'ADMIN':
            return True
        
        if hasattr(obj, 'agent'):
            return obj.agent.user == request.user
        
        return False


class IsMerchantOwner(permissions.BasePermission):
    """
    Permission to check if user is the merchant owner.
    """
    
    def has_object_permission(self, request, view, obj):
        if request.user.user_type == 'ADMIN':
            return True
        
        if hasattr(obj, 'merchant'):
            return obj.merchant.user == request.user
        
        return False


class CanAccessTransaction(permissions.BasePermission):
    """
    Permission to check if user can access a transaction.
    """
    
    def has_object_permission(self, request, view, obj):
        # Admin can access all transactions
        if request.user.user_type == 'ADMIN':
            return True
        
        # Check different transaction types
        if hasattr(obj, 'sender') and hasattr(obj, 'receiver'):
            return request.user in [obj.sender, obj.receiver]
        
        if hasattr(obj, 'customer'):
            return request.user == obj.customer
        
        if hasattr(obj, 'buyer'):
            return request.user == obj.buyer
        
        if hasattr(obj, 'payer'):
            return request.user == obj.payer
        
        if hasattr(obj, 'borrower'):
            return request.user == obj.borrower
        
        # For wallet transactions
        if hasattr(obj, 'wallet'):
            return request.user == obj.wallet.user
        
        return False