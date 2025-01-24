#!/bin/bash
set -o errexit

# Install Python dependencies
python -m pip install --upgrade pip
python -m pip install gunicorn
python -m pip install -r requirements.txt 