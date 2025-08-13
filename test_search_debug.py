#!/usr/bin/env python3

from app import create_app
from database import SessionLocal
from models.user import User
from routes.json_api import generate_access_token

app = create_app()

with app.app_context():
    db_session = SessionLocal()
    admin_user = db_session.query(User).filter(User.username == 'admin').first()
    
    if admin_user:
        jwt_token = generate_access_token(admin_user.id)
        db_session.close()
        
        with app.test_client() as client:
            headers = {
                'X-API-Key': 'xAQhm3__ZH6MvRIPMIBSDRAsIa1w2Slh5uaCtc4NurM',
                'Authorization': f'Bearer {jwt_token}'
            }
            
            print("Testing search endpoints...")
            
            # Test global search
            response = client.get('/api/v1/search/global?q=laptop&limit=2', headers=headers)
            print(f"Global search status: {response.status_code}")
            if response.status_code != 200:
                try:
                    error_data = response.get_json()
                    print(f"Error: {error_data}")
                except:
                    print(f"Raw error: {response.data}")
            else:
                data = response.get_json()
                counts = data.get('counts', {})
                print(f"Success: Found {counts.get('total', 0)} total results")
                print(f"  Assets: {counts.get('assets', 0)}")
                print(f"  Accessories: {counts.get('accessories', 0)}")
                print(f"  Customers: {counts.get('customers', 0)}")
                print(f"  Tickets: {counts.get('tickets', 0)}")
            
            # Test suggestions
            response = client.get('/api/v1/search/suggestions?q=mac&type=assets&limit=5', headers=headers)
            print(f"Suggestions status: {response.status_code}")
            
            # Test filters
            response = client.get('/api/v1/search/filters?type=assets', headers=headers)
            print(f"Filters status: {response.status_code}")
    else:
        print("No admin user found")
        db_session.close()