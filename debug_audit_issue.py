#!/usr/bin/env python3

import sys
import os
sys.path.append('/Users/user/invK/inventory')

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from models.asset import Asset
from models.user import User, UserType
from utils.db_manager import DatabaseManager

def debug_audit_issue():
    """Debug the audit total asset count issue"""
    print("=== Debugging Audit Issue ===")
    
    # Initialize database manager
    db_manager = DatabaseManager()
    session = db_manager.get_session()
    
    try:
        # 1. Check total assets in database
        total_assets = session.query(Asset).count()
        print(f"Total assets in database: {total_assets}")
        
        # 2. Check available countries
        countries_raw = session.query(Asset.country).distinct().filter(Asset.country.isnot(None), Asset.country != '').all()
        countries = [c[0] for c in countries_raw if c[0]]
        print(f"Available countries: {countries}")
        
        # 3. Check asset counts by country
        print("\nAssets by country:")
        for country in countries:
            count = session.query(Asset).filter(func.lower(Asset.country) == func.lower(country)).count()
            print(f"  {country}: {count} assets")
        
        # 4. Check sample assets
        sample_assets = session.query(Asset).limit(5).all()
        print(f"\nSample assets ({len(sample_assets)} shown):")
        for asset in sample_assets:
            print(f"  ID: {asset.id}, Tag: {asset.asset_tag}, Country: {asset.country}, Company: {asset.company_id}")
        
        # 5. Check users and their types
        users = session.query(User).all()
        print(f"\nTotal users: {len(users)}")
        for user in users:
            print(f"  User: {user.username}, Type: {user.user_type}, Country: {user.assigned_country}, Company: {user.company_id}")
        
        # 6. Simulate the audit start query for different countries
        print("\nSimulating audit queries:")
        for country in countries[:3]:  # Test first 3 countries
            # Basic query (like Super Admin)
            basic_count = session.query(Asset).filter(func.lower(Asset.country) == func.lower(country)).count()
            print(f"  {country} - Basic query: {basic_count} assets")
            
            # Query with company filter (like Country Admin)
            company_counts = {}
            for company_id in [1, 2, None]:  # Test some company IDs
                company_count = session.query(Asset).filter(
                    func.lower(Asset.country) == func.lower(country),
                    Asset.company_id == company_id
                ).count()
                if company_count > 0:
                    company_counts[company_id] = company_count
            
            if company_counts:
                print(f"    With company filter: {company_counts}")
    
    except Exception as e:
        print(f"Error during debugging: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        session.close()

if __name__ == "__main__":
    debug_audit_issue()