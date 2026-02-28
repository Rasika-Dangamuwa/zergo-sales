# Commission Payout System - Visual Architecture

## System Overview
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ZERGO DISTRIBUTORS SALES SYSTEM                      │
│                     Automated Commission Payout Architecture                │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────┐         ┌──────────────────────┐         ┌──────────────────────┐
│   COMMISSION         │         │   PAYOUT             │         │   MONEY              │
│   TRACKING           │────────▶│   SCHEDULER          │────────▶│   ACCOUNTS           │
│                      │         │                      │         │                      │
│ • Bills              │         │ • Schedule Config    │         │ • User Balance       │
│ • Payments           │         │ • Execution History  │         │ • Transactions       │
│ • Returns            │         │ • User Payouts       │         │ • Advances           │
└──────────────────────┘         └──────────────────────┘         └──────────────────────┘
```

## Data Flow Diagram

### Phase 1: Commission Tracking (Existing System)
```
┌─────────┐
│  BILL   │ Created by sales_rep
│ CREATED │
└────┬────┘
     │
     ▼
┌─────────────────────┐
│ Django Signal Fires │
└────┬────────────────┘
     │
     ▼
┌──────────────────────────┐
│ CommissionTransaction    │
│ created automatically    │
│                          │
│ • transaction_type:      │
│   'bill_created'         │
│ • amount: bill total × % │
│ • rate: current rate     │
│ • running_balance: sum   │
└────┬─────────────────────┘
     │
     ▼
┌─────────────────────────┐
│ Sales Rep Commission    │
│ Balance Accumulates     │
└─────────────────────────┘

Similar flows for:
- Payment Received (adds commission)
- Return Processed (reduces commission)
- Write-off (adjusts commission)
```

### Phase 2: Payout Scheduling (New System)

#### Configuration (One-Time Setup)
```
┌───────────────┐
│ Office Staff  │
│ Logs In       │
└───────┬───────┘
        │
        ▼
┌──────────────────────────────┐
│ /sales/commissions/settings/ │
└───────┬──────────────────────┘
        │
        ▼
┌─────────────────────────────────────┐
│ Configure Schedule:                 │
│                                     │
│ Frequency: [Monthly ▼]             │
│ Day: [1 ▼]                         │
│ Time: [09:00]                      │
│ Minimum: [Rs. 500]                 │
│ Active: [✓]                        │
│                                     │
│ [Save Schedule]                     │
└───────┬─────────────────────────────┘
        │
        ▼
┌─────────────────────────────┐
│ CommissionPayoutSchedule    │
│ saved to database           │
│                             │
│ • frequency: 'monthly'      │
│ • payout_day_of_month: 1    │
│ • payout_time: 09:00        │
│ • minimum_payout: 500.00    │
│ • is_active: True           │
│ • next_run_date:            │
│   2026-02-01 09:00:00       │
└─────────────────────────────┘
```

#### Automated Execution (Recurring)
```
┌────────────────────────┐
│ Windows Task Scheduler │
│ Runs every 1 minute    │
└──────────┬─────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│ run_commission_payouts.bat           │
│                                      │
│ .\venv\Scripts\activate.bat          │
│ python manage.py                     │
│   process_commission_payouts         │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│ Management Command Checks:           │
│                                      │
│ Is there an active schedule?  ─────▶ No ─▶ Exit (do nothing)
│           │                          │
│           Yes                        │
│           │                          │
│           ▼                          │
│ Has next_run_date passed?     ─────▶ No ─▶ Exit (do nothing)
│           │                          │
│           Yes                        │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│ Get All Active Sales Reps            │
│                                      │
│ Query: User.objects.filter(          │
│   user_type='sales_rep',             │
│   is_active=True                     │
│ )                                    │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│ FOR EACH Sales Rep:                  │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│ Get Commission Balance               │
│                                      │
│ balance =                            │
│   CommissionTransaction              │
│   .get_rep_balance(user)             │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│ Check Minimum Threshold              │
│                                      │
│ if balance < minimum_payout_amount:  │
│   Skip user (log as skipped)         │
│ else:                                │
│   Continue to payout                 │
└──────────┬───────────────────────────┘
           │ balance >= minimum
           ▼
┌──────────────────────────────────────┐
│ Create Money Transaction             │
│                                      │
│ MoneyTransaction.objects.create(     │
│   user=user,                         │
│   transaction_type='credit',         │
│   money_type='commission_payment',   │
│   amount=balance,                    │
│   description='Automated...',        │
│   commission_reference='2026-01',    │
│   created_by=system                  │
│ )                                    │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│ Create User Payout Record            │
│                                      │
│ UserCommissionPayout.objects.create( │
│   history=history,                   │
│   user=user,                         │
│   commission_balance=balance,        │
│   amount_credited=balance,           │
│   money_transaction=transaction,     │
│   status='success'                   │
│ )                                    │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│ Update User Money Account            │
│                                      │
│ account.current_balance +=           │
│   transaction.amount                 │
│                                      │
│ (Calculated automatically via        │
│  aggregate queries)                  │
└──────────┬───────────────────────────┘
           │
           ▼ (After all users processed)
┌──────────────────────────────────────┐
│ Create Payout History Record         │
│                                      │
│ CommissionPayoutHistory.create(      │
│   schedule=schedule,                 │
│   execution_date=now(),              │
│   status='success',                  │
│   total_users_processed=3,           │
│   total_amount_credited=2500.00,     │
│   successful_payouts=3,              │
│   failed_payouts=0,                  │
│   skipped_payouts=2,                 │
│   duration_seconds=0.5               │
│ )                                    │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│ Calculate Next Run Date              │
│                                      │
│ schedule.calculate_next_run_date()   │
│ schedule.next_run_date =             │
│   2026-03-01 09:00:00                │
│ schedule.last_run_date = now()       │
│ schedule.save()                      │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│ Console Output:                      │
│                                      │
│ ✓ User: john_doe (Rs. 1,250.00)     │
│ ○ User: jane (Rs. 400) - Below min  │
│ ✓ User: bob_jones (Rs. 850.00)      │
│                                      │
│ Summary:                             │
│ Total Users: 3                       │
│ Total Amount: Rs. 2,500.00           │
│ Next run: 2026-03-01 09:00:00        │
└──────────────────────────────────────┘
```

## Database Schema Relationships

```
┌──────────────────────────────┐
│ CommissionPayoutSchedule     │
│ (Singleton - only 1 active)  │
│                              │
│ PK: id                       │
│ • frequency                  │
│ • payout_day_of_month        │
│ • payout_time                │
│ • minimum_payout_amount      │
│ • is_active                  │
│ • next_run_date              │
│ • last_run_date              │
└──────────┬───────────────────┘
           │
           │ 1:N
           ▼
┌──────────────────────────────┐
│ CommissionPayoutHistory      │
│ (Execution logs)             │
│                              │
│ PK: id                       │
│ FK: schedule_id              │
│ • execution_date             │
│ • status                     │
│ • total_users_processed      │
│ • total_amount_credited      │
│ • successful_payouts         │
│ • failed_payouts             │
│ • skipped_payouts            │
│ • period_start               │
│ • period_end                 │
│ • duration_seconds           │
│ • details (JSON)             │
└──────────┬───────────────────┘
           │
           │ 1:N
           ▼
┌──────────────────────────────┐         ┌──────────────────────────────┐
│ UserCommissionPayout         │    FK   │ User (accounts.User)         │
│ (Individual user records)    │────────▶│                              │
│                              │         │ PK: id                       │
│ PK: id                       │         │ • username                   │
│ FK: history_id               │         │ • user_type                  │
│ FK: user_id                  │◀────────│ • is_active                  │
│ FK: money_transaction_id     │         └──────────────────────────────┘
│ • commission_balance         │                      │
│ • amount_credited            │                      │ 1:N
│ • status                     │                      ▼
│ • error_message              │         ┌──────────────────────────────┐
└──────────┬───────────────────┘         │ UserMoneyAccount             │
           │                             │                              │
           │ FK                          │ PK: id                       │
           ▼                             │ FK: user (OneToOne)          │
┌──────────────────────────────┐         │ • opening_balance            │
│ MoneyTransaction             │         │ (balance calculated via      │
│ (accounts.MoneyTransaction)  │         │  aggregates)                 │
│                              │         └──────────────────────────────┘
│ PK: id                       │                      ▲
│ FK: user_id                  │                      │
│ • transaction_type (credit)  │──────────────────────┘ 1:N
│ • money_type                 │
│   ('commission_payment')     │
│ • amount                     │
│ • description                │
│ • commission_reference       │
│ • transaction_date           │
│ • created_by                 │
└──────────────────────────────┘
```

## User Interface Flow

### Office Staff - Configuration
```
┌────────────────────────────────────────────────────────────┐
│ Commission Settings Page                                   │
│ /sales/commissions/settings/                               │
├────────────────────────────────────────────────────────────┤
│                                                            │
│ ┌─ Automated Payout Schedule ─────────────────────────┐   │
│ │                                                      │   │
│ │ Status: ● Active - Next: Feb 01, 2026 09:00 AM     │   │
│ │                                                      │   │
│ │ Frequency: [Monthly ▼]      Day: [1 ▼]             │   │
│ │ Time: [09:00]               Minimum: [Rs. 500]      │   │
│ │                                                      │   │
│ │ [✓] Enable Automatic Payouts                        │   │
│ │                                                      │   │
│ │ [Save Schedule]              Last Run: Jan 01 09:00 │   │
│ └──────────────────────────────────────────────────────┘   │
│                                                            │
│ ┌─ Payout History ─────────────────────────────────────┐   │
│ │ Date          Status    Users  Amount               │   │
│ │ Jan 27 09:00  Success   3      Rs. 2,500.00        │   │
│ │ Jan 01 09:00  Partial   2      Rs. 1,800.00        │   │
│ │ Dec 15 09:00  Success   5      Rs. 4,200.00        │   │
│ └──────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────┘
```

### Sales Rep - Money Account View
```
┌────────────────────────────────────────────────────────────┐
│ My Money Account                                           │
│ /accounts/money-account/                                   │
├────────────────────────────────────────────────────────────┤
│                                                            │
│ Balance Due: Rs. 7,500.00                                 │
│                                                            │
│ ┌─ This Month ──────────────────────────────────────────┐  │
│ │ Earned:    Rs. 5,500.00  (Commission + Manual)        │  │
│ │ Paid:      Rs. 1,000.00  (Disbursements)              │  │
│ │ Advances:  Rs. 5,000.00  (Advance Drawn)              │  │
│ │ ─────────────────────────────────────────────────────  │  │
│ │ Net:      -Rs. 500.00                                 │  │
│ └───────────────────────────────────────────────────────┘  │
│                                                            │
│ ┌─ Recent Transactions ─────────────────────────────────┐  │
│ │ Jan 27  Commission Payment      +Rs. 2,500.00         │  │
│ │ Jan 25  Advance Drawn           -Rs. 3,000.00         │  │
│ │ Jan 15  Manual Credit           +Rs. 1,500.00         │  │
│ │ Jan 10  Disbursement            -Rs. 1,000.00         │  │
│ │ Jan 01  Commission Payment      +Rs. 1,500.00         │  │
│ └───────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

## Frequency Options Explained

### Monthly (Day 1-28 or Last Day)
```
January    February   March      April
  1         1          1          1     ← Runs on these dates at 09:00
 ...       ...        ...        ...
 28        28         28         28
 29 ←──────────────────────────────────── If day=0, uses last day
 30
 31 ←─── Runs here    29/28      30
```

### Weekly (Every Monday)
```
Week 1: Monday Jan 05, 09:00
Week 2: Monday Jan 12, 09:00
Week 3: Monday Jan 19, 09:00
Week 4: Monday Jan 26, 09:00
Week 5: Monday Feb 02, 09:00
...
```

### Bi-weekly (1st & 15th)
```
January:  1st at 09:00, 15th at 09:00
February: 1st at 09:00, 15th at 09:00
March:    1st at 09:00, 15th at 09:00
...
```

## Money Flow Example

### Before Payout (Jan 31, 2026)
```
┌─────────────────────────────────┐
│ Sales Rep: John Doe             │
├─────────────────────────────────┤
│ Commission Balance: Rs. 5,500   │ ← From CommissionTransaction
│ Money Account Balance: Rs. 2,000│ ← From MoneyTransaction
└─────────────────────────────────┘
```

### Payout Execution (Feb 01, 2026 09:00)
```
┌─────────────────────────────────────────────────────┐
│ process_commission_payouts executes                 │
├─────────────────────────────────────────────────────┤
│ 1. Get balance: Rs. 5,500                          │
│ 2. Check minimum: Rs. 5,500 >= Rs. 500 ✓           │
│ 3. Create MoneyTransaction:                        │
│    - Type: commission_payment                      │
│    - Amount: Rs. 5,500                             │
│ 4. Create UserCommissionPayout record              │
│ 5. Link to CommissionPayoutHistory                 │
└─────────────────────────────────────────────────────┘
```

### After Payout (Feb 01, 2026 09:00:01)
```
┌─────────────────────────────────┐
│ Sales Rep: John Doe             │
├─────────────────────────────────┤
│ Commission Balance: Rs. 0       │ ← Still tracked for new commissions
│ Money Account Balance: Rs. 7,500│ ← Rs. 2,000 + Rs. 5,500 (CREDITED!)
└─────────────────────────────────┘

Sales rep can now:
• Request advances against Rs. 7,500
• Receive disbursements
• See increased "Balance Due"
```

## Error Handling Flow

```
┌─────────────────────────┐
│ Execute Payout for User │
└──────────┬──────────────┘
           │
     ┌─────▼─────┐
     │ Try:      │
     └─────┬─────┘
           │
           ▼
┌──────────────────────────┐
│ Create MoneyTransaction  │
└──────────┬───────────────┘
           │
     ┌─────▼─────┐
     │ Success?  │
     └─────┬─────┘
           │
      ┌────┴────┐
      │         │
     Yes       No
      │         │
      ▼         ▼
┌──────────┐  ┌──────────────────────┐
│ Status:  │  │ Status: 'failed'     │
│ success  │  │ error_message: str   │
└──────────┘  │ Log to history       │
              │ Continue to next user│
              └──────────────────────┘

After all users:
┌────────────────────────────┐
│ If any failed:             │
│   history.status='partial' │
│ Elif all skipped:          │
│   history.status='skipped' │
│ Else:                      │
│   history.status='success' │
└────────────────────────────┘
```

## Task Scheduler Integration

```
┌─────────────────────────────────────────────────────────┐
│ Windows Task Scheduler                                  │
├─────────────────────────────────────────────────────────┤
│ Task Name: Commission Payout Processor                  │
│ Trigger:   Daily at 12:00 AM                           │
│            Repeat every 1 minute                        │
│            For a duration of: Indefinitely              │
│                                                         │
│ Action:    Start a Program                             │
│ Program:   C:\...\run_commission_payouts.bat           │
│                                                         │
│ Conditions: Run whether user logged on or not          │
│             Run with highest privileges                 │
│             Don't stop if on batteries                  │
│                                                         │
│ Settings:  Allow task to run on demand                 │
│            Run as soon as possible if missed           │
└─────────────────────────────────────────────────────────┘
```

## Security & Audit Trail

```
┌────────────────────────────────────────────────────────────────┐
│ Audit Trail Components                                         │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│ 1. CommissionPayoutHistory                                    │
│    • When: execution_date                                     │
│    • Who: schedule configuration (set by office staff)        │
│    • What: Total users, amounts, status                       │
│    • How long: duration_seconds                               │
│                                                                │
│ 2. UserCommissionPayout                                       │
│    • Which user received payout                               │
│    • How much: commission_balance → amount_credited           │
│    • Links to specific MoneyTransaction                       │
│    • Status: success/failed/skipped                           │
│                                                                │
│ 3. MoneyTransaction                                           │
│    • Immutable record of credit                               │
│    • Description: "Automated Commission Payout - monthly"     │
│    • Commission reference: "2026-01"                          │
│    • Created by: system user                                  │
│    • Timestamp: transaction_date                              │
│                                                                │
│ Complete trail: Schedule → History → UserPayout → Transaction │
│ Can trace any payout back to original configuration           │
└────────────────────────────────────────────────────────────────┘
```

---

**Version**: 1.0  
**Created**: January 27, 2026  
**Purpose**: Visual reference for commission payout automation architecture
