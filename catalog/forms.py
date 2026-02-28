"""
Catalog Forms - for Global Product Catalog management.
"""
from django import forms
from .models import GlobalCompany, GlobalCategory, GlobalProduct


class GlobalCompanyForm(forms.ModelForm):
    class Meta:
        model = GlobalCompany
        fields = [
            'company_name', 'company_code', 'tagline', 'description',
            'contact_person', 'phone_number', 'email', 'website',
            'address', 'city', 'country',
            'logo', 'logo_receipt',
            'is_active', 'notes',
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'company_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., MAX'}),
            'tagline': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class GlobalCategoryForm(forms.ModelForm):
    class Meta:
        model = GlobalCategory
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class GlobalProductForm(forms.ModelForm):
    class Meta:
        model = GlobalProduct
        fields = [
            'product_code', 'product_name', 'description',
            'company', 'category',
            'size', 'marked_price', 'bottles_per_pack',
            'barcode', 'product_image',
            'display_order', 'is_active',
        ]
        widgets = {
            'product_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., MAX-ORG-500'}),
            'product_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Max Orange 500ml'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'company': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'size': forms.Select(attrs={'class': 'form-select'}),
            'marked_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'bottles_per_pack': forms.NumberInput(attrs={'class': 'form-control'}),
            'barcode': forms.TextInput(attrs={'class': 'form-control'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control'}),
        }
