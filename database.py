import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from models.base import Base
import models  # Import all models
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


# Load environment variables from .env file
load_dotenv()

# Get database URL from environment variable, use SQLite as fallback for development
DATABASE_URL = os.getenv('DATABASE_URL')

# Handle special case for Render.com PostgreSQL URLs
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
# Handle MySQL URLs (ensure pymysql driver is used)
elif DATABASE_URL and DATABASE_URL.startswith("mysql://"):
    DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+pymysql://", 1)
elif not DATABASE_URL:
    # Use absolute path for SQLite database
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inventory.db')
    DATABASE_URL = f'sqlite:///{db_path}'

# Create engine with appropriate settings
if DATABASE_URL.startswith('sqlite'):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
elif DATABASE_URL.startswith('mysql'):
    # MySQL-specific settings for PythonAnywhere
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=280,  # PythonAnywhere has 5-minute connection timeout
        pool_size=5,
        max_overflow=10
    )
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.info("Failed to initialize database: {str(e)}")
        raise

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create session factory using the main engine
Session = sessionmaker(bind=engine)

# Create a session
db_session = Session() 