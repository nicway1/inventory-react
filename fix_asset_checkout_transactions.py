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
    logger.info("🔧 Starting Asset Checkout Transaction Fix...")
    logger.info("=" * 60)
    
    db = SessionLocal()
    fixed_count = 0
    error_count = 0
    
    try:
        # Find all Asset Checkout (claw) tickets
        logger.info("📋 Finding Asset Checkout (claw) tickets...")
        claw_tickets = db.query(Ticket).filter(
            Ticket.category == TicketCategory.ASSET_CHECKOUT_CLAW
        ).all()
        
        logger.info("Found {len(claw_tickets)} Asset Checkout (claw) tickets")
        
        if not claw_tickets:
            logger.info("ℹ️  No Asset Checkout (claw) tickets found. Nothing to fix.")
            return
        
        logger.info("\n🔍 Checking for missing asset transactions...")
        
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
                            logger.info("🔧 Creating transaction for Asset {asset.asset_tag} from Ticket #{ticket.id}")
                            
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
                                logger.info("   💾 Saving batch... ({fixed_count} transactions created so far)")
                                try:
                                    db.commit()
                                except Exception as batch_error:
                                    logger.info("   ⚠️  Batch save error: {batch_error}")
                                    db.rollback()
                                    error_count += 1
                        else:
                            logger.info("✅ Transaction already exists for Asset {asset.asset_tag} from Ticket #{ticket.id}")
                            
            except Exception as e:
                logger.info("❌ Error processing ticket #{ticket.id}: {e}")
                error_count += 1
                continue
        
        # Final commit
        if fixed_count > 0:
            try:
                db.commit()
                logger.info("\n💾 Final save completed!")
            except Exception as final_error:
                logger.info("❌ Final save error: {final_error}")
                db.rollback()
                error_count += 1
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("🎉 Asset Transaction Fix Complete!")
        logger.info("✅ Created {fixed_count} missing asset transactions")
        if error_count > 0:
            logger.info("⚠️  Encountered {error_count} errors")
        else:
            logger.info("✨ No errors encountered!")
        logger.info("=" * 60)
        
        # Verify the fix
        logger.info("\n🔍 Verifying fix...")
        total_transactions = db.query(AssetTransaction).count()
        recent_transactions = db.query(AssetTransaction).filter(
            AssetTransaction.transaction_date >= datetime.utcnow() - timedelta(days=30)
        ).count()
        
        logger.info("📊 Total asset transactions: {total_transactions}")
        logger.info("📊 Transactions in last 30 days: {recent_transactions}")
        
        return {
            'fixed_count': fixed_count,
            'error_count': error_count,
            'total_transactions': total_transactions,
            'recent_transactions': recent_transactions
        }
        
    except Exception as e:
        logger.info("💥 Critical error: {e}")
        db.rollback()
        return None
    finally:
        db.close()

if __name__ == "__main__":
    logger.info("🚀 Asset Checkout Transaction Fixer")
    logger.info("This script will create missing asset transactions for Asset Checkout (claw) tickets")
    logger.info("")
    
    # Import timedelta here to avoid circular import
    from datetime import timedelta
    
    # Run the fix
    results = fix_missing_asset_transactions()
    
    if results:
        logger.info("\n📈 Results:")
        logger.info("   Fixed: {results['fixed_count']} transactions")
        logger.info("   Errors: {results['error_count']} errors")
        logger.info("   Total transactions now: {results['total_transactions']}")
        logger.info("   Recent transactions: {results['recent_transactions']}")
    
    logger.info("\n✨ Script completed!") 