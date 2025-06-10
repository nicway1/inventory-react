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
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(f"Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed!")
        print(f"Error: {e.stderr}")
        return False

def update_database():
    """Update database schema"""
    print(f"\n🔄 Updating database schema...")
    try:
        # Import and run database initialization
        from app import app
        from database import init_db
        
        with app.app_context():
            init_db()
            print("✅ Database schema updated successfully")
            return True
    except Exception as e:
        print(f"❌ Database update failed: {str(e)}")
        return False

def main():
    print("=" * 60)
    print("🚀 PythonAnywhere Deployment Script")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Step 1: Pull latest code from GitHub
    if not run_command("git pull origin main", "Pulling latest code from GitHub"):
        print("\n❌ Deployment failed at code pull step")
        sys.exit(1)
    
    # Step 2: Update database schema
    if not update_database():
        print("\n❌ Deployment failed at database update step")
        sys.exit(1)
    
    # Step 3: Show reload instructions
    print("\n" + "=" * 60)
    print("✅ DEPLOYMENT COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    
    print("\n📋 FINAL STEP - Manual Action Required:")
    print("   1. Go to your PythonAnywhere Web tab")
    print("   2. Click the 'Reload' button for your web app")
    print("   3. Wait for the green 'Running' status")
    
    print("\n🎉 Your ticket category management fixes are now live!")
    print("\n📝 What's new:")
    print("   ✅ Categories can be properly enabled/disabled")
    print("   ✅ Disabled categories won't appear in ticket creation")
    print("   ✅ Individual category editing works correctly")
    print("   ✅ Bulk category management improved")
    
    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main() 