from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # Settlement Management
    path('', views.payment_list, name='settlement_list'),
    path('add/', views.add_payment, name='add_settlement'),
    path('<int:pk>/', views.payment_detail, name='settlement_detail'),
    path('<int:pk>/cancel/', views.cancel_payment, name='cancel_settlement'),
    path('<int:pk>/verify/', views.verify_payment, name='verify_settlement'),
    
    # Cheque and Bank Transfer Management
    path('<int:pk>/clear-cheque/', views.clear_cheque, name='clear_cheque'),
    path('<int:pk>/bounce-cheque/', views.bounce_cheque, name='bounce_cheque'),
    path('<int:pk>/confirm-bank-transfer/', views.confirm_bank_transfer, name='confirm_bank_transfer'),
    path('<int:pk>/reject-bank-transfer/', views.reject_bank_transfer, name='reject_bank_transfer'),
    
    # Bad Debt Write-Off System
    path('write-offs/', views.write_off_list, name='write_off_list'),
    path('write-offs/<int:pk>/', views.write_off_detail, name='write_off_detail'),
    path('write-offs/bill/<int:bill_pk>/confirm/', views.write_off_confirm, name='write_off_confirm'),
    path('write-offs/bill/<int:bill_pk>/execute/', views.write_off_execute, name='write_off_execute'),
    
    # Special views
    path('pending/', views.pending_payments, name='pending'),
]

