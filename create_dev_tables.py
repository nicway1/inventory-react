#!/usr/bin/env python3
"""
Database migration script for Feature/Bug/Release management system.
Creates tables for the development workflow management.
"""

import os
import sys
from sqlalchemy import create_engine, text
from datetime import datetime

# Add the current directory to the path so we can import our models
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import engine, SessionLocal
from models.base import Base
from models.feature_request import FeatureRequest, FeatureComment
from models.bug_report import BugReport, BugComment
from models.release import Release
from models.changelog_entry import ChangelogEntry

def create_development_tables():
    """Create all development-related tables"""
    print("Creating development management tables...")

    try:
        # Create all tables defined in our models
        Base.metadata.create_all(bind=engine, checkfirst=True)

        print("✅ Successfully created development tables:")
        print("   - feature_requests")
        print("   - feature_comments")
        print("   - bug_reports")
        print("   - bug_comments")
        print("   - releases")
        print("   - changelog_entries")

        return True

    except Exception as e:
        print(f"❌ Error creating tables: {str(e)}")
        return False

def verify_tables():
    """Verify that all tables were created successfully"""
    print("\nVerifying table creation...")

    db_session = SessionLocal()
    try:
        # Test each table by running a simple query
        tables_to_check = [
            ('feature_requests', 'SELECT COUNT(*) FROM feature_requests'),
            ('feature_comments', 'SELECT COUNT(*) FROM feature_comments'),
            ('bug_reports', 'SELECT COUNT(*) FROM bug_reports'),
            ('bug_comments', 'SELECT COUNT(*) FROM bug_comments'),
            ('releases', 'SELECT COUNT(*) FROM releases'),
            ('changelog_entries', 'SELECT COUNT(*) FROM changelog_entries')
        ]

        all_tables_exist = True
        for table_name, query in tables_to_check:
            try:
                result = db_session.execute(text(query))
                count = result.fetchone()[0]
                print(f"✅ {table_name}: {count} records")
            except Exception as e:
                print(f"❌ {table_name}: Error - {str(e)}")
                all_tables_exist = False

        return all_tables_exist

    finally:
        db_session.close()

def create_sample_data():
    """Create some sample data for testing"""
    print("\nCreating sample data...")

    db_session = SessionLocal()
    try:
        # Check if we already have data
        if db_session.query(Release).count() > 0:
            print("Sample data already exists, skipping...")
            return True

        # Create a sample release
        release = Release(
            version="1.0.0",
            name="Initial Development System",
            description="First release of the Feature/Bug/Release management system",
            release_type="MINOR",
            status="PLANNING",
            planned_date=datetime.now().date()
        )
        db_session.add(release)
        db_session.flush()  # Get the ID

        # Create a sample feature
        feature = FeatureRequest(
            title="Development Dashboard",
            description="Create a comprehensive dashboard for tracking development progress",
            priority="HIGH",
            component="development",
            requester_id=1,  # Assuming user ID 1 exists
            target_release_id=release.id,
            business_value="Critical",
            estimated_effort="Large"
        )
        db_session.add(feature)

        # Create a sample bug
        bug = BugReport(
            title="Navigation menu not displaying correctly",
            description="The development navigation menu overlaps with other content on mobile devices",
            severity="MEDIUM",
            priority="HIGH",
            component="navigation",
            environment="production",
            reporter_id=1,  # Assuming user ID 1 exists
            steps_to_reproduce="1. Open app on mobile\n2. Navigate to development section\n3. Menu overlaps content"
        )
        db_session.add(bug)

        db_session.commit()
        print("✅ Sample data created successfully")
        return True

    except Exception as e:
        db_session.rollback()
        print(f"❌ Error creating sample data: {str(e)}")
        print("Note: This might be due to missing user records, which is normal for a fresh install")
        return True  # Don't fail the migration for sample data issues

    finally:
        db_session.close()

def main():
    """Main migration function"""
    print("🚀 Starting Development System Database Migration")
    print("=" * 50)

    # Step 1: Create tables
    if not create_development_tables():
        print("\n❌ Migration failed at table creation step")
        return False

    # Step 2: Verify tables
    if not verify_tables():
        print("\n❌ Migration failed at table verification step")
        return False

    # Step 3: Create sample data (optional, won't fail migration if it errors)
    create_sample_data()

    print("\n" + "=" * 50)
    print("🎉 Development System Migration Complete!")
    print("\nYou can now:")
    print("1. Access the development dashboard at /development/dashboard")
    print("2. Create feature requests at /development/features/new")
    print("3. Report bugs at /development/bugs/new")
    print("4. Manage releases at /development/releases")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)