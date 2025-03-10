import os
import sys
from alembic import command
from alembic.config import Config

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def run_migrations():
    try:
        # Get the path to alembic.ini
        alembic_cfg = Config(os.path.join(project_root, "alembic.ini"))
        
        # Set the path to your migrations directory
        alembic_cfg.set_main_option("script_location", os.path.join(project_root, "migrations"))
        
        # Set the SQLAlchemy URL
        alembic_cfg.set_main_option("sqlalchemy.url", "sqlite:////" + os.path.join(project_root, "inventory.db"))
        
        # Run the migration
        command.upgrade(alembic_cfg, "head")
        
        print("Migration completed successfully!")
        
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_migrations() 