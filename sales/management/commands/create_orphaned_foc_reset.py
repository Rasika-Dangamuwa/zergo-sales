"""
Management command to create a reset record for archived FOC transactions
that don't have a reset record.
"""
from django.core.management.base import BaseCommand
from django.db import transaction as db_transaction
from django.utils import timezone
from decimal import Decimal

from products.models import FOCValueTransaction
from sales.foc_reset_models import FOCReset, FOCResetTransaction
from accounts.models import User


class Command(BaseCommand):
    help = 'Create a reset record for orphaned archived FOC transactions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='User ID to assign as reset_by (default: first admin user)',
        )

    def handle(self, *args, **options):
        # Get archived transactions that don't have a reset
        archived_txns = FOCValueTransaction.objects.filter(is_archived=True)
        
        if not archived_txns.exists():
            self.stdout.write(self.style.WARNING('No archived transactions found'))
            return
        
        # Check if these transactions already have a reset
        existing_reset_txns = FOCResetTransaction.objects.filter(
            transaction_type__isnull=False
        )
        
        if existing_reset_txns.exists():
            self.stdout.write(self.style.WARNING(
                f'Found {existing_reset_txns.count()} transactions already in reset records'
            ))
            # Transactions already have a reset, nothing to do
            return
        
        self.stdout.write(self.style.SUCCESS(
            f'Found {archived_txns.count()} archived transactions without reset record'
        ))
        
        # Get user for reset_by
        user_id = options.get('user_id')
        if user_id:
            try:
                reset_by = User.objects.get(id=user_id)
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'User with ID {user_id} not found'))
                return
        else:
            # Get first admin user
            reset_by = User.objects.filter(user_type='admin').first()
            if not reset_by:
                self.stdout.write(self.style.ERROR('No admin user found'))
                return
        
        self.stdout.write(f'Creating reset record with user: {reset_by.get_full_name()}')
        
        try:
            with db_transaction.atomic():
                # Import aggregation functions
                from django.db.models import Sum, Q, Count
                
                # Calculate totals
                total_foc_received = archived_txns.filter(
                    transaction_type='foc_received'
                ).aggregate(total=Sum('foc_value'))['total'] or Decimal('0')
                
                total_foc_given = archived_txns.filter(
                    transaction_type__in=['foc_given', 'implicit_foc']
                ).aggregate(total=Sum('foc_value'))['total'] or Decimal('0')
                
                total_foc_returned = archived_txns.filter(
                    transaction_type='return_foc_restored'
                ).aggregate(total=Sum('foc_value'))['total'] or Decimal('0')
                
                net_foc_value = total_foc_received - total_foc_given + total_foc_returned
                
                # Build snapshots from archived transactions
                # Company accounts snapshot - calculate from transactions, not from FOCValueAccount
                company_summary = archived_txns.exclude(
                    foc_account__isnull=True
                ).values(
                    'foc_account__company__company_name'
                ).annotate(
                    foc_received=Sum('foc_value', filter=Q(transaction_type='foc_received')),
                    foc_given=Sum('foc_value', filter=Q(transaction_type__in=['foc_given', 'implicit_foc'])),
                    foc_returned=Sum('foc_value', filter=Q(transaction_type='return_foc_restored')),
                ).order_by('foc_account__company__company_name')
                
                company_accounts_data = []
                for comp in company_summary:
                    foc_received = float(comp['foc_received'] or 0)
                    foc_given = float(comp['foc_given'] or 0)
                    foc_returned = float(comp['foc_returned'] or 0)
                    net_value = foc_received - foc_given + foc_returned
                    utilization = (foc_given / foc_received * 100) if foc_received > 0 else 0
                    
                    company_accounts_data.append({
                        'company': comp['foc_account__company__company_name'],
                        'foc_received': foc_received,
                        'foc_given': foc_given,
                        'net_value': net_value,
                        'utilization': utilization,
                    })
                
                # Product summary snapshot
                product_summary = archived_txns.values(
                    'product__product_name',
                    'product__size',
                    'product__company__company_name'
                ).annotate(
                    foc_received_qty=Sum('foc_quantity', filter=Q(transaction_type='foc_received')),
                    foc_given_qty=Sum('foc_quantity', filter=Q(transaction_type='foc_given')),
                    foc_returned_qty=Sum('foc_quantity', filter=Q(transaction_type='return_foc_restored')),
                    foc_received_value=Sum('foc_value', filter=Q(transaction_type='foc_received')),
                    foc_given_value=Sum('foc_value', filter=Q(transaction_type='foc_given')),
                    implicit_foc_value=Sum('foc_value', filter=Q(transaction_type='implicit_foc')),
                    foc_returned_value=Sum('foc_value', filter=Q(transaction_type='return_foc_restored')),
                ).order_by('product__product_name')
                
                product_summary_data = [
                    {
                        'product': f"{p['product__product_name']} - {p['product__size']}" if p['product__size'] else p['product__product_name'],
                        'company': p['product__company__company_name'] or '',
                        'foc_received_qty': float(p['foc_received_qty'] or 0),
                        'foc_given_qty': float(p['foc_given_qty'] or 0),
                        'foc_returned_qty': float(p['foc_returned_qty'] or 0),
                        'foc_received_value': float(p['foc_received_value'] or 0),
                        'foc_given_value': float(p['foc_given_value'] or 0),
                        'implicit_foc_value': float(p['implicit_foc_value'] or 0),
                        'foc_returned_value': float(p['foc_returned_value'] or 0),
                    }
                    for p in product_summary
                ]
                
                # Sales rep summary snapshot
                sales_rep_summary = archived_txns.filter(
                    sales_rep__isnull=False
                ).values(
                    'sales_rep__first_name',
                    'sales_rep__last_name',
                    'sales_rep__username'
                ).annotate(
                    foc_given_qty=Sum('foc_quantity', filter=Q(transaction_type='foc_given')),
                    foc_returned_qty=Sum('foc_quantity', filter=Q(transaction_type='return_foc_restored')),
                    foc_given_value=Sum('foc_value', filter=Q(transaction_type='foc_given')),
                    implicit_foc_value=Sum('foc_value', filter=Q(transaction_type='implicit_foc')),
                    foc_returned_value=Sum('foc_value', filter=Q(transaction_type='return_foc_restored')),
                    bills_count=Count('bill_item_id', distinct=True)
                ).order_by('sales_rep__first_name')
                
                sales_rep_summary_data = [
                    {
                        'sales_rep': f"{s['sales_rep__first_name']} {s['sales_rep__last_name']}",
                        'foc_given_qty': float(s['foc_given_qty'] or 0),
                        'foc_returned_qty': float(s['foc_returned_qty'] or 0),
                        'foc_given_value': float(s['foc_given_value'] or 0),
                        'implicit_foc_value': float(s['implicit_foc_value'] or 0),
                        'foc_returned_value': float(s['foc_returned_value'] or 0),
                        'bills_count': s['bills_count'] or 0,
                    }
                    for s in sales_rep_summary
                ]
                
                # Transaction type breakdown
                txn_breakdown = archived_txns.values('transaction_type').annotate(
                    count=Count('id'),
                    total_value=Sum('foc_value')
                )
                
                transaction_breakdown_data = [
                    {
                        'type': t['transaction_type'],
                        'count': t['count'],
                        'total_value': float(t['total_value'] or 0),
                    }
                    for t in txn_breakdown
                ]
                
                # Calculate average utilization from company data
                utilizations = [comp['utilization'] for comp in company_accounts_data if comp['foc_received'] > 0]
                avg_utilization = Decimal(str(sum(utilizations) / len(utilizations))) if utilizations else Decimal('0')
                
                # Create reset record
                reset = FOCReset.objects.create(
                    reset_by=reset_by,
                    reset_date=timezone.now(),
                    total_foc_received=total_foc_received,
                    total_foc_given=total_foc_given,
                    total_foc_returned=total_foc_returned,
                    net_foc_value=net_foc_value,
                    avg_utilization=avg_utilization,
                    total_transactions=archived_txns.count(),
                    total_products=archived_txns.values('product').distinct().count(),
                    total_sales_reps=archived_txns.filter(
                        sales_rep__isnull=False
                    ).values('sales_rep').distinct().count(),
                    company_accounts_snapshot=company_accounts_data,
                    product_summary_snapshot=product_summary_data,
                    sales_rep_summary_snapshot=sales_rep_summary_data,
                    transaction_types_breakdown=transaction_breakdown_data,
                    notes='Retroactively created for orphaned archived transactions'
                )
                
                # Archive transactions
                created_count = 0
                for txn in archived_txns:
                    # Get IDs for creating links
                    purchase_id = txn.purchase_item.purchase.id if txn.purchase_item and txn.purchase_item.purchase else None
                    bill_id = txn.bill_item.bill.id if txn.bill_item and txn.bill_item.bill else None
                    return_id = txn.return_item.return_ref.id if txn.return_item and txn.return_item.return_ref else None
                    
                    FOCResetTransaction.objects.create(
                        reset=reset,
                        transaction_type=txn.transaction_type,
                        transaction_date=txn.transaction_date,
                        company_name=txn.foc_account.company.company_name if txn.foc_account else '',
                        product_name=txn.product.product_name if txn.product else '',
                        product_size=txn.product.size if txn.product else '',
                        shop_name=txn.shop.shop_name if txn.shop else '',
                        sales_rep_name=f"{txn.sales_rep.first_name} {txn.sales_rep.last_name}" if txn.sales_rep else '',
                        foc_quantity=txn.foc_quantity,
                        shop_price_at_time=txn.shop_price_at_time,
                        foc_value=txn.foc_value,
                        reference_number=txn.reference_number,
                        notes=txn.notes or '',
                        purchase_id=purchase_id,
                        bill_id=bill_id,
                        return_id=return_id,
                    )
                    created_count += 1
                
                self.stdout.write(self.style.SUCCESS(
                    f'\n✅ Successfully created reset record: {reset.reset_number}'
                ))
                self.stdout.write(self.style.SUCCESS(
                    f'   - Archived {created_count} transactions'
                ))
                self.stdout.write(self.style.SUCCESS(
                    f'   - Total FOC Received: Rs. {total_foc_received:,.2f}'
                ))
                self.stdout.write(self.style.SUCCESS(
                    f'   - Total FOC Given: Rs. {total_foc_given:,.2f}'
                ))
                self.stdout.write(self.style.SUCCESS(
                    f'   - Net FOC Value: Rs. {net_foc_value:,.2f}'
                ))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            import traceback
            self.stdout.write(traceback.format_exc())
