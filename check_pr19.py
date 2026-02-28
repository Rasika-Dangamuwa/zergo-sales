import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import PurchaseReturn

pr = PurchaseReturn.objects.get(pk=19)
print(f"\n=== PR #{pr.pk} ({pr.pr_number}) ===")
print(f"Total Amount: Rs. {pr.total_amount:,.2f}")
print(f"Approved Amount: Rs. {pr.approved_amount:,.2f}" if pr.approved_amount else "Approved Amount: None/0")
print(f"Total Settled Amount: Rs. {pr.total_settled_amount:,.2f}")
print(f"Settlement Percentage: {pr.settlement_percentage}%")
print(f"\nCalculation:")
target = pr.approved_amount if pr.approved_amount and pr.approved_amount > 0 else pr.total_amount
print(f"Target Amount (approved or total): Rs. {target:,.2f}")
print(f"Formula: ({pr.total_settled_amount:,.2f} / {target:,.2f}) * 100 = {(pr.total_settled_amount / target) * 100:.2f}%")

print(f"\nSettlement Records:")
for s in pr.settlements.all():
    print(f"  - {s.get_settlement_method_display()}: Rs. {s.settlement_amount:,.2f}")
