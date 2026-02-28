from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import User


class UserCreateForm(UserCreationForm):
    """Form to create a new user"""
    
    def __init__(self, *args, **kwargs):
        self.current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)
        # Non-admin users cannot create admin accounts
        if self.current_user and self.current_user.user_type != 'admin':
            self.fields['user_type'].choices = [
                c for c in User.USER_TYPE_CHOICES if c[0] != 'admin'
            ]
    
    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First name',
            'autofocus': True,
        })
    )
    last_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last name',
        })
    )
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username',
        }),
        help_text='Required. Letters, digits and @/./+/-/_ only.'
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email address (optional)',
        })
    )
    user_type = forms.ChoiceField(
        choices=User.USER_TYPE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select',
        })
    )
    phone_number = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Phone number',
        })
    )
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Address',
        })
    )
    employee_id = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Auto-generated if left blank',
        }),
        help_text='Unique employee ID. Leave blank to auto-generate.'
    )
    profile_picture = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*',
        })
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
        })
    )
    password2 = forms.CharField(
        label='Confirm password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm password',
        })
    )
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'username', 'email',
            'user_type', 'phone_number', 'address', 'employee_id',
            'profile_picture', 'password1', 'password2',
        ]
    
    def clean_employee_id(self):
        emp_id = self.cleaned_data.get('employee_id')
        if emp_id:
            qs = User.objects.filter(employee_id=emp_id)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError('This Employee ID is already in use.')
        return emp_id or None
    
    def save(self, commit=True):
        user = super().save(commit=False)
        if not user.employee_id:
            user.employee_id = self._generate_employee_id(user.user_type)
        if commit:
            user.save()
        return user
    
    @staticmethod
    def _generate_employee_id(user_type):
        prefix_map = {'admin': 'ADM', 'office': 'OFF', 'sales_rep': 'SR'}
        prefix = prefix_map.get(user_type, 'USR')
        last_user = User.objects.filter(
            employee_id__startswith=prefix
        ).order_by('-employee_id').first()
        if last_user and last_user.employee_id:
            try:
                num = int(last_user.employee_id[len(prefix):]) + 1
            except (ValueError, IndexError):
                num = 1
        else:
            num = 1
        return f"{prefix}{num:04d}"


class UserEditForm(forms.ModelForm):
    """Form to edit an existing user"""
    
    def __init__(self, *args, **kwargs):
        self.current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)
        # Non-admin users cannot assign admin role
        if self.current_user and self.current_user.user_type != 'admin':
            self.fields['user_type'].choices = [
                c for c in User.USER_TYPE_CHOICES if c[0] != 'admin'
            ]
    
    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
        })
    )
    last_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
        })
    )
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
        })
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
        })
    )
    user_type = forms.ChoiceField(
        choices=User.USER_TYPE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select',
        })
    )
    phone_number = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
        })
    )
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
        })
    )
    employee_id = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
        })
    )
    profile_picture = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*',
        })
    )
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'username', 'email',
            'user_type', 'phone_number', 'address', 'employee_id',
            'profile_picture',
        ]
    
    def clean_employee_id(self):
        emp_id = self.cleaned_data.get('employee_id')
        if emp_id:
            qs = User.objects.filter(employee_id=emp_id)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError('This Employee ID is already in use.')
        return emp_id or None
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        qs = User.objects.filter(username=username)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('This username is already taken.')
        return username


class PasswordResetByAdminForm(forms.Form):
    """Form for admin to reset a user's password"""
    
    new_password1 = forms.CharField(
        label='New password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'New password',
        })
    )
    new_password2 = forms.CharField(
        label='Confirm new password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password',
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('new_password1')
        p2 = cleaned_data.get('new_password2')
        if p1 and p2 and p1 != p2:
            raise ValidationError('Passwords do not match.')
        return cleaned_data
