"""Check existing companies in database"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import Company

companies = Company.objects.all()
print(f"Found {companies.count()} companies:\n")
for company in companies:
    print(f"ID: {company.id}")
    print(f"  Name: {company.company_name}")
    print(f"  Code: {company.company_code}")
    print(f"  Tagline: {company.tagline or 'None'}")
    print(f"  Phone: {company.phone_number}")
    print(f"  Email: {company.email}")
    print(f"  Website: {company.website or 'None'}")
    print()
