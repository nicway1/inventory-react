"""
Script to fix the missing SQLAlchemy imports in the Asset model.
This will update the models/asset.py file to add the required imports.
"""
import os
import re

# File path
ASSET_MODEL = 'models/asset.py'

def fix_asset_model_imports():
    print(f"Fixing imports in {ASSET_MODEL}")
    if not os.path.exists(ASSET_MODEL):
        print(f"Error: {ASSET_MODEL} not found!")
        return False
    
    with open(ASSET_MODEL, 'r') as f:
        asset_content = f.read()
    
    # Check if sqlalchemy Table is already imported
    if "from sqlalchemy import Table" in asset_content:
        print("Table is already imported in Asset model")
        return True
    
    # Add the required imports
    required_imports = "from sqlalchemy import Table, Column, Integer, ForeignKey\n"
    
    # Find the import section and add the missing imports
    import_section_pattern = r'(import .+?\n|from .+? import .+?\n)+'
    match = re.search(import_section_pattern, asset_content)
    
    if match:
        # Add the imports at the end of the import section
        import_section_end = match.end()
        new_content = asset_content[:import_section_end] + required_imports + asset_content[import_section_end:]
        
        # Write the updated content
        with open(ASSET_MODEL, 'w') as f:
            f.write(new_content)
        
        print(f"Added missing imports to {ASSET_MODEL}")
        return True
    else:
        print(f"Could not find import section in {ASSET_MODEL}")
        return False

# Main execution
try:
    print("==== Fixing missing imports ====")
    
    if fix_asset_model_imports():
        print("\nSuccessfully added missing imports. Please restart your web application:")
        print("1. Go to the Web tab in PythonAnywhere")
        print("2. Click on 'Reload <username>.pythonanywhere.com'")
    else:
        print("\nWARNING: Failed to add missing imports!")
        print("You may need to manually add the following import to models/asset.py:")
        print("from sqlalchemy import Table, Column, Integer, ForeignKey")
        
except Exception as e:
    import traceback
    print(f"Error fixing imports: {str(e)}")
    traceback.print_exc()
    print("\nPlease manually add the following import to models/asset.py:")
    print("from sqlalchemy import Table, Column, Integer, ForeignKey") 