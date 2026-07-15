"""
World-Class Print Management System for Zergo Distributors Sales App

This module provides a unified, professional print management system that consolidates:
- User printer settings (BillSettings)
- Receipt templates (BillTemplate)
- Company branding (CompanyBranding)
- Thermal printer configuration (PrinterProfile)

Into a single, cohesive PrintManager model.

Author: GitHub Copilot
Date: January 4, 2026
"""

from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from accounts.models import User
from PIL import Image
import os


class PrintManager(models.Model):
    """
    Unified Print Management System
    
    This single model replaces:
    - BillSettings (user printer preferences)
    - BillTemplate (receipt templates)
    - CompanyBranding (company logo/info)
    - PrinterProfile (thermal printer hardware config)
    
    Features:
    - Per-user printer configuration
    - Multiple receipt templates per user
    - Integrated branding management
    - Thermal printer hardware profiles
    - Per-receipt-type settings
    """
    
    # Import paper size choices
    from .paper_config import PaperSizeConfig
    PAPER_SIZE_CHOICES = PaperSizeConfig.PAPER_SIZE_CHOICES
    
    RECEIPT_TYPE_CHOICES = (
        ('bill', 'Sales Bill/Invoice'),
        ('payment', 'Payment Receipt'),
        ('return_cash', 'Cash Payment Voucher'),
        ('field_receipt', 'Field Cash Receipt'),
    )
    
    LANGUAGE_CHOICES = (
        ('en', 'English'),
        ('si', 'Sinhala'),
        ('ta', 'Tamil'),
    )
    
    CUT_BEHAVIOR_CHOICES = (
        ('full', 'Full Cut'),
        ('partial', 'Partial Cut'),
        ('none', 'No Cut (Manual)'),
    )
    
    DENSITY_CHOICES = (
        (0, 'Lightest'),
        (25, 'Light'),
        (50, 'Normal'),
        (75, 'Dark'),
        (100, 'Darkest'),
    )
    
    # ========================================================================
    # SECTION 1: PROFILE INFORMATION
    # ========================================================================
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='print_profiles')
    profile_name = models.CharField(
        max_length=200, 
        help_text="Profile name (e.g., 'Office Printer', 'Mobile Bluetooth', 'Invoice Template')"
    )
    
    # Company/Distributor Selection - Load branding from selected source
    company = models.ForeignKey(
        'products.Company',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Select a company to use their branding (logo, name, contact). Leave blank to use Distributor Profile."
    )
    use_distributor_profile = models.BooleanField(
        default=True,
        help_text="Use Distributor Profile branding instead of company-specific branding"
    )
    
    is_default = models.BooleanField(
        default=False, 
        help_text="Default print profile for this user"
    )
    is_active = models.BooleanField(default=True)
    
    # ========================================================================
    # SECTION 2: COMPANY BRANDING
    # ========================================================================
    
    # Logo
    company_logo = models.ImageField(
        upload_to='company_logos/', 
        blank=True, 
        null=True, 
        help_text="Company logo (optimized for thermal printing)"
    )
    logo_width = models.IntegerField(
        default=200, 
        help_text="Logo width in pixels"
    )
    logo_height = models.IntegerField(
        default=80, 
        help_text="Logo height in pixels"
    )
    show_logo = models.BooleanField(
        default=True, 
        help_text="Show logo on receipts"
    )
    
    # Company Information
    company_name = models.CharField(
        max_length=200, 
        default="Zergo Distributors"
    )
    company_tagline = models.CharField(
        max_length=200, 
        blank=True, 
        null=True, 
        help_text="Company tagline/slogan"
    )
    address_line1 = models.CharField(max_length=200, blank=True, null=True)
    address_line2 = models.CharField(max_length=200, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    email = models.CharField(max_length=100, blank=True, null=True)
    website = models.CharField(max_length=100, blank=True, null=True)
    tax_id = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        help_text="Tax/VAT registration number"
    )
    
    # Receipt Footer
    footer_line1 = models.CharField(
        max_length=200, 
        blank=True, 
        null=True, 
        default="Thank you for your business!"
    )
    footer_line2 = models.CharField(max_length=200, blank=True, null=True)
    footer_line3 = models.CharField(max_length=200, blank=True, null=True)
    
    # Display Settings
    show_tagline = models.BooleanField(default=True)
    show_address = models.BooleanField(default=True)
    show_contact = models.BooleanField(default=True)
    show_website = models.BooleanField(default=False)
    show_tax_id = models.BooleanField(default=False)
    
    # ========================================================================
    # SECTION 3: RECEIPT TEMPLATE SETTINGS
    # ========================================================================
    
    receipt_type = models.CharField(
        max_length=20, 
        choices=RECEIPT_TYPE_CHOICES, 
        default='bill',
        help_text="Type of receipt this profile is optimized for"
    )
    
    # Display Options
    show_barcode = models.BooleanField(
        default=False, 
        help_text="Show receipt number as barcode"
    )
    show_qr_code = models.BooleanField(
        default=True, 
        help_text="Show QR code for verification"
    )
    qr_code_size = models.IntegerField(
        default=150, 
        help_text="QR code size in pixels"
    )
    show_tax_breakdown = models.BooleanField(default=True)
    show_discount_details = models.BooleanField(default=True)
    show_payment_method = models.BooleanField(default=True)
    show_sales_rep = models.BooleanField(default=True)
    show_shop_location = models.BooleanField(default=True)
    
    # Localization
    language = models.CharField(
        max_length=5, 
        choices=LANGUAGE_CHOICES, 
        default='en',
        help_text="Receipt language"
    )
    
    # Custom Header/Footer Text
    custom_header = models.TextField(
        blank=True, 
        null=True, 
        help_text="Custom header text (appears below company info)"
    )
    custom_footer = models.TextField(
        blank=True, 
        null=True, 
        help_text="Custom footer text (appears above footer lines)"
    )
    
    # ========================================================================
    # SECTION 4: PRINTER HARDWARE SETTINGS
    # ========================================================================
    
    # Paper Configuration
    paper_size = models.CharField(
        max_length=20, 
        choices=PAPER_SIZE_CHOICES, 
        default='thermal_80mm',
        help_text="Paper size (auto-configures fonts and layout)"
    )
    
    # Printer Details
    printer_name = models.CharField(
        max_length=200, 
        blank=True, 
        null=True, 
        help_text="Printer model/name (for desktop printers)"
    )
    bluetooth_address = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        help_text="Bluetooth MAC address (for mobile printers)"
    )
    is_bluetooth = models.BooleanField(
        default=True, 
        help_text="Bluetooth thermal printer (mobile)"
    )
    
    # Print Quality & Behavior
    print_density = models.IntegerField(
        choices=DENSITY_CHOICES, 
        default=50,
        help_text="Print darkness (0-100)"
    )
    print_speed = models.IntegerField(
        default=5, 
        help_text="Print speed (1-9, lower is faster)"
    )
    cut_behavior = models.CharField(
        max_length=20, 
        choices=CUT_BEHAVIOR_CHOICES, 
        default='partial',
        help_text="Paper cutting behavior"
    )
    feed_lines = models.IntegerField(
        default=3, 
        help_text="Blank lines before cutting"
    )
    
    # Auto-Print Settings
    auto_print = models.BooleanField(
        default=False, 
        help_text="Auto-print after transaction creation"
    )
    
    # Print Copies - Per Receipt Type
    bill_print_copies = models.IntegerField(
        default=1, 
        help_text="Copies to print for bills"
    )
    payment_print_copies = models.IntegerField(
        default=1, 
        help_text="Copies to print for payment receipts"
    )
    return_print_copies = models.IntegerField(
        default=1, 
        help_text="Copies to print for return receipts"
    )
    field_receipt_print_copies = models.IntegerField(
        default=1, 
        help_text="Copies to print for field receipts"
    )
    
    # Margins (in mm) - Override PaperSizeConfig defaults if needed
    margin_top = models.IntegerField(
        default=5, 
        help_text="Top margin in mm (0 for default)"
    )
    margin_bottom = models.IntegerField(
        default=5, 
        help_text="Bottom margin in mm (0 for default)"
    )
    margin_left = models.IntegerField(
        default=5, 
        help_text="Left margin in mm (0 for default)"
    )
    margin_right = models.IntegerField(
        default=5, 
        help_text="Right margin in mm (0 for default)"
    )
    
    # Font Size Overrides (0 = use PaperSizeConfig optimal defaults)
    font_size_header = models.IntegerField(
        default=0, 
        help_text="Header font size in pt (0 for auto)"
    )
    font_size_body = models.IntegerField(
        default=0, 
        help_text="Body font size in pt (0 for auto)"
    )
    font_size_footer = models.IntegerField(
        default=0, 
        help_text="Footer font size in pt (0 for auto)"
    )
    
    # ESC/POS Commands (Advanced)
    custom_init_commands = models.TextField(
        blank=True, 
        null=True, 
        help_text="Custom ESC/POS initialization commands (hex)"
    )
    custom_cut_commands = models.TextField(
        blank=True, 
        null=True, 
        help_text="Custom ESC/POS cut commands (hex)"
    )
    
    # ========================================================================
    # SECTION 5: METADATA
    # ========================================================================
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_used_at = models.DateTimeField(
        blank=True, 
        null=True,
        help_text="Last time this profile was used"
    )
    
    class Meta:
        db_table = 'print_managers'
        ordering = ['-is_default', '-last_used_at', 'profile_name']
        verbose_name = 'Print Manager'
        verbose_name_plural = 'Print Managers'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'is_default', 'receipt_type'],
                condition=models.Q(is_default=True),
                name='one_default_per_user_per_receipt_type'
            )
        ]
    
    def __str__(self):
        return f"{self.profile_name} ({self.user.username})"
    
    def save(self, *args, **kwargs):
        """Override save to handle defaults and logo optimization"""
        # Ensure only one default profile per user per receipt type
        if self.is_default:
            PrintManager.objects.filter(
                user=self.user,
                receipt_type=self.receipt_type,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        
        # Process logo if uploaded
        if self.company_logo:
            super().save(*args, **kwargs)  # Save first to get file path
            self._optimize_logo()
        else:
            super().save(*args, **kwargs)
    
    def _optimize_logo(self):
        """Optimize logo for thermal printing (convert to B&W, resize)"""
        if not self.company_logo:
            return
        
        try:
            img = Image.open(self.company_logo.path)
            
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize maintaining aspect ratio
            img.thumbnail((self.logo_width, self.logo_height), Image.Resampling.LANCZOS)
            
            # For thermal printing, convert to black & white for better results
            # But save as RGB for web preview compatibility
            img = img.convert('L')  # Grayscale
            img = img.point(lambda x: 0 if x < 128 else 255, '1')  # B&W threshold
            img = img.convert('RGB')  # Back to RGB for saving
            
            # Save optimized logo
            img.save(self.company_logo.path, quality=95, optimize=True)
        except Exception as e:
            print(f"Error optimizing logo: {e}")
    
    def mark_as_used(self):
        """Mark profile as recently used"""
        self.last_used_at = timezone.now()
        self.save(update_fields=['last_used_at'])
    
    def get_print_copies(self) -> int:
        """Get print copies for this profile's receipt type"""
        copies_map = {
            'bill': self.bill_print_copies,
            'payment': self.payment_print_copies,
            'return_cash': self.return_print_copies,
            'field_receipt': self.field_receipt_print_copies,
        }
        return copies_map.get(self.receipt_type, 1)
    
    def get_esc_pos_density_command(self) -> str:
        """Generate ESC/POS command for print density"""
        density_byte = int((self.print_density / 100) * 255)
        return f"1B 37 {density_byte:02X} {density_byte:02X} {density_byte:02X}"
    
    def get_esc_pos_cut_command(self) -> str:
        """Generate ESC/POS command for paper cutting"""
        if self.custom_cut_commands:
            return self.custom_cut_commands
        
        # Standard cut commands
        if self.cut_behavior == 'full':
            return "1D 56 00"  # GS V 0 (Full cut)
        elif self.cut_behavior == 'partial':
            return "1D 56 01"  # GS V 1 (Partial cut)
        else:
            return ""  # No cut
    
    def get_full_address(self) -> str:
        """Get formatted full address"""
        parts = []
        if self.address_line1:
            parts.append(self.address_line1)
        if self.address_line2:
            parts.append(self.address_line2)
        if self.city:
            city_postal = self.city
            if self.postal_code:
                city_postal += f" {self.postal_code}"
            parts.append(city_postal)
        return '\n'.join(parts)
    
    def get_footer_text(self) -> str:
        """Get formatted footer text (all 3 lines)"""
        lines = []
        if self.footer_line1:
            lines.append(self.footer_line1)
        if self.footer_line2:
            lines.append(self.footer_line2)
        if self.footer_line3:
            lines.append(self.footer_line3)
        return '\n'.join(lines) if lines else "Thank you for your business!"
    
    @classmethod
    def get_user_default(cls, user: User, receipt_type: str = 'bill'):
        """
        Get user's default print profile for a specific receipt type.
        Creates one if it doesn't exist.
        
        Args:
            user: Django User object
            receipt_type: Type of receipt ('bill', 'payment', etc.)
            
        Returns:
            PrintManager instance
        """
        profile = cls.objects.filter(
            user=user,
            receipt_type=receipt_type,
            is_default=True,
            is_active=True
        ).first()
        
        if not profile:
            # Inherit printer/branding settings from bill profile if available
            defaults = {
                'user': user,
                'profile_name': f"Default {receipt_type.replace('_', ' ').title()} Profile",
                'receipt_type': receipt_type,
                'is_default': True,
                'is_active': True,
            }
            if receipt_type != 'bill':
                bill_profile = cls.objects.filter(
                    user=user, receipt_type='bill', is_default=True, is_active=True
                ).first()
                if bill_profile:
                    # Copy printer hardware and branding settings from bill profile
                    for field in [
                        'paper_size', 'use_distributor_profile', 'company_id',
                        'company_name', 'company_tagline', 'show_logo',
                        'company_logo', 'logo_width', 'logo_height',
                        'address_line1', 'address_line2', 'city', 'postal_code',
                        'phone', 'email', 'website', 'tax_id',
                        'footer_line1', 'footer_line2', 'footer_line3',
                        'show_tagline', 'show_address', 'show_contact',
                        'show_website', 'show_tax_id',
                        'is_bluetooth', 'print_density', 'print_speed',
                        'cut_behavior', 'feed_lines',
                    ]:
                        defaults[field] = getattr(bill_profile, field)
            profile = cls.objects.create(**defaults)
        
        return profile
    
    @classmethod
    def get_all_user_defaults(cls, user: User):
        """
        Get all default profiles for a user (one per receipt type).
        
        Args:
            user: Django User object
            
        Returns:
            Dict mapping receipt_type to PrintManager instance
        """
        defaults = {}
        for receipt_type, _ in cls.RECEIPT_TYPE_CHOICES:
            defaults[receipt_type] = cls.get_user_default(user, receipt_type)
        return defaults
