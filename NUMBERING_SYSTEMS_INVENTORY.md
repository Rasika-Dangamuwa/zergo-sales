# Complete Numbering Systems Inventory

**Last Updated:** January 13, 2026  
**Purpose:** Comprehensive list of all document numbering systems across the application

---

## ✅ UPDATED SYSTEMS (Yearly Reset Format: PREFIX-YYYY-NNNN)

### Products Module - Updated ✅

| System | Current Format | Example | Location | Status |
|--------|---------------|---------|----------|---------|
| **Purchase Order** | `PO-YYYY-NNNN` | PO-2026-0001 | products/models.py (PurchaseOrder) | ✅ Updated Jan 13 |
| **GRN (Goods Received Note)** | `GRN-YYYY-NNNN` | GRN-2026-0001 | products/models.py (Purchase) | ✅ Updated Jan 13 |
| **Purchase Return** | `PR-YYYY-NNNN` | PR-2026-0001 | products/models.py (PurchaseReturn) | ✅ Updated Jan 13 |
| **Company Payment** | `CPY-YYYY-NNNN` | CPY-2026-0001 | products/models.py (CompanyPayment) | ✅ Updated Jan 13 |
| **Stock Count** | `SC-YYYY-NNNN` | SC-2026-0001 | products/models.py (StockCount) | ✅ Updated Jan 13 |
| **Status Adjustment** | `ADJ-YYYY-NNNN` | ADJ-2026-0001 | products/models.py (ProductStatusAdjustment) | ✅ Updated Jan 13 |
| **Disposal Reference** | `DISP-YYYY-NNNN` | DISP-2026-0001 | products/views.py (dispose_non_resaleable_stock) | ✅ Updated Jan 13 |

---

## ⏳ PENDING SYSTEMS (Old Daily Reset Format - Need Update)

### Sales Module - Daily Reset Format ⏳

| System | Current Format | Example | Location | Migration Priority |
|--------|---------------|---------|----------|-------------------|
| **Sale Number** | `SALYYYYMMDDNNN` | SAL20251222001 | sales/models.py (Sale.generate_sale_number) | 🔴 HIGH |
| **Bill Number** | `BILLYYYYMMDDNNN` | BILL20251222001 | sales/models.py (Bill.generate_bill_number) | 🔴 HIGH |
| **Payment Number** | `PAYYYYYMMDDNNN` | PAY20251222001 | sales/models.py (Payment.generate_payment_number) | 🔴 HIGH |
| **Return Number** | `RN-YYYYMMDD-NNN` | RN-20260110-001 | sales/models.py (Return.generate_return_number) | 🔴 HIGH |
| **Exchange Number** | `EXC-YYYYMMDD-NNN` | EXC-20260106-001 | sales/models.py (ItemExchange.generate_exchange_number) | 🟡 MEDIUM |

### Products Module - Daily Reset Format ⏳

| System | Current Format | Example | Location | Migration Priority |
|--------|---------------|---------|----------|-------------------|
| ~~**Company Return**~~ | ~~`CR-YYYYMMDD-NNN`~~ | ~~CR-20260110-001~~ | **REMOVED Jan 19, 2026** | ✅ DELETED |

### Payments Module - Daily Reset Format ⏳

| System | Current Format | Example | Location | Migration Priority |
|--------|---------------|---------|----------|-------------------|
| **Old Payment Number** | `PAY-YYYYMMDD-NNNN` | PAY-20260110-0001 | payments/models.py (OldPayment.generate_payment_number) | 🟢 LOW |

### Sales Returns - Field Cash Vouchers (In-View Generation) ⏳

| System | Current Format | Example | Location | Migration Priority |
|--------|---------------|---------|----------|-------------------|
| **Cash Payment Voucher** | `CPV-YYYYMMDD-NNN` | CPV-20260113-001 | sales/return_views.py (settle_return_cash, line 295-306) | 🔴 HIGH |

---

## 📝 REFERENCE-ONLY SYSTEMS (No Auto-Generation)

### Static/Manual Number Fields

| Field | Purpose | Location | Notes |
|-------|---------|----------|-------|
| **Shop Code** | `SHOPNNNNNN` (6 digits, sequential) | shops/models.py (Shop.save) | Auto-generated on shop creation, never resets |
| **Credit Note Number** | No auto-generation | payments/models.py (CreditNote) | Manually entered or TBD |
| **Reference Number** | Free-form text field | payments/models.py (OldPayment) | For bank/cheque references |
| **Supplier Invoice Number** | Free-form text field | products/models.py (Purchase) | External supplier's invoice |
| **Batch Number** | Free-form text field | products/models.py (StockMovement, ProductStatusAdjustment, CompanyReturn) | Product batch tracking |
| **Cash Receipt Number** | Stored in Return model | sales/models.py (Return.cash_receipt_number) | Generated in return_views.py as CPV number |
| **Vehicle Number** | Free-form text field | products/models.py (Not found in search) | Delivery vehicle plate |
| **Phone Number** | Free-form text field | Multiple models (Shop, User, etc.) | Contact information |

---

## 🔍 DETAILED FORMAT ANALYSIS

### Old Format Pattern A: Compact Daily Reset (No Separators)
**Pattern:** `PREFIXYYYYMMDDNNN`  
**Used By:**
- Sale Number: `SAL20251222001`
- Bill Number: `BILL20251222001`
- Payment Number: `PAY20251222001`

**Characteristics:**
- No hyphens/separators
- 3-digit daily sequence (001-999)
- Resets every day
- Hard to read, prone to gaps in low-volume operations

### Old Format Pattern B: Separated Daily Reset (With Hyphens)
**Pattern:** `PREFIX-YYYYMMDD-NNN`  
**Used By:**
- Return Number: `RN-20260110-001`
- Exchange Number: `EXC-20260106-001`
- Company Return: `CR-20260110-001`
- Cash Payment Voucher: `CPV-20260113-001`
- Old Payment: `PAY-20260110-0001` (4 digits)

**Characteristics:**
- Hyphen-separated for readability
- 3 or 4-digit daily sequence
- Resets every day
- More readable but still creates gaps

### New Format Pattern: Yearly Reset (Standardized)
**Pattern:** `PREFIX-YYYY-NNNN`  
**Used By:** All updated systems (PO, GRN, PR, CPY, SC, ADJ, DISP)

**Characteristics:**
- Clean, professional appearance
- 4-digit yearly sequence (0001-9999)
- Resets annually on Jan 1
- Ideal for low-volume operations (1-2 transactions/week)
- No gaps, sequential within year
- Future-proof for up to 9,999 transactions/year per document type

---

## 📊 MIGRATION STATUS SUMMARY

### By Module
- **Products Module:** 7/8 systems updated (87.5% complete)
  - ✅ PO, GRN, PR, CPY, SC, ADJ, DISP
  - ⏳ Company Return (CR)

- **Sales Module:** 0/5 systems updated (0% complete)
  - ⏳ Sale, Bill, Payment, Return, Exchange

- **Payments Module:** 0/1 systems updated (0% complete)
  - ⏳ Old Payment

- **Sales Return Views:** 0/1 in-view generation updated (0% complete)
  - ⏳ CPV (Cash Payment Voucher)

### Overall Progress
**Total Systems:** 14 numbering systems requiring management (CompanyReturn removed)  
**Updated:** 7 systems (50%)  
**Pending:** 7 systems (50%)  
**Deleted:** 1 system (CompanyReturn - replaced by PurchaseReturn)

---

## 🎯 RECOMMENDED UPDATE PRIORITY

### Phase 1: Critical Sales Documents (Immediate)
1. **Sale Number** (SAL) - Core sales transaction
2. **Bill Number** (BILL) - Customer invoices
3. **Payment Number** (PAY) - Payment receipts
4. **Return Number** (RN) - Sales returns
5. **Cash Payment Voucher** (CPV) - Field cash settlement

### Phase 2: Supporting Documents (Next)
6. **Exchange Number** (EXC) - Product exchanges
7. **Company Return** (CR) - Returns to suppliers

### Phase 3: Legacy/Low Priority (Optional)
8. **Old Payment** (PAY in payments app) - Legacy payment system

---

## 📋 BUSINESS CONTEXT

**Transaction Volume:** 1-2 transactions per week per document type  
**Current Issues with Daily Reset:**
- Long, hard-to-read numbers (e.g., BILL20251222001)
- Sequence gaps (jumps from 001 to 200+ in single day)
- Impractical for low-volume business
- Inconsistent with modernized systems

**Benefits of Yearly Reset:**
- Clean, professional format (e.g., BILL-2026-0001)
- Sequential within year (no gaps)
- Easier to reference and communicate
- Consistent across all document types
- Supports up to 9,999 documents/year (50+ years of current volume)

---

## 🛠️ TECHNICAL IMPLEMENTATION NOTES

### Generation Method Locations
All auto-generation happens in model `save()` methods or view logic:

**Model-Based Generation:**
- Products: PurchaseOrder, Purchase, PurchaseReturn, CompanyPayment, StockCount, ProductStatusAdjustment, CompanyReturn
- Sales: Sale, Bill, Payment, Return, ItemExchange
- Payments: OldPayment
- Shops: Shop (shop_code only)

**View-Based Generation:**
- products/views.py: `dispose_non_resaleable_stock()` - DISP numbers
- sales/return_views.py: `settle_return_cash()` - CPV numbers (lines 295-306, 522-533)

### Standard Generation Pattern (Updated Systems)
```python
def generate_X_number(self):
    """Generate X number: PREFIX-YYYY-NNNN format"""
    from datetime import date
    
    today = date.today()
    year = today.year
    prefix = f"PREFIX-{year}-"
    
    last_record = self.__class__.objects.filter(
        x_number__startswith=prefix
    ).order_by('-x_number').first()
    
    if last_record and last_record.x_number:
        last_number = int(last_record.x_number.split('-')[-1])
        new_number = last_number + 1
    else:
        new_number = 1
    
    return f"{prefix}{new_number:04d}"
```

---

## 🔄 NEXT STEPS

1. ✅ Complete this inventory document
2. ⏳ Update remaining 8 numbering systems to yearly format
3. ⏳ Run database migrations for any new fields
4. ⏳ Update documentation and training materials
5. ⏳ Test number generation across all updated systems
6. ⏳ Monitor for any gaps or issues in production

---

**Document Version:** 1.0  
**Author:** System Analysis  
**Review Date:** January 13, 2026
