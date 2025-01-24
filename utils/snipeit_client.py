import requests
import html
import json
from config.snipeit_config import SNIPEIT_API_URL, SNIPEIT_API_KEY, ENDPOINTS

class SnipeITClient:
    def __init__(self):
        self.base_url = SNIPEIT_API_URL
        self.headers = {
            'Authorization': f'Bearer {SNIPEIT_API_KEY}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        # Create a session for better performance
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def get_assets(self, limit=20, offset=0, search=''):
        """Get paginated assets with search"""
        params = {
            'limit': limit,
            'offset': offset,
            'search': search
        }
        response = requests.get(
            f"{self.base_url}{ENDPOINTS['assets']}", 
            headers=self.headers,
            params=params
        )
        response.raise_for_status()
        return response.json()

    def get_all_assets(self):
        """Get all assets with their location and country information"""
        try:
            response = self.session.get(
                f"{self.base_url}{ENDPOINTS['assets']}",
                params={
                    'limit': 500,
                    'offset': 0,
                    'sort': 'created_at',
                    'order': 'desc',
                    'expand': 'location,company,model,status_label,custom_fields'
                }
            )
            
            print(f"Request URL: {response.url}")
            print(f"Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Total assets found: {len(data.get('rows', []))}")
                assets = data.get('rows', [])
                
                for asset in assets:
                    # Debug print custom fields for first asset
                    if assets.index(asset) == 0:
                        print("\nCustom Fields for first asset:")
                        for field_key, field_value in asset.get('custom_fields', {}).items():
                            print(f"Field: {field_key} = {field_value}")
                    
                    # Get country from custom fields
                    custom_fields = asset.get('custom_fields', {})
                    country = None
                    receiving_date = None
                    
                    # Loop through custom fields to find country and receiving date
                    for field_key, field_value in custom_fields.items():
                        print(f"Processing field: {field_key} = {field_value}")  # Debug print
                        
                        if isinstance(field_value, dict):
                            field_name = field_value.get('field', '').lower()
                            field_value = field_value.get('value')
                            
                            if 'country' in field_name:
                                country = field_value
                                print(f"Found country: {country}")  # Debug print
                            
                            if 'receiving date' in field_name or 'received' in field_name:
                                receiving_date = field_value
                                print(f"Found receiving date: {receiving_date}")  # Debug print

                    # Set country in location data
                    if not asset.get('location'):
                        asset['location'] = {
                            'name': 'N/A',
                            'country': {'name': country if country else 'N/A'}
                        }
                    else:
                        asset['location']['country'] = {'name': country if country else 'N/A'}

                    # Set receiving date
                    asset['created_at'] = receiving_date if receiving_date else 'N/A'

                    # Rest of the asset processing...
                    asset['serial'] = asset.get('serial') or 'N/A'
                    asset['asset_tag'] = asset.get('asset_tag') or 'N/A'
                    asset['name'] = asset.get('name') or 'Unnamed Asset'
                    
                    if not asset.get('model'):
                        asset['model'] = {'name': 'N/A'}
                    
                    if not asset.get('company'):
                        asset['company'] = {'name': 'N/A'}
                    
                    if not asset.get('status_label'):
                        asset['status_label'] = {
                            'name': 'Unknown',
                            'status_meta': 'other'
                        }

                # Debug print first asset after processing
                if assets:
                    first_asset = assets[0]
                    print("\nProcessed first asset:")
                    print(f"Country: {first_asset['location']['country']['name']}")
                    print(f"Receiving Date: {first_asset['created_at']}")
                    print("Full asset data:", json.dumps(first_asset, indent=2))
                
                return assets
            else:
                print(f"Error response: {response.text}")
                return []
        except Exception as e:
            print(f"Error fetching assets: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_all_accessories(self):
        """Get all accessories"""
        try:
            response = requests.get(
                f"{self.base_url}{ENDPOINTS['accessories']}?limit=1000", 
                headers=self.headers,
                timeout=10  # Add timeout
            )
            response.raise_for_status()
            data = response.json()
            return data.get('rows', [])
        except Exception as e:
            print(f"Error fetching accessories: {e}")
            return []

    def get_asset_details(self, asset_id):
        """Get detailed information about a specific asset"""
        try:
            print(f"\n=== Fetching asset {asset_id} ===")  # Debug print
            url = f"{self.base_url}{ENDPOINTS['assets']}/{asset_id}"
            print(f"Request URL: {url}")  # Debug print
            
            # Print headers being used
            print(f"Request Headers: {self.headers}")
            
            response = self.session.get(url)
            print(f"Response status code: {response.status_code}")  # Debug print
            
            # Print full response for debugging
            print(f"Response headers: {response.headers}")
            print(f"Response content: {response.text[:500]}...")  # Print first 500 chars
            
            if response.status_code == 200:
                data = response.json()
                print(f"Asset data received: {data}")  # Debug print
                
                # Clean HTML entities from asset name
                if isinstance(data, dict) and data.get('name'):
                    data['name'] = html.unescape(data['name'])
                
                return data
            else:
                print(f"Error response: {response.text}")  # Debug print
                return None
            
        except Exception as e:
            print(f"Error fetching asset details: {str(e)}")  # Debug print
            print(f"Full traceback:")
            import traceback
            traceback.print_exc()
            return None

    def test_connection(self):
        """Test the connection to Snipe-IT"""
        try:
            response = requests.get(
                f"{self.base_url}{ENDPOINTS['assets']}?limit=1", 
                headers=self.headers
            )
            response.raise_for_status()
            return True
        except:
            return False 

    def get_companies(self):
        """Get all companies"""
        try:
            response = self.session.get(f"{self.base_url}/companies")
            if response.status_code == 200:
                return response.json()['rows']
            return []
        except Exception as e:
            print(f"Error fetching companies: {e}")
            return []

    def get_company(self, company_id):
        """Get a specific company"""
        try:
            response = self.session.get(f"{self.base_url}/companies/{company_id}")
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error fetching company: {e}")
            return None

    def create_company(self, company_data):
        """Create a new company"""
        try:
            response = self.session.post(f"{self.base_url}/companies", json=company_data)
            return response.status_code in [200, 201]
        except Exception as e:
            print(f"Error creating company: {e}")
            return False

    def update_company(self, company_id, company_data):
        """Update a company"""
        try:
            response = self.session.put(f"{self.base_url}/companies/{company_id}", json=company_data)
            return response.status_code == 200
        except Exception as e:
            print(f"Error updating company: {e}")
            return False

    def delete_company(self, company_id):
        """Delete a company"""
        try:
            response = self.session.delete(f"{self.base_url}/companies/{company_id}")
            return response.status_code in [200, 204]
        except Exception as e:
            print(f"Error deleting company: {e}")
            return False

    def get_categories(self):
        """Get list of categories with their IDs"""
        try:
            response = self.session.get(f"{self.base_url}{ENDPOINTS['categories']}")
            if response.status_code == 200:
                return response.json().get('rows', [])
            return []
        except Exception as e:
            print(f"Error fetching categories: {str(e)}")
            return []

    def get_models(self):
        """Get list of models with their IDs"""
        try:
            response = self.session.get(f"{self.base_url}{ENDPOINTS['models']}")
            if response.status_code == 200:
                return response.json().get('rows', [])
            return []
        except Exception as e:
            print(f"Error fetching models: {str(e)}")
            return []

    def get_accessory_details(self, accessory_id):
        """Get detailed information about a specific accessory"""
        try:
            url = f"{self.base_url}{ENDPOINTS['accessories']}/{accessory_id}"
            response = self.session.get(url)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error fetching accessory details: {str(e)}")
            return None

    def checkout_accessory(self, accessory_id, user_id, notes=None):
        """Checkout an accessory to a user"""
        try:
            url = f"{self.base_url}{ENDPOINTS['accessories']}/{accessory_id}/checkout"
            data = {
                'assigned_to': user_id,
                'note': notes
            }
            response = self.session.post(url, json=data)
            return response.status_code == 200
        except Exception as e:
            print(f"Error checking out accessory: {str(e)}")
            return False

    def get_users(self):
        """Get list of users from Snipe-IT"""
        try:
            response = self.session.get(f"{self.base_url}{ENDPOINTS['users']}")
            if response.status_code == 200:
                return response.json().get('rows', [])
            return []
        except Exception as e:
            print(f"Error fetching users: {str(e)}")
            return [] 

    def create_asset(self, asset_data):
        """Create a new asset in Snipe-IT"""
        try:
            # Ensure custom fields are properly formatted
            if 'custom_fields' in asset_data:
                for field, value in asset_data['custom_fields'].items():
                    # Convert any non-string values to strings
                    asset_data['custom_fields'][field] = str(value)
            
            print(f"Sending asset data to API: {asset_data}")  # Debug print
            response = self.session.post(
                f"{self.base_url}{ENDPOINTS['assets']}", 
                json=asset_data
            )
            print(f"API Response Status: {response.status_code}")  # Debug print
            print(f"API Response Content: {response.text}")  # Debug print
            
            response_data = response.json()
            if response.status_code in [200, 201] and response_data.get('status') != 'error':
                return True
            else:
                print(f"API Error: {response.text}")  # Debug print
                return False
            
        except Exception as e:
            print(f"Error creating asset: {str(e)}")
            return False

    def create_accessory(self, accessory_data):
        """Create a new accessory in Snipe-IT"""
        try:
            response = self.session.post(
                f"{self.base_url}{ENDPOINTS['accessories']}", 
                json=accessory_data
            )
            return response.status_code in [200, 201]
        except Exception as e:
            print(f"Error creating accessory: {str(e)}")
            return False 

    def get_locations(self):
        """Get all locations"""
        try:
            response = self.session.get(f"{self.base_url}/locations")
            if response.status_code == 200:
                return response.json()['rows']
            return []
        except Exception as e:
            print(f"Error fetching locations: {e}")
            return [] 

    def get_status_labels(self):
        """Get all status labels"""
        try:
            response = self.session.get(f"{self.base_url}/statuslabels")
            if response.status_code == 200:
                data = response.json()
                print("Available status labels:", data['rows'])  # Debug print
                return data['rows']
            return []
        except Exception as e:
            print(f"Error fetching status labels: {e}")
            return []

    def update_asset_status(self, asset_id, status_id, notes=""):
        """Update an asset's inventory status"""
        try:
            data = {
                'custom_fields': {
                    '_snipeit_inventory_10': 'SHIPPED'  # Update the INVENTORY custom field
                },
                'notes': notes
            }
            print(f"Updating asset {asset_id} with data:", data)
            
            # Use the same URL construction as other methods
            url = f"{self.base_url}{ENDPOINTS['assets']}/{asset_id}"
            print(f"Request URL: {url}")
            
            print("Request Headers:", self.session.headers)
            print("Request Data:", json.dumps(data, indent=2))
            
            # Use PATCH for partial updates
            response = self.session.patch(
                url,
                json=data
            )
            
            print(f"Response Status Code: {response.status_code}")
            print(f"Response Content: {response.text}")
            
            if response.status_code != 200:
                print(f"Error response from API: {response.text}")
            
            return response.status_code == 200
        except Exception as e:
            print(f"Exception in update_asset_status: {str(e)}")
            import traceback
            traceback.print_exc()
            return False 