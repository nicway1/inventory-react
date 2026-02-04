#!/usr/bin/env python3
"""
Quick script to check if user_category_permissions table exists and has data
Run this on PythonAnywhere after deploying to verify migration was run
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_migration():
    try:
        # Import database manager
        from utils.store_instances import db_manager

        db_session = db_manager.get_session()

        try:
            # Try to query the table
            from models.user_category_permission import UserCategoryPermission

            # Count total permissions
            total_count = db_session.query(UserCategoryPermission).count()

            print("=" * 60)
            print("✓ SUCCESS: user_category_permissions table EXISTS")
            print("=" * 60)
            print(f"Total permissions in database: {total_count}")

            if total_count > 0:
                # Show some examples
                print("\nSample permissions:")
                perms = db_session.query(UserCategoryPermission).limit(10).all()
                for perm in perms:
                    print(f"  - User ID {perm.user_id}: {perm.category_key}")
            else:
                print("\n⚠ WARNING: Table exists but has NO permissions!")
                print("Users with SUPERVISOR/COUNTRY_ADMIN role will see NO categories.")
                print("Go to /admin/users/{user_id}/edit to grant category permissions.")

            print("=" * 60)
            return True

        except Exception as e:
            print("=" * 60)
            print("✗ ERROR: user_category_permissions table DOES NOT EXIST")
            print("=" * 60)
            print(f"Error: {str(e)}")
            print("\nYou need to run the migration:")
            print("  python3 migrations/add_category_permissions.py")
            print("=" * 60)
            return False

        finally:
            db_session.close()

    except Exception as e:
        print("=" * 60)
        print("✗ ERROR: Failed to connect to database")
        print("=" * 60)
        print(f"Error: {str(e)}")
        print("=" * 60)
        return False

if __name__ == "__main__":
    success = check_migration()
    sys.exit(0 if success else 1)
