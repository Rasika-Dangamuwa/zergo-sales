"""
Django Management Command: Process Commission Payouts
Automatically credits commission balances to user money accounts

Usage:
    python manage.py process_commission_payouts
    python manage.py process_commission_payouts --dry-run
    python manage.py process_commission_payouts --force
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
from datetime import datetime, timedelta
import time
import json

from sales.commission_schedule_models import (
    CommissionPayoutSchedule,
    CommissionPayoutHistory,
    UserCommissionPayout
)
from sales.models import CommissionTransaction
from accounts.models import User
from accounts.money_account_models import UserMoneyAccount, MoneyTransaction


class Command(BaseCommand):
    help = 'Process scheduled commission payouts to user money accounts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate payout without creating transactions',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force payout even if not scheduled',
        )
        parser.add_argument(
            '--schedule-id',
            type=int,
            help='Process specific schedule by ID',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        schedule_id = options.get('schedule_id')
        
        self.stdout.write(self.style.SUCCESS(f'\n{"="*60}'))
        self.stdout.write(self.style.SUCCESS('Commission Payout Processor'))
        self.stdout.write(self.style.SUCCESS(f'{"="*60}'))
        self.stdout.write(f'Execution Time: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}')
        if dry_run:
            self.stdout.write(self.style.WARNING('*** DRY RUN MODE - No changes will be saved ***'))
        self.stdout.write('')

        # Get schedules to process
        if schedule_id:
            schedules = CommissionPayoutSchedule.objects.filter(id=schedule_id)
            if not schedules.exists():
                self.stdout.write(self.style.ERROR(f'Schedule with ID {schedule_id} not found'))
                return
        else:
            schedules = CommissionPayoutSchedule.objects.filter(is_active=True)

        if not schedules.exists():
            self.stdout.write(self.style.WARNING('No active payout schedules found'))
            return

        total_schedules_processed = 0
        total_amount_credited = Decimal('0.00')
        total_users_credited = 0

        for schedule in schedules:
            self.stdout.write(f'\nProcessing Schedule: {schedule}')
            self.stdout.write(f'Frequency: {schedule.get_frequency_display()}')
            self.stdout.write(f'Next Run: {schedule.next_run_date}')
            
            # Check if should run
            now = timezone.now()
            should_run = force or (schedule.next_run_date and schedule.next_run_date <= now)
            
            if not should_run:
                self.stdout.write(self.style.WARNING(f'  → Skipping - not yet scheduled (next run: {schedule.next_run_date})'))
                continue
            
            self.stdout.write(self.style.SUCCESS('  → Processing payout...'))
            
            # Execute payout
            start_time = time.time()
            result = self.execute_payout(schedule, dry_run)
            duration = int(time.time() - start_time)
            
            # Display results
            self.stdout.write(f'  ✓ Completed in {duration}s')
            self.stdout.write(f'  - Users processed: {result["users_processed"]}')
            self.stdout.write(f'  - Successful: {result["successful"]}')
            self.stdout.write(f'  - Failed: {result["failed"]}')
            self.stdout.write(f'  - Skipped: {result["skipped"]}')
            self.stdout.write(f'  - Total credited: Rs. {result["total_amount"]:,.2f}')
            
            total_schedules_processed += 1
            total_amount_credited += result["total_amount"]
            total_users_credited += result["successful"]
            
            # Update schedule next run date
            if not dry_run:
                schedule.last_run_date = now
                schedule.next_run_date = schedule.calculate_next_run_date()
                schedule.save()
                self.stdout.write(f'  - Next scheduled: {schedule.next_run_date}')

        # Summary
        self.stdout.write(f'\n{"="*60}')
        self.stdout.write(self.style.SUCCESS('Execution Summary'))
        self.stdout.write(f'{"="*60}')
        self.stdout.write(f'Schedules Processed: {total_schedules_processed}')
        self.stdout.write(f'Total Users Credited: {total_users_credited}')
        self.stdout.write(f'Total Amount: Rs. {total_amount_credited:,.2f}')
        self.stdout.write(f'{"="*60}\n')

    def execute_payout(self, schedule, dry_run=False):
        """
        Execute payout for a single schedule
        Returns dict with execution results
        """
        result = {
            "users_processed": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "total_amount": Decimal('0.00'),
            "details": []
        }
        
        # Create history record
        history = CommissionPayoutHistory(
            schedule=schedule,
            status='success',
            period_start=timezone.localdate() - timedelta(days=30),
            period_end=timezone.localdate()
        )
        
        # Get all users with commission balances
        users_with_commissions = User.objects.filter(
            commission_transactions__isnull=False
        ).distinct()
        
        for user in users_with_commissions:
            result["users_processed"] += 1
            
            try:
                # Get current commission balance
                balance = CommissionTransaction.get_rep_balance(user)
                
                # Check minimum threshold
                if balance < schedule.minimum_payout_amount:
                    result["skipped"] += 1
                    result["details"].append({
                        "user": user.get_full_name(),
                        "status": "skipped",
                        "reason": f"Below minimum ({balance} < {schedule.minimum_payout_amount})",
                        "balance": str(balance)
                    })
                    continue
                
                if balance <= Decimal('0.00'):
                    result["skipped"] += 1
                    continue
                
                # Create payout
                if not dry_run:
                    with transaction.atomic():
                        # Get or create money account
                        money_account, _ = UserMoneyAccount.objects.get_or_create(
                            user=user,
                            defaults={'created_by': user}
                        )
                        
                        # Create money transaction
                        money_txn = MoneyTransaction.objects.create(
                            account=money_account,
                            transaction_type='commission_payment',
                            amount=balance,
                            description=f'Automated Commission Payout - {schedule.get_frequency_display()}',
                            commission_reference=f'{timezone.now().strftime("%Y-%m")}',
                            notes=f'Auto-credited from commission balance. Schedule ID: {schedule.id}',
                            created_by=schedule.created_by or user
                        )
                        
                        # CRITICAL: Create CommissionTransaction to clear the commission balance
                        # This debits the commission (negative amount) to zero out the running balance
                        CommissionTransaction.objects.create(
                            transaction_type='adjustment',
                            transaction_date=timezone.now(),
                            sales_rep=user,
                            applicable_rate=Decimal('0.00'),
                            commission_earned=-balance,  # NEGATIVE to debit/clear balance
                            notes=f'Commission cleared - Automated payout (Schedule ID: {schedule.id})',
                            bill=None,
                            settlement=None,
                            return_ref=None
                        )
                        
                        # Record user payout
                        UserCommissionPayout.objects.create(
                            history=history,
                            user=user,
                            commission_balance=balance,
                            amount_credited=balance,
                            money_transaction=money_txn,
                            status='success'
                        )
                
                result["successful"] += 1
                result["total_amount"] += balance
                result["details"].append({
                    "user": user.get_full_name(),
                    "status": "success",
                    "amount": str(balance)
                })
                
                self.stdout.write(f'    ✓ {user.get_full_name()}: Rs. {balance:,.2f}')
                
            except Exception as e:
                result["failed"] += 1
                result["details"].append({
                    "user": user.get_full_name(),
                    "status": "failed",
                    "error": str(e)
                })
                self.stdout.write(self.style.ERROR(f'    ✗ {user.get_full_name()}: {str(e)}'))
        
        # Save history
        if not dry_run:
            history.total_users_processed = result["users_processed"]
            history.total_amount_credited = result["total_amount"]
            history.successful_payouts = result["successful"]
            history.failed_payouts = result["failed"]
            history.skipped_payouts = result["skipped"]
            history.details = json.dumps(result["details"], indent=2)
            history.duration_seconds = 0  # Will be updated by caller
            
            if result["failed"] > 0:
                history.status = 'partial' if result["successful"] > 0 else 'failed'
            elif result["successful"] == 0:
                history.status = 'skipped'
            else:
                history.status = 'success'
            
            history.save()
        
        return result
