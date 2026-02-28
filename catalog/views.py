"""
Global Product Catalog Views

Platform admin views for managing the global product catalog (companies,
categories, products). These views run in the public schema and are
accessible only to platform admins.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Count, Q

from .models import GlobalCompany, GlobalCategory, GlobalProduct
from .forms import GlobalCompanyForm, GlobalCategoryForm, GlobalProductForm


def platform_admin_required(view_func):
    """Decorator: only platform super-admins can access."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not (request.user.is_platform_admin or request.user.is_superuser):
            messages.error(request, 'Access denied. Platform admin privileges required.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


# =============================================================================
# CATALOG DASHBOARD
# =============================================================================

@platform_admin_required
def catalog_dashboard(request):
    """Overview of the global product catalog."""
    context = {
        'total_companies': GlobalCompany.objects.filter(is_active=True).count(),
        'total_categories': GlobalCategory.objects.filter(is_active=True).count(),
        'total_products': GlobalProduct.objects.filter(is_active=True).count(),
        'inactive_products': GlobalProduct.objects.filter(is_active=False).count(),
        'recent_products': GlobalProduct.objects.select_related('company', 'category').order_by('-created_at')[:10],
        'companies': GlobalCompany.objects.filter(is_active=True).annotate(
            product_count=Count('products', filter=Q(products__is_active=True))
        ),
    }
    return render(request, 'catalog/dashboard.html', context)


# =============================================================================
# GLOBAL COMPANIES
# =============================================================================

@platform_admin_required
def company_list(request):
    """List all global companies/brands."""
    companies = GlobalCompany.objects.annotate(
        product_count=Count('products', filter=Q(products__is_active=True))
    ).order_by('company_name')
    return render(request, 'catalog/company_list.html', {'companies': companies})


@platform_admin_required
def company_create(request):
    """Create a new global company."""
    if request.method == 'POST':
        form = GlobalCompanyForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, f'Company "{form.instance.company_name}" created successfully.')
            return redirect('catalog:company_list')
    else:
        form = GlobalCompanyForm()
    return render(request, 'catalog/company_form.html', {'form': form, 'action': 'Create'})


@platform_admin_required
def company_edit(request, pk):
    """Edit a global company."""
    company = get_object_or_404(GlobalCompany, pk=pk)
    if request.method == 'POST':
        form = GlobalCompanyForm(request.POST, request.FILES, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, f'Company "{company.company_name}" updated.')
            return redirect('catalog:company_list')
    else:
        form = GlobalCompanyForm(instance=company)
    return render(request, 'catalog/company_form.html', {'form': form, 'action': 'Edit', 'company': company})


# =============================================================================
# GLOBAL CATEGORIES
# =============================================================================

@platform_admin_required
def category_list(request):
    """List all global categories."""
    categories = GlobalCategory.objects.annotate(
        product_count=Count('products', filter=Q(products__is_active=True))
    ).order_by('name')
    return render(request, 'catalog/category_list.html', {'categories': categories})


@platform_admin_required
def category_create(request):
    """Create a new global category."""
    if request.method == 'POST':
        form = GlobalCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f'Category "{form.instance.name}" created successfully.')
            return redirect('catalog:category_list')
    else:
        form = GlobalCategoryForm()
    return render(request, 'catalog/category_form.html', {'form': form, 'action': 'Create'})


@platform_admin_required
def category_edit(request, pk):
    """Edit a global category."""
    category = get_object_or_404(GlobalCategory, pk=pk)
    if request.method == 'POST':
        form = GlobalCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f'Category "{category.name}" updated.')
            return redirect('catalog:category_list')
    else:
        form = GlobalCategoryForm(instance=category)
    return render(request, 'catalog/category_form.html', {'form': form, 'action': 'Edit', 'category': category})


# =============================================================================
# GLOBAL PRODUCTS
# =============================================================================

@platform_admin_required
def product_list(request):
    """List all global products with filtering."""
    products = GlobalProduct.objects.select_related('company', 'category')
    
    # Filters
    company_id = request.GET.get('company')
    category_id = request.GET.get('category')
    size = request.GET.get('size')
    search = request.GET.get('q', '').strip()
    show_inactive = request.GET.get('inactive') == '1'
    
    if company_id:
        products = products.filter(company_id=company_id)
    if category_id:
        products = products.filter(category_id=category_id)
    if size:
        products = products.filter(size=size)
    if search:
        products = products.filter(
            Q(product_name__icontains=search) |
            Q(product_code__icontains=search) |
            Q(company__company_name__icontains=search)
        )
    if not show_inactive:
        products = products.filter(is_active=True)
    
    context = {
        'products': products.order_by('display_order', 'product_name'),
        'companies': GlobalCompany.objects.filter(is_active=True),
        'categories': GlobalCategory.objects.filter(is_active=True),
        'size_choices': GlobalProduct.SIZE_CHOICES,
        'current_company': company_id,
        'current_category': category_id,
        'current_size': size,
        'current_search': search,
        'show_inactive': show_inactive,
    }
    return render(request, 'catalog/product_list.html', context)


@platform_admin_required
def product_create(request):
    """Create a new global product."""
    if request.method == 'POST':
        form = GlobalProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, f'Product "{form.instance.product_name}" added to global catalog.')
            return redirect('catalog:product_list')
    else:
        form = GlobalProductForm()
    return render(request, 'catalog/product_form.html', {'form': form, 'action': 'Create'})


@platform_admin_required
def product_detail(request, pk):
    """View global product details and which distributors have activated it."""
    product = get_object_or_404(
        GlobalProduct.objects.select_related('company', 'category'),
        pk=pk
    )
    
    # Check which distributors have activated this product
    from tenants.models import Distributor
    from django_tenants.utils import schema_context
    
    activated_distributors = []
    for dist in Distributor.objects.filter(is_active=True).exclude(schema_name='public'):
        try:
            with schema_context(dist.schema_name):
                from products.models import Product
                tenant_product = Product.objects.filter(global_product=product).first()
                if tenant_product:
                    activated_distributors.append({
                        'distributor': dist,
                        'product': tenant_product,
                        'stock': tenant_product.quantity_in_stock,
                    })
        except Exception:
            pass
    
    context = {
        'product': product,
        'activated_distributors': activated_distributors,
    }
    return render(request, 'catalog/product_detail.html', context)


@platform_admin_required
def product_edit(request, pk):
    """Edit a global product."""
    product = get_object_or_404(GlobalProduct, pk=pk)
    if request.method == 'POST':
        form = GlobalProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f'Product "{product.product_name}" updated.')
            return redirect('catalog:product_detail', pk=pk)
    else:
        form = GlobalProductForm(instance=product)
    return render(request, 'catalog/product_form.html', {'form': form, 'action': 'Edit', 'product': product})


@platform_admin_required
def product_toggle(request, pk):
    """Toggle product active/inactive status."""
    product = get_object_or_404(GlobalProduct, pk=pk)
    product.is_active = not product.is_active
    product.save()
    status = 'activated' if product.is_active else 'deactivated'
    messages.success(request, f'Product "{product.product_name}" {status}.')
    return redirect('catalog:product_list')
