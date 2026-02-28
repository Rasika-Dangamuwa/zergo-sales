from django.contrib import admin
from .models import Distributor, Domain


class DomainInline(admin.TabularInline):
    model = Domain
    extra = 1


@admin.register(Distributor)
class DistributorAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'plan', 'is_active', 'owner_name', 'created_on']
    list_filter = ['is_active', 'plan']
    search_fields = ['name', 'code', 'owner_name']
    inlines = [DomainInline]
    readonly_fields = ['schema_name', 'created_on', 'updated_on']
