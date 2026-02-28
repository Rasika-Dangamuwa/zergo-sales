# Timezone Usage in Number Generation - Deep Investigation

## Django Settings

**Configured Timezone**: `Asia/Colombo` (Sri Lanka)  
**USE_TZ**: `True` (Django uses timezone-aware datetimes)

**Location**: `zergo_sales/settings.py` Line 118, 122

```python
TIME_ZONE = 'Asia/Colombo'  # Sri Lanka timezone
USE_TZ = True
```

## Summary of Findings

**ALL number generation methods use `timezone.now()`** which returns a **timezone-aware datetime** in **UTC**, then Django automatically converts it to the local timezone (`Asia/Colombo`) when needed.

This ensures consistent number generation regardless of server timezone or DST changes.

---

## Detailed Breakdown by Model

### 1. SALES MODULE (`sales/models.py`)

#### Sale Number: `SAL-YYYYMMDD-###`
**Method**: `Sale.generate_sale_number()` - Line 79  
**Timezone Source**: `timezone.now()`  
**Code**:
```python
today = timezone.now()
prefix = f"SAL{today.strftime('%Y%m%d')}"
```
**Behavior**: 
- Uses UTC time from `timezone.now()`
- Django converts to Asia/Colombo when displaying
- Format: SAL20260126001

---

#### Bill Number: `BILL-YYYYMMDD-###`
**Method**: `Bill.generate_bill_number()` - Line 228  
**Timezone Source**: `self.bill_date` (if set) OR `timezone.now()` (fallback)  
**Code**:
```python
today = self.bill_date if self.bill_date else timezone.now()
prefix = f"BILL{today.strftime('%Y%m%d')}"
```
**Behavior**:
- Prefers bill_date field (DateTimeField with default=timezone.now)
- Falls back to timezone.now() if bill_date not set
- Format: BILL20260126001

---

#### Return Number (Legacy): `RET-YYYYMMDD-###`
**Method**: `Return.generate_return_number()` - Line 378  
**Timezone Source**: `timezone.now()`  
**Code**:
```python
today = timezone.now()
prefix = f"RET{today.strftime('%Y%m%d')}"
```
**Status**: Legacy model (commented out)

---

#### Return Number (Active): `RN-YYYYMMDD-###`
**Method**: `Return.generate_return_number()` - Line 944  
**Timezone Source**: `timezone.now()`  
**Code**:
```python
today = timezone.now()
prefix = f"RN-{today.strftime('%Y%m%d')}-"
```
**Behavior**:
- Uses UTC from timezone.now()
- Format: RN-20260126-001

---

#### Exchange Number: `EXC-YYYYMMDD-###`
**Method**: `ItemExchange.generate_exchange_number()` - Line 1043  
**Timezone Source**: `timezone.now()`  
**Code**:
```python
today = timezone.now()
prefix = f"EXC-{today.strftime('%Y%m%d')}-"
```
**Behavior**:
- Uses UTC from timezone.now()
- Format: EXC-20260126-001

---

### 2. PAYMENTS MODULE (`payments/models.py`)

#### Settlement Number: `SET-YYYYMMDD-####`
**Method**: `SalesAccountSettlement.generate_payment_number()` - Line 84  
**Timezone Source**: `timezone.now()`  
**Code**:
```python
today = timezone.now()
prefix = f"SET-{today.strftime('%Y%m%d')}-"
```
**Behavior**:
- Uses UTC from timezone.now()
- Format: SET-20260126-0001 (4 digits)

---

#### Write-Off Number: `DISP-YYYY-####`
**Method**: `BadDebtWriteOff.generate_write_off_number()` - Line 207  
**Timezone Source**: `timezone.now().year` (year only)  
**Code**:
```python
current_year = timezone.now().year
prefix = f"DISP-{current_year}-"
```
**Behavior**:
- Uses year from UTC timezone.now()
- Resets annually
- Format: DISP-2026-0001

---

### 3. PRODUCTS MODULE (`products/models.py`)

#### Stock Count Number: `SC-YYYY-####`
**Method**: `StockCount.generate_count_number()` - Line 295  
**Timezone Source**: `timezone.now().year`  
**Code**:
```python
current_year = timezone.now().year
prefix = f"SC-{current_year}-"
```
**Behavior**:
- Year-based, resets annually
- Format: SC-2026-0001

---

#### Adjustment Number: `ADJ-YYYY-####`
**Method**: `ProductStatusAdjustment.generate_adjustment_number()` - Line 406  
**Timezone Source**: `timezone.now().year`  
**Code**:
```python
current_year = timezone.now().year
prefix = f"ADJ-{current_year}-"
```
**Behavior**:
- Year-based, resets annually
- Format: ADJ-2026-0001

---

#### Purchase Order Number: `PO-YYYY-####`
**Method**: `PurchaseOrder.generate_po_number()` - Line 548  
**Timezone Source**: `timezone.now().year`  
**Code**:
```python
current_year = timezone.now().year
prefix = f"PO-{current_year}-"
```
**Behavior**:
- Year-based, resets annually
- Format: PO-2026-0001

---

#### GRN Number: `GRN-YYYY-####`
**Method**: `Purchase.generate_grn_number()` - Line 747  
**Timezone Source**: `timezone.now().year`  
**Code**:
```python
current_year = timezone.now().year
prefix = f"GRN-{current_year}-"
```
**Behavior**:
- Year-based, resets annually
- Format: GRN-2026-0001

---

#### Purchase Return Number: `PR-YYYY-####`
**Method**: `PurchaseReturn.generate_pr_number()` - Line 1084  
**Timezone Source**: `timezone.now().year`  
**Code**:
```python
current_year = timezone.now().year
prefix = f"PR-{current_year}-"
```
**Behavior**:
- Year-based, resets annually
- Format: PR-2026-0001

---

#### Company Payment Number: `CPY-YYYY-####`
**Method**: `CompanyPayment.generate_payment_number()` - Line 1698  
**Timezone Source**: `timezone.now().year`  
**Code**:
```python
current_year = timezone.now().year
prefix = f"CPY-{current_year}-"
```
**Behavior**:
- Year-based, resets annually
- Format: CPY-2026-0001

---

## Special Cases

### Shop Code: `SHOP######` (6 digits, no date)
**Generation**: Auto-incremented, not date-based
**No timezone dependency**

---

## How Django's `timezone.now()` Works

```python
from django.utils import timezone

# When called:
timezone.now()  # Returns datetime in UTC

# Example:
# If current time in Sri Lanka (UTC+5:30) is 2026-01-26 10:00:00
# timezone.now() returns: 2026-01-26 04:30:00+00:00 (UTC)

# When formatting with strftime:
timezone.now().strftime('%Y%m%d')  # Returns: '20260126'
# Uses UTC date, but when it's midnight in UTC (00:00:00),
# it's already morning (05:30:00) in Sri Lanka

# Conversion happens automatically in templates/display
```

---

## Potential Timezone Issues

### ⚠️ **Date Boundary Issue**

**Problem**: Numbers generated near midnight may use different dates depending on UTC vs local time.

**Example Scenario**:
- **Sri Lanka Time**: 2026-01-26 03:00 AM (early morning)
- **UTC Time**: 2026-01-25 21:30 (still previous day)
- **Generated Number**: Uses UTC date → `BILL20260125001` instead of `BILL20260126001`

**Impact**:
- Bills created early morning in Sri Lanka (00:00-05:30 AM) get **previous day's date** in number
- This creates inconsistency between bill_date display and bill_number

---

## Where Timezone Conversion Happens

### Views Using Local Timezone Conversion

**Files converting UTC to Asia/Colombo**:

1. **`sales/views.py` Line 31**:
```python
local_tz = pytz.timezone(settings.TIME_ZONE)
today = timezone.now().astimezone(local_tz).date()
```

2. **`sales/return_views.py` Lines 62, 202, 496**:
```python
local_tz = pytz.timezone(settings.TIME_ZONE)
today = timezone.now().astimezone(local_tz).date()
```

3. **`products/views.py` Line 457**:
```python
local_tz = pytz.timezone(settings.TIME_ZONE)
```

**Purpose**: Convert UTC datetime to local date for filtering/display

---

## Recommendations

### ✅ Current Implementation is CONSISTENT
All number generation uses `timezone.now()` (UTC-based), ensuring:
- No DST issues
- Consistent across servers
- Database-agnostic

### ⚠️ Potential Improvement
For numbers including dates (SAL, BILL, RN, EXC, SET), consider using:

```python
# Instead of:
today = timezone.now()

# Use:
from django.conf import settings
import pytz

local_tz = pytz.timezone(settings.TIME_ZONE)
today = timezone.now().astimezone(local_tz)
```

This ensures bill numbers match the local business day, avoiding:
- Bill created at 02:00 AM Sri Lanka time getting previous day's number
- Confusion when bill_date shows Jan 26 but bill_number shows BILL20260125

---

## Complete Number Format Reference

| Number Type | Format | Example | Timezone Source | Resets |
|------------|--------|---------|-----------------|---------|
| **Sale Number** | `SAL-YYYYMMDD-###` | SAL-20260126-001 | timezone.now() | Daily |
| **Bill Number** | `BILL-YYYYMMDD-###` | BILL-20260126-001 | self.bill_date OR timezone.now() | Daily |
| **Return Number** | `RN-YYYYMMDD-###` | RN-20260126-001 | timezone.now() | Daily |
| **Exchange Number** | `EXC-YYYYMMDD-###` | EXC-20260126-001 | timezone.now() | Daily |
| **Settlement Number** | `SET-YYYYMMDD-####` | SET-20260126-0001 | timezone.now() | Daily |
| **Write-Off Number** | `DISP-YYYY-####` | DISP-2026-0001 | timezone.now().year | Annually |
| **Stock Count** | `SC-YYYY-####` | SC-2026-0001 | timezone.now().year | Annually |
| **Adjustment** | `ADJ-YYYY-####` | ADJ-2026-0001 | timezone.now().year | Annually |
| **Purchase Order** | `PO-YYYY-####` | PO-2026-0001 | timezone.now().year | Annually |
| **GRN Number** | `GRN-YYYY-####` | GRN-2026-0001 | timezone.now().year | Annually |
| **Purchase Return** | `PR-YYYY-####` | PR-2026-0001 | timezone.now().year | Annually |
| **Company Payment** | `CPY-YYYY-####` | CPY-2026-0001 | timezone.now().year | Annually |
| **Shop Code** | `SHOP######` | SHOP000001 | N/A (sequential) | Never |

---

## Testing Timezone Behavior

To test timezone impact, run this in Django shell:

```python
from django.utils import timezone
from django.conf import settings
import pytz

# Current UTC time
utc_now = timezone.now()
print(f"UTC: {utc_now}")

# Local time (Asia/Colombo)
local_tz = pytz.timezone(settings.TIME_ZONE)
local_now = utc_now.astimezone(local_tz)
print(f"Local: {local_now}")

# Date difference
print(f"UTC Date: {utc_now.date()}")
print(f"Local Date: {local_now.date()}")
print(f"Same day?: {utc_now.date() == local_now.date()}")
```

If run between 00:00-05:30 Sri Lanka time, you'll see different dates!

---

## Conclusion

**✅ FIXED - January 26, 2026**

All number generation methods have been updated to use **local timezone (`Asia/Colombo`)** instead of UTC.

**Timezone Configuration**: `Asia/Colombo` (UTC+5:30)

**What Was Fixed**:
- **Sale Numbers**: Now use `timezone.now().astimezone(local_tz)` for date
- **Bill Numbers**: Now use `bill_date.astimezone(local_tz)` for date
- **Return Numbers**: Now use `timezone.now().astimezone(local_tz)` for date
- **Exchange Numbers**: Now use `timezone.now().astimezone(local_tz)` for date
- **Settlement Numbers**: Now use `timezone.now().astimezone(local_tz)` for date
- **All Year-based Numbers**: Now use `timezone.now().astimezone(local_tz).year`

**Result**: Bill numbers now **perfectly sync** with the local business date in Sri Lanka. No more mismatches between `bill_date` display and `bill_number`.

**Test Results**:
```
Bill created at 2:00 AM Sri Lanka time on Jan 26, 2026:
  OLD: BILL20260125XXX (UTC was still Jan 25) ❌
  NEW: BILL20260126XXX (Local date Jan 26) ✅
  
Bill date display: January 26, 2026 ✅
Bill number shows: 20260126 ✅
PERFECT MATCH!
```
