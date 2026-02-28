from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User
from .money_account_models import UserMoneyAccount, MoneyTransaction, AdvanceRequest


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'user_type', 'is_active_employee']
    list_filter = ['user_type', 'is_active_employee', 'is_staff']
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login',)}),
        ('Additional Info', {
            'fields': ('user_type', 'phone_number', 'address', 'profile_picture', 'employee_id', 'is_active_employee')
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Additional Info', {
            'fields': ('user_type', 'phone_number', 'employee_id')
        }),
    )
    
    readonly_fields = ['date_joined', 'last_login']


@admin.register(UserMoneyAccount)
class UserMoneyAccountAdmin(admin.ModelAdmin):
    list_display = ['user', 'current_balance', 'total_credited', 'total_debited', 'outstanding_advance', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['user__username', 'user__first_name', 'user__last_name']
    readonly_fields = ['total_credited', 'total_debited', 'total_advance_given', 'total_advance_recovered', 'current_balance', 'created_at', 'updated_at']
    
    fieldsets = (
        ('User', {
            'fields': ('user', 'is_active')
        }),
        ('Opening Balance', {
            'fields': ('opening_balance', 'opening_date', 'opening_notes')
        }),
        ('Current Status', {
            'fields': ('current_balance', 'total_credited', 'total_debited', 'total_advance_given', 'total_advance_recovered')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )


@admin.register(MoneyTransaction)
class MoneyTransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_number', 'account_user', 'transaction_type', 'amount', 'transaction_date', 'created_by']
    list_filter = ['transaction_type', 'payment_method', 'transaction_date']
    search_fields = ['transaction_number', 'account__user__username', 'account__user__first_name', 'account__user__last_name', 'description']
    readonly_fields = ['transaction_number', 'created_at', 'updated_at']
    date_hierarchy = 'transaction_date'
    
    fieldsets = (
        ('Transaction Details', {
            'fields': ('transaction_number', 'account', 'transaction_type', 'amount', 'transaction_date')
        }),
        ('Payment Information', {
            'fields': ('payment_method', 'reference_number')
        }),
        ('Description', {
            'fields': ('description', 'notes')
        }),
        ('References', {
            'fields': ('advance_request', 'commission_reference')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )
    
    def account_user(self, obj):
        return obj.account.user.get_full_name()
    account_user.short_description = 'User'
    account_user.admin_order_field = 'account__user'


@admin.register(AdvanceRequest)
class AdvanceRequestAdmin(admin.ModelAdmin):
    list_display = ['request_number', 'user', 'requested_amount', 'approved_amount', 'status', 'request_date']
    list_filter = ['status', 'request_date', 'approved_at', 'paid_at']
    search_fields = ['request_number', 'user__username', 'user__first_name', 'user__last_name', 'reason']
    readonly_fields = ['request_number', 'created_at', 'updated_at']
    date_hierarchy = 'request_date'
    
    fieldsets = (
        ('Request Details', {
            'fields': ('request_number', 'user', 'requested_amount', 'reason', 'request_date')
        }),
        ('Approval', {
            'fields': ('status', 'approved_amount', 'approved_by', 'approved_at', 'approval_notes')
        }),
        ('Rejection', {
            'fields': ('rejection_reason',),
            'classes': ('collapse',)
        }),
        ('Payment', {
            'fields': ('paid_at', 'payment_method', 'payment_reference')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )
