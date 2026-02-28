from django.contrib import admin
from django.utils.safestring import mark_safe
from .models import (
    Company, Category, Product, StockMovement, StockCount,
    PurchaseOrder, PurchaseOrderItem, ProductStatusAdjustment, ProductStatusAdjustmentItem,
    Purchase, PurchaseItem, PurchaseReturn, PurchaseReturnItem,
    CompanyPayment, PaymentAllocation, CompanyAccount
)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['logo_preview', 'company_code', 'company_name', 'contact_person', 'phone_number', 'city', 'is_active']
    list_filter = ['is_active', 'country', 'city']
    search_fields = ['company_name', 'company_code', 'contact_person', 'email', 'tax_id']
    readonly_fields = ['logo_preview_large', 'created_at', 'updated_at']
    
    fieldsets = (
        ('🏢 Basic Information', {
            'fields': ('company_name', 'company_code', 'tagline', 'description')
        }),
        ('🎨 Branding', {
            'fields': ('logo', 'logo_receipt', 'logo_preview_large', 'primary_color')
        }),
        ('📞 Contact Information', {
            'fields': ('contact_person', 'phone_number', 'secondary_phone', 'email', 'secondary_email', 'website')
        }),
        ('📍 Address', {
            'fields': ('address', 'city', 'country')
        }),
        ('🌐 Social Media', {
            'fields': ('facebook_url', 'instagram_url', 'linkedin_url'),
            'classes': ['collapse']
        }),
        ('📋 Business Information', {
            'fields': ('tax_id', 'registration_number'),
            'classes': ['collapse']
        }),
        ('⚙️ Settings', {
            'fields': ('is_active', 'notes', 'created_at', 'updated_at')
        }),
    )
    
    def logo_preview(self, obj):
        """Small logo preview for list view"""
        if obj.logo:
            from django.utils.html import format_html
            return format_html('<img src="{}" style="width: 40px; height: 40px; object-fit: contain; border-radius: 4px;" />', obj.logo.url)
        return mark_safe('<span style="color: gray;">No logo</span>')
    logo_preview.short_description = 'Logo'
    
    def logo_preview_large(self, obj):
        """Large logo preview for detail view"""
        if obj.logo:
            from django.utils.html import format_html
            return format_html('<img src="{}" style="max-width: 300px; max-height: 200px; object-fit: contain; border: 1px solid #ddd; padding: 10px; border-radius: 8px; background: white;" />', obj.logo.url)
        return mark_safe('<span style="color: gray;">No logo uploaded</span>')
    logo_preview_large.short_description = 'Logo Preview'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['display_order', 'product_code', 'product_name', 'size', 'bottles_per_pack', 'marked_price', 'discount_percentage', 'shop_price', 'company_price', 'quantity_in_stock', 'pack_loose_display', 'is_low_stock', 'is_active']
    list_filter = ['is_active', 'company', 'category', 'size']
    search_fields = ['product_code', 'product_name', 'barcode']
    readonly_fields = ['discount_amount', 'shop_price', 'company_discount_amount', 'company_price', 'our_profit_per_unit', 'packs', 'loose', 'pack_loose_display', 'created_at', 'updated_at']
    list_editable = ['display_order']
    list_display_links = ['product_code', 'product_name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('product_code', 'product_name', 'description')
        }),
        ('Company & Classification', {
            'fields': ('company', 'category')
        }),
        ('Product Specifications', {
            'fields': ('size', 'marked_price', 'bottles_per_pack')
        }),
        ('Inventory', {
            'fields': ('quantity_in_stock', 'minimum_stock_level', 'packs', 'loose', 'pack_loose_display')
        }),
        ('Pricing - To Shops', {
            'fields': ('discount_percentage', 'discount_amount', 'shop_price'),
            'description': 'Pricing when selling to shops'
        }),
        ('Pricing - From Company', {
            'fields': ('company_discount_percentage', 'company_discount_amount', 'company_price', 'our_profit_per_unit'),
            'description': 'Price we pay to company and our profit margin'
        }),
        ('FOC (Free of Charge) Ratios', {
            'fields': (('company_foc_buy', 'company_foc_free'), ('shop_foc_buy', 'shop_foc_free')),
            'description': 'FOC ratios: company_foc = FOC we get from company, shop_foc = FOC we give to shops'
        }),
        ('Display Settings', {
            'fields': ('display_order',)
        }),
        ('Additional Info', {
            'fields': ('barcode', 'product_image', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(StockCount)
class StockCountAdmin(admin.ModelAdmin):
    list_display = ['count_date', 'product', 'system_stock', 'physical_count', 'variance', 'stock_updated', 'counted_by']
    list_filter = ['stock_updated', 'count_date']
    search_fields = ['product__product_code', 'product__product_name']
    readonly_fields = ['count_date', 'variance']
    
    fieldsets = (
        ('Stock Count Information', {
            'fields': ('product', 'system_stock', 'physical_count', 'variance')
        }),
        ('Adjustment', {
            'fields': ('adjustment_reason', 'stock_updated')
        }),
        ('Audit', {
            'fields': ('counted_by', 'count_date')
        }),
    )


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ['product', 'movement_type', 'quantity', 'previous_quantity', 'new_quantity', 'reference_number', 'created_at', 'created_by']
    list_filter = ['movement_type', 'created_at']
    search_fields = ['product__product_code', 'reference_number']
    readonly_fields = ['created_at']


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1
    readonly_fields = ['total_bottles', 'value_before_discount', 'discount_amount', 'line_total']
    fields = ['product', 'packs', 'bottles_per_pack', 'total_bottles', 'unit_price', 'value_before_discount', 'discount_percentage', 'discount_amount', 'line_total', 'received_quantity']


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['po_number', 'company', 'order_date', 'status', 'total', 'created_at']
    list_filter = ['status', 'company', 'order_date']
    search_fields = ['po_number', 'company__company_name']
    readonly_fields = ['created_at']
    inlines = [PurchaseOrderItemInline]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('po_number', 'company', 'order_date', 'expected_delivery_date', 'received_date', 'status')
        }),
        ('Totals', {
            'fields': ('subtotal', 'discount', 'total')
        }),
        ('Additional Info', {
            'fields': ('notes', 'created_at', 'created_by')
        }),
    )


class ProductStatusAdjustmentItemInline(admin.TabularInline):
    model = ProductStatusAdjustmentItem
    extra = 0
    readonly_fields = ['stock_updated', 'previous_resaleable', 'new_resaleable', 'previous_non_resaleable', 'new_non_resaleable']
    fields = ['product', 'quantity', 'stock_updated', 'previous_resaleable', 'new_resaleable', 'previous_non_resaleable', 'new_non_resaleable']


@admin.register(ProductStatusAdjustment)
class ProductStatusAdjustmentAdmin(admin.ModelAdmin):
    list_display = ['adjustment_number', 'adjustment_date', 'status_type', 'total_items', 'total_quantity', 'approval_status', 'stock_action', 'adjusted_by']
    list_filter = ['status_type', 'approval_status', 'stock_action', 'adjustment_date']
    search_fields = ['adjustment_number', 'reason', 'adjusted_by__username']
    readonly_fields = ['adjustment_number', 'adjustment_date', 'adjusted_by', 'approved_by', 'approved_at']
    inlines = [ProductStatusAdjustmentItemInline]
    
    fieldsets = (
        ('Adjustment Info', {
            'fields': ('adjustment_number', 'status_type', 'reason', 'reference_number', 'stock_action')
        }),
        ('Approval', {
            'fields': ('approval_status', 'approved_by', 'approved_at')
        }),
        ('Audit', {
            'fields': ('adjustment_date', 'adjusted_by', 'stock_updated')
        }),
    )


# Purchase Management

class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    extra = 1
    fields = ['product', 'packs', 'bottles_per_pack', 'quantity', 'foc_quantity', 'unit_price', 'discount_percentage', 'line_total']
    readonly_fields = ['line_total']


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ['grn_number', 'company', 'grn_date', 'status', 'total_amount', 'payment_status', 'stock_updated']
    list_filter = ['status', 'payment_status', 'grn_date', 'company']
    search_fields = ['grn_number', 'supplier_invoice_number', 'company__company_name']
    readonly_fields = ['grn_number', 'created_at', 'updated_at']
    inlines = [PurchaseItemInline]
    
    fieldsets = (
        ('GRN Information', {
            'fields': ('grn_number', 'company', 'grn_date', 'invoice_date', 'supplier_invoice_number')
        }),
        ('Status', {
            'fields': ('status', 'payment_status')
        }),
        ('Financial', {
            'fields': ('subtotal', 'discount_amount', 'total_amount', 'amount_paid')
        }),
        ('Tracking', {
            'fields': ('stock_updated', 'created_by', 'received_by')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


class PurchaseReturnItemInline(admin.TabularInline):
    model = PurchaseReturnItem
    extra = 1
    fields = ['product', 'quantity', 'unit_price', 'line_total', 'batch_number', 'expiry_date']
    readonly_fields = ['line_total']


@admin.register(PurchaseReturn)
class PurchaseReturnAdmin(admin.ModelAdmin):
    list_display = ['pr_number', 'company', 'return_date', 'return_reason', 'status', 'settlement_type', 'total_amount']
    list_filter = ['status', 'return_reason', 'settlement_type', 'return_date']
    search_fields = ['pr_number', 'company__company_name', 'credit_note_number']
    readonly_fields = ['pr_number', 'created_at', 'updated_at', 'approved_at']
    inlines = [PurchaseReturnItemInline]
    
    fieldsets = (
        ('Return Information', {
            'fields': ('pr_number', 'purchase', 'company', 'return_date', 'sent_date')
        }),
        ('Return Details', {
            'fields': ('return_reason', 'detailed_reason', 'status', 'settlement_type')
        }),
        ('Financial', {
            'fields': ('total_amount', 'credit_amount', 'credit_note_number')
        }),
        ('Approval', {
            'fields': ('approved_by', 'approved_at')
        }),
        ('Tracking', {
            'fields': ('stock_updated', 'created_by')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


class PaymentAllocationInline(admin.TabularInline):
    model = PaymentAllocation
    extra = 0
    readonly_fields = ['created_at']
    raw_id_fields = ['purchase']
    fields = ['purchase', 'allocated_amount', 'notes', 'created_at']


@admin.register(CompanyPayment)
class CompanyPaymentAdmin(admin.ModelAdmin):
    list_display = ['payment_number', 'company', 'payment_date', 'payment_method', 'total_amount', 'allocated_amount', 'unallocated_amount', 'is_fully_allocated']
    list_filter = ['payment_method', 'payment_date', 'company']
    search_fields = ['payment_number', 'company__company_name', 'cheque_number', 'transfer_reference']
    readonly_fields = ['payment_number', 'created_at', 'updated_at', 'allocated_amount', 'unallocated_amount', 'is_fully_allocated']
    inlines = [PaymentAllocationInline]
    raw_id_fields = ['company', 'company_transaction']
    
    fieldsets = (
        ('Payment Information', {
            'fields': ('payment_number', 'company', 'payment_date', 'payment_method', 'total_amount')
        }),
        ('Cheque Details', {
            'fields': ('cheque_number', 'cheque_date', 'bank_name'),
            'classes': ('collapse',),
        }),
        ('Bank Transfer Details', {
            'fields': ('transfer_reference', 'transfer_date'),
            'classes': ('collapse',),
        }),
        ('Allocation Summary', {
            'fields': ('allocated_amount', 'unallocated_amount', 'is_fully_allocated')
        }),
        ('Notes & Links', {
            'fields': ('reference_notes', 'company_transaction')
        }),
        ('Audit', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )


@admin.register(PaymentAllocation)
class PaymentAllocationAdmin(admin.ModelAdmin):
    list_display = ['payment', 'purchase', 'allocated_amount', 'created_at']
    list_filter = ['created_at', 'payment__payment_method']
    search_fields = ['payment__payment_number', 'purchase__grn_number']
    readonly_fields = ['created_at']
    raw_id_fields = ['payment', 'purchase']

