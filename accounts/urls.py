from django.urls import path
from . import views
from . import money_views
from . import user_views

app_name = 'accounts'

urlpatterns = [
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/change-password/', views.change_password, name='change_password'),
    
    # User Management URLs
    path('users/', user_views.user_list, name='user_list'),
    path('users/create/', user_views.user_create, name='user_create'),
    path('users/<int:pk>/', user_views.user_detail, name='user_detail'),
    path('users/<int:pk>/edit/', user_views.user_edit, name='user_edit'),
    path('users/<int:pk>/toggle-active/', user_views.user_toggle_active, name='user_toggle_active'),
    path('users/<int:pk>/reset-password/', user_views.user_reset_password, name='user_reset_password'),
    path('users/<int:pk>/shop-access/', user_views.user_manage_shop_access, name='user_manage_shop_access'),
    
    # Money Account URLs
    path('money-account/', money_views.money_account_dashboard, name='money_account_dashboard'),
    path('money-accounts/', money_views.all_money_accounts, name='all_money_accounts'),
    path('money-account/add-credit/', money_views.add_credit, name='add_credit'),
    path('money-account/add-debit/', money_views.add_debit, name='add_debit'),
    path('money-account/make-payment/', money_views.make_payment, name='make_payment'),
    path('money-account/request-advance/', money_views.request_advance, name='request_advance'),
    # Removed: recover_advance - advances are early payments, not recoverable loans
    path('money-account/transactions/', money_views.transaction_history, name='transaction_history'),
    
    # Advance Request Management
    path('advances/', money_views.advance_requests_list, name='advance_requests_list'),
    path('advances/<int:pk>/approve/', money_views.approve_advance, name='approve_advance'),
    path('advances/<int:pk>/reject/', money_views.reject_advance, name='reject_advance'),
    path('advances/<int:pk>/pay/', money_views.pay_advance, name='pay_advance'),
]
