#!/usr/bin/env python3
"""
PythonAnywhere Deployment Script
Run this script on PythonAnywhere to update your application with the latest changes.
"""

import subprocess
import sys
import os
from datetime import datetime

def run_command(command, description):
    """Run a shell command and handle errors"""
    logger.info("\n🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        logger.info("✅ {description} completed successfully")
        if result.stdout:
            logger.info("Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        logger.info("❌ {description} failed!")
        logger.info("Error: {e.stderr}")
        return False

def update_database():
    """Update database schema"""
    logger.info("\n🔄 Updating database schema...")
    try:
        # Import and run database initialization
        from app import app
        from database import init_db
        
        with app.app_context():
            init_db()
            logger.info("✅ Database schema updated successfully")
            return True
    except Exception as e:
        logger.info("❌ Database update failed: {str(e)}")
        return False

def main():
    logger.info("=" * 60)
    logger.info("🚀 PythonAnywhere Deployment Script")
    logger.info("=" * 60)
    logger.info("Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Step 1: Pull latest code from GitHub
    if not run_command("git pull origin main", "Pulling latest code from GitHub"):
        logger.info("\n❌ Deployment failed at code pull step")
        sys.exit(1)
    
    # Step 2: Update database schema
    if not update_database():
        logger.info("\n❌ Deployment failed at database update step")
        sys.exit(1)
    
    # Step 3: Show reload instructions
    logger.info("\n" + "=" * 60)
    logger.info("✅ DEPLOYMENT COMPLETED SUCCESSFULLY!")
    logger.info("=" * 60)
    
    logger.info("\n📋 FINAL STEP - Manual Action Required:")
    logger.info("   1. Go to your PythonAnywhere Web tab")
    logger.info("   2. Click the 'Reload' button for your web app")
    logger.info("   3. Wait for the green 'Running' status")
    
    logger.info("\n🎉 Your ticket category management fixes are now live!")
    logger.info("\n📝 What's new:")
    logger.info("   ✅ Categories can be properly enabled/disabled")
    logger.info("   ✅ Disabled categories won't appear in ticket creation")
    logger.info("   ✅ Individual category editing works correctly")
    logger.info("   ✅ Bulk category management improved")
    
    logger.info("\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main() 