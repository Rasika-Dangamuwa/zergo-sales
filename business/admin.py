"""
Admin Interface for Business Settings

Provides comprehensive admin interface for managing distributor business profile,
bank accounts, and additional business addresses.

Author: GitHub Copilot
Date: January 20, 2026
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import DistributorProfile, BankAccount, BusinessAddress


class BankAccountInline(admin.TabularInline):
    """Inline admin for bank accounts"""
    model = BankAccount
    extra = 1
    fields = ['bank_name', 'branch_name', 'account_number', 'account_type', 'is_primary', 'is_active']
    classes = ['collapse']


class BusinessAddressInline(admin.TabularInline):
    """Inline admin for business addresses"""
    model = BusinessAddress
    extra = 1
    fields = ['address_type', 'location_name', 'city', 'phone', 'is_active']
    classes = ['collapse']


@admin.register(DistributorProfile)
class DistributorProfileAdmin(admin.ModelAdmin):
    """Comprehensive admin for Distributor Business Profile"""
    
    list_display = ['business_name', 'business_type', 'primary_phone', 'primary_email', 'city', 'is_active_badge', 'updated_at']
    list_filter = ['is_active', 'business_type', 'country']
    search_fields = ['business_name', 'trade_name', 'primary_email', 'primary_phone', 'tax_id', 'business_registration_number']
    readonly_fields = ['created_at', 'updated_at']
    
    inlines = [BankAccountInline, BusinessAddressInline]
    
    fieldsets = (
        ('🏢 Basic Information', {
            'fields': ('business_name', 'trade_name', 'tagline', 'description', 'business_type', 'established_date')
        }),
        ('📋 Registration & Legal', {
            'fields': ('business_registration_number', 'tax_id', 'vat_number', 'svat_number', 'trade_license_number', 'import_export_license'),
            'classes': ['collapse']
        }),
        ('📞 Contact Information', {
            'fields': ('primary_phone', 'secondary_phone', 'mobile_phone', 'fax_number', 'primary_email', 'secondary_email', 'support_email', 'accounts_email', 'website')
        }),
        ('📍 Primary Address', {
            'fields': ('address_line1', 'address_line2', 'city', 'district', 'postal_code', 'country', 'latitude', 'longitude')
        }),
        ('🌐 Social Media', {
            'fields': ('facebook_url', 'instagram_url', 'twitter_url', 'linkedin_url', 'whatsapp_number'),
            'classes': ['collapse']
        }),
        ('🎨 Branding & Visual Identity', {
            'fields': ('logo', 'logo_receipt', 'logo_document', 'favicon', 'primary_color', 'secondary_color', 'accent_color'),
            'classes': ['collapse']
        }),
        ('⚙️ Operational Settings', {
            'fields': ('currency_code', 'currency_symbol', 'fiscal_year_start_month', 'default_payment_terms_days', 'business_hours')
        }),
        ('🧾 Receipt/Invoice Settings', {
            'fields': ('receipt_footer_line1', 'receipt_footer_line2', 'receipt_footer_line3', 'terms_and_conditions', 'return_policy', 'warranty_info'),
            'classes': ['collapse']
        }),
        ('👁️ Display Preferences', {
            'fields': ('show_logo_on_receipts', 'show_tagline', 'show_address_on_receipts', 'show_contact_on_receipts', 'show_social_media', 'show_tax_info'),
            'classes': ['collapse']
        }),
        ('📝 Metadata', {
            'fields': ('is_active', 'notes', 'created_at', 'updated_at')
        }),
    )
    
    def is_active_badge(self, obj):
        """Display active status with colored badge"""
        if obj.is_active:
            return mark_safe('<span style="color: green; font-weight: bold;">✓ ACTIVE</span>')
        return mark_safe('<span style="color: gray;">Inactive</span>')
    is_active_badge.short_description = 'Status'
    
    def save_model(self, request, obj, form, change):
        """Ensure only one active profile exists"""
        if obj.is_active:
            DistributorProfile.objects.exclude(pk=obj.pk).update(is_active=False)
        super().save_model(request, obj, form, change)


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    """Admin for Bank Accounts"""
    
    list_display = ['bank_name', 'account_number', 'account_type', 'currency', 'is_primary_badge', 'is_active', 'distributor']
    list_filter = ['is_primary', 'is_active', 'account_type', 'bank_name', 'currency']
    search_fields = ['bank_name', 'account_number', 'account_name', 'swift_code']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Bank Details', {
            'fields': ('distributor', 'bank_name', 'branch_name', 'account_number', 'account_type')
        }),
        ('Account Holder', {
            'fields': ('account_name',)
        }),
        ('International Banking', {
            'fields': ('swift_code', 'iban', 'currency'),
            'classes': ['collapse']
        }),
        ('Settings', {
            'fields': ('is_primary', 'is_active', 'purpose', 'notes')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ['collapse']
        }),
    )
    
    def is_primary_badge(self, obj):
        """Display primary status with badge"""
        if obj.is_primary:
            return mark_safe('<span style="background-color: #28a745; color: white; padding: 2px 8px; border-radius: 3px;">PRIMARY</span>')
        return ''
    is_primary_badge.short_description = 'Primary'


@admin.register(BusinessAddress)
class BusinessAddressAdmin(admin.ModelAdmin):
    """Admin for Business Addresses"""
    
    list_display = ['location_name', 'address_type', 'city', 'phone', 'is_active', 'distributor']
    list_filter = ['address_type', 'is_active', 'city', 'country']
    search_fields = ['location_name', 'address_line1', 'city', 'contact_person']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Location Information', {
            'fields': ('distributor', 'address_type', 'location_name')
        }),
        ('Address', {
            'fields': ('address_line1', 'address_line2', 'city', 'district', 'postal_code', 'country', 'latitude', 'longitude')
        }),
        ('Contact Information', {
            'fields': ('contact_person', 'phone', 'email')
        }),
        ('Settings', {
            'fields': ('is_active', 'is_default_for_type', 'notes')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ['collapse']
        }),
    )


