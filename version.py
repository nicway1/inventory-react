"""
Application Version Management
This file tracks the version information for the Inventory Management System
"""

import os
from datetime import datetime

# Version Information
VERSION_MAJOR = 8
VERSION_MINOR = 2
VERSION_PATCH = 1
VERSION_BUILD = 2

# Build the version string
VERSION = f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_PATCH}"
VERSION_FULL = f"{VERSION}.{VERSION_BUILD}"

# Build information
BUILD_DATE = "2025-01-08"
BUILD_TIME = "16:45:00"

# Git information (if available)
def get_git_info():
    """Get git commit information if available"""
    try:
        import subprocess
        commit_hash = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode('ascii').strip()
        branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).decode('ascii').strip()
        return {
            'commit': commit_hash,
            'branch': branch
        }
    except:
        return {
            'commit': 'unknown',
            'branch': 'unknown'
        }

GIT_INFO = get_git_info()

# Version metadata
VERSION_INFO = {
    'version': VERSION,
    'version_full': VERSION_FULL,
    'major': VERSION_MAJOR,
    'minor': VERSION_MINOR,
    'patch': VERSION_PATCH,
    'build': VERSION_BUILD,
    'build_date': BUILD_DATE,
    'build_time': BUILD_TIME,
    'git_commit': GIT_INFO['commit'],
    'git_branch': GIT_INFO['branch'],
    'name': 'Inventory Management System',
    'codename': 'Phoenix'
}

def get_version_string():
    """Get a formatted version string"""
    return f"v{VERSION_FULL}"

def get_full_version_info():
    """Get complete version information"""
    return VERSION_INFO

def increment_build():
    """Increment build number (for deployment scripts)"""
    global VERSION_BUILD, VERSION_FULL
    VERSION_BUILD += 1
    VERSION_FULL = f"{VERSION}.{VERSION_BUILD}"
    return VERSION_FULL 