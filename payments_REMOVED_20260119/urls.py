from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('', views.payment_list, name='list'),
    path('add/', views.add_payment, name='add'),
    path('<int:pk>/', views.payment_detail, name='detail'),
    path('<int:pk>/cancel/', views.cancel_payment, name='cancel'),
    path('<int:pk>/verify/', views.verify_payment, name='verify'),
    path('<int:pk>/confirm-bank-transfer/', views.confirm_bank_transfer, name='confirm_bank_transfer'),
    path('<int:pk>/clear-cheque/', views.clear_cheque, name='clear_cheque'),
    path('<int:pk>/bounce-cheque/', views.bounce_cheque, name='bounce_cheque'),
    path('pending/', views.pending_payments, name='pending'),
    path('cheques/', views.cheque_list, name='cheque_list'),
    path('credit-notes/', views.credit_note_list, name='credit_note_list'),
]
