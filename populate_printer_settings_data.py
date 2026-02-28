"""
Populate sample data for printer settings (business profile and companies)
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from business.models import DistributorProfile
from products.models import Company

def populate_distributor_profile():
    """Update or create distributor profile with sample data"""
    profile, created = DistributorProfile.objects.get_or_create(
        is_active=True,
        defaults={
            'business_name': 'Zergo Distributors',
            'trade_name': 'Zergo Distributors',
            'tagline': 'Quality Products, Trusted Service',
            'description': 'Leading distributor of premium beverages in Sri Lanka',
            'business_type': 'distributor',
            
            # Contact Information
            'primary_phone': '+94 77 123 4567',
            'secondary_phone': '+94 77 765 4321',
            'mobile_phone': '+94 71 234 5678',
            'primary_email': 'info@zergodistributors.lk',
            'secondary_email': 'sales@zergodistributors.lk',
            'website': 'https://www.zergodistributors.lk',
            
            # Address
            'address_line1': '123 Main Street',
            'address_line2': 'Colombo 03',
            'city': 'Colombo',
            'district': 'Western Province',
            'postal_code': '00300',
            'country': 'Sri Lanka',
            
            # Business Registration
            'business_registration_number': 'BR123456789',
            'tax_id': 'TIN987654321',
            'vat_number': 'VAT123456789',
        }
    )
    
    if not created:
        # Update existing profile
        profile.business_name = 'Zergo Distributors'
        profile.tagline = 'Quality Products, Trusted Service'
        profile.primary_phone = '+94 77 123 4567'
        profile.primary_email = 'info@zergodistributors.lk'
        profile.website = 'https://www.zergodistributors.lk'
        profile.address_line1 = '123 Main Street, Colombo 03'
        profile.save()
        print("✅ Updated existing Distributor Profile")
    else:
        print("✅ Created new Distributor Profile")
    
    print(f"   Business Name: {profile.business_name}")
    print(f"   Tagline: {profile.tagline}")
    print(f"   Phone: {profile.primary_phone}")
    print(f"   Email: {profile.primary_email}")
    print(f"   Address: {profile.address_line1}")

def populate_companies():
    """Update existing companies with sample data"""
    
    # Get all existing companies
    companies = Company.objects.all()
    
    if not companies.exists():
        print("⚠️  No companies found in database")
        return
    
    updated_count = 0
    for company in companies:
        # Update with sample data if fields are empty
        if not company.tagline:
            company.tagline = f"Quality Beverages Since {company.created_at.year}"
        
        if not company.website:
            # Generate a sample website based on company name
            domain_name = company.company_name.lower().replace(' ', '').replace('(', '').replace(')', '').replace('.', '')
            company.website = f"https://www.{domain_name}.lk"
        
        company.save()
        
        print(f"✅ Updated {company.company_name} (ID: {company.id})")
        print(f"   Code: {company.company_code}")
        print(f"   Tagline: {company.tagline}")
        print(f"   Phone: {company.phone_number}")
        print(f"   Email: {company.email}")
        print(f"   Website: {company.website}")
        print()
        updated_count += 1
    
    print(f"✅ Updated {updated_count} companies")

if __name__ == '__main__':
    print("=" * 60)
    print("POPULATING PRINTER SETTINGS DATA")
    print("=" * 60)
    print()
    
    print("📋 Distributor Profile")
    print("-" * 60)
    populate_distributor_profile()
    print()
    
    print("📋 Companies")
    print("-" * 60)
    populate_companies()
    print()
    
    print("=" * 60)
    print("✅ DONE!")
    print("=" * 60)
    print()
    print("NOTE: You still need to upload logo_receipt images manually via:")
    print("  - Django Admin: /admin/business/distributorprofile/")
    print("  - Django Admin: /admin/products/company/")
