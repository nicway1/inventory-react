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
        # First, try to get the current heads
        print("Checking database revision status...")
        command.current(alembic_cfg)
        
        # Run the specific migration for company queue permissions
        print("Applying company queue permissions migration...")
        target_revision = "675ed76a9bca"  # The revision ID of our company queue permissions migration
        command.upgrade(alembic_cfg, target_revision)
        print("Company Queue Permissions migration completed successfully!")
    except Exception as e:
        print(f"Error during migration: {e}")
        raise

if __name__ == '__main__':
    run_migration() 