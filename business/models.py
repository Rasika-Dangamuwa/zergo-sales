"""
Business Settings Models for Zergo Distributors Sales Management System

This module contains models for managing the distributor's business details,
settings, and configuration. Provides a centralized single source of truth
for all business information used across the system.

Author: GitHub Copilot
Date: January 20, 2026
"""

from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from PIL import Image
import os


class DistributorProfile(models.Model):
    """
    Single Source of Truth for Distributor Business Information
    
    This model stores all business details, registration info, contact details,
    branding assets, and operational settings. Only ONE active profile should
    exist at a time (enforced by save method).
    
    Used by:
    - Print System (receipts, invoices)
    - Reports (headers, footers)
    - Admin Interface
    - Public-facing pages
    """
    
    # ========================================================================
    # SECTION 1: BASIC BUSINESS INFORMATION
    # ========================================================================
    
    business_name = models.CharField(
        max_length=200,
        default="Zergo Distributors",
        help_text="Official registered business name"
    )
    
    trade_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Trading name (if different from business name)"
    )
    
    tagline = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Business tagline/slogan (e.g., 'Quality Products, Trusted Service')"
    )
    
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Business description for reports and documents"
    )
    
    business_type = models.CharField(
        max_length=100,
        choices=(
            ('distributor', 'Distributor'),
            ('wholesaler', 'Wholesaler'),
            ('retailer', 'Retailer'),
            ('manufacturer', 'Manufacturer'),
            ('importer', 'Importer'),
            ('other', 'Other'),
        ),
        default='distributor'
    )
    
    established_date = models.DateField(
        blank=True,
        null=True,
        help_text="Date business was established"
    )
    
    # ========================================================================
    # SECTION 2: REGISTRATION & LEGAL INFORMATION
    # ========================================================================
    
    business_registration_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
        help_text="Official business registration number (BR Number)"
    )
    
    tax_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
        help_text="Tax Identification Number (TIN)"
    )
    
    vat_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
        help_text="VAT Registration Number (if applicable)"
    )
    
    svat_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="SVAT Number (if applicable)"
    )
    
    trade_license_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Trade License Number"
    )
    
    import_export_license = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Import/Export License Number (if applicable)"
    )
    
    # ========================================================================
    # SECTION 3: PRIMARY CONTACT INFORMATION
    # ========================================================================
    
    primary_phone = models.CharField(
        max_length=20,
        help_text="Primary contact number"
    )
    
    secondary_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Secondary/Alternative contact number"
    )
    
    mobile_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Mobile contact number"
    )
    
    fax_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Fax number"
    )
    
    primary_email = models.EmailField(
        help_text="Primary business email address"
    )
    
    secondary_email = models.EmailField(
        blank=True,
        null=True,
        help_text="Secondary email address"
    )
    
    support_email = models.EmailField(
        blank=True,
        null=True,
        help_text="Customer support email"
    )
    
    accounts_email = models.EmailField(
        blank=True,
        null=True,
        help_text="Accounts/Finance email"
    )
    
    website = models.URLField(
        blank=True,
        null=True,
        help_text="Business website URL"
    )
    
    # ========================================================================
    # SECTION 4: PRIMARY ADDRESS
    # ========================================================================
    
    address_line1 = models.CharField(
        max_length=200,
        help_text="Street address, building name, P.O. Box"
    )
    
    address_line2 = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Additional address information"
    )
    
    city = models.CharField(max_length=100)
    
    district = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="District/State/Province"
    )
    
    postal_code = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )
    
    country = models.CharField(
        max_length=100,
        default="Sri Lanka"
    )
    
    # Location Coordinates (for mapping)
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True,
        help_text="Latitude coordinate"
    )
    
    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True,
        help_text="Longitude coordinate"
    )
    
    # ========================================================================
    # SECTION 5: SOCIAL MEDIA & ONLINE PRESENCE
    # ========================================================================
    
    facebook_url = models.URLField(blank=True, null=True)
    instagram_url = models.URLField(blank=True, null=True)
    twitter_url = models.URLField(blank=True, null=True)
    linkedin_url = models.URLField(blank=True, null=True)
    whatsapp_number = models.CharField(max_length=20, blank=True, null=True)
    
    # ========================================================================
    # SECTION 6: BRANDING & VISUAL IDENTITY
    # ========================================================================
    
    # Primary Logo (Full Color)
    logo = models.ImageField(
        upload_to='business/logos/',
        blank=True,
        null=True,
        help_text="Primary business logo (PNG/JPEG, recommended 500x200px)"
    )
    
    # Logo for Receipts (Optimized for thermal printing)
    logo_receipt = models.ImageField(
        upload_to='business/logos/',
        blank=True,
        null=True,
        help_text="Logo optimized for thermal receipts (Black & White, 200x80px)"
    )
    
    # Logo for Reports/Documents
    logo_document = models.ImageField(
        upload_to='business/logos/',
        blank=True,
        null=True,
        help_text="Logo for PDF reports and documents (High res, 800x320px)"
    )
    
    # Favicon
    favicon = models.ImageField(
        upload_to='business/logos/',
        blank=True,
        null=True,
        help_text="Favicon for web interface (32x32px or 64x64px)"
    )
    
    # Brand Colors
    primary_color = models.CharField(
        max_length=7,
        default="#667eea",
        help_text="Primary brand color (Hex code, e.g., #667eea)"
    )
    
    secondary_color = models.CharField(
        max_length=7,
        default="#764ba2",
        help_text="Secondary brand color (Hex code)"
    )
    
    accent_color = models.CharField(
        max_length=7,
        default="#f093fb",
        help_text="Accent color for highlights (Hex code)"
    )
    
    # ========================================================================
    # SECTION 6B: NAVBAR & LOGIN PAGE APPEARANCE
    # ========================================================================
    
    navbar_title = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        help_text="Short name shown in the navbar (max 30 chars). Defaults to business name."
    )
    
    NAVBAR_BRAND_CHOICES = (
        ('logo', 'Company Logo'),
        ('icon', 'FontAwesome Icon'),
    )
    navbar_brand_type = models.CharField(
        max_length=10,
        choices=NAVBAR_BRAND_CHOICES,
        default='logo',
        help_text="Show company logo or a FontAwesome icon next to the title"
    )
    
    NAVBAR_STYLE_CHOICES = (
        ('gradient', 'Gradient (Primary → Secondary)'),
        ('solid', 'Solid Primary Color'),
        ('dark', 'Dark (Dark Grey/Black)'),
    )
    navbar_style = models.CharField(
        max_length=10,
        choices=NAVBAR_STYLE_CHOICES,
        default='gradient',
        help_text="Visual style for the top navigation bar"
    )
    
    navbar_icon = models.CharField(
        max_length=50,
        default='fas fa-store',
        blank=True,
        help_text="FontAwesome icon class for navbar brand (e.g., fas fa-store, fas fa-truck)"
    )
    
    login_subtitle = models.CharField(
        max_length=200,
        default='Sales Management System',
        blank=True,
        help_text="Subtitle text shown on the login page below the business name"
    )
    
    LOGIN_BRAND_CHOICES = (
        ('logo', 'Company Logo'),
        ('icon', 'FontAwesome Icon'),
    )
    login_brand_type = models.CharField(
        max_length=10,
        choices=LOGIN_BRAND_CHOICES,
        default='logo',
        help_text="Show company logo or a FontAwesome icon on the login page"
    )
    
    login_bg_style = models.CharField(
        max_length=10,
        choices=(
            ('gradient', 'Brand Gradient'),
            ('solid', 'Solid Color'),
            ('image', 'Background Image'),
        ),
        default='gradient',
        help_text="Login page background style"
    )
    
    login_bg_image = models.ImageField(
        upload_to='business/login/',
        blank=True,
        null=True,
        help_text="Custom background image for login page (recommended 1920x1080px)"
    )
    
    sidebar_active_style = models.CharField(
        max_length=10,
        choices=(
            ('line', 'Left Border Line'),
            ('fill', 'Filled Background'),
            ('pill', 'Rounded Pill'),
        ),
        default='line',
        help_text="Active menu item highlight style in the sidebar"
    )
    
    # ========================================================================
    # SECTION 7: OPERATIONAL SETTINGS
    # ========================================================================
    
    currency_code = models.CharField(
        max_length=3,
        default="LKR",
        help_text="Currency code (ISO 4217, e.g., LKR, USD, EUR)"
    )
    
    currency_symbol = models.CharField(
        max_length=10,
        default="Rs.",
        help_text="Currency symbol to display (e.g., Rs., $, €)"
    )
    
    fiscal_year_start_month = models.IntegerField(
        default=1,
        choices=[(i, timezone.datetime(2000, i, 1).strftime('%B')) for i in range(1, 13)],
        help_text="Fiscal year start month (1=January, 4=April, etc.)"
    )
    
    default_payment_terms_days = models.IntegerField(
        default=30,
        help_text="Default payment terms in days (e.g., 30 for Net 30)"
    )
    
    business_hours = models.CharField(
        max_length=100,
        default="Mon-Sat: 8:00 AM - 6:00 PM",
        blank=True,
        null=True,
        help_text="Business operating hours"
    )
    
    # ========================================================================
    # SECTION 8: RECEIPT/INVOICE SETTINGS
    # ========================================================================
    
    receipt_footer_line1 = models.CharField(
        max_length=200,
        default="Thank you for your business!",
        blank=True,
        null=True
    )
    
    receipt_footer_line2 = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Second footer line (e.g., warranty info, return policy)"
    )
    
    receipt_footer_line3 = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Third footer line (e.g., social media, website)"
    )
    
    terms_and_conditions = models.TextField(
        blank=True,
        null=True,
        help_text="Terms and conditions to print on invoices"
    )
    
    return_policy = models.TextField(
        blank=True,
        null=True,
        help_text="Return policy statement"
    )
    
    warranty_info = models.TextField(
        blank=True,
        null=True,
        help_text="Warranty information"
    )
    
    # ========================================================================
    # SECTION 9: DISPLAY PREFERENCES
    # ========================================================================
    
    show_logo_on_receipts = models.BooleanField(default=True)
    show_tagline = models.BooleanField(default=True)
    show_address_on_receipts = models.BooleanField(default=True)
    show_contact_on_receipts = models.BooleanField(default=True)
    show_social_media = models.BooleanField(default=False)
    show_tax_info = models.BooleanField(default=True)
    
    # ========================================================================
    # SECTION 10: METADATA
    # ========================================================================
    
    is_active = models.BooleanField(
        default=True,
        help_text="Only one active profile should exist. Setting this will deactivate others."
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Internal notes about this profile"
    )
    
    class Meta:
        ordering = ['-is_active', '-created_at']
        verbose_name = "Distributor Business Profile"
        verbose_name_plural = "Distributor Business Profiles"
    
    def __str__(self):
        status = "✓ ACTIVE" if self.is_active else "Inactive"
        return f"{self.business_name} ({status})"
    
    def save(self, *args, **kwargs):
        """
        Ensure only ONE active profile exists at a time.
        When setting is_active=True, deactivate all other profiles.
        """
        if self.is_active:
            # Deactivate all other profiles
            DistributorProfile.objects.exclude(pk=self.pk).update(is_active=False)
        
        # Ensure at least one profile is active
        if not self.is_active and not DistributorProfile.objects.exclude(pk=self.pk).filter(is_active=True).exists():
            self.is_active = True
        
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validate business registration numbers are unique"""
        super().clean()
        
        # Check unique registration numbers if provided
        if self.business_registration_number:
            existing = DistributorProfile.objects.filter(
                business_registration_number=self.business_registration_number
            ).exclude(pk=self.pk)
            if existing.exists():
                raise ValidationError({
                    'business_registration_number': 'A profile with this registration number already exists.'
                })
    
    @classmethod
    def get_active(cls):
        """
        Get the currently active distributor profile.
        Creates a default one if none exists.
        Uses the current tenant's name for new profiles.
        """
        profile = cls.objects.filter(is_active=True).first()
        
        if not profile:
            # Try to get the current tenant's name
            business_name = "My Distributor"
            try:
                from django.db import connection
                tenant = getattr(connection, 'tenant', None)
                if tenant and hasattr(tenant, 'name'):
                    business_name = tenant.name
            except Exception:
                pass

            # Create default profile
            profile = cls.objects.create(
                business_name=business_name,
                primary_phone="000-0000000",
                primary_email="info@example.com",
                address_line1="Address",
                city="City",
                country="Sri Lanka",
                is_active=True
            )
        
        return profile
    
    def get_full_address(self):
        """Return formatted complete address"""
        parts = [self.address_line1]
        if self.address_line2:
            parts.append(self.address_line2)
        parts.append(self.city)
        if self.district:
            parts.append(self.district)
        if self.postal_code:
            parts.append(self.postal_code)
        parts.append(self.country)
        return ", ".join(parts)
    
    def get_contact_numbers(self):
        """Return list of all contact numbers"""
        numbers = [self.primary_phone]
        if self.secondary_phone:
            numbers.append(self.secondary_phone)
        if self.mobile_phone:
            numbers.append(self.mobile_phone)
        return numbers
    
    def get_primary_logo(self):
        """Get the appropriate logo (primary logo or receipt logo)"""
        return self.logo if self.logo else self.logo_receipt


class BankAccount(models.Model):
    """
    Bank Account Details for the Distributor Business
    
    Supports multiple bank accounts (different banks, currencies, purposes).
    Used for payment instructions on invoices and receipts.
    """
    
    distributor = models.ForeignKey(
        DistributorProfile,
        on_delete=models.CASCADE,
        related_name='bank_accounts'
    )
    
    account_name = models.CharField(
        max_length=200,
        help_text="Account holder name (should match business name)"
    )
    
    bank_name = models.CharField(
        max_length=200,
        help_text="Name of the bank"
    )
    
    branch_name = models.CharField(
        max_length=200,
        help_text="Branch name/location"
    )
    
    account_number = models.CharField(
        max_length=50,
        help_text="Bank account number"
    )
    
    account_type = models.CharField(
        max_length=50,
        choices=(
            ('current', 'Current Account'),
            ('savings', 'Savings Account'),
            ('foreign_currency', 'Foreign Currency Account'),
        ),
        default='current'
    )
    
    swift_code = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="SWIFT/BIC code for international transfers"
    )
    
    iban = models.CharField(
        max_length=34,
        blank=True,
        null=True,
        help_text="IBAN (International Bank Account Number)"
    )
    
    currency = models.CharField(
        max_length=3,
        default="LKR",
        help_text="Account currency (e.g., LKR, USD)"
    )
    
    is_primary = models.BooleanField(
        default=False,
        help_text="Primary bank account (shown on invoices)"
    )
    
    is_active = models.BooleanField(default=True)
    
    purpose = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Purpose of this account (e.g., 'Operations', 'International Payments')"
    )
    
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_primary', '-is_active', 'bank_name']
        verbose_name = "Bank Account"
        verbose_name_plural = "Bank Accounts"
    
    def __str__(self):
        primary = " (PRIMARY)" if self.is_primary else ""
        return f"{self.bank_name} - {self.account_number}{primary}"
    
    def save(self, *args, **kwargs):
        """Ensure only one primary account per distributor"""
        if self.is_primary:
            BankAccount.objects.filter(
                distributor=self.distributor,
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        
        super().save(*args, **kwargs)
    
    def get_full_details(self):
        """Return formatted bank details for display"""
        details = f"{self.bank_name} - {self.branch_name}\n"
        details += f"Account: {self.account_number}\n"
        details += f"Name: {self.account_name}"
        if self.swift_code:
            details += f"\nSWIFT: {self.swift_code}"
        return details


class BusinessAddress(models.Model):
    """
    Additional Business Addresses/Locations
    
    For businesses with multiple branches, warehouses, or offices.
    Supports different address types for various purposes.
    """
    
    ADDRESS_TYPE_CHOICES = (
        ('head_office', 'Head Office'),
        ('branch', 'Branch Office'),
        ('warehouse', 'Warehouse'),
        ('showroom', 'Showroom'),
        ('billing', 'Billing Address'),
        ('shipping', 'Shipping Address'),
        ('registered', 'Registered Office'),
        ('other', 'Other'),
    )
    
    distributor = models.ForeignKey(
        DistributorProfile,
        on_delete=models.CASCADE,
        related_name='additional_addresses'
    )
    
    address_type = models.CharField(max_length=20, choices=ADDRESS_TYPE_CHOICES)
    
    location_name = models.CharField(
        max_length=200,
        help_text="Name of this location (e.g., 'Colombo Warehouse', 'Kandy Branch')"
    )
    
    address_line1 = models.CharField(max_length=200)
    address_line2 = models.CharField(max_length=200, blank=True, null=True)
    city = models.CharField(max_length=100)
    district = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=100, default="Sri Lanka")
    
    # Contact Information for this location
    contact_person = models.CharField(max_length=200, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    
    # Location Coordinates
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True
    )
    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True
    )
    
    is_active = models.BooleanField(default=True)
    is_default_for_type = models.BooleanField(
        default=False,
        help_text="Default address for this address type"
    )
    
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['address_type', 'location_name']
        verbose_name = "Business Address"
        verbose_name_plural = "Business Addresses"
        unique_together = ['distributor', 'address_type', 'location_name']
    
    def __str__(self):
        return f"{self.get_address_type_display()} - {self.location_name}"
    
    def get_full_address(self):
        """Return formatted complete address"""
        parts = [self.address_line1]
        if self.address_line2:
            parts.append(self.address_line2)
        parts.append(self.city)
        if self.district:
            parts.append(self.district)
        if self.postal_code:
            parts.append(self.postal_code)
        parts.append(self.country)
        return ", ".join(parts)
