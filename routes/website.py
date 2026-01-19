"""
Public Website Routes

Serves the TrueLog public website (React app) without requiring authentication.
"""

from flask import Blueprint, send_from_directory, current_app
import os

website_bp = Blueprint('website', __name__)

# Path to the React build folder
WEBSITE_BUILD_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'truelog.com.sg', 'truelog-modern', 'build')


@website_bp.route('/')
def index():
    """Serve the React app index.html"""
    return send_from_directory(WEBSITE_BUILD_PATH, 'index.html')


@website_bp.route('/<path:path>')
def serve_static(path):
    """Serve static files from the React build folder"""
    # Check if the file exists
    file_path = os.path.join(WEBSITE_BUILD_PATH, path)

    if os.path.isfile(file_path):
        return send_from_directory(WEBSITE_BUILD_PATH, path)

    # For React Router - serve index.html for all non-file routes
    # This allows client-side routing to work
    return send_from_directory(WEBSITE_BUILD_PATH, 'index.html')
