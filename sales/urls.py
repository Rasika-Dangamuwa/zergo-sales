from django.urls import path
from . import views
from . import return_views
from . import exchange_views
from . import commission_views
from . import manual_payout_views
from . import foc_views
from . import foc_reset_views
from . import eod_views
from . import monthly_plan_views
from . import ai_views
from payments import views as payment_views

app_name = 'sales'

urlpatterns = [
    path('', views.bill_list, name='list'),
    path('create/', views.create_bill, name='create'),
    path('<int:pk>/', views.bill_detail, name='detail'),
    path('<int:pk>/mobile-print/', views.mobile_print, name='mobile_print'),
    path('<int:pk>/prep-receipt/', views.prep_receipt, name='prep_receipt'),
    path('<int:pk>/edit/', views.edit_bill, name='edit'),
    path('<int:pk>/cancel/', views.cancel_bill, name='cancel'),
    path('<int:pk>/delete/', views.delete_bill, name='delete'),
    path('<int:pk>/update-discount/', views.update_discount, name='update_discount'),
    
    # Returns Management - Simplified (3 pages only)
    path('returns/', return_views.return_list, name='return_list'),
    path('returns/create/', return_views.create_return_mobile, name='create_return'),
    path('returns/<int:pk>/', return_views.return_detail, name='return_detail'),
    path('returns/<int:pk>/mobile-print/', return_views.mobile_return_print, name='mobile_return_print'),
    path('returns/<int:pk>/receipt/print/', return_views.return_receipt_print, name='return_receipt_print'),
    path('api/return-by-number/<str:return_number>/', return_views.get_return_id_by_number, name='return_id_by_number'),
    
    # Item Exchange Management - Direct exchange without return approval
    path('exchanges/', exchange_views.exchange_list, name='exchange_list'),
    path('exchanges/create/', exchange_views.create_exchange, name='create_exchange'),
    path('exchanges/<int:pk>/', exchange_views.exchange_detail, name='exchange_detail'),
    path('exchanges/<int:pk>/cancel/', exchange_views.cancel_exchange, name='cancel_exchange'),
    path('exchanges/<int:pk>/print/', exchange_views.exchange_print, name='exchange_print'),
    
    # Settlement Management (all settlement operations consolidated here)
    path('<int:pk>/add-settlement/', views.add_payment, name='add_settlement'),
    path('settlements/', payment_views.payment_list, name='settlement_list'),
    path('settlements/add/', payment_views.add_payment, name='add_settlement_form'),
    path('settlements/pending/', payment_views.pending_payments, name='pending'),
    path('settlements/<int:pk>/', payment_views.payment_detail, name='settlement_detail'),
    path('settlements/<int:pk>/cancel/', payment_views.cancel_payment, name='cancel_settlement'),
    path('settlements/<int:pk>/verify/', payment_views.verify_payment, name='verify_settlement'),
    path('settlements/<int:pk>/receipt/', views.payment_receipt, name='settlement_receipt'),
    path('settlements/<int:pk>/mobile-print/', views.payment_mobile_print, name='settlement_mobile_print'),
    path('settlements/<int:pk>/mark-collected/', views.mark_payment_collected, name='mark_settlement_collected'),
    path('settlements/<int:pk>/mark-bounced/', views.mark_payment_bounced, name='mark_settlement_bounced'),
    path('settlements/<int:pk>/mark-cheque-collected/', views.mark_cheque_collected, name='mark_cheque_collected'),
    path('settlements/<int:pk>/edit-cheque-details/', views.edit_cheque_details, name='edit_cheque_details'),
    
    # Cheque and Bank Transfer Management
    path('settlements/<int:pk>/clear-cheque/', payment_views.clear_cheque, name='clear_cheque'),
    path('settlements/<int:pk>/bounce-cheque/', payment_views.bounce_cheque, name='bounce_cheque'),
    path('settlements/<int:pk>/confirm-bank-transfer/', payment_views.confirm_bank_transfer, name='confirm_bank_transfer'),
    path('settlements/<int:pk>/reject-bank-transfer/', payment_views.reject_bank_transfer, name='reject_bank_transfer'),
    
    # Bad Debt Write-Off System
    path('settlements/write-offs/', payment_views.write_off_list, name='write_off_list'),
    path('settlements/write-offs/<int:pk>/', payment_views.write_off_detail, name='write_off_detail'),
    path('settlements/write-offs/bill/<int:bill_pk>/confirm/', payment_views.write_off_confirm, name='write_off_confirm'),
    path('settlements/write-offs/bill/<int:bill_pk>/execute/', payment_views.write_off_execute, name='write_off_execute'),
    
    # Bill Summary and Print
    path('bill/<int:pk>/summary/', views.bill_summary, name='bill_summary'),
    path('bill/<int:pk>/print-preview/', views.bill_print_preview, name='bill_print_preview'),
    
    # Commission Management
    path('commissions/', commission_views.commission_dashboard, name='commission_dashboard'),
    path('commissions/settings/', commission_views.commission_settings, name='commission_settings'),
    path('commissions/export/csv/', commission_views.export_commission_csv, name='export_commission_csv'),
    path('commissions/export/pdf/', commission_views.export_commission_pdf, name='export_commission_pdf'),
    path('commissions/generate/', commission_views.generate_commission_records, name='generate_commission_records'),
    
    # Manual Commission Payouts (must come BEFORE commission_detail to avoid conflicts)
    path('commissions/payouts/', manual_payout_views.manual_payout_list, name='manual_payout_list'),
    path('commissions/payouts/process/', manual_payout_views.process_manual_payout, name='process_manual_payout'),
    path('commissions/payouts/<int:history_id>/', manual_payout_views.payout_history_detail, name='payout_history_detail'),
    path('commissions/payouts/number/<str:payout_number>/', manual_payout_views.payout_detail_by_number, name='payout_by_number'),
    
    # Commission detail by month (generic pattern - must be LAST)
    path('commissions/<str:month>/', commission_views.commission_detail, name='commission_detail'),
    
    # FOC Value Usage Management
    path('foc/', foc_views.foc_dashboard, name='foc_dashboard'),
    path('foc/company/<int:company_id>/', foc_views.foc_company_detail, name='foc_company_detail'),
    path('foc/products/', foc_views.foc_product_report, name='foc_product_report'),
    path('foc/sales-reps/', foc_views.foc_sales_rep_report, name='foc_sales_rep_report'),
    path('foc/company/<int:company_id>/export/', foc_views.export_foc_transactions, name='export_foc_transactions'),
    
    # FOC Reset/Archive System
    path('foc/reset/confirm/', foc_reset_views.foc_reset_confirm, name='foc_reset_confirm'),
    path('foc/reset/execute/', foc_reset_views.process_foc_reset, name='process_foc_reset'),
    path('foc/resets/', foc_reset_views.foc_reset_list, name='foc_reset_list'),
    path('foc/resets/<int:reset_id>/', foc_reset_views.foc_reset_detail, name='foc_reset_detail'),
    
    # Settings
    path('settings/printer/', views.printer_settings, name='printer_settings'),
    path('settings/billing-preference/', views.save_billing_preference, name='save_billing_preference'),
    path('settings/product-price/', views.save_user_product_price, name='save_user_product_price'),

    # AI Features
    path('ai/settings/', ai_views.ai_settings, name='ai_settings'),
    path('ai/test-connection/', ai_views.ai_test_connection, name='ai_test_connection'),
    path('ai/credit-risk/<int:shop_id>/', ai_views.ai_credit_risk, name='ai_credit_risk'),
    path('ai/collection-intelligence/', ai_views.ai_collection_intelligence, name='ai_collection_intelligence'),
    
    # EOD (End of Day) Reports
    path('eod/', eod_views.eod_date_list, name='eod_date_list'),
    path('eod/settings/', eod_views.eod_settings, name='eod_settings'),
    path('eod/<str:date>/', eod_views.eod_detail, name='eod_detail'),
    path('eod/<str:date>/set-route/', eod_views.eod_set_route, name='eod_set_route'),
    path('eod/<str:date>/update-route/', eod_views.eod_update_route, name='eod_update_route'),
    path('eod/<str:date>/export/text/', eod_views.eod_export_text, name='eod_export_text'),
    path('eod/<str:date>/export/pdf/', eod_views.eod_export_pdf, name='eod_export_pdf'),

    # Monthly Plan
    path('plan/', monthly_plan_views.monthly_plan_list, name='monthly_plan_list'),
    path('plan/create/', monthly_plan_views.monthly_plan_create, name='monthly_plan_create'),
    path('plan/<int:pk>/', monthly_plan_views.monthly_plan_detail, name='monthly_plan_detail'),
    path('plan/<int:pk>/export/pdf/', monthly_plan_views.monthly_plan_export_pdf, name='monthly_plan_export_pdf'),
]
