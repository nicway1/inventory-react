# Snipe-IT API Configuration
SNIPEIT_API_URL = "https://truelogg.snipe-it.io"  # Base URL without trailing slash
SNIPEIT_API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiIxIiwianRpIjoiY2Q3N2VkNmYwMTU1MmRkZTYwMjZmNGUxODE4Yzk4NTZiMGMzNGRjOTk3ZGU3YWEyMGEzNjJmYzZlZjcwN2UzMGQwMjQ0M2VmMWEyMjI0MDkiLCJpYXQiOjE3MzY1MDE0NTEuOTkyMTIyLCJuYmYiOjE3MzY1MDE0NTEuOTkyMTI2LCJleHAiOjIzNjc2NTM0NTEuOTg2NTg2LCJzdWIiOiIxIiwic2NvcGVzIjpbXX0.JJ2K6EQdDPOmozxg_pXPguJwjpu__VieUhj7Hn5QQLmNZA8nuqxf-wSB4RS1pKUAHrMC1OnU3xP7OZyhofctTaZ4g0scgj-gTVwoQ1kEosiqtjS9cDTtrr5kRsJP_JWgt3wsueeCxc0tJoe7ixQWIGl7yr2nCO2Dmyzd1XnOKY5oMWglyEnsvMnkQ3uVRo2byCTT0_XBqA_FcR4zmdDug6oJz9e46SxWX_R8WvXt0uq0tKMtJN18m5kLVZC73QlwZSI08qaqflIoGuyAhBnJWUJxXXDERVNqQi3fwMTeb6BM7t4Mk58q3O_R-8uQ0jzzO1i7fHlr-ngLh48wMBNFkXdk2y1MnAcGKK7LnXJ8GURwGIw6EsK-nzr89RcGH-0kqJLU6PiQeCdyVmhve5dc_FojoJdQJ7td6KMvy62JZpF_Egf9ry_99oUbiyqqMgmO656jbE9ySbQPok-WgddAdZU6mu_UzrQPHTsZOGsPVnwJz3iSFDmTFbNeExgkRHJk3FYwdEjnTCKwLhyOOY_lkrXRzJbTVIgV7_s_v7kcnTNAdXs7-9ido4v9OTO8Wnn8MhbF9jUK3dqEVq5nZiqZjMKq6glwkLGXZA8idawGdz2yijX3YC1BBKZtf8VWB4YkRpk1eKpwzQUYcqrA_X0iAz1IGOcmMLbxZguRJJTMbzE"  # Replace with your API key

# API Endpoints
ENDPOINTS = {
    'assets': '/api/v1/hardware',
    'accessories': '/api/v1/accessories',
    'categories': '/api/v1/categories',
    'companies': '/api/v1/companies',
    'models': '/api/v1/models',
    'users': '/api/v1/users',
    'locations': '/api/v1/locations',
    'status_labels': '/api/v1/statuslabels'
}

# Data storage configuration
DATA_DIR = 'data'
COMMENTS_FILE = 'data/comments.json'
USERS_FILE = 'data/users.json'
TICKETS_FILE = 'data/tickets.json'
SHIPMENTS_FILE = 'data/shipments.json'
QUEUES_FILE = 'data/queues.json'

# 17TRACK API Configuration
TRACK17_API_KEY = "your_17track_api_key"
TRACK17_BASE_URL = "https://api.17track.net/track/v2" 