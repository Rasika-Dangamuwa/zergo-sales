"""
Catalog App URL Configuration

Platform-level URLs for managing the global product catalog.
Mounted at /platform/catalog/ in urls_public.py.
"""
from django.urls import path
from . import views

app_name = 'catalog'

urlpatterns = [
    # Dashboard
    path('', views.catalog_dashboard, name='dashboard'),
    
    # Global Companies (brands)
    path('companies/', views.company_list, name='company_list'),
    path('companies/create/', views.company_create, name='company_create'),
    path('companies/<int:pk>/edit/', views.company_edit, name='company_edit'),
    
    # Global Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    
    # Global Products
    path('products/', views.product_list, name='product_list'),
    path('products/create/', views.product_create, name='product_create'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),
    path('products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('products/<int:pk>/toggle/', views.product_toggle, name='product_toggle'),
]
