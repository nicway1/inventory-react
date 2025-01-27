#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Create data directory
mkdir -p data

# Initialize the database
python recreate_db.py 