"""
Demonstration of Corrected Money Account System
Shows how advances work as early payments, not loans
"""

print("\n" + "="*80)
print("CORRECTED MONEY ACCOUNT SYSTEM - YOU ARE THE MONEY HOLDER")
print("="*80 + "\n")

balance = 0
print(f"Starting Balance: Rs. {balance:,.2f}")
print("(Positive = You owe user | Negative = Should not happen with validation)\n")

print("-" * 80)
print("STEP 1: User earns commission from sales")
print("-" * 80)
commission = 10000
balance += commission
print(f"+ Commission credited: Rs. {commission:,.2f}")
print(f"→ Balance: Rs. {balance:,.2f} (You owe user)")
print()

print("-" * 80)
print("STEP 2: User requests and receives advance (EARLY PAYMENT)")
print("-" * 80)
advance = 3000
print(f"User takes advance: Rs. {advance:,.2f}")
print(f"  - This is EARLY PAYMENT from their future commissions")
print(f"  - You give them cash/bank transfer NOW")
balance -= advance
print(f"→ Balance: Rs. {balance:,.2f} (You still owe user)")
print(f"  Total advances taken: Rs. {advance:,.2f} (just for reporting)")
print()

print("-" * 80)
print("STEP 3: User earns more commission")
print("-" * 80)
commission2 = 5000
balance += commission2
print(f"+ Commission credited: Rs. {commission2:,.2f}")
print(f"→ Balance: Rs. {balance:,.2f} (You owe user)")
print()

print("-" * 80)
print("STEP 4: Make final payment")
print("-" * 80)
payment = balance
balance -= payment
print(f"- Pay user: Rs. {payment:,.2f}")
print(f"→ Balance: Rs. {balance:,.2f} (All settled!)")
print()

print("="*80)
print("KEY POINTS:")
print("="*80)
print("✅ Advances are EARLY PAYMENTS, not loans")
print("✅ When advance is given, balance DECREASES immediately")
print("✅ NO recovery step needed - already deducted")
print("✅ 'Total Advances Taken' is just for reporting")
print("✅ Balance always shows: Money you still owe them")
print("="*80 + "\n")

print("VALIDATION RULES:")
print("-" * 80)
print("1. Cannot take advance > current balance (no negative balance allowed)")
print("2. Can set max advance limit (e.g., 50% of balance)")
print("3. Can limit advance frequency (e.g., once per month)")
print("="*80 + "\n")
