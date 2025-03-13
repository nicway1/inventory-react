from alembic import command
from alembic.config import Config
from pathlib import Path

def run_migration():
    # Get the directory containing this script
    base_path = Path(__file__).parent
    
    # Create an Alembic configuration object
    alembic_cfg = Config()
    alembic_cfg.set_main_option('script_location', str(base_path / 'migrations'))
    alembic_cfg.set_main_option('sqlalchemy.url', 'sqlite:///inventory.db')
    
    try:
        # Run the upgrade command
        command.upgrade(alembic_cfg, 'head')
        print("Migration completed successfully!")
    except Exception as e:
        print(f"Error during migration: {e}")
        raise

if __name__ == '__main__':
    run_migration() 