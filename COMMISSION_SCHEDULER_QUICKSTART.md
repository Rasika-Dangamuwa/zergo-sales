# Commission Payout Scheduler - Quick Setup Guide

## What This Does
Automatically credits commission balances to user money accounts at scheduled intervals (monthly, weekly, bi-weekly, or custom dates).

## Quick Start (5 Minutes)

### 1. Configure the Schedule

1. **Login** as admin or office staff
2. **Navigate** to: http://127.0.0.1:8000/sales/commissions/settings/
3. **Scroll** to "Automated Payout Schedule" section
4. **Set**:
   - **Frequency**: Monthly (recommended to start)
   - **Day of Month**: 1 (first day of each month)
   - **Payout Time**: 09:00
   - **Minimum Amount**: Rs. 500 (adjust based on your needs)
   - **Enable**: ✓ Checked
5. **Click** "Save Schedule"
6. **Verify**: "Next Payout" shows the correct date/time

### 2. Test with Dry-Run

Open PowerShell and run:

```powershell
cd "c:\Users\LENOVO\Desktop\My Projects\zergo_distributors_sales_app"
.\venv\Scripts\python.exe manage.py process_commission_payouts --dry-run
```

This shows what would happen without actually creating transactions.

### 3. Setup Windows Task Scheduler

**Option A: Quick Setup (Recommended)**

1. Open Task Scheduler (Win + R → `taskschd.msc`)
2. Click "Create Basic Task"
3. **Name**: "Commission Payout Processor"
4. **Trigger**: Daily at 12:00 AM
5. **Action**: Start a program
6. **Program**: Browse to `run_commission_payouts.bat` in your project folder
7. Click Finish

**Option B: Advanced Setup (Every Minute)**

After creating the basic task above:
1. Right-click the task → Properties
2. **Triggers tab** → Edit → Advanced settings:
   - ✓ Repeat task every: **1 minute**
   - For a duration of: **Indefinitely**
3. **Conditions tab**:
   - ✗ Uncheck "Start only if on AC power"
4. **Settings tab**:
   - ✓ Run task as soon as possible if missed
   - ✓ Allow task to run on demand
5. Click OK

### 4. Test It Works

Force an immediate payout to test:

```powershell
.\venv\Scripts\python.exe manage.py process_commission_payouts --force
```

Then check:
1. Commission Settings page → Payout History table (should show 1 new execution)
2. Money Account Dashboard → This Month → Earned (should include commission amount)

## How It Works

```
┌─────────────────────┐
│ Commission Tracking │ ← Bills, Payments, Returns create commission transactions
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Payout Scheduler    │ ← Runs every minute via Windows Task Scheduler
│ (Management Command)│    Checks if it's time to execute
└──────────┬──────────┘
           │
           ▼
    ┌──────────┐
    │ Is it    │ No → Exit (do nothing)
    │ time?    │
    └────┬─────┘
         │ Yes
         ▼
┌─────────────────────┐
│ Get all sales reps  │
│ with commissions    │
└──────────┬──────────┘
           │
           ▼
    ┌──────────────┐
    │ For each user│
    └──────┬───────┘
           │
           ▼
    ┌──────────────────┐
    │ Balance >=       │ No → Skip user
    │ Minimum?         │
    └────┬─────────────┘
         │ Yes
         ▼
┌─────────────────────┐
│ Create Money        │ ← Credits to user's money account
│ Transaction         │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Log Payout History  │ ← Audit trail
└─────────────────────┘
```

## Frequency Options Explained

### Monthly
- Runs on a specific day each month (1-28 or Last Day)
- Example: Day 15 → 15th of every month at 09:00 AM
- Example: Last Day → Jan 31, Feb 28/29, Mar 31, Apr 30, etc.

### Weekly
- Every Monday at the specified time
- Good for frequent payouts

### Bi-weekly
- 1st and 15th of every month
- Common payroll schedule

### Custom
- Set your own next run date/time
- For one-off or irregular payouts

## Money Flow Example

**Before Payout**:
- Commission Balance: Rs. 5,500
- Money Account Balance Due: Rs. 2,000

**After Payout** (monthly on 1st at 09:00):
- Commission Balance: Rs. 0 (reset)
- Money Account Balance Due: Rs. 7,500 (Rs. 2,000 + Rs. 5,500)
- Money Transaction Created: "Automated Commission Payout - monthly"

## Common Scenarios

### Scenario 1: Monthly Payouts on Last Day
- **Frequency**: Monthly
- **Day**: Last Day (0)
- **Time**: 17:00 (5 PM)
- **Minimum**: Rs. 1,000
- **Result**: Runs on Jan 31, Feb 28, Mar 31, Apr 30, etc. at 5 PM. Only pays users with Rs. 1,000+ balance.

### Scenario 2: Weekly Payouts
- **Frequency**: Weekly
- **Time**: 09:00
- **Minimum**: Rs. 0 (no minimum)
- **Result**: Every Monday at 9 AM, pays all users regardless of amount.

### Scenario 3: Bi-weekly Payouts
- **Frequency**: Bi-weekly
- **Time**: 12:00 (Noon)
- **Minimum**: Rs. 500
- **Result**: 1st and 15th of every month at noon. Skips users below Rs. 500.

## Safety Features

✅ **No Duplicates**: Even if Windows Task Scheduler runs it 1000 times, only executes once per schedule
✅ **Dry-Run Mode**: Test changes without affecting data
✅ **Minimum Threshold**: Prevents tiny transactions
✅ **Audit Trail**: Complete history of all payouts
✅ **Rollback**: If anything fails, entire payout is cancelled (atomic)
✅ **Timezone Aware**: Uses Asia/Colombo timezone

## Monitoring

### Check Schedule Status
Visit: http://127.0.0.1:8000/sales/commissions/settings/

Look for:
- **Status**: Active or Inactive
- **Next Payout**: When it will run next
- **Last Run**: When it last executed

### View Payout History
Same page, scroll to "Payout History" table:
- **Success** (green): All users paid successfully
- **Partial** (yellow): Some users paid, some failed
- **Failed** (red): None paid (check errors)
- **Skipped** (gray): No users met minimum threshold

## Troubleshooting

**Problem**: "No active payout schedules found"
- ✓ Solution: Enable the schedule (check "Enable Automatic Payouts" and save)

**Problem**: Schedule not executing
- ✓ Check Windows Task Scheduler is enabled
- ✓ Verify the batch file path is correct
- ✓ Check if trigger is set to repeat every 1 minute

**Problem**: Users not getting paid
- ✓ Check commission balance: http://127.0.0.1:8000/sales/commissions/
- ✓ Verify balance exceeds minimum threshold
- ✓ Ensure user is active (is_active=True)

**Problem**: Payout history shows "Failed"
- ✓ Run with `--dry-run` to see error messages
- ✓ Check if users have money accounts created
- ✓ Review Django logs for exceptions

## Advanced Usage

### Force Immediate Payout
Ignore schedule and pay right now:
```powershell
.\venv\Scripts\python.exe manage.py process_commission_payouts --force
```

### Test Specific Schedule
If you have multiple schedules (future):
```powershell
.\venv\Scripts\python.exe manage.py process_commission_payouts --schedule-id 1
```

### View Help
```powershell
.\venv\Scripts\python.exe manage.py process_commission_payouts --help
```

## Next Steps

1. ✅ Configure your first schedule
2. ✅ Test with dry-run mode
3. ✅ Setup Windows Task Scheduler
4. ✅ Force a test payout
5. ✅ Verify money accounts updated
6. ✅ Monitor payout history weekly

## Need Help?

Refer to the full documentation: [COMMISSION_PAYOUT_SCHEDULER.md](COMMISSION_PAYOUT_SCHEDULER.md)

---

**Setup Time**: 5 minutes  
**Maintenance**: Check weekly  
**Support**: Review payout history for issues
