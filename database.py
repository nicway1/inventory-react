import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from models.base import Base
import models  # Import all models

# Load environment variables from .env file
load_dotenv()

# Get database URL from environment variable, use SQLite as fallback for development
DATABASE_URL = os.getenv('DATABASE_URL')

# Handle special case for Render.com PostgreSQL URLs
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
elif not DATABASE_URL:
    # Use absolute path for SQLite database
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inventory.db')
    DATABASE_URL = f'sqlite:///{db_path}'

# Create engine with appropriate settings
if DATABASE_URL.startswith('sqlite'):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        print("Database initialized successfully")
    except Exception as e:
        print(f"Failed to initialize database: {str(e)}")
        raise

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 