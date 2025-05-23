#!/usr/bin/env python3

"""
Debug script to check if ASSET_RETURN_CLAW category is properly defined
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from models.ticket import TicketCategory
    
    print("=== TICKET CATEGORIES DEBUG ===")
    print(f"Total categories found: {len(list(TicketCategory))}")
    print()
    
    print("All available ticket categories:")
    for i, category in enumerate(TicketCategory, 1):
        marker = "✅ FOUND!" if category.name == 'ASSET_RETURN_CLAW' else ""
        print(f"{i:2d}. {category.name:<25} = '{category.value}' {marker}")
    
    print()
    
    # Check specifically for ASSET_RETURN_CLAW
    try:
        asset_return_claw = TicketCategory.ASSET_RETURN_CLAW
        print(f"✅ ASSET_RETURN_CLAW found:")
        print(f"   - Name: {asset_return_claw.name}")
        print(f"   - Value: '{asset_return_claw.value}'")
        print(f"   - Can be used in forms: YES")
    except AttributeError:
        print("❌ ASSET_RETURN_CLAW NOT FOUND in TicketCategory enum!")
    
    print("\n=== TESTING ENUM ACCESS ===")
    test_cases = [
        ('ASSET_RETURN_CLAW', 'TicketCategory.ASSET_RETURN_CLAW'),
        ('ASSET_CHECKOUT_CLAW', 'TicketCategory.ASSET_CHECKOUT_CLAW'),
        ('ASSET_INTAKE', 'TicketCategory.ASSET_INTAKE')
    ]
    
    for case_name, case_code in test_cases:
        try:
            result = eval(case_code)
            print(f"✅ {case_name}: {result.value}")
        except Exception as e:
            print(f"❌ {case_name}: ERROR - {e}")

except ImportError as e:
    print(f"❌ Error importing TicketCategory: {e}")
    print("Make sure you're running this from the project root directory.")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc() 