#!/usr/bin/env python
"""
Script to reverse a specific accessory transaction and fix inventory quantity
"""

from models.base import Base
from models.accessory import Accessory
from models.accessory_transaction import AccessoryTransaction
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Database connection
engine = create_engine('sqlite:///inventory.db')
Session = sessionmaker(bind=engine)
session = Session()

def reverse_transaction(transaction_number):
    """Reverse a specific transaction by its transaction number"""

    # Find the transaction
    transaction = session.query(AccessoryTransaction).filter(
        AccessoryTransaction.transaction_number == transaction_number
    ).first()

    if not transaction:
        print(f"❌ Transaction {transaction_number} not found!")
        return False

    print(f"Found transaction:")
    print(f"  Transaction #: {transaction.transaction_number}")
    print(f"  Type: {transaction.transaction_type}")
    print(f"  Accessory ID: {transaction.accessory_id}")
    print(f"  Quantity: {transaction.quantity}")
    print(f"  Notes: {transaction.notes}")
    print()

    # Get the accessory
    accessory = session.query(Accessory).filter(
        Accessory.id == transaction.accessory_id
    ).first()

    if not accessory:
        print(f"❌ Accessory ID {transaction.accessory_id} not found!")
        return False

    print(f"Current accessory state:")
    print(f"  Name: {accessory.name}")
    print(f"  Current Available Quantity: {accessory.available_quantity}")
    print()

    # Calculate the reversal
    # This was an OUT transaction that incorrectly decreased inventory
    # We need to ADD back the quantity
    reversal_quantity = transaction.quantity
    new_quantity = accessory.available_quantity + reversal_quantity

    print(f"Reversal calculation:")
    print(f"  Current quantity: {accessory.available_quantity}")
    print(f"  Adding back: +{reversal_quantity}")
    print(f"  New quantity will be: {new_quantity}")
    print()

    # Ask for confirmation
    confirm = input("Do you want to proceed with this reversal? (yes/no): ")

    if confirm.lower() != 'yes':
        print("❌ Reversal cancelled.")
        session.close()
        return False

    try:
        # Update the accessory quantity
        old_quantity = accessory.available_quantity
        accessory.available_quantity = new_quantity

        # Create a reversal transaction record
        reversal_transaction = AccessoryTransaction(
            accessory_id=accessory.id,
            transaction_type="Transaction Reversal",
            quantity=reversal_quantity,
            transaction_number=f"REV-{transaction_number}",
            user_id=transaction.user_id,
            notes=f"Reversal of incorrect transaction {transaction_number}. Added {reversal_quantity} back to inventory."
        )
        session.add(reversal_transaction)

        # Commit the changes
        session.commit()

        print()
        print("✅ Transaction reversed successfully!")
        print(f"  Accessory: {accessory.name}")
        print(f"  Previous quantity: {old_quantity}")
        print(f"  New quantity: {accessory.available_quantity}")
        print(f"  Reversal transaction created: REV-{transaction_number}")

        return True

    except Exception as e:
        session.rollback()
        print(f"❌ Error during reversal: {str(e)}")
        return False
    finally:
        session.close()

if __name__ == "__main__":
    print("=" * 60)
    print("Accessory Transaction Reversal Tool")
    print("=" * 60)
    print()

    # The specific transaction to reverse
    transaction_number = "OUT-821-78-1763441669"

    print(f"Reversing transaction: {transaction_number}")
    print()

    reverse_transaction(transaction_number)

    print()
    print("=" * 60)
