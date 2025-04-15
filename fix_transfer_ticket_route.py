"""
Script to fix the transfer_ticket route to match the template's expectations
"""

import os
import re

def fix_transfer_ticket_route():
    routes_file = 'routes/tickets.py'
    
    if not os.path.exists(routes_file):
        print(f"Error: {routes_file} not found!")
        return False
    
    with open(routes_file, 'r') as f:
        content = f.read()
    
    # Find the transfer_ticket route definition
    pattern = r"@tickets_bp\.route\('/<int:ticket_id>/transfer', methods=\['POST'\]\)\n@login_required\ndef transfer_ticket\(ticket_id\):"
    
    # Replace with named endpoint version
    replacement = "@tickets_bp.route('/<int:ticket_id>/transfer', methods=['POST'], endpoint='transfer_ticket')\n@login_required\ndef transfer_ticket(ticket_id):"
    
    # Check if pattern exists
    if re.search(pattern, content):
        # Make the replacement
        updated_content = re.sub(pattern, replacement, content)
        
        # Write changes back to file
        with open(routes_file, 'w') as f:
            f.write(updated_content)
        
        print(f"Successfully updated transfer_ticket route in {routes_file}")
        return True
    else:
        print(f"Could not find transfer_ticket route in {routes_file}")
        return False

if __name__ == "__main__":
    print("==== Fixing transfer_ticket route ====")
    
    if fix_transfer_ticket_route():
        print("\nSuccessfully fixed the transfer_ticket route")
        print("Please restart your web application for the changes to take effect")
    else:
        print("\nWARNING: Failed to fix the transfer_ticket route!")
        print("You may need to manually update the route in routes/tickets.py to include 'endpoint='transfer_ticket''") 