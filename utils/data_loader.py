import csv
import pandas as pd
from utils.snipeit_client import SnipeITClient
from config.snipeit_config import SNIPEIT_API_URL, SNIPEIT_API_KEY
import os
import time
from datetime import datetime

class SnipeITDataLoader:
    def __init__(self):
        self.client = SnipeITClient()
        # Update required fields based on your CSV structure
        self.required_asset_fields = [
            'ASSET TAG', 
            'SERIAL NUMBER',
            'MODEL',
            'HARDWARE TYPE',
            'CUSTOMER'
        ]
        
        # Add field mappings to match Snipe-IT API fields
        self.field_mappings = {
            'no': None,  # Skip this field
            'Asset Type': 'category',
            'Product': 'model_name',
            'ASSET TAG': 'asset_tag',
            'Receiving date': 'purchase_date',
            'SKU': 'order_number',
            'SERIAL NUMBER': 'serial',
            'PO': 'order_number',
            'MODEL': 'model_number',
            'ERASED': 'notes',
            'CUSTOMER': 'company',
            'CONDITION': '_snipeit_condition_5',
            'DIAG': 'notes',
            'HARDWARE TYPE': 'name',
            'CPU TYPE': '_snipeit_cpu_type_2',
            'CPU CORES': '_snipeit_cpu_cores_3',
            'GPU CORES': '_snipeit_gpu_cores_6',
            'MEMORY': '_snipeit_memory_7',
            'HARDDRIVE': '_snipeit_harddrive_8',
            'STATUS': 'status',
            'CHARGER': '_snipeit_charger_4',
            'INVENTORY': 'status',
            'Country': 'location'
        }
        
        # Create uploads directory if it doesn't exist
        if not os.path.exists('uploads'):
            os.makedirs('uploads')
        
        # Clean up old temporary files
        self.cleanup_old_files()

    def cleanup_old_files(self):
        """Clean up temporary files older than 1 hour"""
        try:
            current_time = time.time()
            for filename in os.listdir('uploads'):
                filepath = os.path.join('uploads', filename)
                if os.path.getmtime(filepath) < current_time - 3600:  # 1 hour
                    os.remove(filepath)
        except Exception as e:
            print(f"Error cleaning up files: {str(e)}")

    def transform_data(self, row_data):
        """Transform CSV data to Snipe-IT format"""
        transformed = {}
        
        # Initialize custom fields
        transformed['custom_fields'] = {}
        
        # Map specifications to custom fields
        specs_mapping = {
            'CPU TYPE': '_snipeit_cpu_type_2',
            'CPU CORES': '_snipeit_cpu_cores_3',
            'GPU CORES': '_snipeit_gpu_cores_6',
            'MEMORY': '_snipeit_memory_7',
            'HARDDRIVE': '_snipeit_harddrive_8',
            'CONDITION': '_snipeit_condition_5',
            'CHARGER': '_snipeit_charger_4'
        }
        
        # First, handle specifications
        for spec_field, custom_field in specs_mapping.items():
            if spec_field in row_data and pd.notna(row_data[spec_field]):
                transformed['custom_fields'][custom_field] = str(row_data[spec_field])
        
        # Then handle other fields
        for csv_field, value in row_data.items():
            api_field = self.field_mappings.get(csv_field)
            if api_field and pd.notna(value):
                if csv_field == 'CUSTOMER':
                    transformed['company_id'] = self.get_company_id(value)
                elif csv_field == 'Asset Type':
                    transformed['category_id'] = self.get_category_id(value)
                elif csv_field == 'MODEL':
                    transformed['model_id'] = self.get_model_id(value)
                elif csv_field == 'STATUS' or csv_field == 'INVENTORY':
                    transformed['status_id'] = self.get_status_id(value)
                elif csv_field == 'Receiving date':
                    try:
                        date_obj = datetime.strptime(value, '%d-%b-%y')
                        transformed[api_field] = date_obj.strftime('%Y-%m-%d')
                    except:
                        transformed[api_field] = datetime.now().strftime('%Y-%m-%d')
                elif api_field not in ['custom_fields']:  # Skip custom fields as they're handled above
                    transformed[api_field] = str(value)
        
        # Build asset name from specifications
        name_parts = [
            row_data.get('HARDWARE TYPE', ''),
            f"CPU: {row_data.get('CPU TYPE', '')} {row_data.get('CPU CORES', '')}Core",
            f"GPU: {row_data.get('GPU CORES', '')}Core",
            f"RAM: {row_data.get('MEMORY', '')}GB",
            f"SSD: {row_data.get('HARDDRIVE', '')}GB"
        ]
        transformed['name'] = ' - '.join(filter(None, name_parts))
        
        print(f"Transformed data with specs: {transformed}")  # Debug print
        return transformed

    def get_company_id(self, company_name):
        """Get company ID from name"""
        # Add logic to fetch company ID from Snipe-IT
        # You'll need to implement this in SnipeITClient
        return 1  # Temporary default

    def get_category_id(self, category_name):
        """Get category ID from name"""
        # Add logic to fetch category ID
        return 1  # Temporary default

    def get_model_id(self, model_name):
        """Get model ID from name"""
        # Add logic to fetch model ID
        return 1  # Temporary default

    def get_status_id(self, status_name):
        """Get status ID from name"""
        status_map = {
            'IN STOCK': 2,  # Ready to Deploy
            'DEPLOYED': 3,
            'PENDING': 1
        }
        return status_map.get(status_name, 2)

    def validate_csv(self, file_path, import_type):
        """Validate CSV file has required fields"""
        try:
            df = pd.read_csv(file_path)
            required_fields = (self.required_asset_fields 
                             if import_type == 'assets' 
                             else self.required_accessory_fields)
            
            missing_fields = [field for field in required_fields 
                            if field not in df.columns]
            
            if missing_fields:
                return False, f"Missing required fields: {', '.join(missing_fields)}"
            return True, "CSV validation successful"
            
        except Exception as e:
            return False, f"Error validating CSV: {str(e)}"

    def import_assets(self, file_path, dry_run=True):
        """Import assets from CSV file"""
        results = {
            'success': [],
            'errors': [],
            'total': 0,
            'successful': 0,
            'failed': 0
        }
        
        try:
            print(f"Starting import process. Dry run: {dry_run}")  # Debug print
            df = pd.read_csv(file_path)
            results['total'] = len(df)
            
            for index, row in df.iterrows():
                try:
                    # Convert row to dict and clean NaN values
                    asset_data = row.to_dict()
                    asset_data = {k: v for k, v in asset_data.items() 
                                if pd.notna(v)}
                    
                    # Transform the data
                    transformed_data = self.transform_data(asset_data)
                    print(f"Transformed data for row {index + 2}: {transformed_data}")  # Debug print
                    
                    if not dry_run:
                        print(f"Attempting to create asset for row {index + 2}")  # Debug print
                        # Actual import logic
                        response = self.client.create_asset(transformed_data)
                        print(f"API Response: {response}")  # Debug print
                        
                        if response:
                            results['successful'] += 1
                            results['success'].append({
                                'row': index + 2,
                                'asset_tag': asset_data.get('ASSET TAG'),
                                'message': 'Successfully imported'
                            })
                            print(f"Successfully imported row {index + 2}")  # Debug print
                        else:
                            results['failed'] += 1
                            results['errors'].append({
                                'row': index + 2,
                                'asset_tag': asset_data.get('ASSET TAG'),
                                'error': 'Failed to create asset'
                            })
                            print(f"Failed to import row {index + 2}")  # Debug print
                    else:
                        # Dry run logic (existing code...)
                        results['successful'] += 1
                        results['success'].append({
                            'row': index + 2,
                            'asset_tag': asset_data.get('ASSET TAG'),
                            'serial': asset_data.get('SERIAL NUMBER'),
                            'model': asset_data.get('MODEL'),
                            'customer': asset_data.get('CUSTOMER'),
                            'hardware_type': asset_data.get('HARDWARE TYPE'),
                            'status': asset_data.get('STATUS', 'Ready to Deploy'),
                            'specs': {
                                'CPU Type': asset_data.get('CPU TYPE'),
                                'CPU Cores': asset_data.get('CPU CORES'),
                                'GPU Cores': asset_data.get('GPU CORES'),
                                'Memory': asset_data.get('MEMORY'),
                                'Hard Drive': asset_data.get('HARDDRIVE'),
                                'Condition': asset_data.get('CONDITION'),
                                'Charger': asset_data.get('CHARGER')
                            },
                            'message': 'Validation passed (dry run)',
                            'transformed_data': transformed_data
                        })
                    
                except Exception as e:
                    print(f"Error processing row {index + 2}: {str(e)}")  # Debug print
                    results['failed'] += 1
                    results['errors'].append({
                        'row': index + 2,
                        'error': str(e)
                    })
                    
            return results
            
        except Exception as e:
            print(f"File processing error: {str(e)}")  # Debug print
            results['errors'].append({'error': f"File processing error: {str(e)}"})
            return results

    def import_accessories(self, file_path, dry_run=True):
        """Import accessories from CSV file"""
        results = {
            'success': [],
            'errors': [],
            'total': 0,
            'successful': 0,
            'failed': 0
        }
        
        try:
            df = pd.read_csv(file_path)
            results['total'] = len(df)
            
            for index, row in df.iterrows():
                try:
                    accessory_data = row.to_dict()
                    accessory_data = {k: v for k, v in accessory_data.items() 
                                    if pd.notna(v)}
                    
                    if not dry_run:
                        response = self.client.create_accessory(accessory_data)
                        if response:
                            results['successful'] += 1
                            results['success'].append({
                                'row': index + 2,
                                'name': accessory_data.get('name')
                            })
                        else:
                            results['failed'] += 1
                            results['errors'].append({
                                'row': index + 2,
                                'name': accessory_data.get('name'),
                                'error': 'Failed to create accessory'
                            })
                    else:
                        results['successful'] += 1
                        results['success'].append({
                            'row': index + 2,
                            'name': accessory_data.get('name'),
                            'message': 'Validation passed (dry run)'
                        })
                        
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append({
                        'row': index + 2,
                        'error': str(e)
                    })
                    
            return results
            
        except Exception as e:
            results['errors'].append({'error': f"File processing error: {str(e)}"})
            return results 