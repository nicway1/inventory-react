#!/usr/bin/env python3
"""
Check @mention setup in templates
"""

import os

def check_files():
    """Check if all required files exist and have the right content"""
    
    print("=" * 60)
    print("Checking @mention Setup")
    print("=" * 60)
    
    files_to_check = [
        ('templates/development/bug_view.html', 'const availableUsers = {{ users_json|safe }}'),
        ('templates/development/feature_view.html', 'const availableUsers = {{ users_json|safe }}'),
    ]
    
    all_ok = True
    
    for filepath, search_text in files_to_check:
        print(f"\n✓ Checking: {filepath}")
        
        if not os.path.exists(filepath):
            print(f"  ✗ File not found!")
            all_ok = False
            continue
        
        with open(filepath, 'r') as f:
            content = f.read()
            
        if search_text in content:
            print(f"  ✓ Contains @mention JavaScript")
            
            # Check for checkMention function
            if 'function checkMention' in content:
                print(f"  ✓ Has checkMention function")
            else:
                print(f"  ✗ Missing checkMention function")
                all_ok = False
                
            # Check for mentionDropdown
            if 'id="mentionDropdown"' in content:
                print(f"  ✓ Has mention dropdown element")
            else:
                print(f"  ✗ Missing mention dropdown element")
                all_ok = False
        else:
            print(f"  ✗ Missing @mention JavaScript setup")
            all_ok = False
    
    print("\n" + "=" * 60)
    if all_ok:
        print("✓ All @mention components are present")
        print("\nIf @mention still doesn't work, check:")
        print("1. Browser console for JavaScript errors")
        print("2. Verify web app was reloaded after git pull")
        print("3. Clear browser cache")
    else:
        print("✗ Some components are missing")
        print("\nAction needed:")
        print("1. Run: git pull origin main")
        print("2. Reload web app")
    print("=" * 60)
    
    return all_ok

if __name__ == '__main__':
    import sys
    success = check_files()
    sys.exit(0 if success else 1)
