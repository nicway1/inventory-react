#!/usr/bin/env python3
"""
Version Increment Script
Use this script to increment version numbers before deployment

Usage:
    python increment_version.py [major|minor|patch|build]
    
Examples:
    python increment_version.py build    # Increment build number (0.5.0.1 -> 0.5.0.2)
    python increment_version.py patch    # Increment patch (0.5.0.1 -> 0.5.1.1)
    python increment_version.py minor    # Increment minor (0.5.0.1 -> 0.6.0.1)
    python increment_version.py major    # Increment major (0.5.0.1 -> 1.0.0.1)
"""

import sys
import re
from datetime import datetime

def read_version_file():
    """Read the current version.py file"""
    with open('version.py', 'r') as f:
        content = f.read()
    return content

def write_version_file(content):
    """Write the updated version.py file"""
    with open('version.py', 'w') as f:
        f.write(content)

def increment_version(increment_type='build'):
    """Increment version based on type"""
    content = read_version_file()
    
    # Extract current version numbers
    major_match = re.search(r'VERSION_MAJOR = (\d+)', content)
    minor_match = re.search(r'VERSION_MINOR = (\d+)', content)
    patch_match = re.search(r'VERSION_PATCH = (\d+)', content)
    build_match = re.search(r'VERSION_BUILD = (\d+)', content)
    
    if not all([major_match, minor_match, patch_match, build_match]):
        print("Error: Could not parse version numbers from version.py")
        return False
    
    major = int(major_match.group(1))
    minor = int(minor_match.group(1))
    patch = int(patch_match.group(1))
    build = int(build_match.group(1))
    
    # Store old version
    old_version = f"{major}.{minor}.{patch}.{build}"
    
    # Increment based on type
    if increment_type == 'major':
        major += 1
        minor = 0
        patch = 0
        build = 1
    elif increment_type == 'minor':
        minor += 1
        patch = 0
        build = 1
    elif increment_type == 'patch':
        patch += 1
        build = 1
    elif increment_type == 'build':
        build += 1
    else:
        print(f"Error: Unknown increment type '{increment_type}'")
        print("Valid types: major, minor, patch, build")
        return False
    
    # Update version numbers in content
    content = re.sub(r'VERSION_MAJOR = \d+', f'VERSION_MAJOR = {major}', content)
    content = re.sub(r'VERSION_MINOR = \d+', f'VERSION_MINOR = {minor}', content)
    content = re.sub(r'VERSION_PATCH = \d+', f'VERSION_PATCH = {patch}', content)
    content = re.sub(r'VERSION_BUILD = \d+', f'VERSION_BUILD = {build}', content)
    
    # Update build timestamp
    now = datetime.now()
    build_date = now.strftime("%Y-%m-%d")
    build_time = now.strftime("%H:%M:%S")
    
    content = re.sub(r'BUILD_DATE = datetime\.now\(\)\.strftime\("%Y-%m-%d"\)', 
                     f'BUILD_DATE = "{build_date}"', content)
    content = re.sub(r'BUILD_TIME = datetime\.now\(\)\.strftime\("%H:%M:%S"\)', 
                     f'BUILD_TIME = "{build_time}"', content)
    
    # Write the updated file
    write_version_file(content)
    
    new_version = f"{major}.{minor}.{patch}.{build}"
    print(f"Version updated: {old_version} -> {new_version}")
    print(f"Build timestamp: {build_date} {build_time}")
    
    return True

def main():
    """Main function"""
    if len(sys.argv) > 1:
        increment_type = sys.argv[1].lower()
    else:
        increment_type = 'build'  # Default to build increment
    
    if increment_version(increment_type):
        print("Version increment successful!")
        print("\nNext steps:")
        print("1. Review the changes in version.py")
        print("2. Update the changelog if needed")
        print("3. Commit and deploy")
    else:
        print("Version increment failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 