#!/usr/bin/env python3
"""
Test script to verify accessory matching logic
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.db_manager import DatabaseManager
from models.accessory import Accessory
from sqlalchemy import or_

def test_accessory_matching():
    """Test accessory matching for USB-C Digital AV Multiport Adapter"""
    
    db_manager = DatabaseManager()
    db_session = db_manager.get_session()
    
    try:
        product_title = "USB-C Digital AV Multiport Adapter"
        logger.info("Testing accessory matching for: '{product_title}'")
        logger.info("=" * 60)
        
        # Test 1: Exact name matching
        logger.info("1. Testing exact name matching...")
        exact_matches = db_session.query(Accessory).filter(
            Accessory.name.ilike(f'%{product_title}%')
        ).all()
        
        logger.info("   Found {len(exact_matches)} exact matches:")
        for acc in exact_matches:
            logger.info("   - ID: {acc.id}, Name: {acc.name}, Available: {acc.available_quantity}")
        
        # Test 2: Fuzzy matching by terms
        logger.info("\n2. Testing fuzzy matching...")
        search_terms = product_title.lower().split()
        logger.info("   Search terms: {search_terms}")
        
        all_fuzzy_matches = []
        for term in search_terms:
            if len(term) > 3:
                logger.info("   Searching for term: '{term}'")
                fuzzy_matches = db_session.query(Accessory).filter(
                    or_(
                        Accessory.name.ilike(f'%{term}%'),
                        Accessory.category.ilike(f'%{term}%'),
                        Accessory.manufacturer.ilike(f'%{term}%'),
                        Accessory.model_no.ilike(f'%{term}%')
                    )
                ).all()
                
                logger.info("     Found {len(fuzzy_matches)} matches for '{term}':")
                for acc in fuzzy_matches:
                    if acc not in all_fuzzy_matches:
                        all_fuzzy_matches.append(acc)
                        logger.info("     - ID: {acc.id}, Name: {acc.name}, Category: {acc.category}, Available: {acc.available_quantity}")
        
        # Test 3: Check specific accessory
        logger.info("\n3. Checking specific Apple USB-C adapter...")
        apple_adapter = db_session.query(Accessory).filter(
            Accessory.name.ilike('%Apple%USB-C%Digital%AV%Multiport%Adapter%')
        ).first()
        
        if apple_adapter:
            logger.info("   Found Apple adapter: ID {apple_adapter.id}, Name: {apple_adapter.name}")
            logger.info("   Available quantity: {apple_adapter.available_quantity}")
            logger.info("   Category: {apple_adapter.category}")
            logger.info("   Manufacturer: {apple_adapter.manufacturer}")
        else:
            logger.info("   Apple USB-C adapter not found")
        
        # Test 4: List all accessories with "adapter" in name
        logger.info("\n4. All accessories with 'adapter' in name:")
        adapter_accessories = db_session.query(Accessory).filter(
            Accessory.name.ilike('%adapter%')
        ).all()
        
        for acc in adapter_accessories:
            logger.info("   - ID: {acc.id}, Name: {acc.name}, Available: {acc.available_quantity}")
        
        logger.info("\n" + "=" * 60)
        logger.info("Test completed!")
        
    finally:
        db_session.close()

if __name__ == '__main__':
    test_accessory_matching() 