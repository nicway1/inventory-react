#!/usr/bin/env python3

import sys
import os

# Add the project directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.db_manager import DatabaseManager
from models.queue import Queue

def check_and_create_firstbase_queue():
    """Check if FirstBase New Orders queue exists, create if missing"""
    
    db_manager = DatabaseManager()
    db_session = db_manager.get_session()
    
    try:
        print("🔍 Checking for FirstBase New Orders queue...")
        
        # Check if the queue exists
        firstbase_queue = db_session.query(Queue).filter(
            Queue.name == 'FirstBase New Orders'
        ).first()
        
        if firstbase_queue:
            print(f"✅ Queue found: {firstbase_queue.name} (ID: {firstbase_queue.id})")
            print(f"   Description: {firstbase_queue.description}")
        else:
            print("❌ FirstBase New Orders queue not found!")
            print("🔧 Creating FirstBase New Orders queue...")
            
            # Create the queue
            firstbase_queue = Queue(
                name='FirstBase New Orders',
                description='Queue for new order tickets imported from CSV'
            )
            db_session.add(firstbase_queue)
            db_session.commit()
            db_session.refresh(firstbase_queue)
            
            print(f"✅ Queue created successfully: {firstbase_queue.name} (ID: {firstbase_queue.id})")
        
        return firstbase_queue
        
    except Exception as e:
        db_session.rollback()
        print(f"❌ Error checking/creating queue: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        db_session.close()

def list_all_queues():
    """List all existing queues in the database"""
    
    db_manager = DatabaseManager()
    db_session = db_manager.get_session()
    
    try:
        print("\n📋 All queues in database:")
        
        queues = db_session.query(Queue).order_by(Queue.name).all()
        
        if not queues:
            print("   No queues found in database")
        else:
            for queue in queues:
                print(f"   - {queue.name} (ID: {queue.id})")
                if queue.description:
                    print(f"     Description: {queue.description}")
        
        print(f"\n📊 Total queues: {len(queues)}")
        
    except Exception as e:
        print(f"❌ Error listing queues: {e}")
    finally:
        db_session.close()

def main():
    """Main function"""
    print("🚀 FirstBase Queue Checker/Creator\n")
    
    # List all existing queues first
    list_all_queues()
    
    # Check and create FirstBase queue if needed
    queue = check_and_create_firstbase_queue()
    
    if queue:
        print(f"\n🎉 FirstBase New Orders queue is ready!")
        print(f"   Queue ID: {queue.id}")
        print(f"   Queue Name: {queue.name}")
    else:
        print(f"\n❌ Failed to ensure FirstBase New Orders queue exists")

if __name__ == '__main__':
    main() 