from alembic import command
from alembic.config import Config
import os

def run_migrations():
    # Create migrations directory if it doesn't exist
    os.makedirs('migrations/versions', exist_ok=True)

    # Create Alembic configuration
    alembic_cfg = Config("alembic.ini")
    
    try:
        # Run the migration
        command.upgrade(alembic_cfg, "head")
        print("Migration completed successfully!")
    except Exception as e:
        print(f"Error during migration: {str(e)}")

if __name__ == "__main__":
    run_migrations() 