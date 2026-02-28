from django.contrib import admin
from .models import GlobalCompany, GlobalCategory, GlobalProduct


@admin.register(GlobalCompany)
class GlobalCompanyAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'company_code', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['company_name', 'company_code']
    ordering = ['company_name']


@admin.register(GlobalCategory)
class GlobalCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name']
    ordering = ['name']


@admin.register(GlobalProduct)
class GlobalProductAdmin(admin.ModelAdmin):
    list_display = ['product_code', 'product_name', 'company', 'category', 'size', 'marked_price', 'is_active']
    list_filter = ['company', 'category', 'size', 'is_active']
    search_fields = ['product_code', 'product_name']
    ordering = ['display_order', 'product_name']
    raw_id_fields = ['company', 'category']
