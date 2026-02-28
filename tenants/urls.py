"""
Tenants App URL Configuration

Central platform management URLs for managing distributors.
"""
from django.urls import path
from . import views

app_name = 'tenants'

urlpatterns = [
    # Central dashboard
    path('', views.platform_dashboard, name='dashboard'),
    
    # Distributor management
    path('distributors/', views.distributor_list, name='distributor_list'),
    path('distributors/create/', views.distributor_create, name='distributor_create'),
    path('distributors/<int:pk>/', views.distributor_detail, name='distributor_detail'),
    path('distributors/<int:pk>/edit/', views.distributor_edit, name='distributor_edit'),
    path('distributors/<int:pk>/toggle/', views.distributor_toggle, name='distributor_toggle'),
    
    # Aggregated reporting
    path('reports/', views.platform_reports, name='reports'),
    path('reports/sales-summary/', views.sales_summary_report, name='sales_summary'),
    
    # Platform settings (global)
    path('settings/', views.platform_settings, name='platform_settings'),
]
