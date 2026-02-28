import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from products.models import Company, CompanyAccount, CompanyTransaction

company = Company.objects.filter(company_name__icontains='Max').first()
account = company.account

print(f'\nCompany: {company.company_name}')
print(f'Opening Balance: Rs. {account.opening_balance:,.2f}')
print(f'Current Balance: Rs. {account.current_balance:,.2f}')
print(f'\nTransactions ({account.transactions.count()}):')

for i, txn in enumerate(account.transactions.all(), 1):
    print(f'  {i}. {txn.transaction_date.strftime("%Y-%m-%d")} | {txn.transaction_type:15} | {txn.reference_number:20} | Rs. {txn.amount:,.2f}')
    if txn.description:
        print(f'     Description: {txn.description}')
