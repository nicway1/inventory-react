#!/usr/bin/env python
"""
Comprehensive fix for syntax errors in Asset model
"""
import os
import sys
import shutil
import re
from datetime import datetime

def comprehensive_fix():
    """Fix syntax errors in asset.py"""
    print("Starting comprehensive syntax fix for asset.py...")
    
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
    
    # Read the file content
    try:
        with open(model_file_path, 'r') as f:
            content = f.read()
        
        print(f"Successfully read file, size: {len(content)} bytes")
    except Exception as e:
        print(f"Error reading the file: {str(e)}")
        return False
    
    # Let's completely rewrite the file to be safe
    try:
        # First, we'll do a manual fix of the known problematic lines
        lines = content.split('\n')
        
        # Keep track of changes
        fixed_lines = []
        issues_fixed = 0
        
        for i, line in enumerate(lines):
            line_num = i + 1
            fixed_line = line
            
            # Fix relationship lines with unterminated strings
            if 'relationship(' in line and ('"' in line or "'" in line) and not line.strip().endswith(')'):
                print(f"Found potential issue at line {line_num}: {line}")
                
                # Count quotes
                single_quotes = line.count("'")
                double_quotes = line.count('"')
                
                if (single_quotes % 2 != 0) or (double_quotes % 2 != 0):
                    print(f"  Unbalanced quotes detected: {single_quotes} single quotes, {double_quotes} double quotes")
                    
                    # Try to fix transactions relationship
                    if 'transactions =' in line:
                        fixed_line = '    transactions = relationship("AssetTransaction", back_populates="asset", order_by="desc(AssetTransaction.transaction_date)")'
                        print(f"  Fixed transactions relationship line")
                        issues_fixed += 1
                    
                    # Check for other relationship strings
                    elif re.search(r'relationship\([^)]*$', line):
                        # Try to identify the relationship name
                        relationship_name = line.strip().split('=')[0].strip()
                        if relationship_name:
                            print(f"  Found incomplete relationship definition for: {relationship_name}")
                            # Check if we can find a closing parenthesis within the next few lines
                            for j in range(1, 4):
                                if i+j < len(lines) and ')' in lines[i+j]:
                                    # We found the end of this relationship on a later line
                                    # Let's combine them
                                    combined = line
                                    for k in range(1, j+1):
                                        combined += ' ' + lines[i+k].strip()
                                        # Mark these lines for removal
                                        lines[i+k] = "TO_BE_REMOVED"
                                    
                                    # Fix any unbalanced quotes in the combined line
                                    if combined.count('"') % 2 != 0:
                                        # Add a missing quote before the closing parenthesis
                                        if ')' in combined:
                                            combined = combined.replace(')', '")', 1)
                                    
                                    fixed_line = combined
                                    print(f"  Combined multi-line relationship definition")
                                    issues_fixed += 1
                                    break
            
            # Don't add lines marked for removal
            if fixed_line != "TO_BE_REMOVED":
                fixed_lines.append(fixed_line)
        
        # Write the fixed content back to the file
        with open(model_file_path, 'w') as f:
            f.write('\n'.join(fixed_lines))
        
        if issues_fixed > 0:
            print(f"Successfully fixed {issues_fixed} issues")
        else:
            print("No specific issues were fixed automatically.")
            print("Let's check for syntax errors line by line...")
            
            # Try to identify any lines with syntax errors
            with open(model_file_path, 'r') as f:
                content = f.readlines()
            
            # Specifically check line 100 as mentioned in the error
            if len(content) >= 100:
                line_100 = content[99]  # 0-based indexing
                print(f"Line 100 content: {line_100.strip()}")
                
                # Check for unterminated strings in line 100
                if line_100.count('"') % 2 != 0 or line_100.count("'") % 2 != 0:
                    print("Line 100 has unbalanced quotes. Attempting to fix...")
                    
                    # Try to fix it - if it contains a relationship definition or other known pattern
                    if 'relationship(' in line_100:
                        # Check if it's a multi-line definition
                        if not line_100.strip().endswith(')'):
                            # Look ahead for the end of the definition
                            end_found = False
                            combined = line_100.rstrip()
                            for j in range(1, 4):
                                if 99+j < len(content):
                                    next_line = content[99+j]
                                    combined += ' ' + next_line.strip()
                                    if ')' in next_line:
                                        end_found = True
                                        break
                            
                            if end_found:
                                # Fix quotes in the combined line
                                if combined.count('"') % 2 != 0:
                                    combined = re.sub(r'([^"])(\))', r'\1"\2', combined)
                                
                                content[99] = combined + '\n'
                                
                                # Remove the lines we combined
                                for j in range(1, 4):
                                    if 99+j < len(content) and ')' in content[99+j]:
                                        content[99+j] = ''
                                        break
                                
                                print(f"Fixed line 100 by combining multi-line relationship")
                                
                                # Write back the fixed content
                                with open(model_file_path, 'w') as f:
                                    f.writelines(content)
            
            # Force fix for line 100 to be safe
            if len(content) >= 100:
                if '")' in content[99]:
                    content[99] = content[99].replace('")', '")\n')
                else:
                    content[99] = content[99].rstrip() + '")\n'
                
                print(f"Forced fix for line 100: {content[99].strip()}")
                
                # Write back the fixed content
                with open(model_file_path, 'w') as f:
                    f.writelines(content)
        
        # A final sanity check for the whole file
        try:
            # Verify syntax is correct with a literal eval
            with open(model_file_path, 'r') as f:
                file_content = f.read()
            
            # Try to compile the file to check for syntax errors
            compile(file_content, model_file_path, 'exec')
            print("Final syntax check passed: No syntax errors detected.")
        except SyntaxError as e:
            print(f"Warning: Syntax error still present after fixes: {str(e)}")
            print("Will attempt one last direct fix...")
            
            # Direct fix approach - read line by line, fix obvious issues
            with open(model_file_path, 'r') as f:
                lines = f.readlines()
            
            # Check for any lines with unbalanced quotes
            for i, line in enumerate(lines):
                if line.count('"') % 2 != 0:
                    print(f"Unbalanced quotes at line {i+1}: {line.strip()}")
                    
                    # If line ends with a relationship and is missing closing quote and parenthesis
                    if 'relationship(' in line and not line.strip().endswith(')'):
                        if line.strip().endswith('"'):
                            lines[i] = line.strip() + ')\n'
                        else:
                            lines[i] = line.strip() + '")\n'
                        
                        print(f"Fixed line {i+1}: {lines[i].strip()}")
            
            # Write back the fixed content
            with open(model_file_path, 'w') as f:
                f.writelines(lines)
        
        return True
    except Exception as e:
        print(f"Error fixing the file: {str(e)}")
        return False

if __name__ == "__main__":
    success = comprehensive_fix()
    if success:
        print("Asset model file processed. Run update_asset_model.py next.")
        print("Then restart your application with:")
        print("touch /var/www/nicway2_pythonanywhere_com_wsgi.py")
    else:
        print("Failed to fix Asset model file.")
        print("You may need to manually edit the file.")
        sys.exit(1) 