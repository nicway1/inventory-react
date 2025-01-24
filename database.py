import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    raise ValueError("No DATABASE_URL environment variable set")

try:
    # Modify the DATABASE_URL to explicitly include SSL mode
    if 'postgresql://' in DATABASE_URL and '?' not in DATABASE_URL:
        DATABASE_URL += '?sslmode=verify-full'

    # Create engine with minimal connection settings
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30
    )
except Exception as e:
    print(f"Failed to initialize database connection: {str(e)}")
    raise

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Import models here after Base is defined
from models.asset import Asset
from models.accessory import Accessory

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    try:
        # Test the connection before creating tables
        with engine.connect() as connection:
            print("Successfully connected to database")
        Base.metadata.create_all(bind=engine)
        print("Database initialized successfully")
    except Exception as e:
        print(f"Failed to initialize database tables: {str(e)}")
        raise 