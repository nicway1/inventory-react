#!/usr/bin/env python
# Diagnostic script for comments functionality

from utils.store_instances import comment_store, db_manager
from models.ticket import Ticket
from models.comment import Comment
import json
import os

def diagnose_comments():
    print("\n=== COMMENTS DIAGNOSTIC ===\n")
    
    # Check if comments file exists
    comments_file = 'data/comments.json'
    print(f"1. Checking if comments file exists: {os.path.exists(comments_file)}")
    
    # Check content of comments file
    if os.path.exists(comments_file):
        try:
            with open(comments_file, 'r') as f:
                comments_data = json.load(f)
                print(f"2. Comments file contains {len(comments_data)} comments")
                if comments_data:
                    print(f"   First comment: {comments_data[0]}")
        except Exception as e:
            print(f"2. Error reading comments file: {e}")
    else:
        print("2. Comments file does not exist")
    
    # Check comment_store
    print(f"\n3. CommentStore contains {len(comment_store.comments)} comments")
    if comment_store.comments:
        print(f"   First comment key: {list(comment_store.comments.keys())[0]}")
    
    # Check tickets in database
    db_session = db_manager.get_session()
    try:
        tickets = db_session.query(Ticket).all()
        print(f"\n4. Database has {len(tickets)} tickets")
        
        if tickets:
            # Check first ticket
            ticket = tickets[0]
            print(f"   First ticket ID: {ticket.id}")
            
            # Check comments in DB for first ticket
            db_comments = db_session.query(Comment).filter(Comment.ticket_id == ticket.id).all()
            print(f"   Ticket {ticket.id} has {len(db_comments)} comments in the database")
            
            # Check relationship
            if hasattr(ticket, 'comments'):
                rel_comments = ticket.comments
                print(f"   Ticket {ticket.id} has {len(rel_comments) if rel_comments else 0} comments via relationship")
            else:
                print(f"   Ticket {ticket.id} does not have a 'comments' relationship attribute")
            
            # Check comments from store
            store_comments = comment_store.get_ticket_comments(ticket.id)
            print(f"   Ticket {ticket.id} has {len(store_comments)} comments via comment_store")
    except Exception as e:
        print(f"\nError checking database: {e}")
    finally:
        db_session.close()
    
    print("\n=== END DIAGNOSTIC ===\n")

if __name__ == "__main__":
    diagnose_comments() 