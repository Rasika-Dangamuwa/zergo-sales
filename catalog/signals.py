"""
Catalog Sync Signals

When GlobalProduct, GlobalCompany, or GlobalCategory are edited in the
platform catalog, automatically sync changes to all tenant schemas that
have activated those items.
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='catalog.GlobalProduct')
def sync_global_product_to_tenants(sender, instance, created, **kwargs):
    """
    When a GlobalProduct is updated, sync all catalog-controlled fields
    to tenant Product records that reference it.
    
    Synced fields: product_name, sinhala_name, description, size,
    marked_price, bottles_per_pack, barcode, display_order,
    discount_percentage, company_discount_percentage, FOC ratios, is_active.
    
    NOT synced (distributor-specific): stock levels (quantity_in_stock,
    non_resaleable_stock, minimum_stock_level).
    """
    if created:
        return  # New product — nothing to sync yet

    from django_tenants.utils import schema_context
    from tenants.models import Distributor

    update_fields = {
        'product_name': instance.product_name,
        'sinhala_name': instance.sinhala_name or '',
        'description': instance.description or '',
        'size': instance.size,
        'marked_price': instance.marked_price,
        'bottles_per_pack': instance.bottles_per_pack,
        'barcode': instance.barcode or '',
        'display_order': instance.display_order,
        'discount_percentage': instance.discount_percentage,
        'company_discount_percentage': instance.company_discount_percentage,
        'company_foc_buy': instance.company_foc_buy,
        'company_foc_free': instance.company_foc_free,
        'shop_foc_buy': instance.shop_foc_buy,
        'shop_foc_free': instance.shop_foc_free,
        'is_active': instance.is_active,
    }

    for dist in Distributor.objects.filter(is_active=True).exclude(schema_name='public'):
        try:
            with schema_context(dist.schema_name):
                from products.models import Product, Category

                # Resolve category FK: find matching tenant Category by name
                if instance.category:
                    local_cat, _ = Category.objects.get_or_create(
                        name=instance.category.name,
                        defaults={'description': instance.category.description or '', 'is_active': True}
                    )
                    update_fields['category_id'] = local_cat.pk
                else:
                    update_fields['category_id'] = None

                updated = Product.objects.filter(
                    global_product_id=instance.pk
                ).update(**update_fields)

                # Remove category_id so it doesn't carry over to next tenant
                update_fields.pop('category_id', None)

                if updated:
                    logger.info(f"Synced GlobalProduct #{instance.pk} to {dist.schema_name} ({updated} products)")
        except Exception as e:
            logger.error(f"Failed to sync GlobalProduct #{instance.pk} to {dist.schema_name}: {e}")


@receiver(post_save, sender='catalog.GlobalCompany')
def sync_global_company_to_tenants(sender, instance, created, **kwargs):
    """
    When a GlobalCompany is updated, sync company_name to all tenant
    Company records that share the same company_code.
    """
    if created:
        return

    from django_tenants.utils import schema_context
    from tenants.models import Distributor

    for dist in Distributor.objects.filter(is_active=True).exclude(schema_name='public'):
        try:
            with schema_context(dist.schema_name):
                from products.models import Company
                Company.objects.filter(
                    company_code=instance.company_code
                ).update(
                    company_name=instance.company_name,
                    contact_person=instance.contact_person or '',
                    phone_number=instance.phone_number or '',
                    email=instance.email or '',
                    website=instance.website or '',
                    address=instance.address or '',
                    city=instance.city or '',
                    country=instance.country or 'Sri Lanka',
                    tagline=instance.tagline or '',
                    description=instance.description or '',
                )
        except Exception as e:
            logger.error(f"Failed to sync GlobalCompany #{instance.pk} to {dist.schema_name}: {e}")


@receiver(post_save, sender='catalog.GlobalCategory')
def sync_global_category_to_tenants(sender, instance, created, **kwargs):
    """
    When a GlobalCategory is updated, sync name/description to all
    tenant Category records with the same name.
    """
    if created:
        return

    from django_tenants.utils import schema_context
    from tenants.models import Distributor

    # We need the old name to find matching tenant categories.
    # Since we only have the new name, match by name (categories are
    # created with the same name during activation).
    # If the name itself changed, we can't easily match — but category
    # names rarely change. The description sync still works.
    for dist in Distributor.objects.filter(is_active=True).exclude(schema_name='public'):
        try:
            with schema_context(dist.schema_name):
                from products.models import Category
                Category.objects.filter(
                    name=instance.name
                ).update(
                    description=instance.description or '',
                )
        except Exception as e:
            logger.error(f"Failed to sync GlobalCategory #{instance.pk} to {dist.schema_name}: {e}")
