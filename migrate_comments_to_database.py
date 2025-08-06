#!/usr/bin/env python3
"""
Migration script to move comments from JSON file to database
Run this script ONCE to migrate existing comments from data/comments.json to the database
"""

import sys
import os
import json
from datetime import datetime

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def migrate_comments():
    """Migrate comments from JSON file to database"""
    
    try:
        from utils.store_instances import db_manager
        from models.comment import Comment
        from models.user import User
        from models.ticket import Ticket
        
        print("🚀 Starting migration of comments from JSON to database...")
        
        # Check if JSON file exists
        json_file = 'data/comments.json'
        if not os.path.exists(json_file):
            print(f"❌ JSON file {json_file} not found. No migration needed.")
            return
        
        # Load comments from JSON
        print(f"📖 Reading comments from {json_file}...")
        with open(json_file, 'r') as f:
            comments_data = json.load(f)
        
        print(f"📊 Found {len(comments_data)} comments to migrate")
        
        # Start database session
        db_session = db_manager.get_session()
        
        try:
            # Check if comments already exist in database
            existing_count = db_session.query(Comment).count()
            print(f"📊 Found {existing_count} existing comments in database")
            
            if existing_count > 0:
                response = input("⚠️  Comments already exist in database. Continue anyway? (y/N): ")
                if response.lower() != 'y':
                    print("❌ Migration cancelled by user")
                    return
            
            # Get valid ticket and user IDs from database
            valid_ticket_ids = set(t[0] for t in db_session.query(Ticket.id).all())
            valid_user_ids = set(u[0] for u in db_session.query(User.id).all())
            
            print(f"📊 Found {len(valid_ticket_ids)} valid tickets and {len(valid_user_ids)} valid users")
            
            # Migrate comments
            migrated_count = 0
            skipped_count = 0
            
            for comment_data in comments_data:
                try:
                    ticket_id = int(comment_data['ticket_id'])
                    user_id = int(comment_data['user_id'])
                    
                    # Skip if ticket or user doesn't exist
                    if ticket_id not in valid_ticket_ids:
                        print(f"⚠️  Skipping comment {comment_data['id']} - ticket {ticket_id} not found")
                        skipped_count += 1
                        continue
                    
                    if user_id not in valid_user_ids:
                        print(f"⚠️  Skipping comment {comment_data['id']} - user {user_id} not found")
                        skipped_count += 1
                        continue
                    
                    # Check if comment already exists (by original ID or content/ticket/user combination)
                    existing_comment = db_session.query(Comment).filter(
                        Comment.ticket_id == ticket_id,
                        Comment.user_id == user_id,
                        Comment.content == comment_data['content'],
                        Comment.created_at == datetime.fromisoformat(comment_data['created_at'])
                    ).first()
                    
                    if existing_comment:
                        skipped_count += 1
                        continue
                    
                    # Create new comment
                    comment = Comment(
                        ticket_id=ticket_id,
                        user_id=user_id,
                        content=comment_data['content']
                    )
                    
                    # Set the created_at from JSON data
                    comment.created_at = datetime.fromisoformat(comment_data['created_at'])
                    
                    db_session.add(comment)
                    migrated_count += 1
                    
                    if migrated_count % 50 == 0:
                        print(f"📊 Migrated {migrated_count} comments so far...")
                        
                except Exception as e:
                    print(f"❌ Error migrating comment {comment_data.get('id', 'unknown')}: {e}")
                    skipped_count += 1
                    continue
            
            # Commit all changes
            print("💾 Committing changes to database...")
            db_session.commit()
            
            print(f"✅ Migration completed successfully!")
            print(f"📊 Migration Summary:")
            print(f"   - Total comments in JSON: {len(comments_data)}")
            print(f"   - Successfully migrated: {migrated_count}")
            print(f"   - Skipped: {skipped_count}")
            
            # Backup the JSON file
            backup_file = f"{json_file}.migrated_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            os.rename(json_file, backup_file)
            print(f"📦 Original JSON file backed up to: {backup_file}")
            
            # Verify migration
            final_count = db_session.query(Comment).count()
            print(f"🔍 Verification: Database now contains {final_count} comments")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            db_session.rollback()
            raise
        
        finally:
            db_session.close()
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running this script from the application root directory")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    print("=" * 60)
    print("       COMMENT MIGRATION SCRIPT")
    print("       JSON to Database Migration")
    print("=" * 60)
    print()
    
    # Confirmation prompt
    print("⚠️  IMPORTANT: This script will migrate all comments from JSON to database.")
    print("⚠️  Make sure you have a backup of your database before proceeding.")
    print()
    
    response = input("Continue with migration? (y/N): ")
    if response.lower() != 'y':
        print("❌ Migration cancelled")
        sys.exit(0)
    
    migrate_comments()
    print()
    print("🎉 All done! Your comments are now stored in the database.")
    print("📝 The old JSON file has been renamed as a backup.")
    print("🚀 You can now deploy the updated application.")