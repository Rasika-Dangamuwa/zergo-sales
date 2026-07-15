# User-Specific Document Number System Plan

## Goal
Prevent document number conflicts when multiple users create bills offline simultaneously.
Each user gets their own number namespace using a role-based prefix + user number.

---

## New Format

```
BILL-001-SR01-20260715-0001
     │    │    │         └── 4-digit daily sequence (per user, resets daily)
     │    │    └──────────── Date (YYYYMMDD)
     │    └───────────────── User code (role prefix + user number)
     └────────────────────── Distributor code (shortened from ZERGO001 → 001)
```

**Examples:**
```
BILL-001-SR01-20260715-0001   ← Fahad's first bill on that day
BILL-001-SR01-20260715-0002   ← Fahad's second bill
BILL-001-DB01-20260715-0001   ← Distributor's first bill (same day, no conflict)
BILL-001-AD01-20260715-0001   ← Admin's first bill (same day, no conflict)
```

Same total length as current format (`BILL-ZERGO001-20260715-0001`) because
shortening `ZERGO001` → `001` offsets the added user code.

---

## Role Prefix Mapping

| Role (in DB) | Prefix | Example codes |
|---|---|---|
| `sales_rep` | `SR` | SR01, SR02, SR03 |
| `office` (Distributor) | `DB` | DB01, DB02 |
| `admin` | `AD` | AD01 |

---

## User Codes (assign before building)

Every user who creates field documents needs an `employee_id` assigned.
The `employee_id` should follow the format: `{ROLEPREFIX}{2-digit number}`

| User | Role | Assign employee_id |
|---|---|---|
| Rasika Dangamuwa (admin) | admin | `AD01` |
| Office User | office | `DB01` |
| Office Manager | office | `DB02` |
| Sales Representative (rep) | sales_rep | `SR01` |
| Mohamed Fahad | sales_rep | `SR02` (currently has `001` — update) |
| Mathara Malli | sales_rep | `SR03` (currently has `SR0001` — update) |

> All users must have `employee_id` set before going offline. If `employee_id` is
> missing, fallback is `U{pk}` (e.g. `U1`) to avoid crashes — but this should not
> happen in production.

---

## Files to Change

### 1. `utils/number_generator.py`
- Add `user_code=None` parameter to `generate_number()`
- When provided in `daily` mode: prefix becomes `{PREFIX}-{DIST}-{user_code}-{DATE}-`
- Sequence is then scoped per user (each user has their own 0001 counter per day)

**Partial change already applied** — `rep_code=None` parameter added to `generate_number()`
(rename `rep_code` → `user_code` when building)

### 2. `sales/models.py` — update these generate methods:

| Method | Model | User field to use |
|---|---|---|
| `Bill.generate_bill_number()` | Bill | `self.sales_rep` |
| `Sale.generate_sale_number()` | Sale | `self.sales_rep` |
| `Return.generate_return_number()` (old, prefix RET) | Return (old) | `self.sales_rep` |
| `Return.generate_return_number()` (new, prefix RN) | Return (new) | `self.created_by` |
| `ItemExchange.generate_exchange_number()` | ItemExchange | `self.created_by` |

Add a helper function at the top of `sales/models.py`:

```python
def _user_doc_code(user):
    """Return role-prefixed employee_id for document numbering."""
    if not user:
        return None
    try:
        if user.employee_id:
            return user.employee_id.upper()
    except Exception:
        pass
    return f"U{user.pk}"  # fallback if employee_id not set
```

Then in each generate method, pass `user_code=_user_doc_code(self.sales_rep)`.

### 3. Update existing `employee_id` values in DB
Run a management command or admin panel update:
- Fahad: `001` → `SR02`
- Mathara Malli: `SR0001` → `SR03`
- Assign IDs to all users without one (see table above)

---

## Sequence Logic (how it works offline)

- SR01 offline, creates 3 bills: `...-SR01-20260715-0001`, `0002`, `0003`
- DB01 offline same day, creates 2 bills: `...-DB01-20260715-0001`, `0002`
- When both sync to server → zero conflict, different namespaces

The sequence lookup in `generate_number()` already filters by `startswith(number_prefix)`,
so adding the user code to the prefix automatically scopes the counter per user.

---

## Prerequisites Before Building

1. Assign/update `employee_id` for all users (see table above)
2. Rename `rep_code` → `user_code` in `number_generator.py` (cosmetic, for clarity)
3. Decide: shorten `ZERGO001` → `001` in dist code? (saves 5 chars, keeps same total length)
   - Change needed in `get_distributor_code()` in `number_generator.py`
   - The `tenant.code` field value would need updating too

---

## What Does NOT Need Changing

- Office-only documents (PO, GRN, ADJ, SC, CPY, MONEY, ADV) — these are created on
  the server, no offline conflict risk. Leave their format unchanged.
- SET (settlements) — created when online, no offline risk.
- SHOP codes — global sequence, office-only. No change needed.
