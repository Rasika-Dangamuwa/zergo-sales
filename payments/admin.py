from django.contrib import admin
from .models import SalesAccountSettlement, SettlementAttachment, BadDebtWriteOff


@admin.register(SalesAccountSettlement)
class SalesAccountSettlementAdmin(admin.ModelAdmin):
    list_display = ['settlement_number', 'shop', 'bill', 'settlement_method', 'amount', 'settlement_status', 'received_by', 'settlement_date']
    list_filter = ['settlement_status', 'settlement_method', 'settlement_date', 'received_by']
    search_fields = ['settlement_number', 'shop__shop_name', 'bill__bill_number', 'reference_number']
    readonly_fields = ['settlement_number', 'created_at', 'updated_at']
    date_hierarchy = 'settlement_date'
    
    fieldsets = (
        ('Settlement Information', {
            'fields': ('settlement_number', 'settlement_date', 'settlement_method', 'amount', 'settlement_status')
        }),
        ('Related Records', {
            'fields': ('shop', 'bill', 'return_ref')
        }),
        ('Settlement Method Details', {
            'fields': ('reference_number', 'bank_name', 'cheque_date'),
            'classes': ('collapse',)
        }),
        ('Verification', {
            'fields': ('received_by', 'verified_by', 'verified_at', 'is_provisional')
        }),
        ('Additional Information', {
            'fields': ('notes', 'attachment')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SettlementAttachment)
class SettlementAttachmentAdmin(admin.ModelAdmin):
    list_display = ['settlement', 'description', 'uploaded_at']
    list_filter = ['uploaded_at']
    search_fields = ['settlement__settlement_number', 'description']
    readonly_fields = ['uploaded_at']


@admin.register(BadDebtWriteOff)
class BadDebtWriteOffAdmin(admin.ModelAdmin):
    list_display = ['write_off_number', 'get_customer', 'bill', 'write_off_amount', 'reason', 'approval_status', 'executed', 'write_off_date']
    list_filter = ['approval_status', 'executed', 'reason', 'write_off_date']
    search_fields = ['write_off_number', 'shop__shop_name', 'customer_name', 'bill__bill_number', 'detailed_notes']
    readonly_fields = ['write_off_number', 'write_off_date', 'created_at', 'updated_at']
    date_hierarchy = 'write_off_date'
    
    def get_customer(self, obj):
        """Display shop name or customer name for unregistered"""
        if obj.shop:
            return obj.shop.shop_name
        return obj.customer_name or 'Unregistered Customer'
    get_customer.short_description = 'Customer'
    
    fieldsets = (
        ('Write-Off Information', {
            'fields': ('write_off_number', 'write_off_date', 'reason', 'detailed_notes')
        }),
        ('Related Records', {
            'fields': ('shop', 'customer_name', 'bill')
        }),
        ('Financial Details', {
            'fields': ('original_amount', 'paid_amount', 'write_off_amount')
        }),
        ('Approval Workflow', {
            'fields': ('approval_status', 'requested_by', 'approved_by', 'approval_date', 'rejection_reason')
        }),
        ('Execution Tracking', {
            'fields': ('executed', 'executed_at', 'bill_updated', 'shop_balance_updated')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
