import requests
from config.snipeit_config import SNIPEIT_API_URL, SNIPEIT_API_KEY, ENDPOINTS

def get_all_assets():
    headers = {
        'Authorization': f'Bearer {SNIPEIT_API_KEY}',
        'Accept': 'application/json'
    }
    
    response = requests.get(
        f"{SNIPEIT_API_URL}{ENDPOINTS['assets']}", 
        headers=headers
    )
    
    if response.status_code == 200:
        return response.json()['rows']
    return []

def get_asset(asset_id):
    headers = {
        'Authorization': f'Bearer {SNIPEIT_API_KEY}',
        'Accept': 'application/json'
    }
    
    response = requests.get(
        f"{SNIPEIT_API_URL}{ENDPOINTS['assets']}/{asset_id}", 
        headers=headers
    )
    
    if response.status_code == 200:
        return response.json()
    return None 

def get_all_accessories():
    headers = {
        'Authorization': f'Bearer {SNIPEIT_API_KEY}',
        'Accept': 'application/json'
    }
    
    response = requests.get(
        f"{SNIPEIT_API_URL}{ENDPOINTS['accessories']}", 
        headers=headers
    )
    
    if response.status_code == 200:
        return response.json()['rows']
    return [] 