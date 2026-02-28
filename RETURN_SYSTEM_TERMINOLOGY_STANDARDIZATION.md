# Return System Terminology Standardization
## Universal Business Standards Implementation

### Current Issues
1. Inconsistent terminology across pages
2. Non-standard receipt naming (CR, FR)
3. Technical terms like "settlement_status" in UI
4. Mixed use of "Return" vs "Sales Return"
5. Confusing cash receipt types

---

## STANDARDIZED TERMINOLOGY

### 1. DOCUMENT NAMES

#### Return Document
- **Label**: "Sales Return Note" or "Return Note"
- **Short Label**: "Return No."
- **Number Format**: `RN-YYYYMMDD-XXX`
  - Example: `RN-20260105-001`
- **Current**: `RET20260105001` ❌
- **Database Field**: `return_number`

#### Cash Payment Voucher
- **Label**: "Cash Payment Voucher"
- **Short Label**: "Voucher No." or "CPV No."
- **Number Format**: `CPV-YYYYMMDD-XXX`
  - Example: `CPV-20260105-001`
- **Current Office**: `CR20260105001` ❌
- **Current Field**: `FR20260105001` ❌
- **Database Fields**: 
  - `cash_receipt_number` → Rename to `voucher_number`
  - `field_receipt_number` → Rename to `field_voucher_number`

---

### 2. STATUS LABELS

#### Return Status
| Current | Universal Standard | Display |
|---------|-------------------|---------|
| `pending` | Pending Approval | 🟡 Pending |
| `approved` | Approved | 🟢 Approved |
| `rejected` | Rejected | 🔴 Rejected |

#### Settlement Method
| Current | Universal Standard | Business Term |
|---------|-------------------|---------------|
| `cash` | Cash Refund | Cash Refund |
| `credit_note` | Credit Note | Credit Note |
| `next_bill` | Apply to Invoice | Adjust in Next Bill |

#### Settlement Status
| Current | Universal Standard | Display Label |
|---------|-------------------|---------------|
| `unsettled` | Pending Payment | ⏳ Awaiting Payment |
| `settled_cash` | Paid | ✅ Cash Paid |
| `available` | Available Credit | 💳 Credit Available |
| `partially_applied` | Partially Used | 🔄 Partially Applied |
| `fully_applied` | Fully Used | ✔️ Fully Applied |

---

### 3. FIELD LABELS (UI Text)

#### Return List Page (`/sales/returns/`)
```
Current → Standard

"Product Returns Management" → "Sales Returns"
"Return Number" → "Return No."
"Return Date" → "Date"
"Return Status" → "Status"
"Settlement Method" → "Refund Method"
"Settlement Status" → "Payment Status"
"Total Returns" → "Total Returns"
"Total Amount" → "Total Value"
"Pending Returns" → "Pending Approval"
"Approved Returns" → "Approved"
"Rejected Returns" → "Rejected"
"Cash Settled" → "Cash Paid"
"Available Credit" → "Available Credit"
```

#### Return Detail Page (`/sales/returns/31/`)
```
Current → Standard

"Return Details" → "Sales Return Note"
"Return Number:" → "Return No.:"
"Return Date:" → "Date:"
"Return Status:" → "Status:"
"Settlement Method:" → "Refund Method:"
"Settlement Status:" → "Payment Status:"
"Approved By:" → "Approved By:"
"Cash Paid By:" → "Paid By:"
"Receipt Number:" → "Voucher No.:"
"Field Receipt:" → "Field Voucher:"
"Official Receipt:" → "Payment Voucher:"
"Settle Cash Return" → "Pay Cash Refund"
"Pay Cash to Customer" → "Process Cash Payment"
```

#### Create Return Page (`/sales/returns/create/`)
```
Current → Standard

"Record Return" → "Create Sales Return"
"Return Reason" → "Reason for Return"
"Settlement Method" → "Refund Method"
```

#### Receipt Print Page (`/sales/returns/31/receipt/print/`)
```
Current → Standard

"Cash Return Receipt" → "Cash Payment Voucher"
"Field Cash Receipt" → "Field Cash Voucher"
"CASH RETURN RECEIPT" → "CASH PAYMENT VOUCHER"
"Receipt Number:" → "Voucher No.:"
"Cash Paid By:" → "Paid By:"
"I acknowledge receipt" → "I acknowledge receipt of cash refund"
```

---

### 4. BUTTON TEXT STANDARDIZATION

| Current | Standard |
|---------|----------|
| "Approve Return" | "Approve Return" ✓ |
| "Reject Return" | "Reject Return" ✓ |
| "Delete Return" | "Delete Return" ✓ |
| "Pay Cash to Customer" | "Process Cash Payment" |
| "View Cash Receipt" | "View Payment Voucher" |
| "Print Receipt" | "Print Voucher" |
| "Settle Cash Return" | "Process Cash Refund" |

---

### 5. DATABASE FIELD STANDARDIZATION

#### Returns Table
```python
# Current → Recommended
return_number          ✓ Keep (change format to RN-)
return_date           ✓ Keep  
return_status         ✓ Keep (update choices display)
return_reason         ✓ Keep (update choices display)
settlement_method     ✓ Keep (update choices display)
settlement_status     ✓ Keep (update choices display)
cash_receipt_number   → voucher_number
field_receipt_number  → field_voucher_number
cash_paid_by         → refund_paid_by
cash_paid_at         → refund_paid_at
field_cash_given     ✓ Keep
field_cash_amount    ✓ Keep
```

---

### 6. RECEIPT NUMBER GENERATION

#### Office Cash Payment Voucher
```python
# Current
prefix = f"CR{today.strftime('%Y%m%d')}"  # CR20260105
cash_receipt_number = f"{prefix}{new_number:03d}"  # CR20260105001

# Standard
prefix = f"CPV-{today.strftime('%Y%m%d')}-"  # CPV-20260105-
voucher_number = f"{prefix}{new_number:03d}"  # CPV-20260105-001
```

#### Field Cash Voucher
```python
# Current
prefix = f"FR{today.strftime('%Y%m%d')}"  # FR20260105
field_receipt_number = f"{prefix}{new_number:03d}"  # FR20260105001

# Standard
prefix = f"FCV-{today.strftime('%Y%m%d')}-"  # FCV-20260105-
field_voucher_number = f"{prefix}{new_number:03d}"  # FCV-20260105-001
```

#### Return Note Number
```python
# Current
prefix = f"RET{today.strftime('%Y%m%d')}"  # RET20260105
return_number = f"{prefix}{new_number:03d}"  # RET20260105001

# Standard
prefix = f"RN-{today.strftime('%Y%m%d')}-"  # RN-20260105-
return_number = f"{prefix}{new_number:03d}"  # RN-20260105-001
```

---

### 7. IMPLEMENTATION PRIORITY

#### Phase 1: UI Labels (No DB Changes)
- ✅ Update all page titles
- ✅ Update field labels  
- ✅ Update button text
- ✅ Update status badge text
- ✅ Update receipt titles

#### Phase 2: Number Formats (Code Only)
- ✅ Change return number generation: `RET` → `RN-`
- ✅ Change cash voucher generation: `CR` → `CPV-`
- ✅ Change field voucher generation: `FR` → `FCV-`

#### Phase 3: Database Migration (Optional - Future)
- Rename `cash_receipt_number` → `voucher_number`
- Rename `field_receipt_number` → `field_voucher_number`
- Rename `cash_paid_by` → `refund_paid_by`
- Rename `cash_paid_at` → `refund_paid_at`

---

### 8. BUSINESS RATIONALE

1. **"Return Note" (RN)**: Universal term in wholesale/distribution
2. **"Cash Payment Voucher" (CPV)**: Standard accounting document for cash out
3. **"Credit Note"**: Standard accounting term for customer credit
4. **"Refund" instead of "Settlement"**: Customer-facing term
5. **"Voucher No." instead of "Receipt No."**: Technically correct (company pays out)
6. **Hyphenated numbers**: Better readability and parsing (RN-20260105-001)

---

### 9. KEY MESSAGES

#### For Sales Rep
- "Create a **Sales Return** when customer returns products"
- "Get a **Field Cash Voucher** if you pay cash immediately"
- "Return must be **approved** by office before processing"

#### For Office Manager  
- "Review pending **Return Notes**"
- "Approve returns to restore stock"
- "Process **Cash Payment Voucher** to refund customer"
- "Issue **Credit Note** for account adjustment"

#### For Customer (Shop Owner)
- "We've issued **Return Note RN-20260105-001** for your return"
- "Your **Cash Payment Voucher CPV-20260105-001** for Rs. 5,000"
- "**Credit Note** will be applied to your next bill"

---

## VALIDATION CHECKLIST

### Return List Page
- [ ] Page title: "Sales Returns"
- [ ] Return numbers: RN-YYYYMMDD-XXX format
- [ ] Status badges: Pending/Approved/Rejected
- [ ] Payment status: Clear labels (Awaiting Payment, Cash Paid, etc.)

### Return Detail Page
- [ ] Page title: "Sales Return Note"
- [ ] All field labels updated
- [ ] Button text: "Process Cash Payment"
- [ ] Receipt links: "View Payment Voucher"

### Create Return Page
- [ ] Page title: "Create Sales Return"
- [ ] Field labels: "Refund Method"
- [ ] Clear help text

### Receipt Print Page
- [ ] Title: "CASH PAYMENT VOUCHER"
- [ ] Voucher number: CPV-YYYYMMDD-XXX or FCV-YYYYMMDD-XXX
- [ ] Clear payment acknowledgment text
- [ ] Professional formatting

---

## FILES TO UPDATE

### Templates
1. `templates/sales/return_list.html` - Labels, titles, badge text
2. `templates/sales/return_detail.html` - Labels, button text, status display
3. `templates/sales/create_return_mobile.html` - Page title, field labels
4. `templates/sales/return_cash_receipt.html` - Receipt title, voucher number

### Views
5. `sales/return_views.py` - Number generation, context labels, messages
6. `sales/models.py` - Choice field display values (verbose names)

### URLs (no changes needed)
- Keep URL structure as is for backward compatibility

---

*End of Standardization Guide*
