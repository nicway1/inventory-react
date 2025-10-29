#!/usr/bin/env python3
"""
Migration script to create feature_tester_assignments table
"""

from sqlalchemy import create_engine, text
from utils.db_manager import DatabaseManager
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_feature_testers():
    """Create feature_tester_assignments table"""
    try:
        # Get database connection
        db_manager = DatabaseManager()
        engine = db_manager.engine

        logger.info("Creating feature_tester_assignments table...")

        with engine.begin() as conn:
            if 'mysql' in str(engine.url):
                # MySQL syntax
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS feature_tester_assignments (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        feature_id INT NOT NULL,
                        tester_id INT NOT NULL,
                        assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        notified VARCHAR(10) DEFAULT 'No',
                        notified_at DATETIME,
                        test_status VARCHAR(20) DEFAULT 'Pending',
                        test_notes TEXT,
                        tested_at DATETIME,
                        FOREIGN KEY (feature_id) REFERENCES feature_requests(id) ON DELETE CASCADE,
                        FOREIGN KEY (tester_id) REFERENCES testers(id) ON DELETE CASCADE,
                        INDEX idx_feature_tester_feature_id (feature_id),
                        INDEX idx_feature_tester_tester_id (tester_id),
                        INDEX idx_feature_tester_status (test_status)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """))
            else:
                # SQLite syntax
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS feature_tester_assignments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        feature_id INTEGER NOT NULL,
                        tester_id INTEGER NOT NULL,
                        assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        notified VARCHAR(10) DEFAULT 'No',
                        notified_at DATETIME,
                        test_status VARCHAR(20) DEFAULT 'Pending',
                        test_notes TEXT,
                        tested_at DATETIME,
                        FOREIGN KEY (feature_id) REFERENCES feature_requests(id) ON DELETE CASCADE,
                        FOREIGN KEY (tester_id) REFERENCES testers(id) ON DELETE CASCADE
                    )
                """))

                # Create indexes for SQLite
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_feature_tester_feature_id ON feature_tester_assignments(feature_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_feature_tester_tester_id ON feature_tester_assignments(tester_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_feature_tester_status ON feature_tester_assignments(test_status)"))

            logger.info("✓ Successfully created feature_tester_assignments table")

        return True

    except Exception as e:
        # Check if table already exists
        if 'already exists' in str(e).lower():
            logger.info("✓ Table 'feature_tester_assignments' already exists")
            return True

        logger.error(f"✗ Error during migration: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys
    success = migrate_feature_testers()
    sys.exit(0 if success else 1)
