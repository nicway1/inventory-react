"""
Import WordPress blog posts from the downloaded truelog.com.sg website.
Parses the HTML files and extracts blog post content.
"""

import os
import re
import json
from datetime import datetime
from bs4 import BeautifulSoup
from database import SessionLocal
from models.blog_post import BlogPost, BlogPostStatus
from models.user import User

# Blog post directories (these are individual article pages, not static pages)
BLOG_POST_SLUGS = [
    'ata-carnet-for-broadcasting-professional-equipment-why-pre-planning-is-crucial',
    'how-geo-economic-shifts-are-reshaping-ict-supply-chains-in-2025',
    'kazakhstans-middle-corridor-what-it-means-for-ict-logistics-in-eurasia',
    'navigating-u-s-tariff-volatility-what-ict-logistics-leaders-need-to-know',
    'new-country-unlocked',
    'truelog-launches-ior-eor-services-into-la-reunion',
]

def get_truelog_dir():
    """Get the truelog.com.sg directory path"""
    # Try multiple possible locations
    base_dir = os.path.dirname(os.path.abspath(__file__))
    local_path = os.path.join(base_dir, 'truelog.com.sg')

    if os.path.exists(local_path):
        return local_path

    # Fallback for PythonAnywhere
    home = os.path.expanduser('~')
    pa_path = os.path.join(home, 'inventory', 'truelog.com.sg')
    if os.path.exists(pa_path):
        return pa_path

    return local_path

TRUELOG_DIR = get_truelog_dir()


def extract_blog_post_from_html(html_path, slug):
    """Extract blog post content from WordPress HTML file."""

    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()

        soup = BeautifulSoup(content, 'html.parser')

        # Extract title
        title = None
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.text.split(' - ')[0].strip()

        # Try to get title from og:title
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            title = og_title['content'].split(' - ')[0].strip()

        # Extract meta description
        meta_desc = None
        og_desc = soup.find('meta', property='og:description')
        if og_desc and og_desc.get('content'):
            meta_desc = og_desc['content']

        # Extract published date
        published_at = None
        pub_time = soup.find('meta', property='article:published_time')
        if pub_time and pub_time.get('content'):
            try:
                published_at = datetime.fromisoformat(pub_time['content'].replace('Z', '+00:00'))
            except:
                pass

        # Extract featured image
        featured_image = None
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            featured_image = og_image['content']

        # Try to extract article content
        article_content = None

        # Look for the main content area - WordPress usually uses these patterns
        content_selectors = [
            'article.post-content',
            '.elementor-widget-theme-post-content',
            '.entry-content',
            '.post-content',
            'article .content',
            '.elementor-section-wrap',
        ]

        for selector in content_selectors:
            content_div = soup.select_one(selector)
            if content_div:
                # Clean up the content
                # Remove scripts, styles, and navigation elements
                for tag in content_div.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                    tag.decompose()

                article_content = str(content_div)
                break

        # If no content found, try to find any main content area
        if not article_content:
            # Try to find the main article section
            main_content = soup.find('main') or soup.find('article')
            if main_content:
                for tag in main_content.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                    tag.decompose()
                article_content = str(main_content)

        # If still no content, use the body with heavy cleanup
        if not article_content:
            body = soup.find('body')
            if body:
                # Remove header, footer, navigation
                for tag in body.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                    tag.decompose()
                article_content = str(body)

        # Create excerpt from meta description or first 200 chars of content
        excerpt = meta_desc
        if not excerpt and article_content:
            text_content = BeautifulSoup(article_content, 'html.parser').get_text()
            text_content = ' '.join(text_content.split())  # Normalize whitespace
            excerpt = text_content[:300] + '...' if len(text_content) > 300 else text_content

        return {
            'title': title or slug.replace('-', ' ').title(),
            'slug': slug,
            'content': article_content or '',
            'excerpt': excerpt,
            'featured_image': featured_image,
            'meta_title': title,
            'meta_description': meta_desc,
            'published_at': published_at,
        }

    except Exception as e:
        print(f"Error parsing {html_path}: {e}")
        return None


def import_blog_posts():
    """Import all blog posts from WordPress HTML files."""

    db = SessionLocal()
    imported = 0
    skipped = 0
    errors = 0

    try:
        # Get admin user to set as author
        admin_user = db.query(User).filter(User.username == 'admin').first()
        author_id = admin_user.id if admin_user else None

        for slug in BLOG_POST_SLUGS:
            html_path = os.path.join(TRUELOG_DIR, slug, 'index.html')

            if not os.path.exists(html_path):
                print(f"Skipping {slug} - file not found")
                skipped += 1
                continue

            # Check if post already exists
            existing = db.query(BlogPost).filter(BlogPost.slug == slug).first()
            if existing:
                print(f"Skipping {slug} - already exists")
                skipped += 1
                continue

            # Extract post data
            post_data = extract_blog_post_from_html(html_path, slug)
            if not post_data:
                print(f"Error extracting {slug}")
                errors += 1
                continue

            # Create blog post
            post = BlogPost(
                title=post_data['title'],
                slug=post_data['slug'],
                content=post_data['content'],
                excerpt=post_data['excerpt'],
                featured_image=post_data['featured_image'],
                author_id=author_id,
                status=BlogPostStatus.PUBLISHED,
                meta_title=post_data['meta_title'],
                meta_description=post_data['meta_description'],
                published_at=post_data['published_at'] or datetime.utcnow(),
            )

            db.add(post)
            print(f"Imported: {post_data['title']}")
            imported += 1

        db.commit()
        print(f"\nImport complete: {imported} imported, {skipped} skipped, {errors} errors")

    except Exception as e:
        db.rollback()
        print(f"Error during import: {e}")
    finally:
        db.close()


def list_available_posts():
    """List all available blog posts for import."""

    print("Available blog posts for import:")
    print("-" * 50)

    for slug in BLOG_POST_SLUGS:
        html_path = os.path.join(TRUELOG_DIR, slug, 'index.html')
        exists = os.path.exists(html_path)
        status = "Found" if exists else "NOT FOUND"
        print(f"  {slug}: {status}")


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--list':
        list_available_posts()
    elif len(sys.argv) > 1 and sys.argv[1] == '--yes':
        # Auto-confirm for remote execution
        print("WordPress Blog Post Importer")
        print("=" * 50)
        list_available_posts()
        print("\n")
        import_blog_posts()
    else:
        print("WordPress Blog Post Importer")
        print("=" * 50)
        list_available_posts()
        print("\n")

        confirm = input("Do you want to import these posts? (y/n): ")
        if confirm.lower() == 'y':
            import_blog_posts()
        else:
            print("Import cancelled.")
