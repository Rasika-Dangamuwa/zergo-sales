"""
Product utility functions shared across views.
"""
from django.db.models import Case, When, Value, IntegerField


def get_size_ordering(field_name='size'):
    """
    Returns a Case expression that maps size strings to numeric values
    for proper ordering. Matches the sales/create view's size_order list:
    250ML, 500ML, 750ML, 1000ML, 1500ML, 2200ML — unknown sizes go last.
    
    Args:
        field_name: The field to match against. Use 'size' for Product querysets,
                   or 'product__size' for related item querysets.
    
    Usage:
        from products.utils import get_size_ordering
        # Direct product queryset:
        products = Product.objects.annotate(
            size_num=get_size_ordering()
        ).order_by('size_num', 'marked_price', 'display_order', 'product_name')
        
        # Related items queryset:
        items = po.items.annotate(
            size_num=get_size_ordering('product__size')
        ).order_by('size_num', 'product__marked_price', 'product__display_order', 'product__product_name')
    """
    return Case(
        When(**{field_name: '250ML'}, then=Value(1)),
        When(**{field_name: '500ML'}, then=Value(2)),
        When(**{field_name: '750ML'}, then=Value(3)),
        When(**{field_name: '1000ML'}, then=Value(4)),
        When(**{field_name: '1500ML'}, then=Value(5)),
        When(**{field_name: '2200ML'}, then=Value(6)),
        default=Value(99),
        output_field=IntegerField(),
    )


def get_products_ordered(queryset=None, select_related_fields=None):
    """
    Returns active products with proper numeric size ordering.
    
    Args:
        queryset: Base queryset (defaults to Product.objects.filter(is_active=True))
        select_related_fields: tuple of fields for select_related
    
    Returns:
        QuerySet ordered by size (numeric), marked_price, display_order, product_name
    """
    from .models import Product
    
    if queryset is None:
        queryset = Product.objects.filter(is_active=True)
    
    if select_related_fields:
        queryset = queryset.select_related(*select_related_fields)
    
    return queryset.annotate(
        size_num=get_size_ordering()
    ).order_by('size_num', 'marked_price', 'display_order', 'product_name')
