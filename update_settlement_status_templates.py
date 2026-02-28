"""
World-Class Settlement Status Template Updater
Updates all templates to use settlement_status instead of payment_status
"""

import os
import re

# Define replacements
REPLACEMENTS = [
    # URL parameters
    ('payment_status=pending', 'settlement_status=unsettled'),
    ('payment_status=partial', 'settlement_status=partial_settled'),
    ('payment_status=paid', 'settlement_status=settled'),
    ('payment_status=unpaid', 'settlement_status=unsettled'),
    
    # Variable names in templates
    ('request.GET.payment_status', 'request.GET.settlement_status'),
    ('bill.payment_status', 'bill.settlement_status'),
    ('sale.payment_status', 'sale.settlement_status'),
    ('commission.payment_status', 'commission.settlement_status'),
    ('commission_record.payment_status', 'commission_record.settlement_status'),
    
    # Method calls
    ('get_payment_status_display', 'get_settlement_status_display'),
    
    # Value comparisons in conditionals
    (" == 'paid'", " == 'settled'"),
    (" == 'partial'", " == 'partial_settled'"),
    (" == 'unpaid'", " == 'unsettled'"),
    (" == 'pending'", " == 'unsettled'"),  # Legacy value used in some places
    
    # CSS classes
    ('payment-{{ bill.settlement_status', 'settlement-{{ bill.settlement_status'),  # After first replacement
    ('status-{{ bill.settlement_status', 'settlement-{{ bill.settlement_status'),  # Normalize class names
]

def update_template_file(filepath):
    """Update a single template file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        modified = False
        
        for old, new in REPLACEMENTS:
            if old in content:
                content = content.replace(old, new)
                modified = True
        
        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ Updated: {filepath}")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"✗ Error updating {filepath}: {str(e)}")
        return False

def main():
    """Update all template files"""
    templates_dir = r'c:\Users\LENOVO\Desktop\My Projects\zergo_distributors_sales_app\templates'
    
    # Only update production templates (exclude backup files)
    exclude_patterns = ['_backup', '_old', '_previous', '_OLD', '_worldclass', '_improved']
    
    updated_count = 0
    total_count = 0
    
    for root, dirs, files in os.walk(templates_dir):
        for filename in files:
            if filename.endswith('.html'):
                # Skip backup/old files
                skip = False
                for pattern in exclude_patterns:
                    if pattern.lower() in filename.lower() or pattern.lower() in root.lower():
                        skip = True
                        break
                
                if skip:
                    continue
                
                filepath = os.path.join(root, filename)
                total_count += 1
                
                if update_template_file(filepath):
                    updated_count += 1
    
    print(f"\n{'='*60}")
    print(f"TEMPLATE UPDATE COMPLETE")
    print(f"{'='*60}")
    print(f"Total templates processed: {total_count}")
    print(f"Templates updated: {updated_count}")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
