#!/usr/bin/env python3
"""
PythonAnywhere Deployment Script
This script sets the correct environment variables and runs deployment fixes for PythonAnywhere.
"""

import os
import sys
import subprocess

def main():
    print("🚀 Starting PythonAnywhere deployment...")
    
    # Set the correct database URL for PythonAnywhere
    os.environ['DATABASE_URL'] = 'sqlite:////home/nicway2/inventory/inventory.db'
    print(f"📍 Set DATABASE_URL to: {os.environ['DATABASE_URL']}")
    
    # Set other environment variables if needed
    if not os.environ.get('SECRET_KEY'):
        os.environ['SECRET_KEY'] = 'pythonanywhere-production-key-change-this'
        print("🔑 Set default SECRET_KEY (remember to change this in production)")
    
    # Run the deployment fix script
    print("🔧 Running deployment fix script...")
    try:
        result = subprocess.run([sys.executable, 'deploy_fix.py'], 
                              capture_output=True, text=True)
        
        print("📝 Deploy fix output:")
        print(result.stdout)
        
        if result.stderr:
            print("⚠️  Deploy fix errors:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ Deployment fix completed successfully!")
            print("\n📋 Next steps:")
            print("1. Reload your PythonAnywhere web app")
            print("2. Check the error logs if issues persist")
            print("3. Test the application functionality")
            print("4. Update your environment variables in PythonAnywhere dashboard")
            return 0
        else:
            print("❌ Deployment fix failed!")
            return 1
            
    except Exception as e:
        print(f"❌ Error running deployment fix: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 