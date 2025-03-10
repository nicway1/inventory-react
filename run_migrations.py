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
        # Create migrations directory if it doesn't exist
        os.makedirs('migrations/versions', exist_ok=True)

        # Get absolute path to alembic.ini
        alembic_ini = os.path.join(project_root, "alembic.ini")
        if not os.path.exists(alembic_ini):
            print(f"Error: Could not find alembic.ini at {alembic_ini}")
            sys.exit(1)

        # Create Alembic configuration
        alembic_cfg = Config(alembic_ini)
        
        # Set the path to your migrations directory
        migrations_dir = os.path.join(project_root, "migrations")
        alembic_cfg.set_main_option("script_location", migrations_dir)
        
        # Set the SQLAlchemy URL
        db_path = os.path.join(project_root, "inventory.db")
        alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:////{db_path}")
        
        # Run the migration
        command.upgrade(alembic_cfg, "head")
        print("Migration completed successfully!")
        
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        print(f"Current directory: {os.getcwd()}")
        print(f"Project root: {project_root}")
        print(f"Python path: {sys.path}")
        sys.exit(1)

if __name__ == "__main__":
    run_migrations() 