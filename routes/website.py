"""
Public Website Routes

Serves the TrueLog public website (React app) without requiring authentication.
"""

from flask import Blueprint, send_from_directory, current_app, jsonify
import os
import mimetypes

website_bp = Blueprint('website', __name__)

# Ensure common MIME types are registered
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('application/json', '.json')


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


@website_bp.route('/static/<path:filename>')
def serve_static_files(filename):
    """Explicitly serve static files (JS, CSS, media)"""
    build_path = get_build_path()
    static_path = os.path.join(build_path, 'static')
    return send_from_directory(static_path, filename)


@website_bp.route('/assets/<path:filename>')
def serve_assets(filename):
    """Explicitly serve asset files (images, etc.)"""
    build_path = get_build_path()
    assets_path = os.path.join(build_path, 'assets')
    return send_from_directory(assets_path, filename)


@website_bp.route('/favicon.ico')
def serve_favicon():
    """Serve favicon"""
    build_path = get_build_path()
    return send_from_directory(build_path, 'favicon.ico')


@website_bp.route('/manifest.json')
def serve_manifest():
    """Serve manifest.json"""
    build_path = get_build_path()
    return send_from_directory(build_path, 'manifest.json')


@website_bp.route('/logo192.png')
def serve_logo192():
    """Serve logo192.png"""
    build_path = get_build_path()
    return send_from_directory(build_path, 'logo192.png')


@website_bp.route('/logo512.png')
def serve_logo512():
    """Serve logo512.png"""
    build_path = get_build_path()
    return send_from_directory(build_path, 'logo512.png')


@website_bp.route('/<path:path>')
def serve_react_routes(path):
    """Serve index.html for all React Router routes"""
    build_path = get_build_path()
    # For React Router - always serve index.html for non-static paths
    return send_from_directory(build_path, 'index.html')
