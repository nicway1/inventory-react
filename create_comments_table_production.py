#!/usr/bin/env python3
"""
Create comments table on production server
Run this BEFORE the migration script
"""

import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_comments_table():
    """Create comments table with proper schema"""
    
    try:
        from utils.store_instances import db_manager
        from sqlalchemy import text
        
        print("🔧 Creating comments table on production server...")
        
        # Get database session
        db_session = db_manager.get_session()
        
        try:
            # Drop existing comments table if it exists (to avoid conflicts)
            print("🗑️  Dropping any existing comments table...")
            db_session.execute(text("DROP TABLE IF EXISTS comments"))
            db_session.commit()
            
            # Create comments table with proper schema
            print("🔧 Creating comments table with correct schema...")
            create_table_sql = """
            CREATE TABLE comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content VARCHAR(2000) NOT NULL,
                ticket_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                created_at DATETIME,
                updated_at DATETIME,
                FOREIGN KEY(ticket_id) REFERENCES tickets(id),
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
            
            db_session.execute(text(create_table_sql))
            db_session.commit()
            
            # Verify table was created
            result = db_session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='comments'")).fetchone()
            
            if result:
                print("✅ Comments table created successfully!")
                
                # Check table structure
                columns = db_session.execute(text("PRAGMA table_info(comments)")).fetchall()
                print("📊 Table structure:")
                for col in columns:
                    print(f"   - {col[1]} ({col[2]})")
                
                # Verify content column exists
                content_col = [col for col in columns if col[1] == 'content']
                if content_col:
                    print("✅ Content column verified!")
                    return True
                else:
                    print("❌ Content column missing!")
                    return False
                
            else:
                print("❌ Comments table creation failed")
                return False
                
        except Exception as e:
            print(f"❌ Error creating table: {e}")
            db_session.rollback()
            return False
        finally:
            db_session.close()
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running this script from the application root directory")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 Production Database Setup: Comments Table")
    print("=" * 60)
    print()
    print("This script will create the comments table on your production server.")
    print("Run this BEFORE running the migration script.")
    print()
    
    success = create_comments_table()
    
    if success:
        print()
        print("🎉 Comments table created successfully!")
        print("📝 Now you can run: python3 migrate_comments_to_database.py")
    else:
        print()
        print("❌ Table creation failed. Please check the errors above.")
    
    print("=" * 60)