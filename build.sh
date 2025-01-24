#!/bin/bash
set -o errexit

# Install system dependencies
apt-get update
apt-get install -y python3-dev gcc

# Install Python dependencies
python -m pip install --upgrade pip
python -m pip install wheel
python -m pip install -r requirements.txt
python -m pip install gunicorn 