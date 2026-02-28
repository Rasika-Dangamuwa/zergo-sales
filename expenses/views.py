"""
Expense Views for Zergo Distributors Sales Management System

Provides CRUD for expenses and categories, expense dashboard with
summary charts, and recurring expense management.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta

from .models import Expense, ExpenseCategory, RecurringExpense
from .forms import ExpenseForm, ExpenseCategoryForm, RecurringExpenseForm


# ============================================================================
# EXPENSE DASHBOARD
# ============================================================================

@login_required
def expense_dashboard(request):
    """Main expense dashboard with summary cards and charts."""
    if request.user.user_type not in ('admin', 'office'):
        messages.error(request, 'Access denied.')
        return redirect('dashboard:home')

    # Seed default categories if none exist
    ExpenseCategory.seed_defaults()

    today = date.today()
    current_month_start = today.replace(day=1)

    # Current month expenses
    month_expenses = Expense.objects.filter(
        expense_date__gte=current_month_start,
        expense_date__lte=today,
        approval_status='approved',
    )
    month_total = month_expenses.aggregate(t=Sum('amount'))['t'] or Decimal('0')
    month_count = month_expenses.count()

    # Last month comparison
    last_month_end = current_month_start - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)
    last_month_total = Expense.objects.filter(
        expense_date__gte=last_month_start,
        expense_date__lte=last_month_end,
        approval_status='approved',
    ).aggregate(t=Sum('amount'))['t'] or Decimal('0')

    month_change = Decimal('0')
    if last_month_total > 0:
        month_change = ((month_total - last_month_total) / last_month_total * 100)

    # Year to date
    year_start = today.replace(month=1, day=1)
    ytd_total = Expense.objects.filter(
        expense_date__gte=year_start,
        expense_date__lte=today,
        approval_status='approved',
    ).aggregate(t=Sum('amount'))['t'] or Decimal('0')

    # Category breakdown (current month)
    category_breakdown = (
        month_expenses
        .values('category__name', 'category__color', 'category__icon')
        .annotate(total=Sum('amount'), count=Count('id'))
        .order_by('-total')
    )

    # Monthly trend (last 6 months)
    six_months_ago = (today - timedelta(days=180)).replace(day=1)
    monthly_trend = (
        Expense.objects.filter(
            expense_date__gte=six_months_ago,
            approval_status='approved',
        )
        .annotate(month=TruncMonth('expense_date'))
        .values('month')
        .annotate(total=Sum('amount'))
        .order_by('month')
    )
    chart_labels = [m['month'].strftime('%b %Y') for m in monthly_trend]
    chart_data = [float(m['total'] or 0) for m in monthly_trend]

    # Recent expenses
    recent_expenses = Expense.objects.select_related(
        'category', 'created_by'
    ).order_by('-expense_date', '-created_at')[:10]

    # Active recurring expenses
    active_recurring = RecurringExpense.objects.filter(
        is_active=True
    ).select_related('category').order_by('next_due_date')[:5]

    # Pending recurring (due today or past due)
    pending_recurring = RecurringExpense.objects.filter(
        is_active=True,
        next_due_date__lte=today,
    ).select_related('category')

    context = {
        'month_total': month_total,
        'month_count': month_count,
        'last_month_total': last_month_total,
        'month_change': month_change,
        'ytd_total': ytd_total,
        'category_breakdown': category_breakdown,
        'chart_labels': chart_labels,
        'chart_data': chart_data,
        'recent_expenses': recent_expenses,
        'active_recurring': active_recurring,
        'pending_recurring': pending_recurring,
    }
    return render(request, 'expenses/expense_dashboard.html', context)


# ============================================================================
# EXPENSE CRUD
# ============================================================================

@login_required
def expense_list(request):
    """List all expenses with filters."""
    if request.user.user_type not in ('admin', 'office'):
        messages.error(request, 'Access denied.')
        return redirect('dashboard:home')

    expenses = Expense.objects.select_related('category', 'created_by').all()

    # Filters
    category_id = request.GET.get('category')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    payment_method = request.GET.get('payment_method')
    search = request.GET.get('search', '').strip()

    if category_id:
        expenses = expenses.filter(category_id=category_id)
    if start_date:
        expenses = expenses.filter(expense_date__gte=start_date)
    if end_date:
        expenses = expenses.filter(expense_date__lte=end_date)
    if payment_method:
        expenses = expenses.filter(payment_method=payment_method)
    if search:
        expenses = expenses.filter(
            Q(expense_number__icontains=search) |
            Q(description__icontains=search) |
            Q(reference_number__icontains=search)
        )

    total_filtered = expenses.aggregate(t=Sum('amount'))['t'] or Decimal('0')
    total_count = expenses.count()
    categories = ExpenseCategory.objects.filter(is_active=True)

    # Pagination
    paginator = Paginator(expenses, 25)  # 25 per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'expenses': page_obj,
        'page_obj': page_obj,
        'categories': categories,
        'total_filtered': total_filtered,
        'total_count': total_count,
        'filter_category': category_id,
        'filter_start_date': start_date or '',
        'filter_end_date': end_date or '',
        'filter_payment_method': payment_method or '',
        'filter_search': search,
    }
    return render(request, 'expenses/expense_list.html', context)


@login_required
def expense_create(request):
    """Create a new expense."""
    if request.user.user_type not in ('admin', 'office'):
        messages.error(request, 'Access denied.')
        return redirect('dashboard:home')

    # Seed default categories if none exist
    ExpenseCategory.seed_defaults()

    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.created_by = request.user
            expense.approved_by = request.user
            expense.approved_at = timezone.now()
            expense.save()
            messages.success(request, f'Expense {expense.expense_number} created successfully.')
            return redirect('expenses:expense_list')
    else:
        form = ExpenseForm(initial={'expense_date': date.today()})

    return render(request, 'expenses/expense_form.html', {
        'form': form,
        'title': 'Record New Expense',
        'is_edit': False,
    })


@login_required
def expense_edit(request, pk):
    """Edit an existing expense."""
    if request.user.user_type not in ('admin', 'office'):
        messages.error(request, 'Access denied.')
        return redirect('dashboard:home')

    expense = get_object_or_404(Expense, pk=pk)

    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES, instance=expense)
        if form.is_valid():
            form.save()
            messages.success(request, f'Expense {expense.expense_number} updated.')
            return redirect('expenses:expense_list')
    else:
        form = ExpenseForm(instance=expense)

    return render(request, 'expenses/expense_form.html', {
        'form': form,
        'expense': expense,
        'title': f'Edit Expense {expense.expense_number}',
        'is_edit': True,
    })


@login_required
def expense_delete(request, pk):
    """Delete an expense."""
    if request.user.user_type != 'admin':
        messages.error(request, 'Only admins can delete expenses.')
        return redirect('expenses:expense_list')

    expense = get_object_or_404(Expense, pk=pk)
    if request.method == 'POST':
        number = expense.expense_number
        expense.delete()
        messages.success(request, f'Expense {number} deleted.')
        return redirect('expenses:expense_list')

    return render(request, 'expenses/expense_confirm_delete.html', {
        'expense': expense,
    })


# ============================================================================
# EXPENSE CATEGORIES
# ============================================================================

@login_required
def category_list(request):
    """Manage expense categories."""
    if request.user.user_type not in ('admin', 'office'):
        messages.error(request, 'Access denied.')
        return redirect('dashboard:home')

    categories = ExpenseCategory.objects.annotate(
        expense_count=Count('expenses'),
        total_amount=Sum('expenses__amount'),
    ).order_by('sort_order', 'name')

    return render(request, 'expenses/category_list.html', {
        'categories': categories,
    })


@login_required
def category_create(request):
    """Create a new expense category."""
    if request.user.user_type not in ('admin', 'office'):
        messages.error(request, 'Access denied.')
        return redirect('dashboard:home')

    if request.method == 'POST':
        form = ExpenseCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f'Category "{form.cleaned_data["name"]}" created.')
            return redirect('expenses:category_list')
    else:
        form = ExpenseCategoryForm()

    return render(request, 'expenses/category_form.html', {
        'form': form,
        'title': 'New Expense Category',
        'is_edit': False,
    })


@login_required
def category_edit(request, pk):
    """Edit an expense category."""
    if request.user.user_type not in ('admin', 'office'):
        messages.error(request, 'Access denied.')
        return redirect('dashboard:home')

    category = get_object_or_404(ExpenseCategory, pk=pk)
    if request.method == 'POST':
        form = ExpenseCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f'Category "{category.name}" updated.')
            return redirect('expenses:category_list')
    else:
        form = ExpenseCategoryForm(instance=category)

    return render(request, 'expenses/category_form.html', {
        'form': form,
        'category': category,
        'title': f'Edit Category: {category.name}',
        'is_edit': True,
    })


@login_required
def category_delete(request, pk):
    """Delete an expense category (only if no expenses linked)."""
    if request.user.user_type != 'admin':
        messages.error(request, 'Only admins can delete categories.')
        return redirect('expenses:category_list')

    category = get_object_or_404(ExpenseCategory, pk=pk)
    if category.expenses.exists():
        messages.error(request, f'Cannot delete "{category.name}" — it has linked expenses. Deactivate it instead.')
        return redirect('expenses:category_list')

    if request.method == 'POST':
        name = category.name
        category.delete()
        messages.success(request, f'Category "{name}" deleted.')
        return redirect('expenses:category_list')

    return render(request, 'expenses/category_confirm_delete.html', {
        'category': category,
    })


# ============================================================================
# RECURRING EXPENSES
# ============================================================================

@login_required
def recurring_list(request):
    """List all recurring expenses."""
    if request.user.user_type not in ('admin', 'office'):
        messages.error(request, 'Access denied.')
        return redirect('dashboard:home')

    recurring = RecurringExpense.objects.select_related(
        'category', 'created_by'
    ).annotate(
        generated_count=Count('generated_expenses'),
        total_generated=Sum('generated_expenses__amount'),
    ).order_by('-is_active', 'next_due_date')

    return render(request, 'expenses/recurring_list.html', {
        'recurring_expenses': recurring,
    })


@login_required
def recurring_create(request):
    """Create a new recurring expense."""
    if request.user.user_type not in ('admin', 'office'):
        messages.error(request, 'Access denied.')
        return redirect('dashboard:home')

    ExpenseCategory.seed_defaults()

    if request.method == 'POST':
        form = RecurringExpenseForm(request.POST)
        if form.is_valid():
            recurring = form.save(commit=False)
            recurring.created_by = request.user
            recurring.save()
            messages.success(request, f'Recurring expense "{recurring.name}" created.')
            return redirect('expenses:recurring_list')
    else:
        form = RecurringExpenseForm(initial={'start_date': date.today()})

    return render(request, 'expenses/recurring_form.html', {
        'form': form,
        'title': 'New Recurring Expense',
        'is_edit': False,
    })


@login_required
def recurring_edit(request, pk):
    """Edit a recurring expense."""
    if request.user.user_type not in ('admin', 'office'):
        messages.error(request, 'Access denied.')
        return redirect('dashboard:home')

    recurring = get_object_or_404(RecurringExpense, pk=pk)
    if request.method == 'POST':
        form = RecurringExpenseForm(request.POST, instance=recurring)
        if form.is_valid():
            form.save()
            messages.success(request, f'Recurring expense "{recurring.name}" updated.')
            return redirect('expenses:recurring_list')
    else:
        form = RecurringExpenseForm(instance=recurring)

    return render(request, 'expenses/recurring_form.html', {
        'form': form,
        'recurring': recurring,
        'title': f'Edit: {recurring.name}',
        'is_edit': True,
    })


@login_required
def recurring_delete(request, pk):
    """Delete a recurring expense."""
    if request.user.user_type != 'admin':
        messages.error(request, 'Only admins can delete recurring expenses.')
        return redirect('expenses:recurring_list')

    recurring = get_object_or_404(RecurringExpense, pk=pk)
    if request.method == 'POST':
        name = recurring.name
        recurring.delete()
        messages.success(request, f'Recurring expense "{name}" deleted.')
        return redirect('expenses:recurring_list')

    return render(request, 'expenses/recurring_confirm_delete.html', {
        'recurring': recurring,
    })


@login_required
def recurring_generate(request, pk):
    """Manually trigger generation of the next due expense from a recurring template."""
    if request.user.user_type not in ('admin', 'office'):
        messages.error(request, 'Access denied.')
        return redirect('dashboard:home')

    recurring = get_object_or_404(RecurringExpense, pk=pk)
    if request.method == 'POST':
        expense = recurring.generate_next_expense()
        if expense:
            messages.success(request, f'Generated expense {expense.expense_number} from "{recurring.name}".')
        else:
            messages.warning(request, f'Could not generate — recurring expense may be inactive or past end date.')
    return redirect('expenses:recurring_list')
