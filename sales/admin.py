from django.contrib import admin
from .models import (
    Sale, SaleItem, Return, ReturnItem,
    Bill, BillItem, PrintManager, ItemExchange, ExchangeItem,
    CommissionRateHistory, CommissionTransaction
)


# Sale/SaleItem/Payment models are hidden - system uses Bill model instead
# These models exist in code but are not used (0 records in database)
# Kept for potential future use or migration reference

# class SaleItemInline(admin.TabularInline):
#     model = SaleItem
#     extra = 1
#     fields = ['product', 'quantity', 'unit_price', 'discount_percentage', 'tax_percentage', 'line_total']
#     readonly_fields = ['line_total']


# @admin.register(Sale)
# class SaleAdmin(admin.ModelAdmin):
#     list_display = ['sale_number', 'shop', 'sales_rep', 'sale_date', 'total_amount', 'payment_status', 'delivery_status']
#     list_filter = ['sale_status', 'payment_status', 'delivery_status', 'sale_date', 'sales_rep']
#     search_fields = ['sale_number', 'shop__shop_name']
#     readonly_fields = ['sale_number', 'created_at', 'updated_at', 'subtotal', 'tax_amount', 'total_amount', 'paid_amount', 'balance_amount']
#     inlines = [SaleItemInline]
#     
#     fieldsets = (
#         ('Sale Information', {
#             'fields': ('sale_number', 'sale_date', 'shop', 'sales_rep')
#         }),
#         ('Financial Details', {
#             'fields': ('subtotal', 'discount_percentage', 'discount_amount', 'tax_amount', 'total_amount', 'paid_amount', 'balance_amount')
#         }),
#         ('Status', {
#             'fields': ('sale_status', 'payment_status', 'delivery_status')
#         }),
#         ('Delivery Details', {
#             'fields': ('vehicle_number', 'delivered_by')
#         }),
#         ('Additional', {
#             'fields': ('notes', 'created_at', 'updated_at')
#         }),
#     )


# @admin.register(Payment)
# class PaymentAdmin(admin.ModelAdmin):
#     list_display = ['payment_number', 'sale', 'payment_type', 'amount', 'collection_status', 'commission_eligible', 'commission_month']
#     list_filter = ['payment_type', 'collection_status', 'commission_eligible', 'payment_date']
#     search_fields = ['payment_number', 'sale__sale_number', 'cheque_number', 'reference_number']
#     readonly_fields = ['payment_number', 'commission_eligible', 'commission_month', 'created_at', 'updated_at']
#     
#     fieldsets = (
#         ('Payment Information', {
#             'fields': ('payment_number', 'sale', 'payment_date', 'payment_type', 'amount')
#         }),
#         ('Payment Details', {
#             'fields': ('cheque_number', 'cheque_date', 'bank_name', 'reference_number')
#         }),
#         ('Collection Status', {
#             'fields': ('collection_status', 'collected_date')
#         }),
#         ('Commission Tracking', {
#             'fields': ('commission_eligible', 'commission_month', 'collected_by')
#         }),
#         ('Additional', {
#             'fields': ('notes', 'created_at', 'updated_at')
#         }),
#     )


class ReturnItemInline(admin.TabularInline):
    model = ReturnItem
    extra = 1


@admin.register(Return)
class ReturnAdmin(admin.ModelAdmin):
    list_display = ['return_number', 'shop', 'return_date', 'total_amount', 'return_reason', 'settlement_status']
    list_filter = ['return_reason', 'return_date', 'settlement_method', 'settlement_status']
    search_fields = ['return_number', 'shop__shop_name', 'sale__sale_number', 'bill__bill_number']
    readonly_fields = ['return_number', 'created_at', 'updated_at']
    inlines = [ReturnItemInline]
    
    fieldsets = (
        ('Return Information', {
            'fields': ('return_number', 'return_date', 'sale', 'bill', 'shop', 'created_by')
        }),
        ('Return Details', {
            'fields': ('return_reason', 'settlement_method', 'settlement_status', 'notes')
        }),
        ('Financial', {
            'fields': ('total_amount', 'refund_amount', 'applied_amount')
        }),
        ('Cash Settlement', {
            'fields': ('cash_paid_by', 'cash_paid_at', 'cash_receipt_number')
        }),
        ('Manager Verification', {
            'fields': ('is_verified', 'verified_by', 'verified_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


# CommissionRecordAdmin removed - replaced by CommissionTransactionAdmin
# See CommissionTransactionAdmin below for real-time commission tracking


# OLD MODELS (for backward compatibility)

class BillItemInline(admin.TabularInline):
    model = BillItem
    extra = 1
    fields = ['product', 'quantity', 'unit_price', 'discount_percentage', 'tax_percentage', 'line_total']
    readonly_fields = ['line_total']


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ['bill_number', 'shop', 'sales_rep', 'bill_date', 'total_amount', 'settlement_status', 'bill_status']
    list_filter = ['bill_status', 'settlement_status', 'bill_date', 'sales_rep']
    search_fields = ['bill_number', 'shop__shop_name']
    readonly_fields = ['created_at', 'updated_at', 'subtotal', 'tax_amount', 'total_amount', 'balance_amount']
    inlines = [BillItemInline]
    
    fieldsets = (
        ('Bill Information', {
            'fields': ('bill_number', 'bill_date', 'shop', 'sales_rep')
        }),
        ('Financial Details', {
            'fields': ('subtotal', 'discount_percentage', 'discount_amount', 'tax_amount', 'total_amount', 'paid_amount', 'balance_amount')
        }),
        ('Status', {
            'fields': ('bill_status', 'settlement_status', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(PrintManager)
class PrintManagerAdmin(admin.ModelAdmin):
    """
    Unified Print Management Administration
    
    Replaces BillSettings, BillTemplate, CompanyBranding, and PrinterProfile admins.
    Provides comprehensive print management in one place.
    """
    
    list_display = [
        'profile_name', 
        'user', 
        'receipt_type',
        'paper_size', 
        'is_default', 
        'is_bluetooth',
        'is_active',
        'last_used_at'
    ]
    
    list_filter = [
        'receipt_type',
        'paper_size', 
        'is_default', 
        'is_bluetooth',
        'is_active',
        'language',
        'cut_behavior'
    ]
    
    search_fields = [
        'profile_name', 
        'company_name',
        'printer_name',
        'bluetooth_address',
        'user__username'
    ]
    
    readonly_fields = ['created_at', 'updated_at', 'last_used_at']
    
    fieldsets = (
        ('✨ Profile Information', {
            'fields': (
                'user',
                'profile_name',
                'receipt_type',
                'is_default',
                'is_active'
            ),
            'description': 'Basic profile settings. Each user can have multiple profiles for different receipt types and printers.'
        }),
        
        ('🏢 Company Branding', {
            'fields': (
                'company_logo',
                ('logo_width', 'logo_height'),
                'show_logo',
                'company_name',
                'company_tagline',
                ('address_line1', 'address_line2'),
                ('city', 'postal_code'),
                ('phone', 'email'),
                'website',
                'tax_id',
                ('show_tagline', 'show_address', 'show_contact', 'show_tax_id')
            ),
            'description': 'Company branding and contact information shown on receipts'
        }),
        
        ('📄 Receipt Template Settings', {
            'fields': (
                'custom_header',
                ('footer_line1', 'footer_line2', 'footer_line3'),
                'language',
                ('show_barcode', 'show_qr_code', 'qr_code_size'),
                ('show_tax_breakdown', 'show_discount_details'),
                ('show_payment_method', 'show_sales_rep', 'show_shop_location')
            ),
            'description': 'What information to display on receipts'
        }),
        
        ('🖨️ Printer Hardware Settings', {
            'fields': (
                'paper_size',
                'printer_name',
                'bluetooth_address',
                'is_bluetooth',
                ('print_density', 'print_speed'),
                ('cut_behavior', 'feed_lines'),
                'auto_print'
            ),
            'description': 'Physical printer configuration and behavior'
        }),
        
        ('📋 Print Copies Per Receipt Type', {
            'fields': (
                ('bill_print_copies', 'payment_print_copies'),
                ('return_print_copies', 'field_receipt_print_copies')
            ),
            'description': 'Number of copies to print for each receipt type'
        }),
        
        ('📐 Layout & Margins', {
            'fields': (
                ('margin_top', 'margin_bottom'),
                ('margin_left', 'margin_right'),
                ('font_size_header', 'font_size_body', 'font_size_footer')
            ),
            'classes': ('collapse',),
            'description': 'Fine-tune margins and font sizes (0 = auto-optimize based on paper size)'
        }),
        
        ('⚙️ Advanced ESC/POS Commands', {
            'fields': (
                'custom_init_commands',
                'custom_cut_commands'
            ),
            'classes': ('collapse',),
            'description': 'Custom ESC/POS commands for advanced thermal printer control (hex format)'
        }),
        
        ('📅 Metadata', {
            'fields': (
                'created_at',
                'updated_at',
                'last_used_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Show only current user's profiles unless superuser"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)
    
    def save_model(self, request, obj, form, change):
        """Auto-set user if creating new profile"""
        if not change:  # Creating new
            obj.user = request.user
        super().save_model(request, obj, form, change)
    
    actions = ['duplicate_profile', 'mark_as_used']
    
    def duplicate_profile(self, request, queryset):
        """Duplicate selected profiles"""
        for profile in queryset:
            profile.pk = None  # Create new instance
            profile.profile_name = f"{profile.profile_name} (Copy)"
            profile.is_default = False
            profile.save()
        self.message_user(request, f"Duplicated {queryset.count()} profile(s)")
    duplicate_profile.short_description = "Duplicate selected profiles"
    
    def mark_as_used(self, request, queryset):
        """Mark profiles as recently used"""
        for profile in queryset:
            profile.mark_as_used()
        self.message_user(request, f"Marked {queryset.count()} profile(s) as used")
    mark_as_used.short_description = "Mark as recently used"


# Exchange Management

class ExchangeItemInline(admin.TabularInline):
    model = ExchangeItem
    extra = 0
    fields = ['returned_product', 'returned_quantity', 'replacement_product', 'replacement_quantity', 'is_resellable', 'notes']


@admin.register(ItemExchange)
class ExchangeAdmin(admin.ModelAdmin):
    list_display = ['exchange_number', 'shop', 'exchange_date', 'exchange_status', 'exchange_reason', 'created_by']
    list_filter = ['exchange_status', 'exchange_reason', 'exchange_date']
    search_fields = ['exchange_number', 'shop__shop_name']
    readonly_fields = ['exchange_number', 'created_at', 'updated_at', 'completed_at']
    inlines = [ExchangeItemInline]
    
    fieldsets = (
        ('Exchange Information', {
            'fields': ('exchange_number', 'exchange_date', 'shop', 'created_by')
        }),
        ('Status & Reason', {
            'fields': ('exchange_status', 'exchange_reason', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


# CommissionSettingsAdmin removed - use CommissionRateHistoryAdmin instead
# All commission rates managed through rate history with effective dates


@admin.register(CommissionRateHistory)
class CommissionRateHistoryAdmin(admin.ModelAdmin):
    """Admin interface for historical commission rates"""
    
    list_display = ['rate', 'effective_from', 'effective_to', 'is_active', 'created_by', 'created_at']
    list_filter = ['is_active', 'effective_from', 'created_at']
    search_fields = ['notes']
    readonly_fields = ['created_at', 'created_by']
    date_hierarchy = 'effective_from'
    
    fieldsets = (
        ('Rate Information', {
            'fields': ('rate', 'effective_from', 'effective_to', 'is_active')
        }),
        ('Additional Details', {
            'fields': ('notes', 'created_by', 'created_at')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Automatically set created_by on new records"""
        if not change:  # Only on creation
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(CommissionTransaction)
class CommissionTransactionAdmin(admin.ModelAdmin):
    """Admin interface for commission transactions"""
    
    list_display = [
        'transaction_date', 'sales_rep', 'transaction_type', 'bill', 
        'sales_amount', 'collected_amount', 'return_amount',
        'applicable_rate', 'commission_earned', 'running_balance'
    ]
    list_filter = ['transaction_type', 'transaction_date', 'sales_rep']
    search_fields = ['sales_rep__username', 'sales_rep__first_name', 'sales_rep__last_name', 'bill__sale_number', 'notes']
    readonly_fields = ['applicable_rate', 'commission_earned', 'running_balance', 'created_at']
    date_hierarchy = 'transaction_date'
    
    fieldsets = (
        ('Transaction Details', {
            'fields': ('transaction_type', 'transaction_date', 'sales_rep', 'bill')
        }),
        ('Financial Amounts', {
            'fields': ('sales_amount', 'collected_amount', 'return_amount')
        }),
        ('Commission Calculation', {
            'fields': ('applicable_rate', 'commission_earned', 'running_balance'),
            'description': 'These fields are automatically calculated'
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """Prevent manual creation - should be created via signals"""
        return False

