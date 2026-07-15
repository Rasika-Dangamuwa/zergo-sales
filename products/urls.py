from django.urls import path
from . import views
from . import purchase_views
from . import po_views
from . import company_account_views

app_name = 'products'

urlpatterns = [
    path('', views.product_list, name='list'),
    path('<int:pk>/', views.product_detail, name='detail'),
    path('companies/', views.company_list, name='company_list'),
    path('stock-alert/', views.stock_alert, name='stock_alert'),
    path('stock-inventory-pdf/', views.stock_inventory_pdf, name='stock_inventory_pdf'),
    path('stock-count/', views.stock_count, name='stock_count'),
    path('stock-count/history/', views.stock_count_history, name='stock_count_history'),
    path('stock-count/<int:count_id>/', views.stock_count_detail, name='stock_count_detail'),
    path('stock-count/<int:count_id>/delete/', views.stock_count_delete, name='stock_count_delete'),
    path('status-adjustment/', views.product_status_adjustment, name='product_status_adjustment'),
    path('status-adjustment/history/', views.product_status_history, name='product_status_history'),
    path('status-adjustment/<int:adjustment_id>/', views.product_status_detail, name='product_status_detail'),
    path('status-adjustment/<int:adjustment_id>/delete/', views.product_status_delete, name='product_status_delete'),
    path('status-adjustment/<int:adjustment_id>/approve/', views.approve_status_adjustment, name='approve_status_adjustment'),
    path('status-adjustment/<int:adjustment_id>/reject/', views.reject_status_adjustment, name='reject_status_adjustment'),
    path('opening-balance/', views.opening_balance, name='opening_balance'),
    path('usage-history/', views.product_usage_history, name='product_usage_history'),
    
    # Non-Resaleable Stock Management
    path('non-resaleable/', views.non_resaleable_inventory_list, name='non_resaleable_inventory_list'),
    path('non-resaleable/dispose/', views.dispose_non_resaleable_stock, name='dispose_non_resaleable_stock'),
    path('non-resaleable/recover/', views.recover_non_resaleable_stock, name='recover_non_resaleable_stock'),
    
    # Purchase Orders (PO)
    path('pos/', po_views.po_list, name='po_list'),
    path('pos/create/', po_views.create_po, name='create_po'),
    path('pos/<int:pk>/', po_views.po_detail, name='po_detail'),
    path('pos/<int:pk>/edit/', po_views.edit_po, name='edit_po'),
    path('pos/<int:pk>/print/', po_views.print_po_pdf, name='print_po_pdf'),
    path('pos/<int:pk>/mark-ordered/', po_views.mark_po_ordered, name='mark_po_ordered'),
    path('pos/<int:pk>/cancel/', po_views.cancel_po, name='cancel_po'),
    path('pos/<int:pk>/create-grn/', po_views.create_grn_from_po, name='create_grn_from_po'),
    
    # Purchase/GRN Management
    path('purchases/', purchase_views.purchase_list, name='purchase_list'),
    path('purchases/create/', purchase_views.create_purchase, name='create_purchase'),
    path('purchases/<int:pk>/', purchase_views.purchase_detail, name='purchase_detail'),
    path('purchases/<int:pk>/edit/', purchase_views.edit_purchase, name='edit_purchase'),
    path('purchases/<int:pk>/update-stock/', purchase_views.update_purchase_stock, name='update_purchase_stock'),
    path('purchases/<int:pk>/delete/', purchase_views.delete_purchase, name='delete_purchase'),
    
    # Purchase Returns
    path('purchase-returns/', purchase_views.purchase_return_list, name='purchase_return_list'),
    path('purchase-returns/create/', purchase_views.create_purchase_return, name='create_purchase_return'),
    path('purchase-returns/<int:pk>/', purchase_views.purchase_return_detail, name='purchase_return_detail'),
    path('purchase-returns/<int:pk>/edit/', purchase_views.edit_purchase_return, name='edit_purchase_return'),
    path('purchase-returns/<int:pk>/print/', purchase_views.print_purchase_return_pdf, name='print_purchase_return_pdf'),
    path('purchase-returns/<int:pk>/approve/', purchase_views.approve_purchase_return, name='approve_purchase_return'),
    path('purchase-returns/<int:pk>/record-company-approval/', purchase_views.record_company_approval, name='record_company_approval'),
    path('purchase-returns/<int:pk>/mark-sent/', purchase_views.mark_return_sent, name='mark_return_sent'),
    path('purchase-returns/<int:pk>/update-settlement/', purchase_views.update_return_settlement, name='update_return_settlement'),
    
    # Company Accounts
    path('company-accounts/', company_account_views.company_account_list, name='company_account_list'),
    path('company-accounts/<int:pk>/', company_account_views.company_account_detail, name='company_account_detail'),
    path('company-accounts/<int:pk>/export/', company_account_views.export_company_ledger, name='export_company_ledger'),
    path('company-accounts/opening-balance/create/', company_account_views.create_opening_balance, name='create_opening_balance'),
    path('company-accounts/payment/record/', company_account_views.record_company_payment, name='record_company_payment'),
    path('company-accounts/settlement/grn-vs-return/', company_account_views.settle_grn_with_return, name='settle_grn_with_return'),
    
    # Company Payments
    path('payments/', company_account_views.payment_list, name='payment_list'),
    path('payments/<int:pk>/', company_account_views.payment_detail, name='payment_detail'),
    path('api/company/<int:company_id>/outstanding-grns/', company_account_views.get_company_outstanding_grns, name='get_company_outstanding_grns'),
    
    # Activate from Global Catalog
    path('catalog/', views.activate_catalog, name='activate_catalog'),
    path('catalog/activate/<int:global_pk>/', views.activate_product, name='activate_product'),
    path('catalog/bulk-activate/', views.bulk_activate_products, name='bulk_activate_products'),
]
