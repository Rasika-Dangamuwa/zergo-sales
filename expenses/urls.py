from django.urls import path
from . import views

app_name = 'expenses'

urlpatterns = [
    # Dashboard
    path('', views.expense_dashboard, name='expense_dashboard'),

    # Expenses CRUD
    path('list/', views.expense_list, name='expense_list'),
    path('create/', views.expense_create, name='expense_create'),
    path('<int:pk>/edit/', views.expense_edit, name='expense_edit'),
    path('<int:pk>/delete/', views.expense_delete, name='expense_delete'),

    # Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),

    # Recurring Expenses
    path('recurring/', views.recurring_list, name='recurring_list'),
    path('recurring/create/', views.recurring_create, name='recurring_create'),
    path('recurring/<int:pk>/edit/', views.recurring_edit, name='recurring_edit'),
    path('recurring/<int:pk>/delete/', views.recurring_delete, name='recurring_delete'),
    path('recurring/<int:pk>/generate/', views.recurring_generate, name='recurring_generate'),
]
