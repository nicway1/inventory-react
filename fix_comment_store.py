#!/usr/bin/env python
# Script to fix comments by syncing the comment store with the database

from utils.store_instances import comment_store, db_manager
from models.comment import Comment
import json
import os
from datetime import datetime

def fix_comment_store():
    print("\n=== FIXING COMMENT STORE ===\n")
    
    # Get all comments from the database
    db_session = db_manager.get_session()
    try:
        db_comments = db_session.query(Comment).all()
        print(f"Found {len(db_comments)} comments in the database")
        
        # Clear existing comments in the store
        comment_store.comments = {}
        
        # Add all database comments to the store
        for db_comment in db_comments:
            print(f"Adding comment ID {db_comment.id} for ticket {db_comment.ticket_id}")
            comment_store.comments[db_comment.id] = db_comment
        
        # Save the updated comments
        comment_store.save_comments()
        print(f"\nSuccessfully synchronized {len(comment_store.comments)} comments")
        
    except Exception as e:
        print(f"Error syncing comments: {e}")
    finally:
        db_session.close()
    
    print("\n=== SYNC COMPLETE ===\n")

if __name__ == "__main__":
    fix_comment_store() 