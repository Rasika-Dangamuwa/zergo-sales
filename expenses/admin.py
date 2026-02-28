from django.contrib import admin
from .models import ExpenseCategory, Expense, RecurringExpense


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon', 'color', 'is_active', 'sort_order']
    list_editable = ['sort_order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['expense_number', 'category', 'amount', 'expense_date',
                    'payment_method', 'approval_status', 'created_by']
    list_filter = ['category', 'payment_method', 'approval_status', 'expense_date']
    search_fields = ['expense_number', 'description', 'reference_number']
    date_hierarchy = 'expense_date'
    readonly_fields = ['expense_number', 'created_at', 'updated_at']


@admin.register(RecurringExpense)
class RecurringExpenseAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'amount', 'frequency',
                    'next_due_date', 'is_active']
    list_filter = ['frequency', 'is_active', 'category']
    search_fields = ['name']
