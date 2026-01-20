#!/bin/bash
# Deploy and Import TrueLog Blog Posts
# Run this on PythonAnywhere: bash scripts/deploy_and_import_blog.sh

set -e

echo "=== TrueLog Blog Import Script ==="
echo ""

# Step 1: Pull latest changes
echo "1. Pulling latest changes from git..."
cd ~/inventory
git pull

echo ""
echo "2. Running blog import..."

# Step 2: Run import via Python/Flask
cd ~/inventory
python3 -c "
import sys
sys.path.insert(0, '/home/truelog/inventory')

from app import app
from database import SessionLocal
from routes.blog import BLOG_POSTS
from models.blog_post import BlogPost, BlogPostStatus
from datetime import datetime
import re

def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text

with app.app_context():
    db = SessionLocal()
    try:
        before_count = db.query(BlogPost).count()
        print(f'   Blog posts before import: {before_count}')

        imported = 0
        skipped = 0

        for post_data in BLOG_POSTS:
            slug = slugify(post_data['title'])

            # Check if already exists
            existing = db.query(BlogPost).filter(BlogPost.slug == slug).first()
            if existing:
                skipped += 1
                continue

            # Parse date
            published_at = None
            if post_data.get('date'):
                try:
                    published_at = datetime.strptime(post_data['date'], '%Y-%m-%d')
                except:
                    pass

            post = BlogPost(
                title=post_data['title'],
                slug=slug,
                content=post_data.get('content', ''),
                excerpt=post_data.get('excerpt', ''),
                featured_image=post_data.get('featured_image'),
                status=BlogPostStatus.PUBLISHED,
                published_at=published_at,
                meta_title=post_data['title'],
                meta_description=post_data.get('excerpt', '')[:160] if post_data.get('excerpt') else None
            )
            db.add(post)
            imported += 1

        db.commit()
        after_count = db.query(BlogPost).count()

        print(f'   Imported: {imported}')
        print(f'   Skipped (already exist): {skipped}')
        print(f'   Total blog posts now: {after_count}')

    except Exception as e:
        db.rollback()
        print(f'   Error: {e}')
        raise
    finally:
        db.close()

print('Done!')
"

echo ""
echo "=== Import Complete ==="
echo ""
echo "Visit https://truelog-test.pythonanywhere.com/blog to see the results"
