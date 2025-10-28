"""
Migration to add test_case field to bug_reports and create tester tables
Run this with: python3 migrations/add_tester_test_case.py
"""

from database import engine, SessionLocal
from sqlalchemy import text

def migrate():
    """Run the migration"""
    session = SessionLocal()

    try:
        print("Starting migration...")

        # Add test_case column to bug_reports
        print("1. Adding test_case column to bug_reports table...")
        try:
            session.execute(text("""
                ALTER TABLE bug_reports
                ADD COLUMN test_case TEXT
            """))
            session.commit()
            print("   ✓ test_case column added")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("   - test_case column already exists, skipping")
                session.rollback()
            else:
                raise

        # Create testers table
        print("2. Creating testers table...")
        try:
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS testers (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL UNIQUE,
                    specialization VARCHAR(100),
                    is_active VARCHAR(10) DEFAULT 'Yes',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """))
            session.commit()
            print("   ✓ testers table created")
        except Exception as e:
            print(f"   - Error creating testers table: {e}")
            session.rollback()

        # Create bug_tester_assignments table
        print("3. Creating bug_tester_assignments table...")
        try:
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS bug_tester_assignments (
                    id INTEGER PRIMARY KEY,
                    bug_id INTEGER NOT NULL,
                    tester_id INTEGER NOT NULL,
                    assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    notified VARCHAR(10) DEFAULT 'No',
                    notified_at DATETIME,
                    test_status VARCHAR(20) DEFAULT 'Pending',
                    test_notes TEXT,
                    tested_at DATETIME,
                    FOREIGN KEY (bug_id) REFERENCES bug_reports(id),
                    FOREIGN KEY (tester_id) REFERENCES testers(id)
                )
            """))
            session.commit()
            print("   ✓ bug_tester_assignments table created")
        except Exception as e:
            print(f"   - Error creating bug_tester_assignments table: {e}")
            session.rollback()

        print("\nMigration completed successfully!")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    migrate()
