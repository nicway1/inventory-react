import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text

def update_erased_field():
    engine = create_engine('sqlite:///inventory.db')
    
    # Update the erased field to boolean
    with engine.begin() as conn:
        # First, create a temporary column
        conn.execute(text("ALTER TABLE assets ADD COLUMN erased_bool BOOLEAN DEFAULT FALSE"))
        
        # Update the new boolean column based on existing string values
        conn.execute(text("UPDATE assets SET erased_bool = CASE WHEN erased = 'true' THEN TRUE ELSE FALSE END"))
        
        # Drop the old column and rename the new one
        conn.execute(text("ALTER TABLE assets DROP COLUMN erased"))
        conn.execute(text("ALTER TABLE assets RENAME COLUMN erased_bool TO erased"))

if __name__ == "__main__":
    update_erased_field() 