"""
Migration script to create the blog_posts table.
Run this script to add blog functionality to the inventory system.
"""

import os
import sys
from sqlalchemy import text
from database import SessionLocal, engine
from models.blog_post import BlogPost, BlogPostStatus
from models.base import Base

def create_blog_posts_table():
    """Create the blog_posts table if it doesn't exist."""

    db = SessionLocal()
    try:
        # Check if table already exists
        result = db.execute(text("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_name = 'blog_posts'
        """))

        exists = result.scalar() > 0

        if exists:
            print("blog_posts table already exists.")
            return True

        # Create the table using SQLAlchemy
        BlogPost.__table__.create(engine, checkfirst=True)

        print("blog_posts table created successfully!")
        return True

    except Exception as e:
        print(f"Error creating blog_posts table: {e}")

        # Try raw SQL for MySQL compatibility
        try:
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS blog_posts (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(500) NOT NULL,
                    slug VARCHAR(500) NOT NULL UNIQUE,
                    content LONGTEXT NOT NULL,
                    excerpt TEXT,
                    featured_image VARCHAR(500),
                    author_id INT,
                    status ENUM('draft', 'published', 'archived') DEFAULT 'draft',
                    meta_title VARCHAR(255),
                    meta_description TEXT,
                    view_count INT DEFAULT 0,
                    published_at DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    wp_post_id INT UNIQUE,
                    FOREIGN KEY (author_id) REFERENCES users(id),
                    INDEX idx_slug (slug),
                    INDEX idx_status (status),
                    INDEX idx_published_at (published_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """))
            db.commit()
            print("blog_posts table created successfully using raw SQL!")
            return True
        except Exception as e2:
            print(f"Error with raw SQL: {e2}")
            return False
    finally:
        db.close()


if __name__ == '__main__':
    create_blog_posts_table()
