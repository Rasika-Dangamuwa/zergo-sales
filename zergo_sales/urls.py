"""
URL configuration for zergo_sales project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from accounts import views as accounts_views
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(url='/dashboard/', permanent=False)),
    path('dashboard/', include('dashboard.urls')),
    path('accounts/', include('accounts.urls')),
    path('shops/', include('shops.urls')),
    path('products/', include('products.urls')),
    path('sales/', include('sales.urls')),
    # path('payments/', include('payments.urls')),  # Removed: All settlement URLs moved to sales/settlements/
    path('business/', include('business.urls')),  # Business settings
    path('expenses/', include('expenses.urls')),  # Expense tracking
    
    # Authentication URLs
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', accounts_views.custom_logout, name='logout'),
]

# Only serve media files in DEBUG mode
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Customize admin site
admin.site.site_header = "Zergo Distributors Admin"
admin.site.site_title = "Zergo Sales Management"
admin.site.index_title = "Welcome to Zergo Distributors Sales Management"
