"""
Expense Forms for Zergo Distributors Sales Management System
"""

from django import forms
from .models import Expense, ExpenseCategory, RecurringExpense


class ExpenseCategoryForm(forms.ModelForm):
    class Meta:
        model = ExpenseCategory
        fields = ['name', 'description', 'icon', 'color', 'is_active', 'sort_order']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Office Rent',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Brief description of this category',
            }),
            'icon': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'fa-building',
            }),
            'color': forms.TextInput(attrs={
                'class': 'form-control form-control-color',
                'type': 'color',
            }),
            'sort_order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }


class ExpenseForm(forms.ModelForm):
    expense_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
        })
    )

    class Meta:
        model = Expense
        fields = [
            'category', 'amount', 'expense_date', 'description',
            'payment_method', 'reference_number', 'receipt_image', 'notes',
        ]
        widgets = {
            'category': forms.Select(attrs={
                'class': 'form-select',
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'placeholder': '0.00',
            }),
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Brief description',
            }),
            'payment_method': forms.Select(attrs={
                'class': 'form-select',
            }),
            'reference_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Invoice/receipt number (optional)',
            }),
            'receipt_image': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Additional notes (optional)',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = ExpenseCategory.objects.filter(is_active=True)
        self.fields['notes'].required = False
        self.fields['reference_number'].required = False
        self.fields['receipt_image'].required = False


class RecurringExpenseForm(forms.ModelForm):
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
        })
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
        })
    )

    class Meta:
        model = RecurringExpense
        fields = [
            'name', 'category', 'amount', 'frequency', 'description',
            'payment_method', 'start_date', 'end_date', 'is_active',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Monthly Office Rent',
            }),
            'category': forms.Select(attrs={
                'class': 'form-select',
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'placeholder': '0.00',
            }),
            'frequency': forms.Select(attrs={
                'class': 'form-select',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Description carried to generated expenses',
            }),
            'payment_method': forms.Select(attrs={
                'class': 'form-select',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = ExpenseCategory.objects.filter(is_active=True)
        self.fields['description'].required = False
        self.fields['end_date'].required = False

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Set next_due_date to start_date on creation
        if not instance.pk:
            instance.next_due_date = instance.start_date
        if commit:
            instance.save()
        return instance
