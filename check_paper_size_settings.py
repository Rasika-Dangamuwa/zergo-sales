"""Check print profile and paper size settings"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zergo_sales.settings')
django.setup()

from sales.print_manager import PrintManager
from sales.print_engine import UnifiedPrintEngine
from sales.paper_config import PaperSizeConfig
from django.contrib.auth import get_user_model

User = get_user_model()

# Get admin user (assuming you're logged in as admin)
user = User.objects.filter(username='admin').first()
if not user:
    print("❌ Admin user not found, trying first user...")
    user = User.objects.first()

print(f"User: {user.username} ({user.get_full_name()})")
print()

# Get print profile
profile = PrintManager.get_user_default(user, 'bill')
print("📋 Print Profile Settings:")
print(f"  Paper Size: {profile.paper_size}")
print(f"  Printer Name: {profile.printer_name}")
print(f"  Use Distributor Profile: {profile.use_distributor_profile}")
print(f"  Company: {profile.company}")
print()

# Get paper specs
specs = PaperSizeConfig.get_specs(profile.paper_size)
print("📏 Paper Size Specifications:")
print(f"  Code: {specs.code}")
print(f"  Display Name: {specs.display_name}")
print(f"  Category: {specs.category}")
print(f"  Width: {specs.width_mm}mm ({specs.width_inch} inches)")
print(f"  Printable Width: {specs.printable_width_mm}mm")
print(f"  Characters per line (normal): {specs.chars_per_line_normal}")
print()

# Create print engine and get context
engine = UnifiedPrintEngine(user, receipt_type='bill')
context = engine.get_print_context({'test': 'data'})

print("📐 Context Values (what template receives):")
print(f"  paper_specs.width_mm: {context['paper_specs']['width_mm']}mm")
print(f"  fonts.header: {context['fonts']['header']}pt")
print(f"  fonts.body: {context['fonts']['body']}pt")
print(f"  fonts.footer: {context['fonts']['footer']}pt")
print(f"  logo.max_width: {context['logo']['max_width']}px")
print(f"  logo.max_height: {context['logo']['max_height']}px")
print(f"  margins.top: {context['margins']['top']}mm")
print(f"  margins.bottom: {context['margins']['bottom']}mm")
print(f"  margins.left: {context['margins']['left']}mm")
print(f"  margins.right: {context['margins']['right']}mm")
