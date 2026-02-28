from sales.models import Bill, CommissionTransaction
from payments.models import SalesAccountSettlement
from django.utils import timezone

print("=" * 80)
print("CREATING MISSING COMMISSION FOR SETTLEMENT #151")
print("=" * 80)

# Get Settlement #151
settlement = SalesAccountSettlement.objects.get(id=151)
print(f"\nSettlement Details:")
print(f"  ID: {settlement.id}")
print(f"  Number: {settlement.settlement_number}")
print(f"  Bill: {settlement.bill.bill_number}")
print(f"  Method: {settlement.settlement_method}")
print(f"  Amount: Rs. {settlement.amount}")
print(f"  Status: {settlement.settlement_status}")
print(f"  Date: {settlement.settlement_date}")

# Check if bill_created commission exists
bill_commission = CommissionTransaction.objects.filter(
    bill=settlement.bill,
    transaction_type='bill_created'
).first()

if not bill_commission:
    print(f"\n⚠️  Bill {settlement.bill.bill_number} has NO bill_created commission!")
    print(f"  Creating bill_created commission first...")
    
    bill_comm = CommissionTransaction.objects.create(
        transaction_type='bill_created',
        transaction_date=settlement.bill.created_at,
        sales_rep=settlement.bill.sales_rep,
        bill=settlement.bill,
        sales_amount=settlement.bill.total_amount,
        notes=f"Bill {settlement.bill.bill_number} created - Commission tracking (retroactive)"
    )
    print(f"  ✅ Created bill_created commission (ID: {bill_comm.id})")
    print(f"     Commission: Rs. {bill_comm.commission_earned}")
else:
    print(f"\n✅ Bill {settlement.bill.bill_number} already has bill_created commission (ID: {bill_commission.id})")

# Check if payment_received commission exists
payment_commission = CommissionTransaction.objects.filter(
    settlement=settlement,
    transaction_type='payment_received'
).first()

if payment_commission:
    print(f"\n✅ Settlement #{settlement.id} already has payment_received commission (ID: {payment_commission.id})")
else:
    print(f"\n⚠️  Settlement #{settlement.id} is missing payment_received commission")
    print(f"  Creating commission transaction...")
    
    # Create payment_received commission
    comm = CommissionTransaction.objects.create(
        transaction_type='payment_received',
        transaction_date=settlement.settlement_date,
        sales_rep=settlement.bill.sales_rep,
        bill=settlement.bill,
        settlement=settlement,
        collected_amount=settlement.amount,
        notes=f"Payment received via {settlement.settlement_method} - Settlement {settlement.settlement_number} (retroactive)"
    )
    
    print(f"  ✅ Created payment_received commission (ID: {comm.id})")
    print(f"     Sales Rep: {comm.sales_rep.get_full_name()}")
    print(f"     Collected: Rs. {comm.collected_amount}")
    print(f"     Commission Rate: {comm.applicable_rate}%")
    print(f"     Commission Earned: Rs. {comm.commission_earned}")
    print(f"     Running Balance: Rs. {comm.running_balance}")

print("\n" + "=" * 80)
print("VERIFICATION")
print("=" * 80)

all_comms = CommissionTransaction.objects.filter(bill=settlement.bill).order_by('transaction_date')
print(f"\nTotal commission transactions for Bill {settlement.bill.bill_number}: {all_comms.count()}")
for c in all_comms:
    print(f"  - {c.transaction_type}: Rs. {c.commission_earned} (ID: {c.id})")

print("\n" + "=" * 80)
print("DONE")
print("=" * 80)
