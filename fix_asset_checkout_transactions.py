#!/usr/bin/env python3
"""
Fix missing asset transactions for Asset Checkout (claw) tickets
This script creates retroactive asset transactions for Asset Checkout (claw) tickets 
that don't have corresponding asset transaction records.

Usage: python3 fix_asset_checkout_transactions.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models.ticket import Ticket, TicketCategory
from models.asset_transaction import AssetTransaction
from models.asset import Asset
from models.user import User
from datetime import datetime
import time
import random

def fix_missing_asset_transactions():
    """Find and fix missing asset transactions for Asset Checkout (claw) tickets"""
    print("🔧 Starting Asset Checkout Transaction Fix...")
    print("=" * 60)
    
    db = SessionLocal()
    fixed_count = 0
    error_count = 0
    
    try:
        # Find all Asset Checkout (claw) tickets
        print("📋 Finding Asset Checkout (claw) tickets...")
        claw_tickets = db.query(Ticket).filter(
            Ticket.category == TicketCategory.ASSET_CHECKOUT_CLAW
        ).all()
        
        print(f"Found {len(claw_tickets)} Asset Checkout (claw) tickets")
        
        if not claw_tickets:
            print("ℹ️  No Asset Checkout (claw) tickets found. Nothing to fix.")
            return
        
        print("\n🔍 Checking for missing asset transactions...")
        
        for ticket in claw_tickets:
            try:
                # Check if ticket has associated assets via ticket_assets relationship
                if hasattr(ticket, 'assets') and ticket.assets:
                    for asset in ticket.assets:
                        # Check if there's already a transaction for this asset from this ticket timeframe
                        existing_transaction = db.query(AssetTransaction).filter(
                            AssetTransaction.asset_id == asset.id,
                            AssetTransaction.transaction_type == 'checkout',
                            AssetTransaction.transaction_date >= ticket.created_at,
                            AssetTransaction.transaction_date <= ticket.created_at + timedelta(hours=1)
                        ).first()
                        
                        if not existing_transaction:
                            print(f"🔧 Creating transaction for Asset {asset.asset_tag} from Ticket #{ticket.id}")
                            
                            # Create missing transaction with slight delay to avoid duplicates
                            time.sleep(0.01 + random.uniform(0, 0.02))
                            
                            transaction = AssetTransaction(
                                asset_id=asset.id,
                                transaction_type='checkout',
                                customer_id=ticket.customer_id,
                                notes=f'Retroactive transaction for Asset Checkout (claw) ticket #{ticket.id}',
                                transaction_date=ticket.created_at
                            )
                            # Set user_id after creation since it's not in __init__
                            transaction.user_id = ticket.requester_id
                            
                            db.add(transaction)
                            fixed_count += 1
                            
                            if fixed_count % 5 == 0:
                                print(f"   💾 Saving batch... ({fixed_count} transactions created so far)")
                                try:
                                    db.commit()
                                except Exception as batch_error:
                                    print(f"   ⚠️  Batch save error: {batch_error}")
                                    db.rollback()
                                    error_count += 1
                        else:
                            print(f"✅ Transaction already exists for Asset {asset.asset_tag} from Ticket #{ticket.id}")
                            
            except Exception as e:
                print(f"❌ Error processing ticket #{ticket.id}: {e}")
                error_count += 1
                continue
        
        # Final commit
        if fixed_count > 0:
            try:
                db.commit()
                print(f"\n💾 Final save completed!")
            except Exception as final_error:
                print(f"❌ Final save error: {final_error}")
                db.rollback()
                error_count += 1
        
        # Summary
        print("\n" + "=" * 60)
        print(f"🎉 Asset Transaction Fix Complete!")
        print(f"✅ Created {fixed_count} missing asset transactions")
        if error_count > 0:
            print(f"⚠️  Encountered {error_count} errors")
        else:
            print(f"✨ No errors encountered!")
        print("=" * 60)
        
        # Verify the fix
        print("\n🔍 Verifying fix...")
        total_transactions = db.query(AssetTransaction).count()
        recent_transactions = db.query(AssetTransaction).filter(
            AssetTransaction.transaction_date >= datetime.utcnow() - timedelta(days=30)
        ).count()
        
        print(f"📊 Total asset transactions: {total_transactions}")
        print(f"📊 Transactions in last 30 days: {recent_transactions}")
        
        return {
            'fixed_count': fixed_count,
            'error_count': error_count,
            'total_transactions': total_transactions,
            'recent_transactions': recent_transactions
        }
        
    except Exception as e:
        print(f"💥 Critical error: {e}")
        db.rollback()
        return None
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Asset Checkout Transaction Fixer")
    print("This script will create missing asset transactions for Asset Checkout (claw) tickets")
    print("")
    
    # Import timedelta here to avoid circular import
    from datetime import timedelta
    
    # Run the fix
    results = fix_missing_asset_transactions()
    
    if results:
        print(f"\n📈 Results:")
        print(f"   Fixed: {results['fixed_count']} transactions")
        print(f"   Errors: {results['error_count']} errors")
        print(f"   Total transactions now: {results['total_transactions']}")
        print(f"   Recent transactions: {results['recent_transactions']}")
    
    print("\n✨ Script completed!") 