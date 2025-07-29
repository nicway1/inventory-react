#!/usr/bin/env python3

import sys
import os
sys.path.append('/Users/user/invK/inventory')

from sqlalchemy import func
from models.asset import Asset
from models.user import User, UserType
from utils.db_manager import DatabaseManager

def test_audit_start(user_type_str="SUPER_ADMIN", test_country="Singapore"):
    """Test the audit start logic for different user types"""
    print(f"=== Testing Audit Start for {user_type_str} on {test_country} ===")
    
    db_manager = DatabaseManager()
    session = db_manager.get_session()
    
    try:
        # Get a test user of the specified type
        user_type = getattr(UserType, user_type_str)
        user = session.query(User).filter(User.user_type == user_type).first()
        
        if not user:
            print(f"No user found with type {user_type_str}")
            return
        
        print(f"Testing with user: {user.username}")
        print(f"User type: {user.user_type}")
        print(f"User assigned country: {user.assigned_country}")
        print(f"User company: {user.company_id}")
        
        # Simulate the audit start logic from routes/inventory.py
        selected_country = test_country
        
        # Basic inventory query (case-insensitive)
        inventory_query = session.query(Asset).filter(func.lower(Asset.country) == func.lower(selected_country))
        
        # Apply additional filtering for Country Admin (like the actual code)
        if user.user_type == UserType.COUNTRY_ADMIN and user.company_id:
            print(f"Applying company filter: company_id = {user.company_id}")
            inventory_query = inventory_query.filter(Asset.company_id == user.company_id)
        
        inventory_assets = inventory_query.all()
        
        print(f"Query result: Found {len(inventory_assets)} assets for {selected_country}")
        
        if len(inventory_assets) == 0:
            # Debug: Check what assets exist for this country
            all_assets_in_country = session.query(Asset).filter(func.lower(Asset.country) == func.lower(selected_country)).all()
            print(f"Debug: Total assets in {selected_country} (ignoring company filter): {len(all_assets_in_country)}")
            
            if all_assets_in_country:
                print("Sample assets in this country:")
                for asset in all_assets_in_country[:5]:
                    print(f"  ID: {asset.id}, Tag: {asset.asset_tag}, Company: {asset.company_id}")
        
        # Test the audit session creation (simulated)
        audit_session = {
            'country': selected_country,
            'total_assets': len(inventory_assets),
            'scanned_assets': [],
            'missing_assets': [],
            'unexpected_assets': []
        }
        
        print(f"Audit session would be created with total_assets: {audit_session['total_assets']}")
        
        return audit_session
        
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        session.close()

def test_all_scenarios():
    """Test various scenarios"""
    scenarios = [
        ("SUPER_ADMIN", "Singapore"),
        ("SUPER_ADMIN", "Australia"),
        ("COUNTRY_ADMIN", "ISRAEL"),
        ("COUNTRY_ADMIN", "PHILIPPINES"),
        ("SUPERVISOR", "India")
    ]
    
    for user_type, country in scenarios:
        print()
        test_audit_start(user_type, country)
        print("-" * 50)

if __name__ == "__main__":
    test_all_scenarios()