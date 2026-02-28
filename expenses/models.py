"""
Expense Tracking Models for Zergo Distributors Sales Management System

Tracks operational expenses per tenant (distributor) to enable accurate
Profit & Loss reporting. Supports categories, recurring expenses,
approval workflows, and document numbering.

Author: GitHub Copilot
Date: February 2026
"""

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal


class ExpenseCategory(models.Model):
    """
    Categories for classifying business expenses.
    Pre-seeded with common categories; users can add more.
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default='')
    icon = models.CharField(
        max_length=50,
        default='fa-receipt',
        help_text="FontAwesome icon class (e.g., fa-gas-pump, fa-building)"
    )
    color = models.CharField(
        max_length=20,
        default='#6b7280',
        help_text="Hex color for dashboard charts"
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0, help_text="Lower = shown first")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name = 'Expense Category'
        verbose_name_plural = 'Expense Categories'

    def __str__(self):
        return self.name

    @classmethod
    def get_default_categories(cls):
        """Default categories to seed when a tenant is first set up."""
        return [
            {'name': 'Rent', 'icon': 'fa-building', 'color': '#2563eb', 'sort_order': 1},
            {'name': 'Utilities', 'icon': 'fa-bolt', 'color': '#f59e0b', 'sort_order': 2},
            {'name': 'Salaries & Wages', 'icon': 'fa-users', 'color': '#10b981', 'sort_order': 3},
            {'name': 'Fuel & Transport', 'icon': 'fa-gas-pump', 'color': '#ef4444', 'sort_order': 4},
            {'name': 'Vehicle Maintenance', 'icon': 'fa-car', 'color': '#8b5cf6', 'sort_order': 5},
            {'name': 'Office Supplies', 'icon': 'fa-pen', 'color': '#06b6d4', 'sort_order': 6},
            {'name': 'Marketing & Advertising', 'icon': 'fa-bullhorn', 'color': '#ec4899', 'sort_order': 7},
            {'name': 'Communication', 'icon': 'fa-phone', 'color': '#14b8a6', 'sort_order': 8},
            {'name': 'Insurance', 'icon': 'fa-shield-alt', 'color': '#6366f1', 'sort_order': 9},
            {'name': 'Repairs & Maintenance', 'icon': 'fa-wrench', 'color': '#f97316', 'sort_order': 10},
            {'name': 'Bank Charges', 'icon': 'fa-university', 'color': '#64748b', 'sort_order': 11},
            {'name': 'Miscellaneous', 'icon': 'fa-ellipsis-h', 'color': '#9ca3af', 'sort_order': 99},
        ]

    @classmethod
    def seed_defaults(cls):
        """Create default categories if none exist."""
        if cls.objects.exists():
            return
        for cat_data in cls.get_default_categories():
            cls.objects.create(**cat_data)


PAYMENT_METHOD_CHOICES = [
    ('cash', 'Cash'),
    ('bank_transfer', 'Bank Transfer'),
    ('cheque', 'Cheque'),
    ('card', 'Card'),
    ('other', 'Other'),
]

APPROVAL_STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
]

RECURRING_FREQUENCY_CHOICES = [
    ('weekly', 'Weekly'),
    ('monthly', 'Monthly'),
    ('quarterly', 'Quarterly'),
    ('yearly', 'Yearly'),
]


class Expense(models.Model):
    """
    Individual expense record. Tracks amount, category, date, payment method,
    and optional approval workflow.
    """
    expense_number = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
        help_text="Auto-generated: EXP-DISTCODE-YYYY-NNNN"
    )
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        related_name='expenses'
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Expense amount"
    )
    expense_date = models.DateField(
        help_text="Date the expense was incurred"
    )
    description = models.TextField(
        help_text="Brief description of the expense"
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='cash'
    )
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text="Invoice/receipt/cheque number"
    )
    receipt_image = models.ImageField(
        upload_to='expenses/receipts/%Y/%m/',
        blank=True,
        null=True,
        help_text="Photo of receipt or invoice"
    )
    notes = models.TextField(
        blank=True,
        default='',
        help_text="Additional notes"
    )

    # Approval
    approval_status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS_CHOICES,
        default='approved',
        help_text="Approved by default for admin/office users"
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_expenses'
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    # Recurring link
    recurring_expense = models.ForeignKey(
        'RecurringExpense',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_expenses',
        help_text="If auto-generated from a recurring expense"
    )

    # Audit
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_expenses'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-expense_date', '-created_at']
        verbose_name = 'Expense'
        verbose_name_plural = 'Expenses'

    def __str__(self):
        return f"{self.expense_number} - {self.category.name} - {self.amount}"

    def save(self, *args, **kwargs):
        if not self.expense_number:
            from utils.number_generator import generate_number
            self.expense_number = generate_number(
                'EXP', Expense, 'expense_number', mode='yearly'
            )
        super().save(*args, **kwargs)


class RecurringExpense(models.Model):
    """
    Template for recurring expenses. Generates Expense records
    on schedule (e.g., monthly rent, weekly fuel allowance).
    """
    name = models.CharField(
        max_length=200,
        help_text="Descriptive name (e.g., 'Monthly Office Rent')"
    )
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        related_name='recurring_expenses'
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    frequency = models.CharField(
        max_length=20,
        choices=RECURRING_FREQUENCY_CHOICES,
        default='monthly'
    )
    description = models.TextField(
        blank=True,
        default='',
        help_text="Description carried to generated expenses"
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='cash'
    )

    # Schedule
    start_date = models.DateField(help_text="When to start generating expenses")
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Leave blank for indefinite"
    )
    next_due_date = models.DateField(
        help_text="Next date this expense will be generated"
    )
    is_active = models.BooleanField(default=True)

    # Audit
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_recurring_expenses'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['next_due_date', 'name']
        verbose_name = 'Recurring Expense'
        verbose_name_plural = 'Recurring Expenses'

    def __str__(self):
        return f"{self.name} ({self.get_frequency_display()}) - {self.amount}"

    def generate_next_expense(self):
        """Create the next Expense record and advance next_due_date."""
        from dateutil.relativedelta import relativedelta

        if not self.is_active:
            return None
        if self.end_date and self.next_due_date > self.end_date:
            self.is_active = False
            self.save(update_fields=['is_active'])
            return None

        expense = Expense.objects.create(
            category=self.category,
            amount=self.amount,
            expense_date=self.next_due_date,
            description=self.description or self.name,
            payment_method=self.payment_method,
            approval_status='approved',
            recurring_expense=self,
            created_by=self.created_by,
        )

        # Advance to next due date
        freq_map = {
            'weekly': relativedelta(weeks=1),
            'monthly': relativedelta(months=1),
            'quarterly': relativedelta(months=3),
            'yearly': relativedelta(years=1),
        }
        self.next_due_date += freq_map[self.frequency]
        if self.end_date and self.next_due_date > self.end_date:
            self.is_active = False
        self.save(update_fields=['next_due_date', 'is_active'])

        return expense
