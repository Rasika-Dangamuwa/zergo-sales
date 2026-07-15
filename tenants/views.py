"""
Central Platform Views

Dashboard and management views for the platform super-admin.
Provides aggregated data across all distributor tenants.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django_tenants.utils import schema_context, tenant_context
from decimal import Decimal

from decouple import config

from .models import Distributor, Domain, GlobalCaseValueSetting
from .forms import DistributorForm
from .utils import create_tenant_schema


def _get_base_domain():
    """Return the base domain for tenant subdomains (e.g., 'zergosales.com' or 'localhost')."""
    return config('PRODUCTION_DOMAIN', default='localhost')


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


@platform_admin_required
def platform_dashboard(request):
    """Central dashboard showing all distributors at a glance."""
    distributors = Distributor.objects.all()
    
    # Basic stats
    total_distributors = distributors.count()
    active_distributors = distributors.filter(is_active=True).count()
    trial_distributors = distributors.filter(plan='trial').count()
    
    # Aggregate data from each tenant
    distributor_summaries = []
    total_sales_all = Decimal('0')
    total_shops_all = 0
    total_users_all = 0
    
    for dist in distributors.filter(is_active=True):
        summary = _get_distributor_summary(dist)
        distributor_summaries.append(summary)
        total_sales_all += summary.get('total_sales', Decimal('0'))
        total_shops_all += summary.get('shop_count', 0)
        total_users_all += summary.get('user_count', 0)
    
    context = {
        'total_distributors': total_distributors,
        'active_distributors': active_distributors,
        'trial_distributors': trial_distributors,
        'distributor_summaries': distributor_summaries,
        'total_sales_all': total_sales_all,
        'total_shops_all': total_shops_all,
        'total_users_all': total_users_all,
    }
    return render(request, 'tenants/platform_dashboard.html', context)


@platform_admin_required
def distributor_list(request):
    """List all distributors with key metrics."""
    distributors = Distributor.objects.all()
    
    summaries = []
    for dist in distributors:
        summary = _get_distributor_summary(dist)
        summaries.append(summary)
    
    context = {
        'summaries': summaries,
    }
    return render(request, 'tenants/distributor_list.html', context)


@platform_admin_required
def distributor_create(request):
    """Create a new distributor (tenant)."""
    base_domain = _get_base_domain()
    
    if request.method == 'POST':
        form = DistributorForm(request.POST, request.FILES)
        if form.is_valid():
            distributor = form.save(commit=False)
            # Generate schema name from code
            distributor.schema_name = f"dist_{distributor.code.lower()}"
            
            # Disable auto schema creation (we clone instead)
            Distributor.auto_create_schema = False
            try:
                distributor.save()
            finally:
                Distributor.auto_create_schema = True
            
            # Clone the public schema structure for the new tenant
            result = create_tenant_schema(distributor.schema_name, copy_data=False)
            if not result['success']:
                messages.error(request, f'Schema creation failed: {", ".join(result["errors"])}')
                distributor.delete()
                return redirect('tenants:distributor_list')
            
            # Create the primary domain using production domain or localhost
            subdomain = form.cleaned_data.get('subdomain', '') or distributor.code.lower()
            domain_name = f"{subdomain}.{base_domain}"
            Domain.objects.create(
                domain=domain_name,
                tenant=distributor,
                is_primary=True,
            )
            
            # Create admin user for the new tenant
            admin_username = form.cleaned_data.get('admin_username', '').strip()
            admin_password = form.cleaned_data.get('admin_password', '').strip()
            admin_user = None
            if admin_username and admin_password:
                from accounts.models import User
                try:
                    admin_user = User.objects.create_user(
                        username=admin_username,
                        password=admin_password,
                        user_type='admin',
                        tenant=distributor,
                        first_name=distributor.owner_name or distributor.name,
                    )
                    messages.success(
                        request,
                        f'Distributor "{distributor.name}" created! '
                        f'Domain: {domain_name} | Admin: {admin_username}'
                    )
                except Exception as e:
                    messages.warning(request, f'Distributor created but admin user failed: {e}')
            else:
                messages.success(
                    request,
                    f'Distributor "{distributor.name}" created! Domain: {domain_name}'
                )
            
            return redirect('tenants:distributor_detail', pk=distributor.pk)
    else:
        form = DistributorForm()
    
    return render(request, 'tenants/distributor_form.html', {
        'form': form,
        'title': 'Create New Distributor',
        'base_domain': base_domain,
    })


@platform_admin_required
def distributor_detail(request, pk):
    """View distributor details with full metrics."""
    distributor = get_object_or_404(Distributor, pk=pk)
    summary = _get_distributor_summary(distributor)
    domains = Domain.objects.filter(tenant=distributor)
    
    # Get users for this distributor
    from accounts.models import User
    users = User.objects.filter(tenant=distributor)
    
    context = {
        'distributor': distributor,
        'summary': summary,
        'domains': domains,
        'users': users,
    }
    return render(request, 'tenants/distributor_detail.html', context)


@platform_admin_required
def distributor_edit(request, pk):
    """Edit distributor settings."""
    distributor = get_object_or_404(Distributor, pk=pk)
    
    if request.method == 'POST':
        form = DistributorForm(request.POST, request.FILES, instance=distributor)
        if form.is_valid():
            form.save()
            messages.success(request, f'Distributor "{distributor.name}" updated.')
            return redirect('tenants:distributor_detail', pk=pk)
    else:
        form = DistributorForm(instance=distributor)
    
    return render(request, 'tenants/distributor_form.html', {
        'form': form,
        'distributor': distributor,
        'title': f'Edit: {distributor.name}',
    })


@platform_admin_required
def distributor_toggle(request, pk):
    """Activate/deactivate a distributor."""
    if request.method == 'POST':
        distributor = get_object_or_404(Distributor, pk=pk)
        # Prevent deactivating the public/platform schema
        if distributor.schema_name == 'public':
            messages.error(request, 'The Platform Admin account cannot be deactivated.')
            return redirect('tenants:distributor_detail', pk=pk)
        distributor.is_active = not distributor.is_active
        distributor.save()
        status = 'activated' if distributor.is_active else 'deactivated'
        messages.success(request, f'Distributor "{distributor.name}" {status}.')
    return redirect('tenants:distributor_list')


@platform_admin_required
def platform_reports(request):
    """Aggregated reports across all distributors."""
    distributors = Distributor.objects.filter(is_active=True)
    
    all_summaries = []
    for dist in distributors:
        summary = _get_distributor_summary(dist)
        all_summaries.append(summary)
    
    # Sort by total sales descending
    all_summaries.sort(key=lambda x: x.get('total_sales', 0), reverse=True)
    
    context = {
        'summaries': all_summaries,
        'total_sales': sum(s.get('total_sales', Decimal('0')) for s in all_summaries),
        'total_shops': sum(s.get('shop_count', 0) for s in all_summaries),
        'total_bills': sum(s.get('bill_count', 0) for s in all_summaries),
        'total_outstanding': sum(s.get('total_outstanding', Decimal('0')) for s in all_summaries),
    }
    return render(request, 'tenants/platform_reports.html', context)


@platform_admin_required
def sales_summary_report(request):
    """Detailed sales comparison across distributors."""
    distributors = Distributor.objects.filter(is_active=True)
    today = timezone.now().date()
    
    data = []
    for dist in distributors:
        if dist.schema_name == 'public':
            continue  # Skip platform admin tenant
        with schema_context(dist.schema_name):
            try:
                from sales.models import Bill
                from shops.models import Shop
                
                # Monthly sales
                month_start = today.replace(day=1)
                monthly_sales = Bill.objects.filter(
                    bill_date__date__gte=month_start
                ).exclude(bill_status='cancelled').aggregate(
                    total=Sum('total_amount')
                )['total'] or Decimal('0')
                
                # Today's sales
                today_sales = Bill.objects.filter(
                    bill_date__date=today
                ).exclude(bill_status='cancelled').aggregate(
                    total=Sum('total_amount')
                )['total'] or Decimal('0')
                
                data.append({
                    'distributor': dist,
                    'monthly_sales': monthly_sales,
                    'today_sales': today_sales,
                    'active_shops': Shop.objects.filter(is_active=True).count(),
                })
            except Exception:
                data.append({
                    'distributor': dist,
                    'monthly_sales': Decimal('0'),
                    'today_sales': Decimal('0'),
                    'active_shops': 0,
                })
    
    context = {'data': data, 'report_date': today}
    return render(request, 'tenants/sales_summary_report.html', context)


def _get_distributor_summary(distributor):
    """
    Get key metrics for a single distributor by querying their schema.
    Returns a dict with shop_count, bill_count, total_sales, etc.
    """
    summary = {
        'distributor': distributor,
        'shop_count': 0,
        'bill_count': 0,
        'total_sales': Decimal('0'),
        'total_outstanding': Decimal('0'),
        'user_count': 0,
        'product_count': 0,
    }
    
    # Count users (in public schema since User is shared)
    from accounts.models import User
    summary['user_count'] = User.objects.filter(tenant=distributor).count()
    
    # Skip public schema (no business data)
    if distributor.schema_name == 'public':
        return summary
    
    # Query tenant schema for business data
    try:
        with schema_context(distributor.schema_name):
            from shops.models import Shop
            from sales.models import Bill
            from products.models import Product
            
            summary['shop_count'] = Shop.objects.filter(is_active=True).count()
            summary['product_count'] = Product.objects.filter(is_active=True).count()
            
            bill_stats = Bill.objects.exclude(bill_status='cancelled').aggregate(
                count=Count('id'),
                total=Sum('total_amount'),
                outstanding=Sum('balance_amount'),
            )
            summary['bill_count'] = bill_stats['count'] or 0
            summary['total_sales'] = bill_stats['total'] or Decimal('0')
            summary['total_outstanding'] = bill_stats['outstanding'] or Decimal('0')
    except Exception:
        pass  # Schema may not exist yet or tables not migrated
    
    return summary


@platform_admin_required
def platform_settings(request):
    """Platform-level global settings (case value, etc.)."""
    
    if request.method == 'POST':
        case_value = request.POST.get('case_value')
        effective_date = request.POST.get('effective_date')
        notes = request.POST.get('notes', '')
        
        try:
            with schema_context('public'):
                GlobalCaseValueSetting.objects.create(
                    case_value=Decimal(case_value),
                    effective_date=effective_date,
                    created_by=request.user,
                    notes=notes,
                    is_active=True
                )
            messages.success(request, f'Case value Rs. {case_value} set successfully!')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
        
        return redirect('tenants:platform_settings')
    
    with schema_context('public'):
        settings_list = list(GlobalCaseValueSetting.objects.all())
        active_setting = GlobalCaseValueSetting.objects.filter(is_active=True).first()
    
    context = {
        'settings': settings_list,
        'active_setting': active_setting,
        'page_title': 'Platform Settings',
    }
    
    return render(request, 'tenants/platform_settings.html', context)
