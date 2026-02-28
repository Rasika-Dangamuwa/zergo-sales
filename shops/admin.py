from django.contrib import admin
# from django.contrib.gis.admin import GISModelAdmin
from .models import Shop, ShopVisit


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):  # Changed from GISModelAdmin to admin.ModelAdmin
    list_display = ['shop_code', 'shop_name', 'owner_name', 'city', 'phone_number', 'assigned_sales_rep', 'is_active']
    list_filter = ['shop_type', 'is_active', 'city', 'assigned_sales_rep']
    search_fields = ['shop_code', 'shop_name', 'owner_name', 'phone_number']
    readonly_fields = ['created_at', 'updated_at', 'created_by']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('shop_code', 'shop_name', 'owner_name', 'shop_type')
        }),
        ('Contact Details', {
            'fields': ('phone_number', 'alternate_phone', 'email')
        }),
        ('Address', {
            'fields': ('address_line1', 'address_line2', 'city', 'district', 'postal_code', 'latitude', 'longitude')
        }),
        ('Business Information', {
            'fields': ('business_registration_no', 'tax_id')
        }),
        ('Credit Management', {
            'fields': ('credit_limit', 'current_balance')
        }),
        ('Assignment & Status', {
            'fields': ('assigned_sales_rep', 'is_active', 'notes')
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at', 'created_by')
        }),
    )


@admin.register(ShopVisit)
class ShopVisitAdmin(admin.ModelAdmin):
    list_display = ['shop', 'sales_rep', 'visit_date']
    list_filter = ['visit_date', 'sales_rep']
    search_fields = ['shop__shop_name', 'sales_rep__username']
