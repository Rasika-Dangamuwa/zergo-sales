from django.contrib import admin
from .models import OldPayment, CreditNote, PaymentReconciliation


# OldPayment admin is hidden - data preserved for historical records
# The system now uses the Payment model in the sales app
# @admin.register(OldPayment)
# class OldPaymentAdmin(admin.ModelAdmin):
#     list_display = ['payment_number', 'shop', 'payment_date', 'payment_method', 'amount', 'status', 'received_by']
#     list_filter = ['payment_method', 'status', 'payment_date']
#     search_fields = ['payment_number', 'shop__shop_name', 'reference_number']
#     readonly_fields = ['created_at', 'updated_at', 'verified_at']
#     
#     fieldsets = (
#         ('Payment Information', {
#             'fields': ('payment_number', 'payment_date', 'shop', 'bill')
#         }),
#         ('Payment Details', {
#             'fields': ('payment_method', 'amount', 'reference_number', 'bank_name', 'cheque_date')
#         }),
#         ('Status & Verification', {
#             'fields': ('status', 'received_by', 'verified_by', 'verified_at')
#         }),
#         ('Additional Info', {
#             'fields': ('notes', 'attachment')
#         }),
#         ('Timestamps', {
#             'fields': ('created_at', 'updated_at')
#         }),
#     )


@admin.register(CreditNote)
class CreditNoteAdmin(admin.ModelAdmin):
    list_display = ['credit_note_number', 'shop', 'credit_note_date', 'amount', 'is_applied']
    list_filter = ['is_applied', 'credit_note_date']
    search_fields = ['credit_note_number', 'shop__shop_name']


@admin.register(PaymentReconciliation)
class PaymentReconciliationAdmin(admin.ModelAdmin):
    list_display = ['shop', 'reconciliation_date', 'opening_balance', 'closing_balance', 'reconciled_by']
    list_filter = ['reconciliation_date']
    search_fields = ['shop__shop_name']
