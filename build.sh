#!/bin/bash
set -o errexit

# Install Python dependencies
python -m pip install --upgrade pip
python -m pip install --only-binary :all: numpy==1.24.3
python -m pip install -r requirements.txt
python -m pip install gunicorn 