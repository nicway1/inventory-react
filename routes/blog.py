"""
Blog Routes for TrueLog Website

Provides public API endpoints for the blog and admin endpoints for content management.
"""

from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from database import SessionLocal
from models.blog_post import BlogPost, BlogPostStatus
from models.user import User
from utils.auth_decorators import admin_required
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)

blog_bp = Blueprint('blog', __name__)


def slugify(text):
    """Convert text to URL-friendly slug"""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text


# =============================================================================
# PUBLIC API ENDPOINTS (for truelog-modern website)
# =============================================================================

@blog_bp.route('/api/blog/posts', methods=['GET'])
def get_blog_posts():
    """
    Get published blog posts for the public website.
    Supports pagination and search.
    """
    db = SessionLocal()
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '', type=str)

        query = db.query(BlogPost).filter(
            BlogPost.status == BlogPostStatus.PUBLISHED
        ).order_by(BlogPost.published_at.desc())

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (BlogPost.title.ilike(search_term)) |
                (BlogPost.content.ilike(search_term)) |
                (BlogPost.excerpt.ilike(search_term))
            )

        total = query.count()
        posts = query.offset((page - 1) * per_page).limit(per_page).all()

        return jsonify({
            'success': True,
            'posts': [post.to_list_dict() for post in posts],
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        })
    except Exception as e:
        logger.error(f"Error fetching blog posts: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@blog_bp.route('/api/blog/posts/<slug>', methods=['GET'])
def get_blog_post(slug):
    """Get a single blog post by slug"""
    db = SessionLocal()
    try:
        post = db.query(BlogPost).filter(
            BlogPost.slug == slug,
            BlogPost.status == BlogPostStatus.PUBLISHED
        ).first()

        if not post:
            return jsonify({'success': False, 'error': 'Post not found'}), 404

        # Increment view count
        post.increment_view_count()
        db.commit()

        return jsonify({
            'success': True,
            'post': post.to_dict()
        })
    except Exception as e:
        logger.error(f"Error fetching blog post: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@blog_bp.route('/api/blog/recent', methods=['GET'])
def get_recent_posts():
    """Get most recent blog posts (for widgets, sidebars, etc.)"""
    db = SessionLocal()
    try:
        limit = request.args.get('limit', 5, type=int)

        posts = db.query(BlogPost).filter(
            BlogPost.status == BlogPostStatus.PUBLISHED
        ).order_by(BlogPost.published_at.desc()).limit(limit).all()

        return jsonify({
            'success': True,
            'posts': [post.to_list_dict() for post in posts]
        })
    except Exception as e:
        logger.error(f"Error fetching recent posts: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


# =============================================================================
# ADMIN API ENDPOINTS (for inventory system blog management)
# =============================================================================

@blog_bp.route('/admin/blog')
@login_required
@admin_required
def admin_blog_dashboard():
    """Admin dashboard for blog management"""
    db = SessionLocal()
    try:
        posts = db.query(BlogPost).order_by(BlogPost.created_at.desc()).all()
        stats = {
            'total': db.query(BlogPost).count(),
            'published': db.query(BlogPost).filter(BlogPost.status == BlogPostStatus.PUBLISHED).count(),
            'drafts': db.query(BlogPost).filter(BlogPost.status == BlogPostStatus.DRAFT).count(),
            'archived': db.query(BlogPost).filter(BlogPost.status == BlogPostStatus.ARCHIVED).count(),
        }
        return render_template('blog/admin_dashboard.html', posts=posts, stats=stats)
    finally:
        db.close()


@blog_bp.route('/admin/blog/create', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_create_post():
    """Create a new blog post"""
    if request.method == 'POST':
        db = SessionLocal()
        try:
            title = request.form.get('title', '').strip()
            content = request.form.get('content', '').strip()
            excerpt = request.form.get('excerpt', '').strip()
            featured_image = request.form.get('featured_image', '').strip()
            status = request.form.get('status', 'draft')
            meta_title = request.form.get('meta_title', '').strip()
            meta_description = request.form.get('meta_description', '').strip()

            if not title or not content:
                flash('Title and content are required', 'error')
                return render_template('blog/admin_create.html')

            # Generate slug
            slug = slugify(title)
            # Ensure unique slug
            existing = db.query(BlogPost).filter(BlogPost.slug == slug).first()
            if existing:
                slug = f"{slug}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

            post = BlogPost(
                title=title,
                slug=slug,
                content=content,
                excerpt=excerpt or content[:200] + '...' if len(content) > 200 else content,
                featured_image=featured_image,
                author_id=current_user.id,
                status=BlogPostStatus(status),
                meta_title=meta_title or title,
                meta_description=meta_description or excerpt,
                published_at=datetime.utcnow() if status == 'published' else None
            )
            db.add(post)
            db.commit()

            flash('Blog post created successfully', 'success')
            return redirect(url_for('blog.admin_blog_dashboard'))
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating blog post: {e}")
            flash(f'Error creating post: {str(e)}', 'error')
        finally:
            db.close()

    return render_template('blog/admin_create.html')


@blog_bp.route('/admin/blog/edit/<int:post_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_post(post_id):
    """Edit an existing blog post"""
    db = SessionLocal()
    try:
        post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
        if not post:
            flash('Post not found', 'error')
            return redirect(url_for('blog.admin_blog_dashboard'))

        if request.method == 'POST':
            post.title = request.form.get('title', '').strip()
            post.content = request.form.get('content', '').strip()
            post.excerpt = request.form.get('excerpt', '').strip()
            post.featured_image = request.form.get('featured_image', '').strip()
            new_status = request.form.get('status', 'draft')
            post.meta_title = request.form.get('meta_title', '').strip()
            post.meta_description = request.form.get('meta_description', '').strip()

            # Handle status change
            old_status = post.status
            post.status = BlogPostStatus(new_status)

            # Set published_at if transitioning to published
            if old_status != BlogPostStatus.PUBLISHED and post.status == BlogPostStatus.PUBLISHED:
                post.published_at = datetime.utcnow()

            db.commit()
            flash('Blog post updated successfully', 'success')
            return redirect(url_for('blog.admin_blog_dashboard'))

        return render_template('blog/admin_edit.html', post=post)
    except Exception as e:
        db.rollback()
        logger.error(f"Error editing blog post: {e}")
        flash(f'Error updating post: {str(e)}', 'error')
        return redirect(url_for('blog.admin_blog_dashboard'))
    finally:
        db.close()


@blog_bp.route('/admin/blog/delete/<int:post_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_post(post_id):
    """Delete a blog post"""
    db = SessionLocal()
    try:
        post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
        if post:
            db.delete(post)
            db.commit()
            flash('Blog post deleted successfully', 'success')
        else:
            flash('Post not found', 'error')
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting blog post: {e}")
        flash(f'Error deleting post: {str(e)}', 'error')
    finally:
        db.close()

    return redirect(url_for('blog.admin_blog_dashboard'))


# =============================================================================
# ADMIN JSON API ENDPOINTS (for dashboard widget)
# =============================================================================

@blog_bp.route('/api/admin/blog/posts', methods=['GET'])
@login_required
@admin_required
def api_admin_get_posts():
    """Get all blog posts for admin"""
    db = SessionLocal()
    try:
        posts = db.query(BlogPost).order_by(BlogPost.created_at.desc()).all()
        return jsonify({
            'success': True,
            'posts': [post.to_dict() for post in posts]
        })
    except Exception as e:
        logger.error(f"Error fetching admin blog posts: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@blog_bp.route('/api/admin/blog/posts', methods=['POST'])
@login_required
@admin_required
def api_admin_create_post():
    """Create blog post via API"""
    db = SessionLocal()
    try:
        data = request.get_json()
        title = data.get('title', '').strip()
        content = data.get('content', '').strip()

        if not title or not content:
            return jsonify({'success': False, 'error': 'Title and content are required'}), 400

        slug = slugify(title)
        existing = db.query(BlogPost).filter(BlogPost.slug == slug).first()
        if existing:
            slug = f"{slug}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        post = BlogPost(
            title=title,
            slug=slug,
            content=content,
            excerpt=data.get('excerpt', content[:200] + '...' if len(content) > 200 else content),
            featured_image=data.get('featured_image'),
            author_id=current_user.id,
            status=BlogPostStatus(data.get('status', 'draft')),
            meta_title=data.get('meta_title', title),
            meta_description=data.get('meta_description'),
            published_at=datetime.utcnow() if data.get('status') == 'published' else None
        )
        db.add(post)
        db.commit()

        return jsonify({'success': True, 'post': post.to_dict()})
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating blog post via API: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@blog_bp.route('/api/admin/blog/posts/<int:post_id>', methods=['PUT'])
@login_required
@admin_required
def api_admin_update_post(post_id):
    """Update blog post via API"""
    db = SessionLocal()
    try:
        post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
        if not post:
            return jsonify({'success': False, 'error': 'Post not found'}), 404

        data = request.get_json()

        if 'title' in data:
            post.title = data['title'].strip()
        if 'content' in data:
            post.content = data['content'].strip()
        if 'excerpt' in data:
            post.excerpt = data['excerpt'].strip()
        if 'featured_image' in data:
            post.featured_image = data['featured_image']
        if 'meta_title' in data:
            post.meta_title = data['meta_title'].strip()
        if 'meta_description' in data:
            post.meta_description = data['meta_description'].strip()
        if 'status' in data:
            old_status = post.status
            post.status = BlogPostStatus(data['status'])
            if old_status != BlogPostStatus.PUBLISHED and post.status == BlogPostStatus.PUBLISHED:
                post.published_at = datetime.utcnow()

        db.commit()
        return jsonify({'success': True, 'post': post.to_dict()})
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating blog post via API: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@blog_bp.route('/api/admin/blog/posts/<int:post_id>', methods=['DELETE'])
@login_required
@admin_required
def api_admin_delete_post(post_id):
    """Delete blog post via API"""
    db = SessionLocal()
    try:
        post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
        if not post:
            return jsonify({'success': False, 'error': 'Post not found'}), 404

        db.delete(post)
        db.commit()
        return jsonify({'success': True, 'message': 'Post deleted successfully'})
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting blog post via API: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@blog_bp.route('/api/admin/blog/stats', methods=['GET'])
@login_required
@admin_required
def api_admin_blog_stats():
    """Get blog statistics for dashboard widget"""
    db = SessionLocal()
    try:
        stats = {
            'total': db.query(BlogPost).count(),
            'published': db.query(BlogPost).filter(BlogPost.status == BlogPostStatus.PUBLISHED).count(),
            'drafts': db.query(BlogPost).filter(BlogPost.status == BlogPostStatus.DRAFT).count(),
            'archived': db.query(BlogPost).filter(BlogPost.status == BlogPostStatus.ARCHIVED).count(),
            'total_views': db.query(BlogPost).with_entities(
                db.query(BlogPost.view_count).scalar_subquery()
            ).scalar() or 0,
        }

        # Get recent posts
        recent_posts = db.query(BlogPost).order_by(BlogPost.created_at.desc()).limit(5).all()

        return jsonify({
            'success': True,
            'stats': stats,
            'recent_posts': [post.to_list_dict() for post in recent_posts]
        })
    except Exception as e:
        logger.error(f"Error fetching blog stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()
