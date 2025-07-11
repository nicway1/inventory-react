#!/usr/bin/env python3
"""
PythonAnywhere Deployment Script
This script sets the correct environment variables and runs deployment fixes for PythonAnywhere.
"""

import os
import sys
import subprocess

def main():
    logger.info("🚀 Starting PythonAnywhere deployment...")
    
    # Set the correct database URL for PythonAnywhere
    os.environ['DATABASE_URL'] = 'sqlite:////home/nicway2/inventory/inventory.db'
    logger.info("📍 Set DATABASE_URL to: {os.environ['DATABASE_URL']}")
    
    # Set other environment variables if needed
    if not os.environ.get('SECRET_KEY'):
        os.environ['SECRET_KEY'] = 'pythonanywhere-production-key-change-this'
        logger.info("🔑 Set default SECRET_KEY (remember to change this in production)")
    
    # Run the deployment fix script
    logger.info("🔧 Running deployment fix script...")
    try:
        result = subprocess.run([sys.executable, 'deploy_fix.py'], 
                              capture_output=True, text=True)
        
        logger.info("📝 Deploy fix output:")
        logger.info(result.stdout)
        
        if result.stderr:
            logger.info("⚠️  Deploy fix errors:")
            logger.info(result.stderr)
        
        if result.returncode == 0:
            logger.info("✅ Deployment fix completed successfully!")
            logger.info("\n📋 Next steps:")
            logger.info("1. Reload your PythonAnywhere web app")
            logger.info("2. Check the error logs if issues persist")
            logger.info("3. Test the application functionality")
            logger.info("4. Update your environment variables in PythonAnywhere dashboard")
            return 0
        else:
            logger.info("❌ Deployment fix failed!")
            return 1
            
    except Exception as e:
        logger.info("❌ Error running deployment fix: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 