"""
Public Schema URL Configuration

These URLs are available on the main domain (not tenant subdomains).
Includes:
  - Central platform admin dashboard (manage all distributors)
  - All standard app URLs (so existing users can still work on localhost)
  - Authentication
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView


urlpatterns = [
    # Django admin (shared — manages tenants, users)
    path('admin/', admin.site.urls),
    
    # Central platform dashboard (platform admins only)
    path('platform/', include('tenants.urls')),
    
    # Global product catalog (platform admins)
    path('platform/catalog/', include('catalog.urls')),
    
    # Standard app URLs (existing functionality on main domain)
    path('', RedirectView.as_view(url='/dashboard/', permanent=False)),
    path('dashboard/', include('dashboard.urls')),
    path('accounts/', include('accounts.urls')),
    path('shops/', include('shops.urls')),
    path('products/', include('products.urls')),
    path('sales/', include('sales.urls')),
    path('business/', include('business.urls')),
    path('expenses/', include('expenses.urls')),
    
    # Authentication
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
