#!/usr/bin/env python3
"""
Script to standardize country names in the database
Fixes case inconsistencies like 'PHILIPPINES' vs 'Philippines'
"""

import sqlite3
import os

def standardize_countries():
    """Standardize country names in the assets table"""
    
    db_path = "inventory.db"
    
    if not os.path.exists(db_path):
        print("❌ Database file not found. Skipping standardization.")
        return
    
    print("🔄 Starting country name standardization...")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all unique country names (including empty strings)
        cursor.execute("SELECT DISTINCT country FROM assets WHERE country IS NOT NULL")
        countries = cursor.fetchall()
        
        print(f"📊 Found {len(countries)} unique country entries:")
        for country in countries:
            print(f"  - '{country[0]}'")
        
        # Group countries by lowercase version to find duplicates
        country_groups = {}
        for country in countries:
            country_name = country[0].strip() if country[0] else ''
            # Skip empty countries for now
            if not country_name:
                continue
            lower_name = country_name.lower()
            if lower_name not in country_groups:
                country_groups[lower_name] = []
            country_groups[lower_name].append(country_name)
        
        # Find and fix duplicates and incorrect cases
        updates_made = 0
        for lower_name, variants in country_groups.items():
            # Choose the properly capitalized version (title case)
            proper_name = lower_name.title()
            
            # Handle special cases
            if lower_name == 'israel':
                proper_name = 'Israel'
            elif lower_name == 'philippines':
                proper_name = 'Philippines'
            elif lower_name == 'singapore':
                proper_name = 'Singapore'
            elif lower_name == 'australia':
                proper_name = 'Australia'
            elif lower_name == 'india':
                proper_name = 'India'
            
            # Check if any variant needs updating (including single variants with wrong case)
            needs_update = False
            for variant in variants:
                if variant != proper_name:
                    needs_update = True
                    break
            
            if needs_update:
                print(f"\n🔧 Standardizing '{lower_name}' variants:")
                for variant in variants:
                    if variant != proper_name:
                        print(f"  '{variant}' → '{proper_name}'")
                        cursor.execute(
                            "UPDATE assets SET country = ? WHERE country = ?",
                            (proper_name, variant)
                        )
                        updates_made += cursor.rowcount
        
        # Also update tickets table if it has country field
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tickets'")
            if cursor.fetchone():
                cursor.execute("PRAGMA table_info(tickets)")
                columns = [column[1] for column in cursor.fetchall()]
                if 'country' in columns:
                    print("\n🎫 Updating tickets table...")
                    for lower_name, variants in country_groups.items():
                        if len(variants) > 1:
                            proper_name = lower_name.title()
                            # Handle special cases
                            if lower_name == 'israel':
                                proper_name = 'Israel'
                            elif lower_name == 'philippines':
                                proper_name = 'Philippines'
                            elif lower_name == 'singapore':
                                proper_name = 'Singapore'
                            elif lower_name == 'australia':
                                proper_name = 'Australia'
                            elif lower_name == 'india':
                                proper_name = 'India'
                            
                            for variant in variants:
                                if variant != proper_name:
                                    cursor.execute(
                                        "UPDATE tickets SET country = ? WHERE country = ?",
                                        (proper_name, variant)
                                    )
                                    updates_made += cursor.rowcount
        except Exception as e:
            print(f"⚠️  Note: Could not update tickets table: {e}")
        
        # Also update accessories table if it has country field
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='accessories'")
            if cursor.fetchone():
                cursor.execute("PRAGMA table_info(accessories)")
                columns = [column[1] for column in cursor.fetchall()]
                if 'country' in columns:
                    print("\n📦 Updating accessories table...")
                    for lower_name, variants in country_groups.items():
                        if len(variants) > 1:
                            proper_name = lower_name.title()
                            # Handle special cases
                            if lower_name == 'israel':
                                proper_name = 'Israel'
                            elif lower_name == 'philippines':
                                proper_name = 'Philippines'
                            elif lower_name == 'singapore':
                                proper_name = 'Singapore'
                            elif lower_name == 'australia':
                                proper_name = 'Australia'
                            elif lower_name == 'india':
                                proper_name = 'India'
                            
                            for variant in variants:
                                if variant != proper_name:
                                    cursor.execute(
                                        "UPDATE accessories SET country = ? WHERE country = ?",
                                        (proper_name, variant)
                                    )
                                    updates_made += cursor.rowcount
        except Exception as e:
            print(f"⚠️  Note: Could not update accessories table: {e}")
        
        conn.commit()
        print(f"\n✅ Successfully standardized country names!")
        print(f"📊 Total updates made: {updates_made}")
        
        # Show final result
        cursor.execute("SELECT country, COUNT(*) as count FROM assets WHERE country IS NOT NULL GROUP BY country ORDER BY country")
        final_countries = cursor.fetchall()
        print(f"\n📋 Final country list ({len(final_countries)} countries):")
        for country, count in final_countries:
            print(f"  - {country}: {count} assets")
        
    except Exception as e:
        print(f"❌ Standardization failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    standardize_countries() 