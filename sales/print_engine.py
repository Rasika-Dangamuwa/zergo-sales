"""
Unified Print Engine for Zergo Distributors Sales App

This module provides a centralized, world-class printing system that integrates:
- PrintManager (unified print management)
- PaperSizeConfig (9 industry-standard paper sizes)
- ReceiptOptimizer (dynamic font/layout optimization)
- Bluetooth thermal printer support
- Multiple receipt types (bills, payments, returns, field receipts)

Author: GitHub Copilot  
Date: January 4, 2026 (Refactored with PrintManager)
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List, TYPE_CHECKING
from django.contrib.auth import get_user_model
from .print_manager import PrintManager
from .paper_config import PaperSizeConfig
from .receipt_optimizer import ReceiptOptimizer

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser as User
else:
    User = get_user_model()


class UnifiedPrintEngine:
    """
    World-class unified printing engine that connects all printing components.
    
    This eliminates code duplication and ensures consistent, optimized printing
    across all receipt types (bills, payments, returns, field receipts).
    
    Features:
    - Dynamic font sizing based on paper width
    - Automatic character limit calculation
    - Logo optimization per paper size
    - ESC/POS command generation for thermal printers
    - Company branding integration
    - Bluetooth printer support
    """
    
    # Receipt type configurations
    RECEIPT_TYPES = {
        'bill': {
            'title': 'SALES INVOICE',
            'number_field': 'bill_number',
            'date_field': 'bill_date',
            'customer_field': 'shop',
            'items_related': 'items',
            'show_payment_info': True,
            'show_signature': True,
            'color_scheme': 'green',  # Primary button color
        },
        'payment': {
            'title': 'PAYMENT RECEIPT',
            'number_field': 'payment_number',
            'date_field': 'payment_date',
            'customer_field': 'shop',
            'items_related': None,  # Payments don't have items
            'show_payment_info': True,
            'show_signature': False,
            'color_scheme': 'blue',
        },
        'return_cash': {
            'title': 'CASH PAYMENT VOUCHER',
            'number_field': 'cash_receipt_number',
            'date_field': 'return_date',
            'customer_field': 'shop',
            'items_related': 'items',
            'show_payment_info': True,
            'show_signature': True,
            'color_scheme': 'red',
        },
        'field_receipt': {
            'title': 'FIELD RECEIPT',
            'number_field': 'field_receipt_number',
            'date_field': 'return_date',
            'customer_field': 'shop',
            'items_related': 'items',
            'show_payment_info': True,
            'show_signature': True,
            'color_scheme': 'orange',
        },
    }
    
    def __init__(self, user: User, receipt_type: str = 'bill'):
        """
        Initialize the print engine.
        
        Args:
            user: Django user object
            receipt_type: Type of receipt ('bill', 'payment', 'return_cash', 'field_receipt')
        """
        if receipt_type not in self.RECEIPT_TYPES:
            raise ValueError(f"Invalid receipt_type. Must be one of: {list(self.RECEIPT_TYPES.keys())}")
        
        self.user = user
        self.receipt_type = receipt_type
        self.receipt_config = self.RECEIPT_TYPES[receipt_type]
        
        # Get user's print profile for this receipt type
        # PrintManager auto-creates if doesn't exist
        self.print_profile = PrintManager.get_user_default(user, receipt_type)
        
        # Get paper size and create optimizer
        self.paper_size = self.print_profile.paper_size
        self.optimizer = ReceiptOptimizer(self.paper_size)
        
        # Get print copies for this receipt type
        self.print_copies = self.print_profile.get_print_copies()
    
    def _get_item_count(self, data: Dict[str, Any]) -> int:
        """
        Extract item count from data based on receipt type.
        
        Args:
            data: Receipt data dictionary
            
        Returns:
            Number of items in receipt
        """
        items_related = self.receipt_config['items_related']
        
        if items_related is None:
            # Payment receipts don't have items
            return 0
        
        # Get items from data
        items = data.get('items', [])
        
        if hasattr(items, '__len__'):
            # List, tuple, or queryset
            return len(items)
        else:
            return 0
    
    def get_print_context(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate complete optimized context for template rendering.
        
        This is the main method that connects everything:
        - User's paper size preference
        - Dynamic optimization based on content
        - Company branding
        - Receipt type configuration
        - Bluetooth printing support
        
        Args:
            data: Receipt-specific data (bill, payment, return, items, etc.)
            
        Returns:
            Complete context dictionary for template rendering
        """
        item_count = self._get_item_count(data)
        
        # Get optimized settings from ReceiptOptimizer
        optimized = self.optimizer.get_optimized_settings(item_count)
        
        # Get paper size specifications
        paper_specs = PaperSizeConfig.get_specs(self.paper_size)
        
        # Get display options from print profile
        display_options = {
            'show_company_logo': self.print_profile.show_logo,
            'show_barcode': self.print_profile.show_barcode,
            'show_qr_code': self.print_profile.show_qr_code,
            'show_tax_breakdown': self.print_profile.show_tax_breakdown,
            'show_discount_details': self.print_profile.show_discount_details,
            'show_payment_method': self.print_profile.show_payment_method,
            'show_sales_rep': self.print_profile.show_sales_rep,
            'show_shop_location': self.print_profile.show_shop_location,
        }
        
        # Get branding from print profile (company or distributor)
        from products.models import Company
        from business.models import DistributorProfile
        
        branding = {}
        if self.print_profile.use_distributor_profile:
            # Use distributor profile branding
            try:
                distributor = DistributorProfile.objects.filter(is_active=True).first()
                if distributor:
                    branding = {
                        'company_name': distributor.business_name,
                        'tagline': distributor.tagline,
                        'logo': distributor.logo_receipt or distributor.logo,  # Prefer receipt logo, fallback to primary
                        'address': distributor.address_line1,
                        'phone': distributor.primary_phone,
                        'email': distributor.primary_email,
                        'website': distributor.website,
                        'show_logo': self.print_profile.show_logo,
                        'show_tagline': self.print_profile.show_tagline,
                        'show_address': self.print_profile.show_address,
                        'show_contact': self.print_profile.show_contact,
                        'show_website': self.print_profile.show_website,
                    }
                    print(f"[PRINT ENGINE] Using Distributor Profile: {distributor.business_name}")
            except Exception as e:
                print(f"[PRINT ENGINE] Error loading distributor: {e}")
        elif self.print_profile.company:
            # Use specific company branding
            company = self.print_profile.company
            branding = {
                'company_name': company.company_name,
                'tagline': company.tagline,
                'logo': company.logo_receipt or company.logo,  # Prefer receipt logo, fallback to primary
                'address': f"{company.address}, {company.city}" if company.city else company.address,
                'phone': company.phone_number,
                'email': company.email,
                'website': company.website,
                'show_logo': self.print_profile.show_logo,
                'show_tagline': self.print_profile.show_tagline,
                'show_address': self.print_profile.show_address,
                'show_contact': self.print_profile.show_contact,
                'show_website': self.print_profile.show_website,
            }
            print(f"[PRINT ENGINE] Using Company: {company.company_name} (ID: {company.id})")
        else:
            print(f"[PRINT ENGINE] No branding - use_distributor: {self.print_profile.use_distributor_profile}, company: {self.print_profile.company}")
        
        print(f"[PRINT ENGINE] Branding data: {branding if branding else 'None'}")
        
        # Build complete context
        context = {
            # Original data (FIRST - can be overridden)
            **data,
            
            # Company branding (IMPORTANT - add this AFTER data to override any conflicts)
            'branding': branding if branding else None,
            
            # Print profile (replaces branding + template)
            'print_profile': self.print_profile,
            'profile': self.print_profile,  # Alias for template compatibility
            
            # Legacy fields for backward compatibility
            'company_name': branding.get('company_name', '') if branding else '',
            'company_logo': branding.get('logo') if branding else None,
            'company_address': branding.get('address', '') if branding else '',
            'company_phone': branding.get('phone', '') if branding else '',
            'company_email': branding.get('email', '') if branding else '',
            'company_website': branding.get('website', '') if branding else '',
            'footer_text': self.print_profile.get_footer_text(),
            
            # Display options from print profile
            **display_options,
            
            # Receipt type configuration
            'receipt_type': self.receipt_type,
            'receipt_config': self.receipt_config,
            'receipt_title': data.get('receipt_title') or self.receipt_config['title'],
            
            # Print copies for this receipt type
            'print_copies': self.print_copies,
            
            # Paper size info
            'paper_size': self.paper_size,
            'paper_specs': {
                'width_mm': paper_specs.width_mm,
                'width_inch': paper_specs.width_inch,
                'printable_width_mm': paper_specs.printable_width_mm,
                'is_thermal': paper_specs.category == 'thermal',
                'category': paper_specs.category,
            },
            
            # Optimized settings from ReceiptOptimizer
            'fonts': optimized['fonts'],
            'logo': optimized['logo'],
            'char_limits': optimized['character_limits'],  # Note: ReceiptOptimizer returns 'character_limits'
            'margins': optimized['margins'],
            'layout': optimized['layout'],
            'qr_code': optimized['qr_barcode']['qr_size'],
            'barcode': {
                'width': optimized['qr_barcode']['barcode_width'],
                'height': optimized['qr_barcode']['barcode_height'],
            },
            
            # Dynamic CSS
            'dynamic_css': optimized['css'],
            
            # ESC/POS commands for Bluetooth printing (call method separately)
            'escpos_commands': self.optimizer.get_escpos_commands(),
            
            # Backward compatibility aliases (NOTE: 'branding' is now the company/distributor dict, not the profile)
            'bill_settings': self.print_profile,  # For old templates
            'template': self.print_profile,  # For old templates
            
            # Helper methods for template
            'helpers': {
                'wrap_text': self.optimizer.wrap_text,
                'truncate_text': self.optimizer.truncate_text,
                'format_line_item': self.optimizer.format_line_item,
                'format_total_line': self.optimizer.format_total_line,
            },
        }
        
        return context
    
    def get_bluetooth_config(self) -> Dict[str, Any]:
        """
        Get Bluetooth printer configuration.
        
        Returns:
            Bluetooth-specific settings
        """
        return {
            'chunk_size': 20,  # Bytes per Bluetooth transmission
            'delay_ms': 50,  # Milliseconds between chunks
            'timeout_ms': 30000,  # Connection timeout
            'auto_disconnect': True,
            'auto_disconnect_delay_ms': 2000,
        }
    
    def format_receipt_number(self, obj: Any) -> str:
        """
        Extract and format receipt number based on receipt type.
        
        Args:
            obj: Receipt object (Bill, Payment, Return)
            
        Returns:
            Formatted receipt number
        """
        number_field = self.receipt_config['number_field']
        return getattr(obj, number_field, 'N/A')
    
    def format_receipt_date(self, obj: Any) -> str:
        """
        Extract and format receipt date based on receipt type.
        
        Args:
            obj: Receipt object (Bill, Payment, Return)
            
        Returns:
            Formatted date string
        """
        date_field = self.receipt_config['date_field']
        date_obj = getattr(obj, date_field, None)
        
        if date_obj:
            from django.utils import timezone
            if hasattr(date_obj, 'tzinfo') and date_obj.tzinfo is not None:
                date_obj = timezone.localtime(date_obj)
            return date_obj.strftime('%Y-%m-%d %H:%M')
        return 'N/A'
    
    def get_customer_info(self, obj: Any) -> Dict[str, str]:
        """
        Extract customer information based on receipt type.
        
        Args:
            obj: Receipt object (Bill, Payment, Return)
            
        Returns:
            Customer information dictionary
        """
        customer_field = self.receipt_config['customer_field']
        customer = getattr(obj, customer_field, None)
        
        if customer:
            return {
                'name': getattr(customer, 'shop_name', 'N/A'),
                'phone': getattr(customer, 'phone_number', ''),
                'address': getattr(customer, 'address_line1', ''),
                'city': getattr(customer, 'city', ''),
            }
        
        return {
            'name': 'Walk-in Customer',
            'phone': '',
            'address': '',
            'city': '',
        }
    
    @classmethod
    def get_available_receipt_types(cls) -> List[str]:
        """
        Get list of all available receipt types.
        
        Returns:
            List of receipt type codes
        """
        return list(cls.RECEIPT_TYPES.keys())
    
    @classmethod
    def get_receipt_type_info(cls, receipt_type: str) -> Dict[str, Any]:
        """
        Get configuration for a specific receipt type.
        
        Args:
            receipt_type: Receipt type code
            
        Returns:
            Receipt type configuration dictionary
        """
        return cls.RECEIPT_TYPES.get(receipt_type, {})


class PrintEngineFactory:
    """
    Factory class for creating PrintEngine instances.
    
    Provides convenience methods for different receipt types.
    """
    
    @staticmethod
    def create_bill_engine(user: User) -> UnifiedPrintEngine:
        """Create engine for bill printing."""
        return UnifiedPrintEngine(user, receipt_type='bill')
    
    @staticmethod
    def create_payment_engine(user: User) -> UnifiedPrintEngine:
        """Create engine for payment receipt printing."""
        return UnifiedPrintEngine(user, receipt_type='payment')
    
    @staticmethod
    def create_return_cash_engine(user: User) -> UnifiedPrintEngine:
        """Create engine for cash return receipt printing."""
        return UnifiedPrintEngine(user, receipt_type='return_cash')
    
    @staticmethod
    def create_field_receipt_engine(user: User) -> UnifiedPrintEngine:
        """Create engine for field receipt printing."""
        return UnifiedPrintEngine(user, receipt_type='field_receipt')


# Convenience functions for views
def get_bill_print_context(user: User, bill, items) -> Dict[str, Any]:
    """
    Get optimized context for bill printing.
    
    Args:
        user: Django user
        bill: Bill object
        items: Bill items queryset
        
    Returns:
        Complete context for mobile_print template
    """
    engine = UnifiedPrintEngine(user, receipt_type='bill')
    return engine.get_print_context({
        'sale': bill,
        'items': items,
    })


def get_payment_print_context(user: User, payment) -> Dict[str, Any]:
    """
    Get optimized context for payment receipt printing.
    
    Args:
        user: Django user
        payment: Payment object
        
    Returns:
        Complete context for payment_mobile_print template
    """
    engine = UnifiedPrintEngine(user, receipt_type='payment')
    return engine.get_print_context({
        'payment': payment,
        'bill': payment.bill,
        'shop': payment.shop,
    })


def get_return_cash_print_context(user: User, return_obj, items) -> Dict[str, Any]:
    """
    Get optimized context for cash return receipt printing.
    
    Args:
        user: Django user
        return_obj: Return object
        items: Return items queryset
        
    Returns:
        Complete context for return_cash_receipt_mobile_print template
    """
    engine = UnifiedPrintEngine(user, receipt_type='return_cash')
    return engine.get_print_context({
        'return': return_obj,
        'items': items,
    })


def get_field_receipt_print_context(user: User, return_obj, items) -> Dict[str, Any]:
    """
    Get optimized context for field receipt printing.
    
    Args:
        user: Django user
        return_obj: Return object
        items: Return items queryset
        
    Returns:
        Complete context for field_receipt_mobile_print template
    """
    engine = UnifiedPrintEngine(user, receipt_type='field_receipt')
    return engine.get_print_context({
        'return': return_obj,
        'items': items,
    })
