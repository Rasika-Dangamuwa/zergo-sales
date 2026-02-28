"""
Commission System Deployment Verification Script
Run this after deployment to verify all components are working
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.models import CommissionTransaction, CommissionRateHistory
from django.contrib.auth import get_user_model
from django.db import connection

User = get_user_model()

def verify_database_constraints():
    """Verify database constraints are applied"""
    print("\n🔍 Verifying Database Constraints...")
    print("=" * 60)
    
    with connection.cursor() as cursor:
        # Check for unique constraints
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name LIKE 'unique_%commission%'
        """)
        unique_constraints = cursor.fetchall()
        
        # Check for indexes
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name LIKE 'idx_commission%'
        """)
        indexes = cursor.fetchall()
    
    print(f"✓ Unique Constraints: {len(unique_constraints)} found")
    for constraint in unique_constraints:
        print(f"  • {constraint[0]}")
    
    print(f"\n✓ Performance Indexes: {len(indexes)} found")
    for index in indexes:
        print(f"  • {index[0]}")
    
    return len(unique_constraints) >= 2 and len(indexes) >= 2


def verify_commission_models():
    """Verify commission models exist and are functional"""
    print("\n📊 Verifying Commission Models...")
    print("=" * 60)
    
    # Check CommissionRateHistory
    rate_count = CommissionRateHistory.objects.count()
    current_rate = CommissionRateHistory.get_current_rate()
    print(f"✓ CommissionRateHistory: {rate_count} rate(s) configured")
    print(f"  • Current Rate: {current_rate}%")
    
    # Check CommissionTransaction
    transaction_count = CommissionTransaction.objects.count()
    print(f"✓ CommissionTransaction: {transaction_count} transaction(s)")
    
    # Check transaction types
    types = CommissionTransaction.objects.values_list('transaction_type', flat=True).distinct()
    print(f"  • Transaction Types: {', '.join(types) if types else 'None yet'}")
    
    return True


def verify_sales_reps():
    """Verify sales reps exist in system"""
    print("\n👥 Verifying Sales Representatives...")
    print("=" * 60)
    
    sales_reps = User.objects.filter(user_type='sales_rep')
    print(f"✓ Found {sales_reps.count()} sales representative(s):")
    
    for rep in sales_reps[:5]:  # Show first 5
        transaction_count = CommissionTransaction.objects.filter(sales_rep=rep).count()
        balance = CommissionTransaction.objects.filter(sales_rep=rep).order_by('-transaction_date').first()
        balance_amount = balance.running_balance if balance else 0
        
        print(f"  • {rep.get_full_name()} - {transaction_count} transactions, Balance: Rs. {balance_amount:,.2f}")
    
    if sales_reps.count() > 5:
        print(f"  ... and {sales_reps.count() - 5} more")
    
    return sales_reps.exists()


def verify_url_routing():
    """Verify URL patterns are configured"""
    print("\n🌐 Verifying URL Routing...")
    print("=" * 60)
    
    from django.urls import reverse
    from django.urls.exceptions import NoReverseMatch
    
    urls_to_check = [
        ('sales:commission_dashboard', 'Commission Dashboard'),
        ('sales:export_commission_csv', 'CSV Export'),
        ('sales:export_commission_pdf', 'PDF Export'),
    ]
    
    all_valid = True
    for url_name, description in urls_to_check:
        try:
            url = reverse(url_name)
            print(f"✓ {description}: {url}")
        except NoReverseMatch:
            print(f"✗ {description}: NOT FOUND")
            all_valid = False
    
    return all_valid


def verify_reportlab():
    """Verify ReportLab is installed"""
    print("\n📄 Verifying PDF Generation Library...")
    print("=" * 60)
    
    try:
        import reportlab
        version = reportlab.Version
        print(f"✓ ReportLab {version} installed")
        return True
    except ImportError:
        print("✗ ReportLab NOT installed")
        print("  Run: pip install reportlab")
        return False


def main():
    """Run all verification checks"""
    print("\n" + "=" * 60)
    print("  COMMISSION SYSTEM DEPLOYMENT VERIFICATION")
    print("=" * 60)
    
    results = []
    
    # Run checks
    results.append(("Database Constraints", verify_database_constraints()))
    results.append(("Commission Models", verify_commission_models()))
    results.append(("Sales Representatives", verify_sales_reps()))
    results.append(("URL Routing", verify_url_routing()))
    results.append(("ReportLab Library", verify_reportlab()))
    
    # Summary
    print("\n" + "=" * 60)
    print("  VERIFICATION SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for check, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {check}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL CHECKS PASSED - System is ready for use!")
        print("\nNext Steps:")
        print("1. Start HTTPS server: .\\venv\\Scripts\\python.exe run_stable_https.py")
        print("2. Access dashboard: https://192.168.1.4:8000/sales/commissions/")
        print("3. Test CSV/PDF exports")
    else:
        print("⚠️  SOME CHECKS FAILED - Review errors above")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
