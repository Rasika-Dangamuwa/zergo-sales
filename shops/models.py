from django.db import models
# from django.contrib.gis.db import models as gis_models
# from django.contrib.gis.geos import Point
from accounts.models import User


class Shop(models.Model):
    """Shop/Customer Model"""
    
    SHOP_TYPE_CHOICES = (
        ('retail', 'Retail Shop'),
        ('wholesale', 'Wholesale'),
        ('supermarket', 'Supermarket'),
        ('pharmacy', 'Pharmacy'),
        ('other', 'Other'),
    )
    
    shop_code = models.CharField(max_length=20, unique=True, blank=True, null=True)
    shop_name = models.CharField(max_length=200)
    owner_name = models.CharField(max_length=200)
    shop_type = models.CharField(max_length=20, choices=SHOP_TYPE_CHOICES, default='retail')
    shop_photo = models.ImageField(upload_to='shop_photos/', blank=True, null=True)
    
    # Contact Information
    phone_number = models.CharField(max_length=15)
    alternate_phone = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    
    # Address
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=10, blank=True, null=True)
    
    # Geolocation - Using regular fields instead of PostGIS PointField
    # location = gis_models.PointField(geography=True, null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Business Details
    business_registration_no = models.CharField(max_length=50, blank=True, null=True)
    tax_id = models.CharField(max_length=50, blank=True, null=True)
    
    # Credit Management
    credit_limit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    current_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Status
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)
    
    # Sales Rep Assignment
    assigned_sales_rep = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='assigned_shops',
        limit_choices_to={'user_type': 'sales_rep'}
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_shops')
    
    class Meta:
        db_table = 'shops'
        ordering = ['-created_at']
        verbose_name = 'Shop'
        verbose_name_plural = 'Shops'
    
    def __str__(self):
        return f"{self.shop_code} - {self.shop_name}"
    
    def save(self, *args, **kwargs):
        """Auto-generate shop_code if not provided"""
        is_new = self.pk is None
        if not self.shop_code:
            from utils.number_generator import generate_number
            self.shop_code = generate_number('SHOP', Shop, 'shop_code', mode='global')
        super().save(*args, **kwargs)
        
        # Auto-grant Level 3 access to creator
        if is_new and self.created_by:
            from shops.models import ShopAccess
            ShopAccess.grant_creator_access(self, self.created_by)
    
    @property
    def available_credit(self):
        """Calculate available credit"""
        return self.credit_limit - self.current_balance
    
    # Latitude and longitude properties kept for backward compatibility
    # @property
    # def latitude(self):
    #     return self.location.y if self.location else None
    
    # @property
    # def longitude(self):
    #     return self.location.x if self.location else None


class ShopVisit(models.Model):
    """Track shop visits by sales reps — manual or auto-marked during activities"""
    
    VISIT_TYPE_CHOICES = [
        ('manual', 'Manual Check-in'),
        ('auto_bill', 'Auto — Bill Created'),
        ('auto_payment', 'Auto — Payment Recorded'),
        ('auto_return', 'Auto — Return Created'),
        ('auto_exchange', 'Auto — Exchange Created'),
    ]
    
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='visits')
    sales_rep = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shop_visits')
    visit_date = models.DateTimeField(auto_now_add=True)
    visit_type = models.CharField(max_length=20, choices=VISIT_TYPE_CHOICES, default='manual')
    # visit_location = gis_models.PointField(geography=True, null=True, blank=True)
    visit_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    visit_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    photos = models.ImageField(upload_to='shop_visits/', blank=True, null=True)
    
    class Meta:
        db_table = 'shop_visits'
        ordering = ['-visit_date']
    
    def __str__(self):
        return f"{self.shop.shop_name} - {self.visit_date.strftime('%Y-%m-%d')} ({self.get_visit_type_display()})"
    
    @classmethod
    def already_visited_today(cls, shop, sales_rep):
        """Check if this rep already visited this shop today"""
        from django.utils import timezone
        today = timezone.localdate()
        return cls.objects.filter(
            shop=shop,
            sales_rep=sales_rep,
            visit_date__date=today
        ).exists()
    
    @classmethod
    def get_last_visit(cls, shop, sales_rep=None):
        """Get the most recent visit to a shop (optionally filtered by rep)"""
        qs = cls.objects.filter(shop=shop)
        if sales_rep:
            qs = qs.filter(sales_rep=sales_rep)
        return qs.first()  # Already ordered by -visit_date


class ShopAccess(models.Model):
    """
    Three-level access control for shops
    
    Level 1 (View Only): Can see shop in list/map, cannot view details
    Level 2 (Standard): Can view details and do activities, cannot see others' engagements
    Level 3 (Full Access): Unlimited access, auto-granted to shop creator
    """
    
    ACCESS_LEVEL_CHOICES = (
        (1, 'Level 1 - View Only (List & Map)'),
        (2, 'Level 2 - Standard Access (Activities)'),
        (3, 'Level 3 - Full Access (Unlimited)'),
    )
    
    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name='access_grants'
    )
    
    sales_rep = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='shop_access_grants',
        limit_choices_to={'user_type': 'sales_rep'}
    )
    
    access_level = models.IntegerField(
        choices=ACCESS_LEVEL_CHOICES,
        default=1,
        help_text='1=View Only, 2=Standard, 3=Full Access'
    )
    
    # Metadata
    granted_at = models.DateTimeField(auto_now_add=True)
    granted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='granted_shop_access'
    )
    notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'shop_access'
        unique_together = ('shop', 'sales_rep')
        ordering = ['-access_level', '-granted_at']
        verbose_name = 'Shop Access Grant'
        verbose_name_plural = 'Shop Access Grants'
        indexes = [
            models.Index(fields=['shop', 'sales_rep', 'is_active']),
            models.Index(fields=['sales_rep', 'access_level']),
        ]
    
    def __str__(self):
        return f"{self.sales_rep.get_full_name()} - {self.shop.shop_name} (Level {self.access_level})"
    
    @classmethod
    def get_rep_access_level(cls, shop, sales_rep):
        """Get access level for a sales rep to a specific shop
        
        Returns Level 1 (View Only) by default for all sales reps.
        This means every sales rep can see all shops in list/map view.
        """
        try:
            access = cls.objects.get(shop=shop, sales_rep=sales_rep, is_active=True)
            return access.access_level
        except cls.DoesNotExist:
            # Default: Level 1 (View Only) for all sales reps
            return 1
    
    @classmethod
    def has_access(cls, shop, sales_rep, required_level=1):
        """Check if sales rep has at least the required access level"""
        access_level = cls.get_rep_access_level(shop, sales_rep)
        return access_level is not None and access_level >= required_level
    
    @classmethod
    def grant_creator_access(cls, shop, created_by):
        """Automatically grant Level 3 access to shop creator"""
        if created_by and created_by.user_type == 'sales_rep':
            access, created = cls.objects.get_or_create(
                shop=shop,
                sales_rep=created_by,
                defaults={
                    'access_level': 3,
                    'granted_by': created_by,
                    'notes': 'Auto-granted to shop creator'
                }
            )
            if not created and access.access_level < 3:
                # Upgrade existing access to level 3
                access.access_level = 3
                access.save()
            return access
        return None


class ShopPhotoHistory(models.Model):
    """Track historical shop photos with yearly upload reminders"""
    
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='photo_history')
    photo = models.ImageField(upload_to='shop_photos/history/%Y/')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='uploaded_shop_photos')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True, help_text='Current active photo')
    notes = models.TextField(blank=True, null=True, help_text='Photo context or notes')
    
    class Meta:
        db_table = 'shop_photo_history'
        ordering = ['-uploaded_at']
        verbose_name = 'Shop Photo'
        verbose_name_plural = 'Shop Photo History'
        indexes = [
            models.Index(fields=['shop', 'is_active']),
            models.Index(fields=['shop', '-uploaded_at']),
        ]
    
    def __str__(self):
        return f"{self.shop.shop_name} - {self.uploaded_at.strftime('%Y-%m-%d')}"
    
    def save(self, *args, **kwargs):
        """When new photo is uploaded, mark it as active and deactivate others"""
        if self.is_active:
            # Deactivate all other photos for this shop
            ShopPhotoHistory.objects.filter(shop=self.shop, is_active=True).update(is_active=False)
            # Update shop's main photo field
            self.shop.shop_photo = self.photo
            self.shop.save(update_fields=['shop_photo'])
        super().save(*args, **kwargs)
    
    @classmethod
    def needs_new_photo(cls, shop):
        """Check if shop needs a new photo (yearly reminder)"""
        from django.utils import timezone
        from datetime import timedelta
        
        latest_photo = cls.objects.filter(shop=shop).first()
        if not latest_photo:
            return True, "No photo uploaded yet"
        
        # Check if latest photo is older than 1 year
        one_year_ago = timezone.now() - timedelta(days=365)
        if latest_photo.uploaded_at < one_year_ago:
            days_old = (timezone.now() - latest_photo.uploaded_at).days
            return True, f"Last photo uploaded {days_old} days ago"
        
        return False, "Photo is current"
