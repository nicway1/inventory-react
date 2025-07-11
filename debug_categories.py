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
    
    logger.info("=== TICKET CATEGORIES DEBUG ===")
    logger.info("Total categories found: {len(list(TicketCategory))}")
    print()
    
    logger.info("All available ticket categories:")
    for i, category in enumerate(TicketCategory, 1):
        marker = "✅ FOUND!" if category.name == 'ASSET_RETURN_CLAW' else ""
        logger.info("{i:2d}. {category.name:<25} = '{category.value}' {marker}")
    
    print()
    
    # Check specifically for ASSET_RETURN_CLAW
    try:
        asset_return_claw = TicketCategory.ASSET_RETURN_CLAW
        logger.info("✅ ASSET_RETURN_CLAW found:")
        logger.info("   - Name: {asset_return_claw.name}")
        logger.info("   - Value: '{asset_return_claw.value}'")
        logger.info("   - Can be used in forms: YES")
    except AttributeError:
        logger.info("❌ ASSET_RETURN_CLAW NOT FOUND in TicketCategory enum!")
    
    logger.info("\n=== TESTING ENUM ACCESS ===")
    test_cases = [
        ('ASSET_RETURN_CLAW', 'TicketCategory.ASSET_RETURN_CLAW'),
        ('ASSET_CHECKOUT_CLAW', 'TicketCategory.ASSET_CHECKOUT_CLAW'),
        ('ASSET_INTAKE', 'TicketCategory.ASSET_INTAKE')
    ]
    
    for case_name, case_code in test_cases:
        try:
            result = eval(case_code)
            logger.info("✅ {case_name}: {result.value}")
        except Exception as e:
            logger.info("❌ {case_name}: ERROR - {e}")

except ImportError as e:
    logger.info("❌ Error importing TicketCategory: {e}")
    logger.info("Make sure you're running this from the project root directory.")
except Exception as e:
    logger.info("❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc() 