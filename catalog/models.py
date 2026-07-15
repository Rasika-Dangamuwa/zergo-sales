"""
Global Product Catalog Models (Shared/Public Schema)

These models live in the PUBLIC schema and are visible to ALL distributors.
Platform admin manages the product catalog centrally. Each distributor then
"activates" products from this catalog into their own tenant schema, where
inventory (stock levels, pricing overrides, FOC ratios) is tracked separately.

Schema layout:
  public.global_companies   → Brand/manufacturer definitions
  public.global_categories  → Product categories
  public.global_products    → Product catalog (SKU, name, size, MRP, image)
  
  tenant.products           → Per-distributor: FK to global_product + inventory +
                              distributor-specific pricing & FOC ratios
"""

from django.db import models
from django.utils import timezone


class GlobalCompany(models.Model):
    """
    Brand/Manufacturer - shared across all distributors.
    
    Platform admin creates companies (e.g., "MAX", "Coca Cola") and all
    distributors can see and use products from these brands.
    """
    
    company_name = models.CharField(max_length=200, unique=True)
    company_code = models.CharField(max_length=20, unique=True)
    tagline = models.CharField(max_length=255, blank=True, default='')
    description = models.TextField(blank=True, default='')
    
    # Contact
    contact_person = models.CharField(max_length=200, blank=True, default='')
    phone_number = models.CharField(max_length=15, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    website = models.URLField(blank=True, default='')
    
    # Address
    address = models.TextField(blank=True, default='')
    city = models.CharField(max_length=100, blank=True, default='')
    country = models.CharField(max_length=100, default='Sri Lanka')
    
    # Branding
    logo = models.ImageField(upload_to='global_company_logos/', blank=True, null=True)
    logo_receipt = models.ImageField(
        upload_to='global_company_logos/',
        blank=True, null=True,
        help_text="Logo optimized for thermal receipts (B&W, 200x80px)"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'global_companies'
        verbose_name = 'Global Company'
        verbose_name_plural = 'Global Companies'
        ordering = ['company_name']
    
    def __str__(self):
        return f"{self.company_name} ({self.company_code})"


class GlobalCategory(models.Model):
    """
    Product Category - shared across all distributors.
    
    Categories like "Soft Drinks", "Energy Drinks", "Water" etc. are
    defined once and used by all distributors.
    """
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'global_categories'
        verbose_name = 'Global Category'
        verbose_name_plural = 'Global Categories'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class GlobalProduct(models.Model):
    """
    Global Product Catalog Entry - shared across all distributors.
    
    Defines the product SKU (identity, specifications, MRP). Each distributor
    can then "activate" this product in their own schema, where they track
    their own inventory levels and distributor-specific pricing/FOC ratios.
    
    Example: "MAX Orange 500ml Rs.130" is ONE global product. Zergo and Galle
    distributors both activate it, each with their own stock counts and 
    possibly different discount percentages.
    """
    
    SIZE_CHOICES = (
        ('220ML', '220ML'),
        ('250ML', '250ML'),
        ('500ML', '500ML'),
        ('750ML', '750ML'),
        ('1000ML', '1000ML (1L)'),
        ('1500ML', '1500ML (1.5L)'),
        ('2200ML', '2200ML (2.2L)'),
    )
    
    # Identity
    product_code = models.CharField(
        max_length=50, unique=True,
        help_text="Global unique product code (e.g., MAX-ORG-500)"
    )
    product_name = models.CharField(
        max_length=200,
        help_text="Full product name (e.g., Max Orange 500ml)"
    )
    sinhala_name = models.CharField(
        max_length=200, blank=True, null=True,
        help_text="Product name in Sinhala (සිංහල නම)"
    )
    description = models.TextField(blank=True, default='')
    
    # Brand & Category
    company = models.ForeignKey(
        GlobalCompany,
        on_delete=models.CASCADE,
        related_name='products',
        help_text="Brand/manufacturer"
    )
    category = models.ForeignKey(
        GlobalCategory,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='products',
        help_text="Product category"
    )
    
    # Specifications
    size = models.CharField(max_length=20, choices=SIZE_CHOICES, default='500ML')
    marked_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00,
        help_text="MRP / Marked Retail Price (global, same everywhere)"
    )
    bottles_per_pack = models.IntegerField(
        default=24,
        help_text="Bottles per pack/case"
    )
    barcode = models.CharField(max_length=50, blank=True, default='')
    product_image = models.ImageField(upload_to='global_products/', blank=True, null=True)
    
    # Default Pricing (distributors can override when activating)
    discount_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=10.00,
        help_text="Default shop discount % off MRP (distributors can override)"
    )
    company_discount_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=23.00,
        help_text="Default company discount % on shop price (distributors can override)"
    )
    
    # Default FOC Ratios (distributors can override when activating)
    company_foc_buy = models.IntegerField(
        default=12,
        help_text="Default: buy X bottles to get FOC from company"
    )
    company_foc_free = models.IntegerField(
        default=1,
        help_text="Default: Y free bottles from company for every X bought"
    )
    shop_foc_buy = models.IntegerField(
        default=12,
        help_text="Default: shop buys X bottles to get FOC"
    )
    shop_foc_free = models.IntegerField(
        default=1,
        help_text="Default: Y free bottles given to shop for every X bought"
    )
    
    # Display
    display_order = models.IntegerField(
        default=0,
        help_text="Lower number appears first in lists"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'global_products'
        verbose_name = 'Global Product'
        verbose_name_plural = 'Global Products'
        ordering = ['display_order', 'product_name']
    
    def __str__(self):
        return f"{self.company.company_name} - {self.product_name} - {self.size} - Rs.{self.marked_price}"
    
    @property
    def full_display_name(self):
        """Full display name for dropdowns/lists"""
        return f"{self.product_name} ({self.size}) - Rs.{self.marked_price}"
