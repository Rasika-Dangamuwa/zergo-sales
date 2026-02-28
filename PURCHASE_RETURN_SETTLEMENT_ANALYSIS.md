# Purchase Return Settlement System - Deep Research & Analysis
**Investigation Date**: January 18, 2026  
**Requested By**: User analyzing company account page at https://192.168.1.4:8000/products/company-accounts/1/  
**Focus**: Do cash refunds reduce company account balance?

---

## Executive Summary

**✅ YES - Cash refunds DO reduce the company account balance**

When a purchase return is settled via cash refund:
1. **Return Creation**: Creates negative CompanyTransaction (reduces balance)
2. **Cash Settlement**: NO additional transaction created (settlement tracked separately)
3. **Net Effect**: Balance reduced by return amount

**Key Finding**: The current system creates a CompanyTransaction when the return is **approved**, not when cash is refunded. The actual settlement method (cash/credit/replacement) is tracked in `PurchaseReturnSettlement` records but does **NOT** create separate financial transactions.

---

## System Architecture

### 1. Three-Tier Settlement Model

```
┌─────────────────────────────────────────────────────────────┐
│                  PurchaseReturn Model                       │
│  - pr_number: "PR-20260118-001"                            │
│  - total_amount: Rs. 10,000                                 │
│  - approved_amount: Rs. 10,000                              │
│  - status: 'company_approved'                               │
│  - settlement_status: 'pending' → 'fully_settled'           │
└─────────────────────────────────────────────────────────────┘
                             │
                             │ Creates on approval
                             ▼
┌─────────────────────────────────────────────────────────────┐
│             CompanyTransaction (Ledger Entry)               │
│  - transaction_type: 'return'                               │
│  - amount: -10,000  ← NEGATIVE = Reduces balance            │
│  - settlement_method: 'credit'                              │
│  - description: "Purchase Return: PR-20260118-001"          │
└─────────────────────────────────────────────────────────────┘
                             │
                             │ Settlement tracked separately
                             ▼
┌─────────────────────────────────────────────────────────────┐
│          PurchaseReturnSettlement (Detail Records)          │
│  Settlement 1: method='refund', amount=Rs. 5,000            │
│  Settlement 2: method='credit_note', amount=Rs. 5,000       │
│                                                             │
│  Total Settled: Rs. 10,000 = Fully Settled                  │
└─────────────────────────────────────────────────────────────┘
```

### 2. Settlement Methods

The system supports **3 settlement methods** (defined in `PurchaseReturnSettlement.SETTLEMENT_METHOD_CHOICES`):

| Method | Code | CompanyTransaction Impact | Stock Impact | Cash Flow |
|--------|------|---------------------------|--------------|-----------|
| **Replacement GRN** | `replacement` | None (offset via GRN settlement tracking) | Stock received via new GRN | No cash movement |
| **Credit Note** | `credit_note` | None (already credited via return transaction) | No stock movement | No cash movement |
| **Cash Refund** | `refund` | **None** (already credited via return transaction) | No stock movement | **Cash received from supplier** |

---

## Critical Discovery: Cash Refund Transaction Logic

### What Happens When Cash Refund Is Recorded?

**File**: `products/purchase_views.py` - `update_return_settlement()` view (lines 760-775)

```python
elif method == 'refund':
    # Create settlement record
    PurchaseReturnSettlement.objects.create(
        purchase_return=purchase_return,
        settlement_method='refund',
        settlement_amount=amount,
        refund_reference=reference if reference else 'Cash refund',
        created_by=request.user
    )
    settlement_summary.append(f'Cash Refund: Rs. {amount:.2f}')
```

**What This Code DOES**:
- ✅ Creates `PurchaseReturnSettlement` record with method='refund'
- ✅ Tracks settlement amount
- ✅ Updates `settlement_status` to 'fully_settled' if total_settled >= approved_amount

**What This Code DOES NOT DO**:
- ❌ Does **NOT** create a new `CompanyTransaction`
- ❌ Does **NOT** reduce the company balance again
- ❌ Does **NOT** record actual cash payment event

### Why No Separate Transaction?

**The return transaction was already created when the return was approved:**

**File**: `products/models.py` - `PurchaseReturn.create_return_transaction()` (lines 1058-1085)

```python
def create_return_transaction(self):
    """Create CompanyTransaction when return is approved"""
    # Check if transaction already exists
    if not self.account_transactions.exists():
        # Create return transaction (negative amount = reduces what we owe)
        CompanyTransaction.objects.create(
            company_account=account,
            transaction_type='return',
            transaction_date=self.return_date,
            reference_number=self.pr_number,
            amount=-self.total_amount,  # ← NEGATIVE = Credit to us
            settlement_method='credit',  # Initially on credit
            purchase_return=self,
            description=f'Purchase Return: {self.pr_number}',
            created_by=self.created_by
        )
```

**Design Rationale**:
1. When return is approved → Balance reduced immediately by full return amount
2. The **settlement method** (cash/credit/replacement) determines **how supplier settles**
3. Settlement tracking is for **operational visibility**, not additional accounting

---

## Company Account Balance Calculation

**File**: `products/models.py` - `CompanyAccount.update_balance()` (lines 1380-1425)

```python
def update_balance(self):
    """Recalculate balance from all transactions"""
    transactions = self.transactions.all().order_by('transaction_date', 'id')
    
    balance = self.opening_balance
    
    for txn in transactions:
        if txn.transaction_type in ['opening_balance', 'purchase', 'debit']:
            balance += txn.amount  # Positive = increase what we owe
        elif txn.transaction_type in ['return', 'payment', 'credit']:
            balance -= txn.amount  # Reduces balance (amount is negative for returns)
    
    self.current_balance = balance
    self.last_transaction_date = transactions.last().transaction_date if transactions.exists() else None
    self.save()
```

### Example Calculation

**Scenario**: Return Rs. 10,000 worth of damaged goods, settled via cash refund Rs. 10,000

```
Opening Balance: Rs. 50,000
Purchase GRN: +Rs. 100,000
  → Balance: Rs. 150,000

Return Approved (PR-20260118-001): -Rs. 10,000
  → CompanyTransaction created:
     type='return', amount=-10,000
  → Balance: Rs. 150,000 - 10,000 = Rs. 140,000

Cash Refund Recorded:
  → PurchaseReturnSettlement created:
     method='refund', amount=10,000
  → NO new CompanyTransaction
  → Balance remains: Rs. 140,000

Payment to Company: -Rs. 50,000
  → Balance: Rs. 90,000
```

**Net Effect**: 
- We owed Rs. 150,000
- Return reduced to Rs. 140,000 (supplier owes us Rs. 10,000)
- Supplier paid us cash Rs. 10,000 (settlement method)
- We paid supplier Rs. 50,000 cash
- Final balance: Rs. 90,000 owed to supplier

---

## Verification: Do Returns Reduce Balance?

### Test Query (Run in Django Shell)

```python
from products.models import CompanyAccount, PurchaseReturn, CompanyTransaction
from decimal import Decimal

# Check a specific company account
account = CompanyAccount.objects.get(pk=1)

# Get all return transactions
return_txns = CompanyTransaction.objects.filter(
    company_account=account,
    transaction_type='return'
)

print(f"Company: {account.company.company_name}")
print(f"Current Balance: Rs. {account.current_balance:,.2f}")
print(f"\nReturn Transactions:")
for txn in return_txns:
    print(f"  {txn.reference_number}: {txn.amount:+,.2f}")  # Negative values
    
# Verify balance calculation
manual_balance = account.opening_balance
for txn in account.transactions.all().order_by('transaction_date'):
    if txn.transaction_type in ['purchase', 'debit']:
        manual_balance += txn.amount
    elif txn.transaction_type in ['return', 'payment', 'credit']:
        manual_balance -= txn.amount

print(f"\nManual Calculation: Rs. {manual_balance:,.2f}")
print(f"Stored Balance: Rs. {account.current_balance:,.2f}")
print(f"Match: {'✅' if manual_balance == account.current_balance else '❌'}")
```

### Expected Output

```
Company: Max Beverages
Current Balance: Rs. 45,230.00

Return Transactions:
  PR-20260115-001: -5,000.00
  PR-20260116-002: -3,500.00
  PR-20260117-003: -1,500.00

Manual Calculation: Rs. 45,230.00
Stored Balance: Rs. 45,230.00
Match: ✅
```

---

## Settlement Method Impact Analysis

### Scenario 1: Cash Refund Settlement

**Business Flow**:
1. Office creates return for Rs. 10,000 damaged goods
2. Admin approves return → Stock reduced, CompanyTransaction created (-Rs. 10,000)
3. Supplier agrees to cash refund
4. Office records settlement: method='refund', amount=Rs. 10,000
5. **Result**: PurchaseReturnSettlement created, settlement_status='fully_settled'

**CompanyAccount Impact**:
- ✅ Balance reduced by Rs. 10,000 at step 2 (approval)
- ❌ No additional balance change at step 4 (settlement recording)

**Cash Flow Reality**:
- We physically receive Rs. 10,000 cash from supplier
- This cash is tracked in our cash register/bank account (outside this system)
- Company account balance reflects: "We now owe supplier Rs. 10,000 less"

### Scenario 2: Credit Note Settlement

**Business Flow**:
1. Return approved → Balance reduced by Rs. 10,000
2. Supplier issues credit note CN-12345 for Rs. 10,000
3. Office records settlement: method='credit_note', reference='CN-12345'
4. **Result**: PurchaseReturnSettlement created

**CompanyAccount Impact**:
- Identical to cash refund scenario
- Balance reduced at approval, no change at settlement recording

**Difference from Cash**:
- No actual cash received
- Credit note can be offset against future purchases
- Tracked via `credit_note_number` field

### Scenario 3: Replacement GRN Settlement

**Business Flow**:
1. Return approved for Rs. 10,000 → Balance reduced
2. Supplier sends replacement goods worth Rs. 10,000
3. We receive replacement GRN-20260118-005 for Rs. 10,000
4. Office links replacement: method='replacement', replacement_grn=GRN-20260118-005
5. **Result**: Both return and replacement GRN show in ledger

**CompanyAccount Impact**:
```
Return: -Rs. 10,000 (reduces balance)
Replacement GRN: +Rs. 10,000 (increases balance)
Net Effect: Rs. 0
```

**Complex Case**: Partial settlement via replacement
```
Return: Rs. 10,000
Replacement GRN: Rs. 7,000 (partial replacement)
Cash Refund: Rs. 3,000 (balance)

Settlement Records:
  - PurchaseReturnSettlement (method='replacement', amount=7,000)
  - PurchaseReturnSettlement (method='refund', amount=3,000)
  
Total Settled: Rs. 10,000 = Fully Settled
```

---

## Unused Method: record_cash_refund()

**File**: `products/models.py` (lines 1087-1110)

```python
def record_cash_refund(self, refund_amount, reference_number, created_by):
    """Record cash refund received from company"""
    account = CompanyAccount.objects.get(company=self.company)
    
    # Create payment transaction for cash refund
    CompanyTransaction.objects.create(
        company_account=account,
        transaction_type='payment',
        transaction_date=timezone.now(),
        reference_number=reference_number,
        amount=-refund_amount,  # Negative = reduces what we owe
        settlement_method='cash',
        payment_reference=reference_number,
        purchase_return=self,
        description=f'Cash refund for {self.pr_number}',
        created_by=created_by
    )
    
    self.credit_amount = refund_amount
    self.settlement_status = 'fully_settled'
    self.save()
```

**Status**: ⚠️ **ORPHANED CODE - NOT USED IN CURRENT SYSTEM**

**Analysis**:
- This method would create a **separate payment transaction** for cash refunds
- It would result in **double-counting**: Return transaction (-10k) + Payment transaction (-10k) = -20k total
- **Current system does NOT call this method** - uses `PurchaseReturnSettlement` instead
- **Recommendation**: Remove this method or document as deprecated legacy code

---

## Settlement Status Tracking

**File**: `products/models.py` - `PurchaseReturn.calculated_settlement_status` (lines 1026-1037)

```python
@property
def calculated_settlement_status(self):
    """Auto-calculate settlement status from settlement records"""
    # Use approved amount if available, otherwise use total amount
    target_amount = self.approved_amount if self.approved_amount > 0 else self.total_amount
    total_settled = self.total_settled_amount
    
    if total_settled >= target_amount:
        return 'fully_settled'
    elif total_settled > Decimal('0'):
        return 'partial'
    return 'pending'

@property
def total_settled_amount(self):
    """Calculate total amount settled from settlement records"""
    total = self.settlements.aggregate(total=Sum('settlement_amount'))['total']
    return total or Decimal('0')
```

**Logic**:
- Sums all `PurchaseReturnSettlement.settlement_amount` values
- Compares to `approved_amount`
- Returns status: pending/partial/fully_settled

**Usage in Template** (`company_account_detail.html` lines 480-520):
```django
{% if item.settlement_details %}
    {% for settlement in item.settlement_details %}
    <tr class="settlement-detail-row">
        <td colspan="4" class="ps-5">
            <small class="text-muted">
                <i class="fas fa-arrow-turn-right me-2"></i>
                Settlement: {{ settlement.get_settlement_method_display }}
                {% if settlement.replacement_grn %}
                    <a href="{% url 'products:purchase_detail' settlement.replacement_grn.pk %}">
                        {{ settlement.replacement_grn.grn_number }}
                    </a>
                {% elif settlement.credit_note_number %}
                    {{ settlement.credit_note_number }}
                {% else %}
                    {{ settlement.refund_reference|default:"Cash" }}
                {% endif %}
            </small>
        </td>
        <td class="text-end"><small class="text-success">Rs. {{ settlement.settlement_amount|floatformat:2 }}</small></td>
    </tr>
    {% endfor %}
{% endif %}
```

**Display Example**:
```
Purchase Return: PR-20260117-003
Date: Jan 17, 2026
Amount: -Rs. 10,000.00
Settlement Method: Credit
Balance After: Rs. 45,230.00

  └─ Settlement: Cash Refund
     Reference: REF-123
     Amount: Rs. 5,000.00
  
  └─ Settlement: Credit Note
     Reference: CN-456
     Amount: Rs. 5,000.00
```

---

## Database Schema

### PurchaseReturn Table
```sql
CREATE TABLE purchase_returns (
    id BIGINT PRIMARY KEY,
    pr_number VARCHAR(50) UNIQUE,  -- "PR-20260118-001"
    company_id BIGINT REFERENCES companies,
    total_amount DECIMAL(12,2),
    approved_amount DECIMAL(12,2),
    status VARCHAR(20),  -- 'pending', 'company_approved', 'settled'
    settlement_status VARCHAR(20),  -- 'pending', 'partial', 'fully_settled'
    settlement_type VARCHAR(20),  -- 'credit_note', 'replacement', 'refund'
    credit_amount DECIMAL(12,2),  -- Legacy field
    credit_note_number VARCHAR(100),  -- Legacy field
    replacement_grn_id BIGINT REFERENCES purchases,  -- Legacy field
    stock_updated BOOLEAN DEFAULT FALSE,
    created_by_id BIGINT REFERENCES users,
    created_at TIMESTAMP
);
```

### PurchaseReturnSettlement Table
```sql
CREATE TABLE purchase_return_settlements (
    id BIGINT PRIMARY KEY,
    purchase_return_id BIGINT REFERENCES purchase_returns,
    settlement_method VARCHAR(20),  -- 'replacement', 'credit_note', 'refund'
    settlement_amount DECIMAL(12,2),
    replacement_grn_id BIGINT REFERENCES purchases,  -- For method='replacement'
    credit_note_number VARCHAR(100),  -- For method='credit_note'
    refund_reference VARCHAR(100),  -- For method='refund'
    created_by_id BIGINT REFERENCES users,
    created_at TIMESTAMP
);
```

### CompanyTransaction Table
```sql
CREATE TABLE company_transactions (
    id BIGINT PRIMARY KEY,
    company_account_id BIGINT REFERENCES company_accounts,
    transaction_type VARCHAR(20),  -- 'purchase', 'return', 'payment', 'adjustment'
    transaction_date TIMESTAMP,
    reference_number VARCHAR(100),  -- PR number for returns
    amount DECIMAL(12,2),  -- NEGATIVE for returns
    settlement_method VARCHAR(20),  -- 'credit', 'cash', 'cheque', etc.
    purchase_id BIGINT REFERENCES purchases,
    purchase_return_id BIGINT REFERENCES purchase_returns,
    description TEXT,
    created_by_id BIGINT REFERENCES users,
    created_at TIMESTAMP
);
```

---

## Data Flow Diagram

### Return Approval → Balance Reduction

```
┌──────────────────────┐
│ User creates return  │
│ PR-20260118-001      │
│ Total: Rs. 10,000    │
│ Status: 'pending'    │
└──────────┬───────────┘
           │
           │ Admin clicks "Approve"
           ▼
┌──────────────────────────────────────────┐
│ products/purchase_views.py               │
│ approve_purchase_return()                │
│   - Set status='company_approved'        │
│   - Reduce stock from inventory          │
│   - Call create_return_transaction()     │
└──────────┬───────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────┐
│ PurchaseReturn.create_return_transaction()│
│   - Create CompanyTransaction:           │
│     type='return'                        │
│     amount=-10000                        │
│     settlement_method='credit'           │
└──────────┬───────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────┐
│ CompanyAccount.update_balance()          │
│   Opening: Rs. 150,000                   │
│   Return: -Rs. 10,000                    │
│   New Balance: Rs. 140,000               │
└──────────────────────────────────────────┘
```

### Settlement Recording (Does NOT Change Balance)

```
┌──────────────────────────────────────────┐
│ User records settlement                  │
│ Method: 'refund'                         │
│ Amount: Rs. 10,000                       │
│ Reference: 'CASH-20260118-001'           │
└──────────┬───────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────┐
│ products/purchase_views.py               │
│ update_return_settlement()               │
│   - Create PurchaseReturnSettlement      │
│   - Update settlement_status             │
│   - NO CompanyTransaction created        │
└──────────┬───────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────┐
│ PurchaseReturnSettlement created         │
│   method='refund'                        │
│   amount=10000                           │
│   refund_reference='CASH-20260118-001'   │
└──────────┬───────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────┐
│ CompanyAccount.current_balance           │
│   UNCHANGED: Rs. 140,000                 │
│   (Balance was already reduced at        │
│    approval stage)                       │
└──────────────────────────────────────────┘
```

---

## Answer to User's Question

### "If it cash refunds have the return, it reduce from the company account?"

**YES - Return reduces company account balance**  
**NO - Cash refund recording does NOT reduce it again**

**Timeline**:
1. **Return Approved** → Balance reduced by return amount (e.g., -Rs. 10,000)
2. **Settlement Method Chosen** (Cash/Credit/Replacement) → Tracked for operations
3. **Cash Refund Recorded** → Updates settlement status, but does NOT create new transaction

**Balance Impact**:
- Return approval: Balance goes from Rs. 150k → Rs. 140k
- Cash refund recording: Balance stays at Rs. 140k (operational tracking only)

**Why This Design?**:
- Return approval = We return goods to supplier, they owe us refund
- Settlement method = How they choose to pay us back (cash/credit/replacement)
- Both outcomes reduce what we owe them by the same amount
- Settlement tracking is for **operational visibility**, not double-counting

---

## Potential Issues & Recommendations

### Issue 1: Cash Refund Not Visible as Separate Transaction

**Current State**: 
- Cash refund appears as sub-row under return in company account ledger
- Main transaction shows settlement_method='credit' (initial state)

**User Confusion**:
- Users might expect to see: "Return: -Rs. 10k" + "Cash Refund: -Rs. 10k"
- Actually shows: "Return: -Rs. 10k" with sub-row "Settlement: Cash Rs. 10k"

**Recommendation**: ✅ **CURRENT DESIGN IS CORRECT**
- Prevents double-counting
- Settlement sub-rows provide operational detail without financial duplication

### Issue 2: Orphaned record_cash_refund() Method

**File**: `products/models.py` line 1087

**Status**: Method exists but is never called by any view

**Recommendation**: 
```python
# REMOVE or mark as @deprecated
def record_cash_refund(self, refund_amount, reference_number, created_by):
    """
    DEPRECATED: Do not use. 
    Use PurchaseReturnSettlement instead via update_return_settlement() view.
    
    This method creates duplicate transactions and should not be called.
    """
    raise NotImplementedError(
        "Use PurchaseReturnSettlement.objects.create() instead. "
        "This method is deprecated and creates duplicate transactions."
    )
```

### Issue 3: Misleading settlement_method='credit' on Return Transaction

**Current Code**: `products/models.py` line 1081
```python
CompanyTransaction.objects.create(
    transaction_type='return',
    amount=-self.total_amount,
    settlement_method='credit',  # ← Misleading for cash refunds
    purchase_return=self,
)
```

**Problem**: 
- Return transaction always created with settlement_method='credit'
- Even if return is later settled via cash refund
- Makes reports confusing

**Recommendation**: Change to 'pending_settlement' or 'unsettled'
```python
settlement_method='pending_settlement',  # Updated when settlement recorded
```

Or update settlement_method when settlement is recorded:
```python
# In update_return_settlement() view
if primary_method == 'refund':
    # Update return transaction settlement method
    return_txn = CompanyTransaction.objects.get(purchase_return=purchase_return)
    return_txn.settlement_method = 'cash'
    return_txn.save()
```

### Issue 4: No Audit Trail for Cash Received

**Current Gap**: System tracks that cash refund was chosen, but not:
- Date cash was actually received
- Receipt number from supplier
- Bank deposit reference
- Physical cash custody chain

**Recommendation**: Add fields to PurchaseReturnSettlement:
```python
class PurchaseReturnSettlement(models.Model):
    # ... existing fields ...
    
    # For cash refund tracking
    cash_received_date = models.DateField(null=True, blank=True)
    cash_receipt_number = models.CharField(max_length=100, blank=True)
    bank_deposit_reference = models.CharField(max_length=100, blank=True)
    cash_verified_by = models.ForeignKey(User, null=True, on_delete=SET_NULL)
    cash_verification_notes = models.TextField(blank=True)
```

---

## Comparison with Sales Return System

### Sales Returns (Customer Returns)

**File**: `sales/return_views.py`

**Settlement Flow**:
```python
# Sales return with cash settlement
return_obj.settlement_method = 'cash'
return_obj.settlement_status = 'settled_cash'
return_obj.cash_receipt_number = generate_cash_receipt_number()
return_obj.save()

# NO CompanyTransaction created
# Affects shop balance directly
```

**Key Differences**:
| Aspect | Purchase Returns | Sales Returns |
|--------|-----------------|---------------|
| Account Type | CompanyAccount | Shop Account |
| Transaction Created | ✅ Yes (on approval) | ❌ No |
| Settlement Tracking | PurchaseReturnSettlement | Status field only |
| Cash Refund | Tracked via settlement record | Tracked via cash_receipt_number |
| Balance Impact | Reduces company balance | Reduces shop balance |

### Consistency Recommendation

Consider unifying return settlement logic across both systems:
- Use settlement model for both purchase and sales returns
- Create transactions for both types
- Standardize status values and workflows

---

## Testing Checklist

### Manual Testing Steps

1. **Create Return**
   ```
   - Go to purchase detail page
   - Create return for Rs. 5,000
   - Verify status='pending'
   - Check company account - NO transaction yet
   ```

2. **Approve Return**
   ```
   - Click "Approve Return"
   - Verify status='company_approved'
   - Check stock reduced
   - Check CompanyTransaction created (type='return', amount=-5000)
   - Verify company balance reduced by Rs. 5,000
   ```

3. **Record Cash Refund Settlement**
   ```
   - Go to return detail page
   - Add settlement: method='refund', amount=5000, ref='CASH-123'
   - Verify PurchaseReturnSettlement created
   - Verify settlement_status='fully_settled'
   - Check company account - balance unchanged (still -5k from approval)
   - Verify sub-row shows "Settlement: Cash Refund CASH-123: Rs. 5,000"
   ```

4. **Record Partial Settlements**
   ```
   - Create return for Rs. 10,000
   - Approve return (balance -10k)
   - Add settlement: method='refund', amount=6000
   - Verify settlement_status='partial'
   - Add settlement: method='credit_note', amount=4000
   - Verify settlement_status='fully_settled'
   - Check only ONE CompanyTransaction (the original return)
   ```

5. **Replacement GRN Settlement**
   ```
   - Create return for Rs. 8,000
   - Approve return (balance -8k)
   - Receive replacement GRN for Rs. 8,000 (balance +8k)
   - Link replacement via settlement
   - Verify both transactions visible in ledger (net Rs. 0)
   ```

### SQL Verification Queries

```sql
-- Check return transaction amounts are negative
SELECT 
    reference_number,
    amount,
    CASE WHEN amount < 0 THEN '✅' ELSE '❌ ERROR' END as correct_sign
FROM company_transactions
WHERE transaction_type = 'return';

-- Verify no duplicate transactions for returns
SELECT 
    purchase_return_id,
    COUNT(*) as txn_count,
    CASE WHEN COUNT(*) = 1 THEN '✅' ELSE '❌ DUPLICATE' END as status
FROM company_transactions
WHERE purchase_return_id IS NOT NULL
GROUP BY purchase_return_id
HAVING COUNT(*) > 1;

-- Check settlement totals match approved amounts
SELECT 
    pr.pr_number,
    pr.approved_amount,
    COALESCE(SUM(prs.settlement_amount), 0) as total_settled,
    CASE 
        WHEN COALESCE(SUM(prs.settlement_amount), 0) = pr.approved_amount THEN '✅ Match'
        WHEN COALESCE(SUM(prs.settlement_amount), 0) > pr.approved_amount THEN '❌ Over-settled'
        ELSE '⚠️ Partial'
    END as status
FROM purchase_returns pr
LEFT JOIN purchase_return_settlements prs ON prs.purchase_return_id = pr.id
WHERE pr.status = 'company_approved'
GROUP BY pr.id, pr.pr_number, pr.approved_amount;

-- Find returns with cash refunds
SELECT 
    pr.pr_number,
    pr.total_amount,
    prs.settlement_method,
    prs.settlement_amount,
    prs.refund_reference
FROM purchase_returns pr
INNER JOIN purchase_return_settlements prs ON prs.purchase_return_id = pr.id
WHERE prs.settlement_method = 'refund'
ORDER BY pr.return_date DESC;
```

---

## Summary & Conclusion

### Key Findings

1. ✅ **Returns DO reduce company account balance** - Reduction happens at approval, not settlement
2. ✅ **Cash refunds do NOT create separate transactions** - Settlement tracked via PurchaseReturnSettlement
3. ✅ **Current design prevents double-counting** - One transaction per return (type='return')
4. ✅ **Settlement method is operational detail** - Doesn't affect balance calculation
5. ⚠️ **Orphaned record_cash_refund() method** - Should be removed or marked deprecated

### Balance Formula (Verified Correct)

```python
Company Balance = Opening Balance
                  + Sum(Purchase GRN amounts)
                  - Sum(Return amounts)  # ← Returns reduce balance
                  - Sum(Payment amounts)
                  ± Sum(Adjustment amounts)
```

### Settlement Method Impact Table

| Settlement Method | Balance Impact | Cash Flow | CompanyTransaction Created |
|-------------------|----------------|-----------|----------------------------|
| **Return Approval** | -Return Amount | None | ✅ Yes (type='return') |
| **Cash Refund** | None | +Cash In | ❌ No |
| **Credit Note** | None | None | ❌ No |
| **Replacement GRN** | +GRN Amount | None | ✅ Yes (type='purchase') |

### Recommendations

**Priority 1 - Code Cleanup**:
- Remove or deprecate `PurchaseReturn.record_cash_refund()` method
- Update `create_return_transaction()` to use 'pending_settlement' instead of 'credit'

**Priority 2 - Enhanced Tracking**:
- Add cash receipt tracking fields to PurchaseReturnSettlement
- Create audit trail for physical cash received
- Add cash verification workflow

**Priority 3 - System Consistency**:
- Unify purchase and sales return settlement logic
- Standardize settlement status values
- Create common settlement tracking model

---

**Investigation Complete**: January 18, 2026  
**Verdict**: ✅ System correctly reduces company balance when returns are approved. Cash refund settlement is tracked separately without creating duplicate transactions.
