"""
URL Configuration for Business Settings App

Author: GitHub Copilot
Date: January 30, 2026
"""

from django.urls import path
from . import views

app_name = 'business'

urlpatterns = [
    # Main settings page (tabbed, inline editing)
    path('settings/', views.business_settings, name='settings'),

    # AJAX – save individual profile sections
    path('save-section/<str:section>/', views.save_section, name='save_section'),

    # Legacy full-page edit (fallback)
    path('profile/edit/', views.edit_business_profile, name='edit_profile'),

    # Bank accounts CRUD
    path('bank-account/add/', views.add_bank_account, name='add_bank_account'),
    path('bank-account/<int:pk>/edit/', views.edit_bank_account, name='edit_bank_account'),
    path('bank-account/<int:pk>/delete/', views.delete_bank_account, name='delete_bank_account'),

    # Business addresses CRUD
    path('address/add/', views.add_business_address, name='add_address'),
    path('address/<int:pk>/edit/', views.edit_business_address, name='edit_address'),
    path('address/<int:pk>/delete/', views.delete_business_address, name='delete_address'),
]
