"""
Script to add a 'Change Case Owner' button to the ticket view page
"""

import os
import re

def add_change_owner_button():
    template_file = 'templates/tickets/view.html'
    
    if not os.path.exists(template_file):
        logger.info("Error: {template_file} not found!")
        return False
    
    with open(template_file, 'r') as f:
        content = f.read()
    
    # Look for the Change Status button to add our button after it
    pattern = r'<button [^>]*?>\s*<[^>]*?>\s*Change Status\s*</button>'
    
    # Find the pattern
    match = re.search(pattern, content)
    if not match:
        logger.info("Could not find the Change Status button")
        return False
    
    # Get the matched text and its position
    matched_text = match.group(0)
    end_pos = match.end()
    
    # Create our new button with similar styling
    new_button = """
            <button class="sf-button" onclick="toggleAssignForm()">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
                </svg>
                Change Case Owner
            </button>"""
    
    # Insert the new button after the Change Status button
    updated_content = content[:end_pos] + new_button + content[end_pos:]
    
    # Write the changes back to the file
    with open(template_file, 'w') as f:
        f.write(updated_content)
    
    logger.info("Successfully added Change Case Owner button to {template_file}")
    return True

if __name__ == "__main__":
    logger.info("==== Adding Change Case Owner button ====")
    
    if add_change_owner_button():
        logger.info("\nSuccessfully added the Change Case Owner button")
        logger.info("Please restart your web application for the changes to take effect")
    else:
        logger.info("\nWARNING: Failed to add the Change Case Owner button!")
        logger.info("You may need to manually add the button to templates/tickets/view.html") 