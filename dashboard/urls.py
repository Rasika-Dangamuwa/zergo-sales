from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home, name='home'),
    path('sales-rep/', views.sales_rep_dashboard, name='sales_rep'),
    path('office/', views.office_dashboard, name='office'),
    path('reports/sales/', views.sales_report, name='sales_report'),
    path('reports/payments/', views.payment_report, name='payment_report'),
    path('reports/profit-loss/', views.profit_loss_report, name='profit_loss_report'),
    path('reports/eod/', views.distributor_eod_report, name='distributor_eod_report'),
]
