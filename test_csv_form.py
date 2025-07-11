#!/usr/bin/env python3
"""
Test script to simulate CSV accessory form submission
"""
import requests
import json

def test_csv_accessory_submission():
    """Test submitting a form with CSV accessory data"""
    
    # Test data - simulating what the frontend should send
    test_accessories = [
        {
            "csvIndex": 0,
            "product": "Test Wireless Mouse",
            "category": "Mouse",
            "quantity": 1,
            "inventoryId": None,
            "inventoryName": None
        },
        {
            "csvIndex": 1,
            "product": "Test USB-C Cable", 
            "category": "Cable",
            "quantity": 2,
            "inventoryId": None,
            "inventoryName": None
        }
    ]
    
    # Convert to JSON string (as the frontend does)
    accessories_json = json.dumps(test_accessories)
    
    logger.info("Test CSV Accessory Data:")
    logger.info("JSON String: {accessories_json}")
    logger.info("Length: {len(accessories_json)}")
    print()
    
    # Simulate form data
    form_data = {
        'category': 'ASSET_CHECKOUT_CLAW',
        'subject': 'Test Asset Checkout with CSV Accessories',
        'description': 'Testing CSV accessory assignment',
        'priority': 'Medium',
        'asset_checkout_serial': 'TEST123',
        'customer_id': '1',
        'shipping_address': '123 Test Street, Test City',
        'selected_accessories': accessories_json,  # This is the key field
        'csrf_token': 'test-token'  # Would need real token in actual test
    }
    
    logger.info("Form Data to be submitted:")
    for key, value in form_data.items():
        if key == 'selected_accessories':
            logger.info(f"  {key}: {value[:100]}..." if len(value) > 100 else f"  {key}: {value}")
        else:
            logger.info("  {key}: {value}")
    
    logger.info("\nThis simulates what the frontend should send to the backend.")
    logger.info("The backend should receive 'selected_accessories' as a JSON string.")
    logger.info("If accessories are not being assigned, check:")
    logger.info("1. Is the hidden input field being populated?")
    logger.info("2. Is the form submission including the selected_accessories field?")
    logger.info("3. Is the backend receiving and parsing the JSON correctly?")

if __name__ == '__main__':
    test_csv_accessory_submission() 