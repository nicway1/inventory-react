#!/usr/bin/env python3
"""
Migration script to add Knowledge Base tables to the database.
This script adds the new knowledge base tables and updates the permissions table.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Add the current directory to Python path so we can import our models
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine, SessionLocal
from models.base import Base
from models.permission import Permission
from models.enums import UserType
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_knowledge_base_permissions():
    """Add knowledge base permission columns to existing permissions table"""
    db = SessionLocal()
    try:
        # Check if columns already exist
        result = db.execute(text("PRAGMA table_info(permissions)"))
        columns = [row[1] for row in result.fetchall()]
        
        knowledge_columns = [
            'can_view_knowledge_base',
            'can_create_articles',
            'can_edit_articles',
            'can_delete_articles',
            'can_manage_categories',
            'can_view_restricted_articles'
        ]
        
        # Add missing columns
        for column in knowledge_columns:
            if column not in columns:
                logger.info(f"Adding column {column} to permissions table")
                db.execute(text(f"ALTER TABLE permissions ADD COLUMN {column} BOOLEAN DEFAULT 1"))
        
        db.commit()
        logger.info("Knowledge base permission columns added successfully")
        
        # Update existing permissions with default values
        permissions = db.query(Permission).all()
        for permission in permissions:
            if permission.user_type == UserType.SUPER_ADMIN:
                permission.can_view_knowledge_base = True
                permission.can_create_articles = True
                permission.can_edit_articles = True
                permission.can_delete_articles = True
                permission.can_manage_categories = True
                permission.can_view_restricted_articles = True
            elif permission.user_type == UserType.COUNTRY_ADMIN:
                permission.can_view_knowledge_base = True
                permission.can_create_articles = True
                permission.can_edit_articles = True
                permission.can_delete_articles = False
                permission.can_manage_categories = True
                permission.can_view_restricted_articles = False
            elif permission.user_type == UserType.CLIENT:
                permission.can_view_knowledge_base = True
                permission.can_create_articles = False
                permission.can_edit_articles = False
                permission.can_delete_articles = False
                permission.can_manage_categories = False
                permission.can_view_restricted_articles = False
            else:  # Supervisor
                permission.can_view_knowledge_base = True
                permission.can_create_articles = False
                permission.can_edit_articles = False
                permission.can_delete_articles = False
                permission.can_manage_categories = False
                permission.can_view_restricted_articles = False
        
        db.commit()
        logger.info("Existing permissions updated with knowledge base defaults")
        
    except Exception as e:
        logger.error(f"Error adding knowledge base permissions: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

def create_knowledge_base_tables():
    """Create all knowledge base tables"""
    try:
        # Import knowledge base models to ensure they're registered
        from models.knowledge_article import KnowledgeArticle
        from models.knowledge_category import KnowledgeCategory
        from models.knowledge_tag import KnowledgeTag, article_tags
        from models.knowledge_feedback import KnowledgeFeedback
        from models.knowledge_attachment import KnowledgeAttachment
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Knowledge base tables created successfully")
        
    except Exception as e:
        logger.error(f"Error creating knowledge base tables: {str(e)}")
        raise

def create_default_categories():
    """Create some default categories"""
    db = SessionLocal()
    try:
        from models.knowledge_category import KnowledgeCategory
        
        # Check if categories already exist
        existing_categories = db.query(KnowledgeCategory).count()
        if existing_categories > 0:
            logger.info("Categories already exist, skipping default category creation")
            return
        
        default_categories = [
            {
                'name': 'IT Procedures',
                'description': 'Information Technology procedures and guidelines',
                'sort_order': 1
            },
            {
                'name': 'HR Policies',
                'description': 'Human Resources policies and procedures',
                'sort_order': 2
            },
            {
                'name': 'Troubleshooting',
                'description': 'Common issues and their solutions',
                'sort_order': 3
            },
            {
                'name': 'Training Materials',
                'description': 'Training guides and educational content',
                'sort_order': 4
            }
        ]
        
        for cat_data in default_categories:
            category = KnowledgeCategory(**cat_data)
            db.add(category)
        
        db.commit()
        logger.info("Default categories created successfully")
        
    except Exception as e:
        logger.error(f"Error creating default categories: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

def main():
    """Run the migration"""
    logger.info("Starting knowledge base migration...")
    
    try:
        # Step 1: Add knowledge base permission columns
        logger.info("Step 1: Adding knowledge base permissions...")
        add_knowledge_base_permissions()
        
        # Step 2: Create knowledge base tables
        logger.info("Step 2: Creating knowledge base tables...")
        create_knowledge_base_tables()
        
        # Step 3: Create default categories
        logger.info("Step 3: Creating default categories...")
        create_default_categories()
        
        logger.info("Knowledge base migration completed successfully!")
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()