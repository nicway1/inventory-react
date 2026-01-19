"""
Public Website Routes

Serves the TrueLog public website (React app) without requiring authentication.
"""

from flask import Blueprint, send_from_directory, current_app, jsonify
import os

website_bp = Blueprint('website', __name__)


def get_build_path():
    """Get the React build folder path"""
    # Try multiple possible locations
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    build_path = os.path.join(base_dir, 'truelog.com.sg', 'truelog-modern', 'build')

    if os.path.exists(build_path):
        return build_path

    # Fallback for PythonAnywhere
    home = os.path.expanduser('~')
    pa_path = os.path.join(home, 'inventory', 'truelog.com.sg', 'truelog-modern', 'build')
    if os.path.exists(pa_path):
        return pa_path

    return build_path


@website_bp.route('/')
def index():
    """Serve the React app index.html"""
    build_path = get_build_path()
    index_file = os.path.join(build_path, 'index.html')

    if not os.path.exists(index_file):
        return jsonify({
            'error': 'Build not found',
            'build_path': build_path,
            'exists': os.path.exists(build_path),
            'files': os.listdir(build_path) if os.path.exists(build_path) else []
        }), 404

    return send_from_directory(build_path, 'index.html')


@website_bp.route('/<path:path>')
def serve_static(path):
    """Serve static files from the React build folder"""
    build_path = get_build_path()
    file_path = os.path.join(build_path, path)

    if os.path.isfile(file_path):
        return send_from_directory(build_path, path)

    # For React Router - serve index.html for all non-file routes
    return send_from_directory(build_path, 'index.html')
