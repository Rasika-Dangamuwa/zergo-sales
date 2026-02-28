"""
Deep Investigation: Cash Refund Impact on Company Receivable Balance
Analyzing the current system behavior vs. expected behavior
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import CompanyAccount, CompanyTransaction, PurchaseReturn, PurchaseReturnSettlement
from decimal import Decimal

print("=" * 100)
print("CASH REFUND IMPACT ON COMPANY BALANCE - DEEP INVESTIGATION")
print("=" * 100)

# Get company account
account = CompanyAccount.objects.first()
if not account:
    print("No company account found")
    exit()

print(f"\nCompany: {account.company.company_name}")
print(f"Current Balance: Rs. {account.current_balance:,.2f}")
print(f"  (Positive = We owe them, Negative = They owe us)")

# Get all return transactions
print("\n" + "=" * 100)
print("RETURN TRANSACTIONS ANALYSIS")
print("=" * 100)

return_txns = CompanyTransaction.objects.filter(
    company_account=account,
    transaction_type='return'
).order_by('transaction_date')

for txn in return_txns:
    print(f"\n{txn.reference_number}:")
    print(f"  Date: {txn.transaction_date.strftime('%Y-%m-%d')}")
    print(f"  Amount in DB: {txn.amount:+,.2f}")
    print(f"  Settlement Method: {txn.get_settlement_method_display()}")
    
    # Get the return object
    if txn.purchase_return:
        pr = txn.purchase_return
        print(f"  Return Total: Rs. {pr.total_amount:,.2f}")
        print(f"  Settlement Status: {pr.settlement_status}")
        
        # Get settlements
        settlements = pr.settlements.all()
        if settlements.exists():
            print(f"  Settlements:")
            for s in settlements:
                print(f"    • {s.get_settlement_method_display()}: Rs. {s.settlement_amount:,.2f}")
                if s.settlement_method == 'refund':
                    print(f"      Cash Received: {s.cash_received_date or 'Not recorded'}")
                    print(f"      Receipt: {s.cash_receipt_number or 'N/A'}")

# Now let's trace the balance calculation step by step
print("\n" + "=" * 100)
print("BALANCE CALCULATION STEP-BY-STEP")
print("=" * 100)

all_txns = account.transactions.all().order_by('transaction_date', 'id')

balance = account.opening_balance
print(f"\nOpening Balance: Rs. {balance:,.2f}")
print("\nTransaction Flow:")
print("-" * 100)

for txn in all_txns:
    old_balance = balance
    
    # This is the actual logic from update_balance()
    if txn.transaction_type in ['opening_balance', 'purchase', 'debit']:
        balance += txn.amount
        operation = f"+{txn.amount:,.2f}"
    elif txn.transaction_type in ['return', 'payment', 'credit']:
        balance -= txn.amount
        operation = f"-({txn.amount:+,.2f})"
    else:
        operation = "No change"
    
    print(f"{txn.transaction_date.strftime('%Y-%m-%d')} | {txn.transaction_type:10} | {txn.reference_number:20} | ", end="")
    print(f"{operation:20} | Balance: {old_balance:+,.2f} → {balance:+,.2f}")

print("-" * 100)
print(f"Final Calculated Balance: Rs. {balance:,.2f}")
print(f"Stored Balance: Rs. {account.current_balance:,.2f}")
print(f"Match: {'✅' if balance == account.current_balance else '❌'}")

# CRITICAL ANALYSIS
print("\n" + "=" * 100)
print("🔍 CRITICAL ISSUE ANALYSIS")
print("=" * 100)

print("\n📋 Current System Behavior:")
print("-" * 100)
print("When return is APPROVED:")
print("  1. CompanyTransaction created: type='return', amount=-10000 (NEGATIVE)")
print("  2. Balance calculation: balance -= amount")
print("  3. Result: balance -= (-10000) = balance + 10000")
print("  4. Effect: INCREASES balance (we owe MORE?)")
print()
print("When cash refund is RECORDED:")
print("  1. PurchaseReturnSettlement created (settlement_method='refund')")
print("  2. NO CompanyTransaction created")
print("  3. Balance: NO CHANGE")

print("\n❓ THE PROBLEM:")
print("-" * 100)
print("If amount is stored as NEGATIVE (-10000) and we do:")
print("  balance -= (-10000)")
print("This INCREASES the balance!")
print()
print("Example:")
print("  Before return: We owe Rs. 100,000 (balance = +100,000)")
print("  Return Rs. 10,000: balance -= (-10000) = +100,000 + 10,000 = +110,000")
print("  Result: ❌ Now we owe MORE? That's WRONG!")

print("\n✅ EXPECTED BEHAVIOR:")
print("-" * 100)
print("Scenario: We owe supplier Rs. 100,000")
print()
print("Step 1: Return Rs. 10,000 goods (approved)")
print("  Expected: Balance = Rs. 90,000 (we owe less)")
print("  OR: Receivable = Rs. 10,000 (they owe us)")
print()
print("Step 2: Supplier gives cash refund Rs. 10,000")
print("  Expected: Receivable = Rs. 0 (settled)")
print("  OR: Balance = Rs. 90,000 (stays same, cash received separately)")

print("\n" + "=" * 100)
print("🔬 TESTING ACTUAL BEHAVIOR")
print("=" * 100)

# Create a test scenario
print("\nSimulation:")
print("  Starting balance: Rs. 50,000 (we owe them)")
print("  Return: Rs. 5,000")
print("  Return transaction amount: -5,000")
print()
test_balance = Decimal('50000')
return_amount = Decimal('-5000')

print(f"Calculation: {test_balance} -= ({return_amount})")
test_balance -= return_amount
print(f"Result: Rs. {test_balance:,.2f}")
print()
if test_balance == Decimal('55000'):
    print("❌ WRONG! Balance INCREASED to Rs. 55,000")
    print("   (We now owe MORE after returning goods?!)")
elif test_balance == Decimal('45000'):
    print("✅ CORRECT! Balance DECREASED to Rs. 45,000")
    print("   (We now owe LESS after returning goods)")

print("\n" + "=" * 100)
print("RECOMMENDATION")
print("=" * 100)
print("""
The issue is in how return transaction amounts are stored/calculated.

Option 1: Store return amounts as POSITIVE, negate in calculation
  - Store: amount = +10000
  - Calculate: balance -= amount (balance reduced by 10000)

Option 2: Fix the calculation logic
  - Store: amount = -10000 (current)
  - Calculate: balance += amount (balance + (-10000) = balance - 10000)

Option 3: Create separate transaction when cash refund is given
  - Return approval: Creates receivable/credit
  - Cash refund: Creates settlement transaction that clears the receivable
""")

print("\n🔍 Let me check actual data...")
print("=" * 100)

# Check if any returns actually exist and their impact
if return_txns.exists():
    first_return = return_txns.first()
    print(f"\nActual Return Transaction:")
    print(f"  Amount stored: {first_return.amount}")
    print(f"  Is negative?: {first_return.amount < 0}")
    
    # Find transactions before and after this return
    before = CompanyTransaction.objects.filter(
        company_account=account,
        transaction_date__lt=first_return.transaction_date
    ).order_by('-transaction_date').first()
    
    after = CompanyTransaction.objects.filter(
        company_account=account,
        transaction_date__gt=first_return.transaction_date
    ).order_by('transaction_date').first()
    
    if before:
        print(f"\n  Balance before return: Check company account page")
    if after:
        print(f"  Balance after return: Check company account page")
else:
    print("\nNo return transactions found to analyze actual behavior")

print("\n" + "=" * 100)
