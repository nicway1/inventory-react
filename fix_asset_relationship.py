#!/usr/bin/env python
"""
Script to fix the unterminated string literal in the Asset model's transactions relationship
"""
import os
import sys
import re
import shutil
from datetime import datetime

def fix_asset_relationship():
    """Fix unterminated string in Asset model relationships"""
    print("Starting fix of Asset model relationship...")
    
    # Determine if we're running locally or on PythonAnywhere
    if os.path.exists('/home/nicway2/inventory'):
        model_file_path = '/home/nicway2/inventory/models/asset.py'
        print("Running on PythonAnywhere environment")
    else:
        model_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models', 'asset.py')
        print(f"Running on local environment, path: {model_file_path}")
    
    if not os.path.exists(model_file_path):
        print(f"Error: Asset model file not found at {model_file_path}")
        return False
    
    # Create a backup of the original file
    backup_path = f"{model_file_path}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
    try:
        shutil.copy2(model_file_path, backup_path)
        print(f"Backup created at {backup_path}")
    except Exception as e:
        print(f"Warning: Could not create backup: {str(e)}")
    
    # Read the current model file
    with open(model_file_path, 'r') as f:
        content = f.readlines()
    
    # Look for the problematic line and fix it
    fixed = False
    for i, line in enumerate(content):
        # Check for the unterminated string in transactions relationship
        if 'transactions = relationship("AssetTransaction"' in line and line.strip()[-1] != ')':
            print(f"Found problematic line at line {i+1}: {line.strip()}")
            
            # Check if it's missing a closing quote
            if '"desc(AssetTransaction.transaction_date)' in line and not line.strip().endswith('"'):
                content[i] = line.replace('transaction_date)', 'transaction_date)")')
                print(f"Fixed line: {content[i].strip()}")
                fixed = True
            # If missing just the closing parenthesis
            elif '"desc(AssetTransaction.transaction_date)"' in line and not line.strip().endswith(')'):
                content[i] = line.rstrip() + ')\n'
                print(f"Fixed line: {content[i].strip()}")
                fixed = True
    
    if not fixed:
        # Try a more general approach - look for any line with "transactions = relationship"
        pattern = re.compile(r'transactions\s*=\s*relationship\(.*')
        for i, line in enumerate(content):
            if pattern.search(line) and not line.strip().endswith(')'):
                print(f"Found problematic relationship line at line {i+1}: {line.strip()}")
                
                # Check if it includes order_by with transaction_date
                if 'transaction_date' in line:
                    # Extract everything up to the last occurrence of "transaction_date"
                    prefix = line[:line.rfind('transaction_date') + len('transaction_date')]
                    # Add proper closure
                    content[i] = prefix + '")\n'
                    print(f"Fixed line: {content[i].strip()}")
                    fixed = True
    
    if not fixed:
        print("Could not automatically fix the issue. Please check the file manually.")
        print(f"Look for unterminated strings near line 78 in {model_file_path}")
        return False
    
    # Write back to the file
    try:
        with open(model_file_path, 'w') as f:
            f.writelines(content)
        print(f"Successfully fixed relationship definition in Asset model at {model_file_path}")
        return True
    except Exception as e:
        print(f"Error writing to file: {str(e)}")
        return False

if __name__ == "__main__":
    success = fix_asset_relationship()
    if success:
        print("Asset model relationship successfully fixed.")
        print("Don't forget to restart your application with:")
        print("touch /var/www/nicway2_pythonanywhere_com_wsgi.py")
    else:
        print("Failed to fix Asset model relationship.")
        sys.exit(1) 