#!/usr/bin/env python3
"""
Fix WSGI Print Statements Script
This script finds and fixes print() statements that can cause BlockingIOError in WSGI environments.
"""

import os
import re
import sys
from pathlib import Path

def fix_print_statements_in_file(file_path):
    """Fix print statements in a single Python file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes_made = []
        
        # Check if logging is already imported
        has_logging_import = 'import logging' in content
        has_logger = 'logger = logging.getLogger(' in content
        
        # Add logging import if needed
        if not has_logging_import and 'print(' in content:
            # Find the best place to add logging import (after other imports)
            lines = content.split('\n')
            import_line_index = -1
            
            for i, line in enumerate(lines):
                if line.strip().startswith('import ') or line.strip().startswith('from '):
                    import_line_index = i
                elif line.strip() and not line.strip().startswith('#'):
                    break
            
            if import_line_index >= 0:
                lines.insert(import_line_index + 1, 'import logging')
                content = '\n'.join(lines)
                changes_made.append("Added 'import logging'")
        
        # Add logger setup if needed
        if not has_logger and 'print(' in content:
            # Add logger after imports
            lines = content.split('\n')
            import_end_index = -1
            
            for i, line in enumerate(lines):
                if line.strip().startswith('import ') or line.strip().startswith('from '):
                    import_end_index = i
                elif line.strip() and not line.strip().startswith('#'):
                    break
            
            if import_end_index >= 0:
                lines.insert(import_end_index + 1, '')
                lines.insert(import_end_index + 2, '# Set up logging for this module')
                lines.insert(import_end_index + 3, 'logger = logging.getLogger(__name__)')
                lines.insert(import_end_index + 4, '')
                content = '\n'.join(lines)
                changes_made.append("Added logger setup")
        
        # Replace print statements with logger calls
        # Pattern to match print statements
        print_patterns = [
            (r'print\(f?"([^"]*)"?\)', r'logger.info("\1")'),  # Simple string prints
            (r'print\(f"([^"]*){([^}]*)}"?\)', r'logger.info(f"\1{\2}")'),  # f-string prints
            (r'print\(f\'([^\']*){([^}]*)}\'?\)', r'logger.info(f\'\1{\2}\')'),  # f-string with single quotes
            (r'print\("WARNING: ([^"]*)"?\)', r'logger.warning("\1")'),  # Warning prints
            (r'print\(f?"ERROR: ([^"]*)"?\)', r'logger.error("\1")'),  # Error prints
            (r'print\(f?"DEBUG: ([^"]*)"?\)', r'logger.debug("\1")'),  # Debug prints
            (r'print\(f"WARNING: ([^"]*){([^}]*)}"?\)', r'logger.warning(f"\1{\2}")'),  # Warning f-strings
            (r'print\(f"ERROR: ([^"]*){([^}]*)}"?\)', r'logger.error(f"\1{\2}")'),  # Error f-strings
            (r'print\(f"DEBUG: ([^"]*){([^}]*)}"?\)', r'logger.debug(f"\1{\2}")'),  # Debug f-strings
        ]
        
        for pattern, replacement in print_patterns:
            new_content = re.sub(pattern, replacement, content)
            if new_content != content:
                changes_made.append(f"Replaced print statements matching pattern: {pattern}")
                content = new_content
        
        # Handle remaining generic print statements
        remaining_prints = re.findall(r'print\([^)]+\)', content)
        for print_stmt in remaining_prints:
            if 'WARNING' in print_stmt.upper():
                new_stmt = print_stmt.replace('print(', 'logger.warning(')
            elif 'ERROR' in print_stmt.upper():
                new_stmt = print_stmt.replace('print(', 'logger.error(')
            elif 'DEBUG' in print_stmt.upper():
                new_stmt = print_stmt.replace('print(', 'logger.debug(')
            else:
                new_stmt = print_stmt.replace('print(', 'logger.info(')
            
            content = content.replace(print_stmt, new_stmt)
            changes_made.append(f"Replaced: {print_stmt} -> {new_stmt}")
        
        # Only write if changes were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ Fixed {file_path}")
            for change in changes_made:
                print(f"   - {change}")
            return True
        else:
            print(f"⏭️  No changes needed in {file_path}")
            return False
            
    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")
        return False

def main():
    """Main function to process all Python files"""
    print("🔧 Fixing WSGI Print Statements")
    print("=" * 50)
    
    # Get current directory
    project_root = Path.cwd()
    
    # Find all Python files (excluding virtual environments and migrations)
    python_files = []
    exclude_dirs = {'.venv', 'venv', '__pycache__', 'migrations', '.git', 'node_modules'}
    
    for py_file in project_root.rglob('*.py'):
        # Skip if in excluded directories
        if any(exclude_dir in str(py_file) for exclude_dir in exclude_dirs):
            continue
        
        # Skip this script itself
        if py_file.name == 'fix_wsgi_print_statements.py':
            continue
            
        python_files.append(py_file)
    
    print(f"Found {len(python_files)} Python files to process")
    print()
    
    fixed_files = 0
    for py_file in python_files:
        if fix_print_statements_in_file(py_file):
            fixed_files += 1
    
    print()
    print("=" * 50)
    print(f"✅ Completed! Fixed {fixed_files} files out of {len(python_files)} total files")
    print()
    print("📋 Next steps:")
    print("1. Test the application locally")
    print("2. Commit and push changes to Git")
    print("3. Deploy to PythonAnywhere")
    print("4. Reload your web app")

if __name__ == "__main__":
    main() 