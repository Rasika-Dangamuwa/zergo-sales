"""Final UI Verification for Settlement Status Migration"""
import os

print("=== SETTLEMENT STATUS UI VERIFICATION ===\n")

# Check bill_list.html for correct labels
bill_list_path = r"c:\Users\LENOVO\Desktop\My Projects\zergo_distributors_sales_app\templates\sales\bill_list.html"

with open(bill_list_path, 'r', encoding='utf-8') as f:
    content = f.read()

print("1. Checking Filter Tab Labels...")
if 'Unsettled</a>' in content:
    print("   ✓ 'Unsettled' filter tab found")
else:
    print("   ✗ 'Unsettled' filter tab NOT found - still shows 'Unpaid'")

if 'Partially Settled</a>' in content:
    print("   ✓ 'Partially Settled' filter tab found")
else:
    print("   ✗ 'Partially Settled' filter tab NOT found - still shows 'Partial'")

if 'Settled</a>' in content:
    print("   ✓ 'Settled' filter tab found (checking context...)")
    # Make sure it's the settlement filter, not status
    if 'settlement_status=settled' in content:
        print("   ✓ Confirmed: Filter tab for settlement_status=settled")
    else:
        print("   ⚠ Warning: Found 'Settled' but not in settlement_status context")
else:
    print("   ✗ 'Settled' filter tab NOT found - still shows 'Paid'")

print("\n2. Checking Table Header...")
if '<th>Settlement</th>' in content:
    print("   ✓ Table header shows 'Settlement'")
elif '<th>Payment</th>' in content:
    print("   ✗ Table header still shows 'Payment' - NOT UPDATED")
else:
    print("   ⚠ Table header not found")

print("\n3. Checking Desktop View Status Badges...")
desktop_section = content[content.find('<table class="table">'):content.find('<!-- Mobile Cards Container')]

if 'Settled</span>' in desktop_section and 'settlement_status' in desktop_section:
    print("   ✓ 'Settled' badge found in desktop view")
else:
    print("   ✗ 'Settled' badge NOT found - still shows 'Paid'")

if 'Partially Settled</span>' in desktop_section:
    print("   ✓ 'Partially Settled' badge found in desktop view")
else:
    print("   ✗ 'Partially Settled' badge NOT found - still shows 'Partial'")

if 'Unsettled</span>' in desktop_section:
    print("   ✓ 'Unsettled' badge found in desktop view")
else:
    print("   ✗ 'Unsettled' badge NOT found - still shows 'Unpaid'")

print("\n4. Checking Mobile View Status Badges...")
mobile_section = content[content.find('<!-- Mobile Cards Container'):] if '<!-- Mobile Cards Container' in content else content

if 'Settled</span>' in mobile_section and 'card-badges' in mobile_section:
    print("   ✓ 'Settled' badge found in mobile view")
else:
    print("   ✗ Mobile view 'Settled' badge issue")

if 'Partially Settled</span>' in mobile_section and 'card-badges' in mobile_section:
    print("   ✓ 'Partially Settled' badge found in mobile view")
else:
    print("   ✗ Mobile view 'Partially Settled' badge issue")

if 'Unsettled</span>' in mobile_section and 'card-badges' in mobile_section:
    print("   ✓ 'Unsettled' badge found in mobile view")
else:
    print("   ✗ Mobile view 'Unsettled' badge issue")

print("\n5. Checking for Old Terminology (Should NOT exist)...")
old_terms_found = []

if '>Unpaid</' in content and 'filter-tab' in content:
    old_terms_found.append("'Unpaid' in filter tabs")

if '>Partial</' in content and 'filter-tab' in content:
    old_terms_found.append("'Partial' in filter tabs")

if '>Paid</' in content and 'settlement_status' in content:
    old_terms_found.append("'Paid' in settlement context")

if old_terms_found:
    print("   ✗ OLD TERMINOLOGY STILL EXISTS:")
    for term in old_terms_found:
        print(f"     - {term}")
else:
    print("   ✓ No old terminology found")

print("\n=== VERIFICATION SUMMARY ===")
print("\nIf all checks show ✓, the template is correctly updated.")
print("\nNext steps:")
print("1. Hard refresh browser (Ctrl+Shift+R or Ctrl+F5)")
print("2. Clear browser cache")
print("3. Check Django server is running with latest code")
print("4. Navigate to: http://127.0.0.1:8000/sales/")
print("\nExpected result:")
print("- Filter tabs: 'Unsettled', 'Partially Settled', 'Settled'")
print("- Table column: 'Settlement' (not 'Payment')")
print("- Status badges: 'Unsettled', 'Partially Settled', 'Settled'")
