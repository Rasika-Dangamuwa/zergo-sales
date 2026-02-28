from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class Company(models.Model):
    """Companies that we have dealership with"""
    
    # Basic Information
    company_name = models.CharField(max_length=200, unique=True)
    company_code = models.CharField(max_length=20, unique=True)
    tagline = models.CharField(max_length=255, blank=True, null=True, help_text="Company slogan or tagline")
    description = models.TextField(blank=True, null=True, help_text="Brief description of the company")
    
    # Contact Information
    contact_person = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=15)
    secondary_phone = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField()
    secondary_email = models.EmailField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    
    # Address
    address = models.TextField()
    city = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, default='Sri Lanka')
    
    # Branding
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True, help_text="Primary company logo")
    logo_receipt = models.ImageField(upload_to='company_logos/', blank=True, null=True, help_text="Logo optimized for thermal receipts (Black & White, 200x80px)")
    primary_color = models.CharField(max_length=7, blank=True, null=True, help_text="Hex color code (e.g., #FF0000)")
    
    # Social Media
    facebook_url = models.URLField(blank=True, null=True)
    instagram_url = models.URLField(blank=True, null=True)
    linkedin_url = models.URLField(blank=True, null=True)
    
    # Business Info
    tax_id = models.CharField(max_length=50, blank=True, null=True, help_text="Tax Identification Number")
    registration_number = models.CharField(max_length=50, blank=True, null=True, help_text="Business registration number")
    
    # Status & Metadata
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'companies'
        verbose_name_plural = 'Companies'
        ordering = ['company_name']
    
    def __str__(self):
        return self.company_name
    
    def get_logo_url(self):
        """Safely get logo URL"""
        if self.logo:
            return self.logo.url
        return None


class Category(models.Model):
    """Product Categories"""
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'categories'
        verbose_name_plural = 'Categories'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Product(models.Model):
    """
    Simplified Product model - direct stock tracking
    No SKU, no flavor complexity - each product tracks its own stock
    Example: Max Orange 500ml Rs.130
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
    
    # Link to Global Catalog (shared/public schema)
    # When a product is activated from the global catalog, this FK links back.
    # Null for legacy products that were created before the catalog existed.
    global_product = models.ForeignKey(
        'catalog.GlobalProduct',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='tenant_products',
        help_text="Link to global product catalog (shared across all distributors)"
    )
    
    # Basic Info
    product_code = models.CharField(max_length=50, unique=True)
    product_name = models.CharField(max_length=200, help_text="e.g., Max Orange 500ml")
    description = models.TextField(blank=True, null=True)
    
    # Company/Brand
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    
    # Product Specifications
    size = models.CharField(max_length=20, choices=SIZE_CHOICES, default='500ML')
    marked_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Marked retail price")
    bottles_per_pack = models.IntegerField(default=24, help_text="Number of bottles in one pack/case (default 24)")
    
    # Inventory - Direct stock tracking
    quantity_in_stock = models.IntegerField(default=0, help_text="Resaleable stock quantity (available for sale)")
    non_resaleable_stock = models.IntegerField(default=0, help_text="Non-resaleable stock (damaged/expired/quarantined)")
    minimum_stock_level = models.IntegerField(default=50, help_text="Minimum stock alert level")
    
    # Pricing
    discount_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=10.00,
        help_text="Discount % given to shops (default 10%)"
    )
    
    # Company Purchase Pricing
    company_discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=23.00,
        help_text="Discount % we get from company on shop price (default 23%)"
    )
    
    # FOC (Free of Charge) Ratios
    company_foc_buy = models.IntegerField(
        default=12,
        help_text="Number of bottles to buy to get FOC from company (e.g., 12)"
    )
    company_foc_free = models.IntegerField(
        default=1,
        help_text="Number of free bottles from company (e.g., 1 free for every 12)"
    )
    shop_foc_buy = models.IntegerField(
        default=12,
        help_text="Number of bottles shop must buy to get FOC (e.g., 12)"
    )
    shop_foc_free = models.IntegerField(
        default=1,
        help_text="Number of free bottles given to shop (e.g., 1 free for every 12)"
    )
    
    # Product Details
    barcode = models.CharField(max_length=50, blank=True, null=True)
    product_image = models.ImageField(upload_to='products/', blank=True, null=True)
    
    # Display Order
    display_order = models.IntegerField(default=0, help_text="Order in which product appears in lists (lower number appears first)")
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'products'
        ordering = ['display_order', 'product_name']
        # unique_together will be added after migration
        # unique_together = [['company', 'size', 'marked_price', 'product_name']]
    
    def __str__(self):
        return f"{self.company.company_name} - {self.product_name} - {self.size} - Rs.{self.marked_price}"
    
    @property
    def total_stock(self):
        """Total stock including non-resaleable"""
        return self.quantity_in_stock + self.non_resaleable_stock
    
    @property
    def available_for_sale(self):
        """Resaleable stock available for sale (alias for quantity_in_stock)"""
        return self.quantity_in_stock
    
    @property
    def is_low_stock(self):
        """Check if resaleable stock is below minimum level"""
        return self.quantity_in_stock <= self.minimum_stock_level
    
    @property
    def discount_amount(self):
        """Calculate discount amount given to shops"""
        return (self.marked_price * self.discount_percentage) / 100
    
    @property
    def shop_price(self):
        """Price to shop (marked price - discount)"""
        return self.marked_price - self.discount_amount
    
    @property
    def final_price(self):
        """Price after discount (same as shop_price)"""
        return self.shop_price
    
    @property
    def company_discount_amount(self):
        """Calculate discount we get from company on shop price"""
        return (self.shop_price * self.company_discount_percentage) / 100
    
    @property
    def company_price(self):
        """Price we pay to company (shop price - company discount)"""
        return self.shop_price - self.company_discount_amount
    
    @property
    def cost_after_foc(self):
        """Effective cost per unit after spreading cost across FOC units.
        E.g. if company_price=69.30 and FOC is 12+1, cost = 69.30 * 12/13 = 63.97"""
        total_units = self.company_foc_buy + self.company_foc_free
        if total_units > 0:
            return self.company_price * self.company_foc_buy / total_units
        return self.company_price
    
    @property
    def our_profit_per_unit(self):
        """Profit per bottle (shop price - company price)"""
        return self.shop_price - self.company_price
    
    @property
    def company_foc_ratio(self):
        """FOC ratio from company as string (e.g., '12+1')"""
        return f"{self.company_foc_buy}+{self.company_foc_free}"
    
    @property
    def shop_foc_ratio(self):
        """FOC ratio to shops as string (e.g., '12+1')"""
        return f"{self.shop_foc_buy}+{self.shop_foc_free}"
    
    @property
    def packs(self):
        """Calculate number of full packs from quantity in stock"""
        if self.bottles_per_pack > 0:
            return self.quantity_in_stock // self.bottles_per_pack
        return 0
    
    @property
    def loose(self):
        """Calculate number of loose bottles from quantity in stock"""
        if self.bottles_per_pack > 0:
            return self.quantity_in_stock % self.bottles_per_pack
        return self.quantity_in_stock
    
    @property
    def pack_loose_display(self):
        """Display stock as 'X packs + Y loose' format"""
        return f"{self.packs} packs + {self.loose} loose"


class StockCount(models.Model):
    """
    Physical stock count - can be done anytime
    Tracks variance and updates product stock
    """
    
    # Reference
    count_number = models.CharField(max_length=50, unique=True, editable=False, blank=True, null=True)
    count_date = models.DateTimeField(auto_now_add=True, help_text="When the count was performed")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_counts')
    
    # Count data
    system_stock = models.IntegerField(help_text="Stock in system before count")
    physical_count = models.IntegerField(help_text="Actual physical count")
    variance = models.IntegerField(help_text="Difference: Physical - System")
    
    # Adjustment
    adjustment_reason = models.TextField(
        blank=True, 
        null=True, 
        help_text="Reason for variance (e.g., damage, theft, counting error)"
    )
    stock_updated = models.BooleanField(default=False, help_text="Whether product stock was updated")
    
    # Audit trail
    counted_by = models.ForeignKey(
        'accounts.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='stock_counts'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'stock_counts'
        ordering = ['-count_date']
    
    def __str__(self):
        return f"{self.count_number} - {self.product} - Variance: {self.variance}"
    
    def save(self, *args, **kwargs):
        # Generate count number if not set
        if not self.count_number:
            self.count_number = self.generate_count_number()
        
        # Calculate variance
        self.variance = self.physical_count - self.system_stock
        super().save(*args, **kwargs)
    
    def generate_count_number(self):
        """Generate unique stock count number: SC-DISTCODE-YYYY-NNNN"""
        from utils.number_generator import generate_number
        return generate_number('SC', StockCount, 'count_number', mode='yearly')


class ProductStatusAdjustment(models.Model):
    """
    Track products marked as damaged, used, expired, etc.
    Requires manager approval before stock is updated
    """
    
    STATUS_CHOICES = (
        ('damaged', 'Damaged'),
        ('expired', 'Expired'),
        ('used', 'Used/Consumed'),
        ('lost', 'Lost/Missing'),
        ('sample', 'Sample/Giveaway'),
        ('other', 'Other'),
    )
    
    APPROVAL_STATUS_CHOICES = (
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    STOCK_ACTION_CHOICES = (
        ('move_to_non_resaleable', 'Move to Non-Resaleable Stock'),
        ('reduce_completely', 'Reduce Stock Completely'),
        ('record_only', 'Record Only (No Stock Change)'),
    )
    
    # Unique number
    adjustment_number = models.CharField(max_length=50, unique=True, editable=False)
    
    # Legacy single-item fields (kept for backward compatibility)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='status_adjustments', null=True, blank=True)
    quantity = models.IntegerField(default=0, help_text="Legacy: Number of units (use items for multi-item)")
    
    # Common fields for all items in this adjustment
    status_type = models.CharField(max_length=30, choices=STATUS_CHOICES)
    reason = models.TextField(help_text="Detailed reason for this adjustment")
    reference_number = models.CharField(max_length=50, blank=True, null=True, help_text="Reference number if any")
    
    # Stock action (how to handle stock when approved)
    stock_action = models.CharField(
        max_length=30,
        choices=STOCK_ACTION_CHOICES,
        default='move_to_non_resaleable',
        help_text="How to handle stock when adjustment is approved"
    )
    
    # Approval workflow
    approval_status = models.CharField(max_length=20, choices=APPROVAL_STATUS_CHOICES, default='pending')
    approved_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_adjustments')
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Stock impact (updated only after approval)
    stock_updated = models.BooleanField(default=False, help_text="Whether stock was deducted")
    previous_stock = models.IntegerField(default=0, help_text="Stock before adjustment")
    new_stock = models.IntegerField(default=0, help_text="Stock after adjustment")
    
    # Tracking
    adjustment_date = models.DateTimeField(auto_now_add=True)
    adjusted_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='product_adjustments')
    
    class Meta:
        db_table = 'product_status_adjustments'
        ordering = ['-adjustment_date']
    
    @property
    def total_items(self):
        """Total number of items in this adjustment"""
        return self.items.count() if hasattr(self, 'items') else (1 if self.product else 0)
    
    @property
    def total_quantity(self):
        """Total quantity across all items"""
        if hasattr(self, 'items') and self.items.exists():
            return sum(item.quantity for item in self.items.all())
        return self.quantity
    
    def __str__(self):
        if hasattr(self, 'items') and self.items.exists():
            return f"{self.adjustment_number} - {self.get_status_type_display()} ({self.total_items} items)"
        return f"{self.adjustment_number} - {self.product.product_name if self.product else 'N/A'} - {self.get_status_type_display()}"
    
    def save(self, *args, **kwargs):
        if not self.adjustment_number:
            self.adjustment_number = self.generate_adjustment_number()
        super().save(*args, **kwargs)
    
    def generate_adjustment_number(self):
        """Generate unique adjustment number: ADJ-DISTCODE-YYYY-NNNN"""
        from utils.number_generator import generate_number
        return generate_number('ADJ', ProductStatusAdjustment, 'adjustment_number', mode='yearly')


class ProductStatusAdjustmentItem(models.Model):
    """Individual product item in a status adjustment transaction"""
    
    adjustment = models.ForeignKey(ProductStatusAdjustment, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='adjustment_items')
    quantity = models.IntegerField(help_text="Number of units with this status")
    
    # Stock impact (updated only after approval)
    stock_updated = models.BooleanField(default=False, help_text="Whether stock was updated")
    previous_resaleable = models.IntegerField(default=0, help_text="Resaleable stock before adjustment")
    new_resaleable = models.IntegerField(default=0, help_text="Resaleable stock after adjustment")
    previous_non_resaleable = models.IntegerField(default=0, help_text="Non-resaleable stock before adjustment")
    new_non_resaleable = models.IntegerField(default=0, help_text="Non-resaleable stock after adjustment")
    
    class Meta:
        db_table = 'product_status_adjustment_items'
        ordering = ['id']
        unique_together = [['adjustment', 'product']]  # Prevent duplicate products in same adjustment
    
    def __str__(self):
        return f"{self.product.product_name} - {self.quantity} units"


class StockMovement(models.Model):
    """Track stock movements for Products"""
    
    MOVEMENT_TYPE_CHOICES = (
        ('opening_balance', 'Opening Balance'),
        ('purchase', 'Purchase/Stock In'),
        ('purchase_return', 'Purchase Return'),
        ('sale', 'Sale/Stock Out'),
        ('adjustment', 'Stock Count Adjustment'),
        ('return', 'Return from Shop'),
        ('exchange', 'Product Exchange'),
        ('damage', 'Damage/Wastage'),
        ('foc_in', 'FOC Received from Company'),
        ('foc_out', 'FOC Given to Shop'),
        ('status_adjustment', 'Status Adjustment (Damaged/Used/etc)'),
        ('non_resaleable_in', 'Transfer to Non-Resaleable'),
        ('non_resaleable_out', 'Dispose Non-Resaleable'),
        ('non_resaleable_restore', 'Restore to Resaleable'),
        ('return_to_company', 'Return to Company/Supplier'),
    )
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_movements', null=True, blank=True)
    movement_type = models.CharField(max_length=25, choices=MOVEMENT_TYPE_CHOICES)
    stock_type = models.CharField(
        max_length=20,
        choices=(('resaleable', 'Resaleable'), ('non_resaleable', 'Non-Resaleable')),
        default='resaleable',
        help_text="Type of stock being moved"
    )
    quantity = models.IntegerField(help_text="Positive for stock in, negative for stock out")
    previous_quantity = models.IntegerField(help_text="Stock before this movement")
    new_quantity = models.IntegerField(help_text="Stock after this movement")
    
    # Reference
    reference_number = models.CharField(max_length=50, blank=True, null=True, help_text="PO number, Bill number, etc.")
    stock_count = models.ForeignKey(
        StockCount, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Link to stock count if this is an adjustment"
    )
    notes = models.TextField(blank=True, null=True)
    
    # Cost tracking
    unit_cost = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True,
        help_text="Cost per unit at time of movement (effective cost including FOC spread)"
    )
    total_cost = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Total cost for this movement = abs(quantity) × unit_cost"
    )
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    
    class Meta:
        db_table = 'stock_movements'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.product.product_code} - {self.movement_type} - {self.quantity}"


class FIFOCostLayer(models.Model):
    """FIFO cost layer tracking for inventory costing.
    
    Each stock-in event (purchase, opening balance, return) creates a layer.
    When stock goes out (sale, exchange out), layers are consumed oldest-first.
    """
    
    LAYER_SOURCE_CHOICES = (
        ('purchase', 'Purchase/GRN'),
        ('opening_balance', 'Opening Balance'),
        ('return', 'Sales Return'),
        ('exchange_in', 'Exchange IN'),
        ('adjustment', 'Stock Adjustment'),
    )
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='cost_layers')
    unit_cost = models.DecimalField(
        max_digits=10, decimal_places=4,
        help_text="Cost per unit for this layer"
    )
    original_quantity = models.IntegerField(
        help_text="Original quantity when layer was created"
    )
    remaining_quantity = models.IntegerField(
        help_text="Remaining unconsumed quantity in this layer"
    )
    layer_source = models.CharField(max_length=20, choices=LAYER_SOURCE_CHOICES)
    reference_number = models.CharField(
        max_length=50, blank=True, null=True,
        help_text="GRN number, OB reference, Return number, etc."
    )
    is_exhausted = models.BooleanField(
        default=False,
        help_text="True when remaining_quantity reaches 0"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'fifo_cost_layers'
        ordering = ['created_at']  # Oldest first — critical for FIFO
        indexes = [
            models.Index(fields=['product', 'is_exhausted', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.product.product_code} | {self.unit_cost} | Rem: {self.remaining_quantity}/{self.original_quantity}"
    
    def consume(self, qty):
        """Consume qty units from this layer. Returns actual consumed qty."""
        actual = min(qty, self.remaining_quantity)
        self.remaining_quantity -= actual
        if self.remaining_quantity <= 0:
            self.remaining_quantity = 0
            self.is_exhausted = True
        self.save()
        return actual
    
    def restore(self, qty):
        """Restore qty units to this layer (e.g. bill cancellation)."""
        self.remaining_quantity += qty
        if self.remaining_quantity > 0:
            self.is_exhausted = False
        self.save()
    
    @classmethod
    def get_available_layers(cls, product):
        """Get non-exhausted layers for a product, oldest first."""
        return cls.objects.filter(
            product=product,
            is_exhausted=False,
            remaining_quantity__gt=0
        ).order_by('created_at')
    
    @classmethod
    def consume_fifo(cls, product, qty):
        """Consume qty units using FIFO from oldest layers.
        
        Returns:
            tuple: (weighted_avg_cost, cost_breakdown)
            - weighted_avg_cost: Decimal - weighted average unit cost
            - cost_breakdown: list of dicts with keys:
              source, reference, unit_cost, qty_consumed
        """
        from decimal import Decimal
        
        layers = cls.get_available_layers(product)
        remaining = int(qty)
        cost_breakdown = []
        total_cost = Decimal('0')
        total_consumed = 0
        
        for layer in layers:
            if remaining <= 0:
                break
            consumed = layer.consume(remaining)
            if consumed > 0:
                cost_breakdown.append({
                    'source': layer.get_layer_source_display(),
                    'reference': layer.reference_number or '',
                    'unit_cost': str(layer.unit_cost),
                    'qty_consumed': consumed,
                })
                total_cost += layer.unit_cost * consumed
                total_consumed += consumed
                remaining -= consumed
        
        # Fallback: if layers insufficient, use product.cost_after_foc
        if remaining > 0:
            fallback_cost = product.cost_after_foc if product.cost_after_foc else Decimal('0')
            cost_breakdown.append({
                'source': 'Fallback (cost_after_foc)',
                'reference': '',
                'unit_cost': str(fallback_cost),
                'qty_consumed': remaining,
            })
            total_cost += fallback_cost * remaining
            total_consumed += remaining
        
        weighted_avg = total_cost / total_consumed if total_consumed > 0 else Decimal('0')
        return weighted_avg, cost_breakdown
    
    @classmethod
    def create_layer(cls, product, qty, unit_cost, source, reference=None):
        """Create a new cost layer for stock coming in."""
        if qty <= 0:
            return None
        return cls.objects.create(
            product=product,
            unit_cost=unit_cost,
            original_quantity=qty,
            remaining_quantity=qty,
            layer_source=source,
            reference_number=reference,
        )

    @classmethod
    def replay_product_fifo(cls, product):
        """Re-replay FIFO for a single product.
        
        Call this after cancelling a stock-in (return, exchange, etc.)
        to reassign consumed quantities to the next available layers
        and update affected BillItems with correct cost_breakdown.
        
        Steps:
        1. Reset all layers for this product to full capacity
        2. Gather all stock-out events chronologically
        3. Re-consume FIFO layers in order
        4. Update affected BillItem costs and cost_breakdown
        5. Reconcile remaining with DB stock
        """
        from decimal import Decimal
        from sales.models import BillItem
        
        # Step 1: Reset all layers for this product
        cls.objects.filter(product=product).update(
            remaining_quantity=models.F('original_quantity'),
            is_exhausted=False,
        )
        
        # Step 2: Gather all stock-out movements for this product
        # Exclude cancelled return reversals
        from sales.models import Return
        cancelled_return_numbers = set(
            Return.objects.filter(
                settlement_status='cancelled'
            ).values_list('return_number', flat=True)
        )
        
        outflow_movements = list(
            StockMovement.objects.filter(
                product=product,
                quantity__lt=0,
            ).exclude(
                # Exclude cancelled return stock reversals
                movement_type='adjustment',
                reference_number__in=cancelled_return_numbers,
            ).order_by('created_at', 'id')
        )
        
        # Step 3: Build BillItem lookup for this product's sales
        bill_items_map = {}
        for item in BillItem.objects.filter(
            product=product,
            bill__bill_status='confirmed',
        ).select_related('bill'):
            key = item.bill.bill_number
            if key not in bill_items_map:
                bill_items_map[key] = []
            bill_items_map[key].append(item)
        
        # Step 4: Replay consumption
        for mv in outflow_movements:
            qty = abs(mv.quantity)
            if qty <= 0:
                continue
            
            weighted_avg, breakdown = cls.consume_fifo(product, int(qty))
            
            # If it's a sale, update the BillItem
            if mv.movement_type == 'sale' and mv.reference_number:
                items = bill_items_map.get(mv.reference_number, [])
                if items:
                    bill_item = items.pop(0)
                    total_qty = bill_item.quantity + (bill_item.foc_quantity or 0)
                    bill_item.unit_cost = weighted_avg
                    bill_item.total_cost = weighted_avg * total_qty
                    bill_item.cost_breakdown = breakdown
                    bill_item.save(update_fields=['unit_cost', 'total_cost', 'cost_breakdown'])
            
            # Update the stock movement cost too
            mv.unit_cost = weighted_avg
            mv.total_cost = weighted_avg * qty
            mv.save(update_fields=['unit_cost', 'total_cost'])
        
        # Step 5: Reconcile FIFO remaining with DB stock
        fifo_rem = cls.objects.filter(product=product).aggregate(
            total=models.Sum('remaining_quantity')
        )['total'] or 0
        diff = fifo_rem - product.quantity_in_stock
        
        if diff > 0:
            # FIFO has more than DB — consume excess
            excess = diff
            for layer in cls.objects.filter(
                product=product, remaining_quantity__gt=0
            ).order_by('created_at'):
                if excess <= 0:
                    break
                take = min(excess, layer.remaining_quantity)
                layer.remaining_quantity -= take
                if layer.remaining_quantity <= 0:
                    layer.is_exhausted = True
                layer.save()
                excess -= take
        elif diff < 0:
            # FIFO has less than DB — create adjustment layer
            shortfall = abs(diff)
            cls.objects.create(
                product=product,
                unit_cost=product.cost_after_foc or Decimal('0'),
                original_quantity=shortfall,
                remaining_quantity=shortfall,
                layer_source='adjustment',
                reference_number='RECONCILE-FIFO',
                is_exhausted=False,
            )
        
        # Update exhausted flags
        cls.objects.filter(
            product=product, remaining_quantity__lte=0
        ).update(is_exhausted=True)
        cls.objects.filter(
            product=product, remaining_quantity__gt=0
        ).update(is_exhausted=False)


class PurchaseOrder(models.Model):
    """Purchase orders from suppliers like Max Beverages"""
    
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('ordered', 'Ordered'),
        ('received', 'Received'),
        ('cancelled', 'Cancelled'),
    )
    
    po_number = models.CharField(max_length=50, unique=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='purchase_orders')
    order_date = models.DateField()
    expected_delivery_date = models.DateField(blank=True, null=True)
    received_date = models.DateField(blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Totals
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    
    class Meta:
        db_table = 'purchase_orders'
        ordering = ['-order_date', '-po_number']
    
    def __str__(self):
        return f"{self.po_number} - {self.company.company_name}"
    
    def save(self, *args, **kwargs):
        if not self.po_number:
            self.po_number = self.generate_po_number()
        super().save(*args, **kwargs)
    
    def generate_po_number(self):
        """Generate unique PO number: PO-DISTCODE-YYYY-NNNN"""
        from utils.number_generator import generate_number
        return generate_number('PO', PurchaseOrder, 'po_number', mode='yearly')
    
    def calculate_totals(self):
        """Calculate PO totals from line items"""
        items = self.items.all()
        self.subtotal = sum(item.value_before_discount for item in items)
        self.discount = sum(item.discount_amount for item in items)
        self.total = sum(item.line_total for item in items)
        self.save()


class PurchaseOrderItem(models.Model):
    """Line items in a purchase order - simple product-based tracking"""
    
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='po_items', null=True, blank=True)
    
    # Packaging info from PO (e.g., 4 packs, 96 bottles per pack)
    packs = models.IntegerField(default=0, help_text="Number of packs/cartons")
    bottles_per_pack = models.IntegerField(default=0, help_text="Bottles in each pack")
    loose_bottles = models.IntegerField(default=0, help_text="Loose bottles (not in full packs)")
    total_bottles = models.IntegerField(help_text="Total bottles (packs × bottles per pack + loose)")
    
    # FOC tracking
    foc_bottles = models.IntegerField(default=0, help_text="Free of Charge bottles received from company")
    
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    value_before_discount = models.DecimalField(max_digits=12, decimal_places=2)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)
    
    received_quantity = models.IntegerField(default=0, help_text="Actual bottles received")
    received_foc = models.IntegerField(default=0, help_text="Actual FOC bottles received")
    
    class Meta:
        db_table = 'purchase_order_items'
    
    def __str__(self):
        return f"{self.purchase_order.po_number} - {self.product.product_code}"
    
    @property
    def total_received(self):
        """Total bottles including FOC"""
        return self.received_quantity + self.received_foc
    
    def save(self, *args, **kwargs):
        # Calculate totals (FOC not included in price calculation)
        self.total_bottles = (self.packs * self.bottles_per_pack) + self.loose_bottles
        self.value_before_discount = self.total_bottles * self.unit_price
        self.discount_amount = (self.value_before_discount * self.discount_percentage) / 100
        self.line_total = self.value_before_discount - self.discount_amount
        super().save(*args, **kwargs)


class Purchase(models.Model):
    """
    Goods Received Note (GRN) - Records actual receipt of products from purchase orders
    Multiple GRNs can be created from a single PO (partial receives)
    """
    
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('received', 'Received'),
        ('cancelled', 'Cancelled'),
    )
    
    # Unique number
    grn_number = models.CharField(max_length=50, unique=True, editable=False)
    
    # Reference to PO (optional - can create GRN without PO)
    purchase_order = models.ForeignKey(
        PurchaseOrder, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='grns',
        help_text="Reference PO if this GRN is against a PO"
    )
    
    # Company info
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='purchases')
    
    # Dates
    grn_date = models.DateTimeField(default=timezone.now, help_text="Date goods were received")
    invoice_date = models.DateField(null=True, blank=True, help_text="Supplier invoice date")
    
    # Supplier Invoice Details
    supplier_invoice_number = models.CharField(max_length=100, blank=True, null=True, help_text="Supplier's invoice number")
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Financial totals
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Total before discount")
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Total discount")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Net amount payable")
    
    # Payment tracking
    payment_status = models.CharField(
        max_length=20,
        choices=(
            ('unpaid', 'Unpaid'),
            ('partially_paid', 'Partially Paid'),
            ('paid', 'Paid'),
        ),
        default='unpaid'
    )
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Notes
    notes = models.TextField(blank=True, null=True)
    
    # Stock update tracking
    stock_updated = models.BooleanField(default=False, help_text="Whether stock has been updated")
    
    # Audit trail
    created_by = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name='created_purchases')
    received_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='received_purchases', help_text="Who physically received the goods")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'purchases'
        ordering = ['-grn_date', '-grn_number']
        verbose_name = 'Purchase (GRN)'
        verbose_name_plural = 'Purchases (GRN)'
    
    def __str__(self):
        return f"{self.grn_number} - {self.company.company_name}"
    
    def save(self, *args, **kwargs):
        if not self.grn_number:
            self.grn_number = self.generate_grn_number()
        
        # Track if this is a new record or status change
        is_new = self.pk is None
        old_status = None
        if not is_new:
            old_instance = Purchase.objects.filter(pk=self.pk).first()
            if old_instance:
                old_status = old_instance.status
        
        super().save(*args, **kwargs)
        
        # Auto-create CompanyTransaction when GRN is marked as received
        if self.status == 'received' and (is_new or old_status != 'received'):
            self.create_company_transaction()
    
    def create_company_transaction(self):
        """Create CompanyTransaction when GRN is received"""
        from decimal import Decimal
        
        # Get or create company account
        account, created = CompanyAccount.objects.get_or_create(
            company=self.company,
            defaults={
                'opening_balance': Decimal('0'),
                'opening_date': timezone.localdate(),
                'created_by': self.created_by
            }
        )
        
        # Check if transaction already exists for this GRN
        if not self.account_transactions.exists():
            CompanyTransaction.objects.create(
                company_account=account,
                transaction_type='purchase',
                transaction_date=self.grn_date,
                reference_number=self.grn_number,
                amount=self.total_amount,
                settlement_method='credit',
                purchase=self,
                description=f'GRN: {self.grn_number} - {self.company.company_name}',
                created_by=self.created_by
            )
    
    def generate_grn_number(self):
        """Generate unique GRN number: GRN-DISTCODE-YYYY-NNNN"""
        from utils.number_generator import generate_number
        return generate_number('GRN', Purchase, 'grn_number', mode='yearly')
    
    def calculate_totals(self):
        """Calculate GRN totals from line items with validation"""
        from decimal import Decimal
        
        items = self.items.all()
        
        # VALIDATION: Must have items
        if not items.exists():
            raise ValidationError('Cannot calculate totals: No items added to GRN')
        
        # Calculate totals
        self.discount_amount = sum(
            item.discount_amount for item in items
        ) or Decimal('0')
        
        # Line totals = sum of (quantity × unit_price) after all discounts
        line_totals_sum = sum(
            item.line_total for item in items
        ) or Decimal('0')
        
        # Subtotal for display = total + discount (what it would cost without discount)
        self.subtotal = line_totals_sum + self.discount_amount
        self.total_amount = line_totals_sum
        
        # VALIDATION: Ensure totals make sense
        if self.subtotal < self.total_amount:
            raise ValidationError(
                f'Subtotal (Rs. {self.subtotal}) cannot be less than total (Rs. {self.total_amount})'
            )
        
        if self.discount_amount < 0:
            raise ValidationError(
                f'Discount amount cannot be negative (Rs. {self.discount_amount})'
            )
        
        if self.total_amount <= 0:
            raise ValidationError(
                f'Total amount must be positive (Rs. {self.total_amount})'
            )
        
        # VALIDATION: Check calculation consistency (within 1 paisa tolerance)
        expected_total = self.subtotal - self.discount_amount
        tolerance = Decimal('0.01')
        if abs(self.total_amount - expected_total) > tolerance:
            raise ValidationError(
                f'Calculation error: Total (Rs. {self.total_amount}) != '
                f'Subtotal (Rs. {self.subtotal}) - Discount (Rs. {self.discount_amount}) = Rs. {expected_total}'
            )
        
        self.save()
    
    @property
    def total_paid(self):
        """Calculate total amount paid from payment allocations"""
        from decimal import Decimal
        total = self.payment_allocations.aggregate(
            total=models.Sum('allocated_amount')
        )['total']
        return total or Decimal('0')
    
    @property
    def total_settled_via_returns(self):
        """Calculate total amount settled via returns using this GRN as replacement
        
        IMPORTANT: Uses NEW PurchaseReturnSettlement system (not legacy replacement_received_value)
        This ensures accurate tracking when multiple returns settle against same GRN
        """
        from decimal import Decimal
        # Import here to avoid circular import
        from products.models import PurchaseReturnSettlement
        
        # Use NEW settlement tracking system (PurchaseReturnSettlement records)
        total = PurchaseReturnSettlement.objects.filter(
            replacement_grn=self,
            settlement_method='replacement'
        ).aggregate(
            total=models.Sum('settlement_amount')
        )['total']
        return total or Decimal('0')
    
    @property
    def amount_outstanding(self):
        """Calculate remaining balance (after payments and return settlements)"""
        return self.total_amount - self.total_paid - self.total_settled_via_returns
    
    @property
    def calculated_payment_status(self):
        """Auto-calculate payment status from allocations and return settlements"""
        from decimal import Decimal
        total_settled = self.total_paid + self.total_settled_via_returns
        
        # Add tolerance for rounding differences (0.01 = 1 paisa)
        tolerance = Decimal('0.01')
        
        if total_settled >= self.total_amount - tolerance:
            return 'paid'
        elif total_settled > tolerance:
            return 'partially_paid'
        return 'unpaid'
    
    @property
    def payment_percentage(self):
        """Percentage of GRN amount paid/settled"""
        from decimal import Decimal
        if self.total_amount > 0:
            total_settled = self.total_paid + self.total_settled_via_returns
            return (total_settled / self.total_amount) * 100
        return Decimal('0')

    def sync_payment_status(self):
        """Sync stored payment_status and amount_paid from computed allocations.
        Call this after any PaymentAllocation or PurchaseReturnSettlement is created/updated."""
        self.amount_paid = self.total_paid
        self.payment_status = self.calculated_payment_status
        self.save(update_fields=['amount_paid', 'payment_status'])


class PurchaseItem(models.Model):
    """Line items in a purchase/GRN"""
    
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='purchase_items')
    
    # Packaging info
    packs = models.IntegerField(default=0, help_text="Number of packs/cartons received")
    bottles_per_pack = models.IntegerField(default=0, help_text="Bottles per pack")
    loose_bottles = models.IntegerField(default=0, help_text="Loose bottles received (not in full packs)")
    quantity = models.IntegerField(default=0, help_text="Total bottles received (packs × bottles_per_pack + loose)")
    
    # FOC tracking - added to main stock
    foc_quantity = models.IntegerField(default=0, help_text="FOC bottles received (added to main stock)")
    
    # Two-tier pricing breakdown
    marked_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Marked/list price per bottle")
    shop_discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Shop/Invoice discount %")
    invoice_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Price after shop discount")
    company_discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Company/Distributor discount %")
    
    # Final pricing (per bottle)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Final price per bottle after all discounts")
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Legacy field - total discount %")
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Legacy field - total discount amount")
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Total for this line (FOC not included)")
    
    # Batch tracking
    batch_number = models.CharField(max_length=100, blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True)
    manufacturing_date = models.DateField(blank=True, null=True)
    
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'purchase_items'
    
    def __str__(self):
        return f"{self.purchase.grn_number} - {self.product.product_code} - Qty: {self.quantity}"
    
    @property
    def total_received(self):
        """Total bottles including FOC"""
        return self.quantity + self.foc_quantity
    
    def save(self, *args, **kwargs):
        # Calculate quantity from packs and loose
        self.quantity = (self.packs * self.bottles_per_pack) + self.loose_bottles
        
        # Two-tier discount calculation:
        # 1. marked_price - shop_discount = invoice_price (shop price from product table)
        # 2. invoice_price - company_discount = unit_price (final price we pay)
        
        # If invoice_price is not set, calculate from marked_price and shop_discount
        if not self.invoice_price or self.invoice_price == 0:
            shop_discount_amount = (self.marked_price * self.shop_discount_percentage) / 100
            self.invoice_price = self.marked_price - shop_discount_amount
        
        # Calculate unit price (invoice_price/shop_price - company discount)
        company_discount_amount = (self.invoice_price * self.company_discount_percentage) / 100
        self.unit_price = self.invoice_price - company_discount_amount
        
        # Legacy discount calculations (for backward compatibility)
        # Total discount = difference between marked price and final unit price
        value_before_discount = self.quantity * self.marked_price
        total_discount = value_before_discount - (self.quantity * self.unit_price)
        self.discount_amount = total_discount
        if value_before_discount > 0:
            self.discount_percentage = (total_discount / value_before_discount) * 100
        
        # Calculate line total
        self.line_total = self.quantity * self.unit_price
        
        super().save(*args, **kwargs)


class PurchaseReturn(models.Model):
    """
    Returns to suppliers for damaged, expired, or incorrect products
    Reduces stock and tracks credit/refund from supplier
    """
    
    RETURN_TYPE_CHOICES = (
        ('expired', 'Expired Product'),
        ('damaged', 'Damaged Product'),
    )
    
    RETURN_REASON_CHOICES = (
        ('damaged', 'Damaged Product'),
        ('expired', 'Expired Product'),
        ('quality', 'Quality Issue'),
        ('wrong_product', 'Wrong Product Delivered'),
        ('excess_qty', 'Excess Quantity'),
        ('other', 'Other'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('sent_to_supplier', 'Sent to Supplier'),
        ('company_approved', 'Approved by Company'),
        ('settled', 'Settled'),
        ('rejected', 'Rejected'),
    )
    
    SETTLEMENT_TYPE_CHOICES = (
        ('replacement', 'Replacement Products'),
        ('refund', 'Cash Refund'),
    )
    
    # Unique number
    pr_number = models.CharField(max_length=50, unique=True, editable=False)
    
    # Reference to original purchase
    purchase = models.ForeignKey(
        Purchase, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='returns',
        help_text="Reference GRN if returning against specific purchase"
    )
    
    # Company info
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='purchase_returns')
    
    # Dates
    return_date = models.DateTimeField(default=timezone.now, help_text="Date return was created")
    sent_date = models.DateField(null=True, blank=True, help_text="Date items sent to supplier")
    
    # Return details
    return_type = models.CharField(max_length=20, choices=RETURN_TYPE_CHOICES, default='damaged', help_text="Main return category")
    return_reason = models.CharField(max_length=20, choices=RETURN_REASON_CHOICES)
    detailed_reason = models.TextField(default='', help_text="Detailed explanation of return")
    
    # Status and settlement
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    settlement_type = models.CharField(max_length=20, choices=SETTLEMENT_TYPE_CHOICES, default='refund')
    settlement_status = models.CharField(
        max_length=20,
        choices=(
            ('pending', 'Pending Settlement'),
            ('partial', 'Partially Settled'),
            ('fully_settled', 'Fully Settled'),
        ),
        default='pending',
        help_text="Settlement completion status"
    )
    
    # Financial tracking
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Total before discount")
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Total discount amount")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Total value of returned items")
    approved_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Amount approved by company for settlement")
    credit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Actual credit/refund received")
    credit_note_number = models.CharField(max_length=100, blank=True, null=True, help_text="Supplier's credit note reference")
    
    # Replacement tracking
    replacement_expected = models.BooleanField(default=False, help_text="Expecting replacement products")
    replacement_value_expected = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Expected replacement value")
    replacement_received = models.BooleanField(default=False, help_text="Replacement products received")
    replacement_received_value = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Actual replacement value received")
    replacement_grn = models.ForeignKey(
        Purchase,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replacement_for_returns',
        help_text="GRN containing replacement products"
    )
    replacement_notes = models.TextField(blank=True, null=True, help_text="Notes about replacement")
    
    # Stock update tracking
    stock_updated = models.BooleanField(default=False, help_text="Whether stock has been reduced")
    
    # Approval workflow
    sent_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_purchase_returns', help_text="User who sent to supplier")
    sent_at = models.DateTimeField(null=True, blank=True, help_text="When sent to supplier")
    
    approved_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_purchase_returns', help_text="User who approved company response")
    approved_at = models.DateTimeField(null=True, blank=True, help_text="When company approval was recorded")
    company_approved_date = models.DateField(null=True, blank=True, help_text="Date company approved the return")
    
    notes = models.TextField(blank=True, null=True)
    
    # Audit trail
    created_by = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name='created_purchase_returns')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'purchase_returns'
        ordering = ['-return_date', '-pr_number']
        verbose_name = 'Purchase Return'
        verbose_name_plural = 'Purchase Returns'
    
    def __str__(self):
        return f"{self.pr_number} - {self.company.company_name}"
    
    def save(self, *args, **kwargs):
        if not self.pr_number:
            self.pr_number = self.generate_pr_number()
        super().save(*args, **kwargs)
    
    def generate_pr_number(self):
        """Generate unique PR number: PR-DISTCODE-YYYY-NNNN"""
        from utils.number_generator import generate_number
        return generate_number('PR', PurchaseReturn, 'pr_number', mode='yearly')
    
    @property
    def total_settled_amount(self):
        """Calculate total amount settled from settlement records"""
        from decimal import Decimal
        total = self.settlements.aggregate(
            total=models.Sum('settlement_amount')
        )['total']
        return total or Decimal('0')
    
    @property
    def calculated_settlement_status(self):
        """Auto-calculate settlement status from settlement records"""
        from decimal import Decimal
        
        # Use approved amount if available, otherwise use total amount
        target_amount = self.approved_amount if self.approved_amount > 0 else self.total_amount
        total_settled = self.total_settled_amount
        
        if total_settled >= target_amount:
            return 'fully_settled'
        elif total_settled > Decimal('0'):
            return 'partial'
        return 'pending'
    
    @property
    def settlement_percentage(self):
        """Calculate percentage of approved amount that has been settled"""
        from decimal import Decimal
        target_amount = self.approved_amount if self.approved_amount and self.approved_amount > 0 else self.total_amount
        if target_amount and target_amount > 0:
            percentage = (self.total_settled_amount / target_amount) * 100
            return float(round(percentage, 2))
        return 0
    
    def calculate_totals(self):
        """Calculate return totals from line items"""
        items = self.items.all()
        self.subtotal = sum(item.line_total for item in items)
        self.discount_amount = 0  # Purchase returns typically don't have discounts
        self.total_amount = self.subtotal
        self.save()
    
    def create_return_transaction(self):
        """Create CompanyTransaction when return is approved"""
        from decimal import Decimal
        
        # Get or create company account
        account, created = CompanyAccount.objects.get_or_create(
            company=self.company,
            defaults={
                'opening_balance': Decimal('0'),
                'opening_date': timezone.localdate(),
                'created_by': self.created_by
            }
        )
        
        # Check if transaction already exists
        if not self.account_transactions.exists():
            # Create return transaction (negative amount = reduces what we owe)
            CompanyTransaction.objects.create(
                company_account=account,
                transaction_type='return',
                transaction_date=self.return_date,
                reference_number=self.pr_number,
                amount=-self.total_amount,  # Negative = credit to us
                settlement_method='pending_settlement',  # Settlement method recorded separately
                purchase_return=self,
                description=f'Purchase Return: {self.pr_number}',
                created_by=self.created_by
            )
    
    def record_cash_refund(self, refund_amount, reference_number, created_by):
        """
        DEPRECATED: Do not use. This method creates duplicate transactions.
        
        Use PurchaseReturnSettlement instead via update_return_settlement() view.
        See: products/purchase_views.py - update_return_settlement()
        
        This method is kept for backward compatibility but should never be called.
        If called, it will raise NotImplementedError to prevent duplicate accounting.
        
        Reason: Return transaction is already created when return is approved via
        create_return_transaction(). Creating another transaction here would
        double-count the refund amount.
        
        Migration Path:
        Instead of: purchase_return.record_cash_refund(amount, ref, user)
        Use: PurchaseReturnSettlement.objects.create(
                 purchase_return=purchase_return,
                 settlement_method='refund',
                 settlement_amount=amount,
                 refund_reference=ref,
                 cash_received_date=date.today(),
                 cash_receipt_number=receipt_no,
                 created_by=user
             )
        """
        raise NotImplementedError(
            "This method is deprecated. Use PurchaseReturnSettlement instead. "
            "Calling this method would create duplicate CompanyTransactions. "
            "See PURCHASE_RETURN_SETTLEMENT_ANALYSIS.md for details."
        )
    
    def link_replacement_grn(self, replacement_grn, created_by):
        """Link replacement GRN and create offset transaction"""
        from decimal import Decimal
        
        # Link the replacement GRN
        self.replacement_grn = replacement_grn
        self.replacement_received = True
        self.replacement_received_value = replacement_grn.total_amount
        self.save()
        
        # Create offset transaction
        account = CompanyAccount.objects.get(company=self.company)
        
        CompanyTransaction.objects.create(
            company_account=account,
            transaction_type='adjustment',
            transaction_date=timezone.now(),
            reference_number=f'{self.pr_number}-REPL',
            amount=Decimal('0'),  # Offset - no net change
            settlement_method='return_offset',
            purchase_return=self,
            description=f'Replacement GRN {replacement_grn.grn_number} for return {self.pr_number}',
            created_by=created_by
        )
        
        self.settlement_status = 'fully_settled'
        self.save()


class PurchaseReturnSettlement(models.Model):
    """
    Track individual settlement entries for a purchase return
    Note: Return itself acts as credit. Settlement methods are for actual transfers:
    - Replacement: Supplier sends replacement goods
    - Refund: Supplier pays cash back
    """
    SETTLEMENT_METHOD_CHOICES = (
        ('replacement', 'Replacement GRN'),
        ('refund', 'Cash Refund'),
    )
    
    purchase_return = models.ForeignKey(
        PurchaseReturn, 
        on_delete=models.CASCADE, 
        related_name='settlements',
        help_text="Parent purchase return"
    )
    
    settlement_method = models.CharField(
        max_length=20, 
        choices=SETTLEMENT_METHOD_CHOICES,
        help_text="Method of settlement"
    )
    
    settlement_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        help_text="Amount settled via this method"
    )
    
    # For replacement settlements
    replacement_grn = models.ForeignKey(
        Purchase,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='settlement_for_returns',
        help_text="GRN used for replacement settlement"
    )
    
    # For credit note settlements
    credit_note_number = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        help_text="Credit note reference number"
    )
    
    # For refund settlements
    refund_reference = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        help_text="Refund transaction reference"
    )
    
    # Cash refund audit trail (for settlement_method='refund')
    cash_received_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date cash was actually received from supplier"
    )
    
    cash_receipt_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Receipt/voucher number for cash received"
    )
    
    cash_verified_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_cash_refunds',
        help_text="User who verified cash receipt"
    )
    
    cash_verification_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Notes about cash verification/receipt"
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        'accounts.User', 
        on_delete=models.PROTECT,
        related_name='created_return_settlements'
    )
    
    class Meta:
        db_table = 'purchase_return_settlements'
        ordering = ['-created_at']
        verbose_name = 'Purchase Return Settlement'
        verbose_name_plural = 'Purchase Return Settlements'
    
    def __str__(self):
        if self.settlement_method == 'replacement' and self.replacement_grn:
            return f"{self.purchase_return.pr_number} - {self.replacement_grn.grn_number}: Rs. {self.settlement_amount}"
        elif self.settlement_method == 'credit_note' and self.credit_note_number:
            return f"{self.purchase_return.pr_number} - CN {self.credit_note_number}: Rs. {self.settlement_amount}"
        else:
            return f"{self.purchase_return.pr_number} - {self.get_settlement_method_display()}: Rs. {self.settlement_amount}"


class PurchaseReturnItem(models.Model):
    """Individual items in a purchase return"""
    
    purchase_return = models.ForeignKey(PurchaseReturn, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='purchase_return_items')
    
    # Quantity details
    quantity = models.IntegerField(default=0, help_text="Number of bottles being returned")
    
    # Two-tier pricing breakdown (added for transparency)
    marked_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Marked/list price per bottle")
    shop_discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Shop/Invoice discount %")
    invoice_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Price after shop discount")
    company_discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Company/Distributor discount %")
    
    # Final pricing
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Final price per bottle after all discounts")
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Total value")
    
    # Batch tracking
    batch_number = models.CharField(max_length=100, blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True)
    
    # Item-specific reason
    item_reason = models.TextField(blank=True, null=True, help_text="Specific reason for this item")
    
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'purchase_return_items'
    
    def __str__(self):
        return f"{self.purchase_return.pr_number} - {self.product.product_code} - Qty: {self.quantity}"
    
    def save(self, *args, **kwargs):
        # Calculate invoice price (marked price - shop discount)
        shop_discount_amount = (self.marked_price * self.shop_discount_percentage) / 100
        self.invoice_price = self.marked_price - shop_discount_amount
        
        # Calculate unit price (invoice price - company discount)
        company_discount_amount = (self.invoice_price * self.company_discount_percentage) / 100
        self.unit_price = self.invoice_price - company_discount_amount
        
        # Calculate line total
        self.line_total = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class CompanyAccount(models.Model):
    """
    Company account to track payables/receivables with opening balance
    Positive balance = We owe them (payable)
    Negative balance = They owe us (receivable)
    """
    
    company = models.OneToOneField(
        Company, 
        on_delete=models.CASCADE, 
        related_name='account',
        help_text="The company this account belongs to"
    )
    
    opening_balance = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        help_text="Opening balance (amount we owe to company at start)"
    )
    
    opening_date = models.DateField(
        blank=True,
        null=True,
        help_text="Date when opening balance was recorded"
    )
    
    opening_notes = models.TextField(
        blank=True, 
        null=True,
        help_text="Notes about the opening balance"
    )
    
    current_balance = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        help_text="Current outstanding balance (auto-calculated from transactions)"
    )
    
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_company_accounts'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'company_accounts'
        verbose_name = 'Company Account'
        verbose_name_plural = 'Company Accounts'
        ordering = ['company__company_name']
    
    def __str__(self):
        return f"{self.company.company_name} Account"
    
    def update_balance(self):
        """Recalculate current balance from opening balance + all transactions"""
        from decimal import Decimal
        
        # Start with opening balance
        balance = self.opening_balance
        
        # Process each transaction in order
        transactions = self.transactions.all().order_by('transaction_date', 'id')
        
        for txn in transactions:
            if txn.transaction_type in ['opening_balance', 'purchase', 'debit']:
                # Purchases increase what we owe (positive amount)
                balance += txn.amount
            elif txn.transaction_type in ['return', 'payment', 'credit', 'settlement']:
                # Returns and payments decrease what we owe
                # Their amounts are stored as NEGATIVE, so subtracting them reduces balance
                # Example: balance -= (-10000) = balance + 10000? NO!
                # Actually: return amount is -10000, so balance -= (-10000) means balance increases
                # But we WANT balance to DECREASE, so we ADD the negative amount
                balance += txn.amount  # Adding negative amount reduces balance
        
        self.current_balance = balance
        self.save(update_fields=['current_balance', 'updated_at'])


class CompanyTransaction(models.Model):
    """
    Individual transactions for company accounts
    Tracks purchases, returns, payments, and settlements
    """
    
    TRANSACTION_TYPES = [
        ('opening_balance', 'Opening Balance'),
        ('purchase', 'Purchase/GRN'),
        ('return', 'Purchase Return'),
        ('payment', 'Payment to Company'),
        ('settlement', 'Settlement Receipt'),
        ('adjustment', 'Manual Adjustment'),
    ]
    
    SETTLEMENT_METHODS = [
        ('credit', 'On Credit'),
        ('cash', 'Cash'),
        ('cheque', 'Cheque'),
        ('bank_transfer', 'Bank Transfer'),
        ('grn_offset', 'GRN Offset'),
        ('return_offset', 'Return Offset'),
        ('pending_settlement', 'Pending Settlement'),
    ]
    
    company_account = models.ForeignKey(
        CompanyAccount,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES,
        help_text="Type of transaction"
    )
    
    transaction_date = models.DateTimeField(
        help_text="Date and time of transaction"
    )
    
    reference_number = models.CharField(
        max_length=100,
        help_text="GRN number, PR number, payment number, etc."
    )
    
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Positive for purchases, negative for payments/returns"
    )
    
    settlement_method = models.CharField(
        max_length=20,
        choices=SETTLEMENT_METHODS,
        default='credit',
        blank=True,
        null=True,
        help_text="How this transaction was settled"
    )
    
    payment_reference = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Cheque number, bank transfer ID, etc."
    )
    
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Description of the transaction"
    )
    
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Additional notes"
    )
    
    # Links to related records
    purchase = models.ForeignKey(
        Purchase,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='account_transactions'
    )
    
    purchase_return = models.ForeignKey(
        PurchaseReturn,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='account_transactions'
    )
    
    # For settlement transactions (offsetting one transaction against another)
    settled_against = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='settling_transactions',
        help_text="The transaction this settles (for offset settlements)"
    )
    
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_company_transactions'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'company_transactions'
        verbose_name = 'Company Transaction'
        verbose_name_plural = 'Company Transactions'
        ordering = ['-transaction_date', '-id']
    
    def __str__(self):
        return f"{self.reference_number} - {self.get_transaction_type_display()}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Update account balance after saving transaction
        self.company_account.update_balance()


class CompanyPayment(models.Model):
    """
    Payment made to a company - can settle multiple GRNs
    Supports cash, cheque, and bank transfer payments
    """
    
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('cheque', 'Cheque'),
        ('bank_transfer', 'Bank Transfer'),
    ]
    
    # Unique payment number
    payment_number = models.CharField(max_length=50, unique=True, editable=False)
    
    # Company this payment is for
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name='payments'
    )
    
    # Payment details
    payment_date = models.DateTimeField(default=timezone.now)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Total payment amount"
    )
    
    # Method-specific details
    cheque_number = models.CharField(max_length=100, blank=True, null=True)
    cheque_date = models.DateField(blank=True, null=True)
    bank_name = models.CharField(max_length=200, blank=True, null=True)
    
    # Bank transfer details
    transfer_reference = models.CharField(max_length=100, blank=True, null=True)
    transfer_date = models.DateField(blank=True, null=True)
    
    # General reference
    reference_notes = models.TextField(blank=True, null=True)
    
    # Link to company transaction (ledger entry)
    company_transaction = models.OneToOneField(
        CompanyTransaction,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='payment_record'
    )
    
    # Audit trail
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='created_company_payments'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'company_payments'
        verbose_name = 'Company Payment'
        verbose_name_plural = 'Company Payments'
        ordering = ['-payment_date', '-payment_number']
    
    def __str__(self):
        return f"{self.payment_number} - Rs. {self.total_amount}"
    
    def save(self, *args, **kwargs):
        if not self.payment_number:
            self.payment_number = self.generate_payment_number()
        
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Auto-create company transaction for this payment
        if is_new:
            self.create_company_transaction()
    
    def generate_payment_number(self):
        """Generate unique payment number: CPY-DISTCODE-YYYY-NNNN"""
        from utils.number_generator import generate_number
        return generate_number('CPY', CompanyPayment, 'payment_number', mode='yearly')
    
    def create_company_transaction(self):
        """Create CompanyTransaction for this payment"""
        if self.company_transaction:
            return  # Already created
        
        # Get or create company account
        account, created = CompanyAccount.objects.get_or_create(
            company=self.company,
            defaults={
                'opening_balance': 0,
                'opening_date': timezone.localdate(),
                'created_by': self.created_by
            }
        )
        
        # Create transaction (negative amount reduces balance)
        transaction = CompanyTransaction.objects.create(
            company_account=account,
            transaction_type='payment',
            transaction_date=self.payment_date,
            reference_number=self.payment_number,
            amount=-self.total_amount,  # Negative = payment (reduces what we owe)
            settlement_method=self.payment_method,
            payment_reference=self.cheque_number or self.transfer_reference or '',
            description=f'Payment: {self.get_payment_method_display()}',
            created_by=self.created_by
        )
        
        self.company_transaction = transaction
        CompanyPayment.objects.filter(pk=self.pk).update(company_transaction=transaction)
    
    @property
    def allocated_amount(self):
        """Total amount allocated to GRNs"""
        from decimal import Decimal
        total = self.allocations.aggregate(
            total=models.Sum('allocated_amount')
        )['total']
        return total or Decimal('0')
    
    @property
    def unallocated_amount(self):
        """Amount not yet allocated to any GRN"""
        return self.total_amount - self.allocated_amount
    
    @property
    def is_fully_allocated(self):
        """Check if all payment amount is allocated"""
        return self.unallocated_amount == 0


class PaymentAllocation(models.Model):
    """
    Allocation of a payment to specific GRN(s)
    Enables: one payment → multiple GRNs, partial payments
    """
    
    # Payment this allocation is part of
    payment = models.ForeignKey(
        CompanyPayment,
        on_delete=models.CASCADE,
        related_name='allocations'
    )
    
    # GRN being settled
    purchase = models.ForeignKey(
        Purchase,
        on_delete=models.CASCADE,
        related_name='payment_allocations'
    )
    
    # Amount allocated to this GRN
    allocated_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Amount of payment allocated to this GRN"
    )
    
    # Notes for this specific allocation
    notes = models.TextField(blank=True, null=True)
    
    # Audit trail
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_payment_allocations'
    )
    
    class Meta:
        db_table = 'payment_allocations'
        verbose_name = 'Payment Allocation'
        verbose_name_plural = 'Payment Allocations'
        unique_together = ['payment', 'purchase']
    
    def __str__(self):
        return f"{self.payment.payment_number} → {self.purchase.grn_number}: Rs. {self.allocated_amount}"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        from decimal import Decimal
        
        # Validate allocated amount doesn't exceed payment total
        if self.allocated_amount > self.payment.total_amount:
            raise ValidationError(
                f"Allocated amount (Rs. {self.allocated_amount}) cannot exceed "
                f"payment total (Rs. {self.payment.total_amount})"
            )
        
        # Validate allocated amount doesn't exceed GRN outstanding
        if self.allocated_amount > self.purchase.amount_outstanding:
            raise ValidationError(
                f"Allocated amount (Rs. {self.allocated_amount}) cannot exceed "
                f"GRN outstanding balance (Rs. {self.purchase.amount_outstanding})"
            )
        
        # Validate total allocations don't exceed payment amount
        other_allocations = self.payment.allocations.exclude(pk=self.pk)
        total_other = other_allocations.aggregate(
            total=models.Sum('allocated_amount')
        )['total'] or Decimal('0')
        
        if total_other + self.allocated_amount > self.payment.total_amount:
            raise ValidationError(
                f"Total allocations (Rs. {total_other + self.allocated_amount}) would exceed "
                f"payment amount (Rs. {self.payment.total_amount})"
            )


class FOCValueAccount(models.Model):
    """
    FOC (Free of Charge) Value Account - Track FOC value received vs given per company
    
    This account tracks the VALUE of FOC products (calculated using shop_price):
    - FOC received from company during purchases (credit to account)
    - FOC given to shops during sales (debit from account)
    - FOC restored from returns (credit to account)
    - Implicit FOC from selling below shop_price (debit from account)
    
    Net position shows whether we've given more FOC value than received.
    """
    
    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        related_name='foc_account',
        help_text="The company this FOC account belongs to"
    )
    
    # Opening balances (historical FOC value at system start)
    opening_foc_received_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="FOC value received from company at opening (shop_price basis)"
    )
    
    opening_foc_given_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="FOC value given to shops at opening (shop_price basis)"
    )
    
    opening_date = models.DateField(
        blank=True,
        null=True,
        help_text="Date when opening balances were recorded"
    )
    
    opening_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Notes about opening FOC balances"
    )
    
    # Current balances (auto-calculated from transactions)
    total_foc_received_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Total FOC value received from company (including opening)"
    )
    
    total_foc_given_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Total FOC value given to shops (including opening)"
    )
    
    net_foc_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Positive = received more, Negative = gave more than received"
    )
    
    # Audit trail
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_foc_accounts'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'foc_value_accounts'
        ordering = ['company__company_name']
        verbose_name = 'FOC Value Account'
        verbose_name_plural = 'FOC Value Accounts'
    
    def __str__(self):
        return f"FOC Account - {self.company.company_name} (Net: Rs. {self.net_foc_value:,.2f})"
    
    def update_balance(self):
        """Recalculate FOC value balances from all transactions (excluding cancelled/archived)"""
        from decimal import Decimal
        from django.db.models import Sum, Q
        
        # Start with opening balances
        received = self.opening_foc_received_value
        given = self.opening_foc_given_value
        
        # Only include active (non-archived) transactions
        active_txns = self.transactions.filter(is_archived=False)
        
        # FOC received from suppliers/companies ONLY (what we GET)
        received_txns = active_txns.filter(
            transaction_type='foc_received'
        ).aggregate(total=Sum('foc_value'))['total'] or Decimal('0')
        
        # FOC given to shops (what we USE)
        given_txns = active_txns.filter(
            transaction_type__in=['foc_given', 'implicit_foc']
        ).aggregate(total=Sum('foc_value'))['total'] or Decimal('0')
        
        # FOC restored from returns (REDUCES what we gave, doesn't increase received)
        restored_txns = active_txns.filter(
            transaction_type='return_foc_restored'
        ).aggregate(total=Sum('foc_value'))['total'] or Decimal('0')
        
        # Handle manual adjustments (can be positive or negative)
        adjustment_txns = active_txns.filter(
            transaction_type='adjustment'
        ).aggregate(total=Sum('foc_value'))['total'] or Decimal('0')
        
        # Update totals
        # FOC Received = opening + received from suppliers + positive adjustments
        self.total_foc_received_value = received + received_txns + (adjustment_txns if adjustment_txns > 0 else Decimal('0'))
        
        # FOC Given = opening + given to shops - restored from returns + negative adjustments
        self.total_foc_given_value = given + given_txns - restored_txns + (abs(adjustment_txns) if adjustment_txns < 0 else Decimal('0'))
        
        # Net FOC Value = Received - Given (should be positive if we received more than we gave)
        self.net_foc_value = self.total_foc_received_value - self.total_foc_given_value
        
        self.save(update_fields=['total_foc_received_value', 'total_foc_given_value', 'net_foc_value', 'updated_at'])
    
    @property
    def foc_utilization_percentage(self):
        """
        Calculate FOC utilization: (gross given / received) × 100
        
        Uses GROSS FOC given (not reduced by returns) to show actual distribution rate.
        This reflects business reality: if you gave Rs. 900 and got Rs. 900 back,
        you still USED/DISTRIBUTED Rs. 900 worth of FOC, even though net is zero.
        
        Only counts active (non-cancelled) transactions.
        """
        from decimal import Decimal
        
        if self.total_foc_received_value == 0:
            return 0
        
        # Calculate GROSS FOC given (before returns) - only active transactions
        gross_given = self.transactions.filter(
            transaction_type__in=['foc_given', 'implicit_foc'],
            is_archived=False
        ).aggregate(total=models.Sum('foc_value'))['total'] or Decimal('0')
        
        # Add opening given value
        gross_given += self.opening_foc_given_value
        
        return (gross_given / self.total_foc_received_value) * 100


class FOCValueTransaction(models.Model):
    """
    Individual FOC Value Transaction Record
    
    Tracks each instance of FOC value movement:
    - foc_received: FOC received from company during GRN
    - foc_given: Explicit FOC given to shop in bill
    - return_foc_restored: FOC value restored when customer returns FOC items
    - implicit_foc: Discount given by selling below shop_price
    - adjustment: Manual adjustment (reset, correction, etc.)
    """
    
    TRANSACTION_TYPES = [
        ('foc_received', 'FOC Received from Company'),
        ('foc_given', 'FOC Given to Shop'),
        ('return_foc_restored', 'Return FOC Restored'),
        ('implicit_foc', 'Implicit FOC (Below Shop Price)'),
        ('adjustment', 'Manual Adjustment'),
    ]
    
    # Unique transaction number: FOC-20260127-001
    transaction_number = models.CharField(
        max_length=50,
        unique=True,
        editable=False,
        help_text="Auto-generated: FOC-YYYYMMDD-###"
    )
    
    # Account and transaction type
    foc_account = models.ForeignKey(
        FOCValueAccount,
        on_delete=models.CASCADE,
        related_name='transactions',
        help_text="FOC account this transaction belongs to"
    )
    
    transaction_type = models.CharField(
        max_length=30,
        choices=TRANSACTION_TYPES,
        help_text="Type of FOC transaction"
    )
    
    transaction_date = models.DateTimeField(
        help_text="When this FOC transaction occurred"
    )
    
    # Value calculation
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='foc_transactions',
        help_text="Product for which FOC was given/received"
    )
    
    foc_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Quantity of FOC (bottles)"
    )
    
    shop_price_at_time = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Shop price at time of transaction (for historical accuracy)"
    )
    
    foc_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Calculated: foc_quantity × shop_price_at_time"
    )
    
    # Reference to source transaction
    reference_number = models.CharField(
        max_length=100,
        help_text="Source document number (GRN#, Bill#, Return#)"
    )
    
    # Foreign keys to source items (nullable - only one will be set)
    purchase_item = models.ForeignKey(
        PurchaseItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='foc_transactions',
        help_text="Link to purchase item (if foc_received)"
    )
    
    bill_item = models.ForeignKey(
        'sales.BillItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='foc_transactions',
        help_text="Link to bill item (if from old bill system)"
    )
    
    return_item = models.ForeignKey(
        'sales.ReturnItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='foc_transactions',
        help_text="Link to return item (if return_foc_restored)"
    )
    
    # Additional context
    shop = models.ForeignKey(
        'shops.Shop',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='foc_transactions',
        help_text="Shop that received FOC (for foc_given transactions)"
    )
    
    sales_rep = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='foc_transactions_as_rep',
        help_text="Sales rep who gave FOC (for foc_given transactions)"
    )
    
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Additional notes about this transaction"
    )
    
    # Archival for reset functionality
    is_archived = models.BooleanField(
        default=False,
        help_text="Archived transactions (after account reset)"
    )
    
    # Audit trail
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_foc_transactions',
        help_text="User who created this transaction"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'foc_value_transactions'
        ordering = ['-transaction_date', '-id']
        verbose_name = 'FOC Value Transaction'
        verbose_name_plural = 'FOC Value Transactions'
        indexes = [
            models.Index(fields=['-transaction_date', 'foc_account']),
            models.Index(fields=['transaction_type', 'foc_account']),
            models.Index(fields=['product', 'transaction_type']),
            models.Index(fields=['is_archived']),
        ]
    
    def __str__(self):
        return f"{self.transaction_number} - {self.get_transaction_type_display()} - Rs. {self.foc_value:,.2f}"
    
    def save(self, *args, **kwargs):
        # Calculate FOC value if not manually set
        # Skip auto-calculation for implicit_foc (already calculated correctly in view)
        # Skip auto-calculation for adjustment (manually set value)
        if not self.foc_value and self.transaction_type not in ['adjustment', 'implicit_foc']:
            self.foc_value = self.foc_quantity * self.shop_price_at_time
        
        # Generate transaction number if not set
        if not self.transaction_number:
            self.transaction_number = self.generate_transaction_number()
        
        super().save(*args, **kwargs)
        
        # Update account balance after save
        self.foc_account.update_balance()
    
    def generate_transaction_number(self):
        """Generate unique transaction number: FOC-DISTCODE-YYYYMMDD-NNNN"""
        from utils.number_generator import generate_number
        return generate_number('FOC', FOCValueTransaction, 'transaction_number')


# Old Sale models moved to sales app
# Sale and SaleItem now live in sales/models.py