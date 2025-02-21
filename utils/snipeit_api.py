import requests
from config.snipeit_config import SNIPEIT_API_URL, SNIPEIT_API_KEY, ENDPOINTS
import logging

logger = logging.getLogger(__name__)

def is_snipeit_configured():
    """Check if Snipe-IT is properly configured"""
    return (
        SNIPEIT_API_URL and 
        SNIPEIT_API_URL != "https://your-snipeit-instance.com/api/v1" and
        SNIPEIT_API_KEY and 
        SNIPEIT_API_KEY != "your-api-key"
    )

def get_all_assets():
    """Get all assets from Snipe-IT"""
    if not is_snipeit_configured():
        logger.warning("Snipe-IT is not configured. Returning empty asset list.")
        return []
        
    try:
        headers = {
            'Authorization': f'Bearer {SNIPEIT_API_KEY}',
            'Accept': 'application/json'
        }
        
        response = requests.get(
            f"{SNIPEIT_API_URL}{ENDPOINTS['assets']}", 
            headers=headers,
            timeout=5  # Add timeout to prevent hanging
        )
        
        if response.status_code == 200:
            return response.json()['rows']
        logger.error(f"Failed to get assets. Status code: {response.status_code}")
        return []
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to Snipe-IT: {str(e)}")
        return []

def get_asset(asset_id):
    """Get a specific asset from Snipe-IT"""
    if not is_snipeit_configured():
        logger.warning("Snipe-IT is not configured. Returning None for asset.")
        return None
        
    try:
        headers = {
            'Authorization': f'Bearer {SNIPEIT_API_KEY}',
            'Accept': 'application/json'
        }
        
        response = requests.get(
            f"{SNIPEIT_API_URL}{ENDPOINTS['assets']}/{asset_id}", 
            headers=headers,
            timeout=5  # Add timeout to prevent hanging
        )
        
        if response.status_code == 200:
            return response.json()
        logger.error(f"Failed to get asset {asset_id}. Status code: {response.status_code}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to Snipe-IT: {str(e)}")
        return None

def get_all_accessories():
    """Get all accessories from Snipe-IT"""
    if not is_snipeit_configured():
        logger.warning("Snipe-IT is not configured. Returning empty accessories list.")
        return []
        
    try:
        headers = {
            'Authorization': f'Bearer {SNIPEIT_API_KEY}',
            'Accept': 'application/json'
        }
        
        response = requests.get(
            f"{SNIPEIT_API_URL}{ENDPOINTS['accessories']}", 
            headers=headers,
            timeout=5  # Add timeout to prevent hanging
        )
        
        if response.status_code == 200:
            return response.json()['rows']
        logger.error(f"Failed to get accessories. Status code: {response.status_code}")
        return []
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to Snipe-IT: {str(e)}")
        return [] 