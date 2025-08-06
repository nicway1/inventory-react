#!/usr/bin/env python3
"""
Create upload directories for Knowledge Base images
"""

import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_upload_directories():
    """Create necessary upload directories"""
    try:
        # Create the upload directory structure
        upload_dirs = [
            'static/uploads',
            'static/uploads/knowledge',
            'static/uploads/knowledge/images'
        ]
        
        for directory in upload_dirs:
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                logger.info(f"Created directory: {directory}")
            else:
                logger.info(f"Directory already exists: {directory}")
        
        # Create .gitkeep files to ensure directories are tracked in git
        gitkeep_files = [
            'static/uploads/.gitkeep',
            'static/uploads/knowledge/.gitkeep',
            'static/uploads/knowledge/images/.gitkeep'
        ]
        
        for gitkeep in gitkeep_files:
            if not os.path.exists(gitkeep):
                with open(gitkeep, 'w') as f:
                    f.write('# This file ensures the directory is tracked in git\n')
                logger.info(f"Created .gitkeep file: {gitkeep}")
        
        logger.info("Upload directories created successfully!")
        
    except Exception as e:
        logger.error(f"Error creating upload directories: {str(e)}")
        raise

if __name__ == '__main__':
    create_upload_directories()