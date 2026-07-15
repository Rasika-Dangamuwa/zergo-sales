"""
Tenant Forms for Distributor Management
"""

from django import forms
from .models import Distributor


class DistributorForm(forms.ModelForm):
    """Form for creating/editing distributor tenants."""
    
    subdomain = forms.CharField(
        max_length=50,
        required=False,
        help_text="Subdomain for this distributor (e.g., 'abc' → abc.yourdomain.com)"
    )
    admin_username = forms.CharField(
        max_length=150,
        required=False,
        help_text='Username for the distributor admin account'
    )
    admin_password = forms.CharField(
        max_length=128,
        required=False,
        widget=forms.PasswordInput,
        help_text='Password for the distributor admin account'
    )
    
    class Meta:
        model = Distributor
        fields = [
            'name', 'code', 'owner_name', 'email', 'phone', 'address',
            'business_registration', 'tax_id',
            'plan', 'plan_expires', 'max_users', 'max_shops',
            'logo', 'notes',
        ]
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'plan_expires': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def clean_code(self):
        code = self.cleaned_data['code'].upper().strip()
        # Ensure code is safe for schema name
        if not code.replace('_', '').replace('-', '').isalnum():
            raise forms.ValidationError("Code must contain only letters, numbers, hyphens, and underscores.")
        return code
