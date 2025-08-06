from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from sqlalchemy import or_, and_, desc, func
from database import SessionLocal
from models.knowledge_article import KnowledgeArticle, ArticleStatus, ArticleVisibility
from models.knowledge_category import KnowledgeCategory
from models.knowledge_tag import KnowledgeTag
from models.knowledge_feedback import KnowledgeFeedback
from models.knowledge_attachment import KnowledgeAttachment
from utils.auth_decorators import permission_required
import logging

logger = logging.getLogger(__name__)

knowledge_bp = Blueprint('knowledge', __name__, url_prefix='/knowledge')

def check_article_permission(article, permission_type='view'):
    """Check if current user has permission to access an article"""
    if not current_user.is_authenticated:
        return False
    
    # Check basic knowledge base permission
    if not current_user.permissions.can_view_knowledge_base:
        return False
    
    # Check article visibility
    if article.visibility == ArticleVisibility.PUBLIC:
        return True
    elif article.visibility == ArticleVisibility.INTERNAL:
        return True  # All authenticated users can view internal articles
    elif article.visibility == ArticleVisibility.RESTRICTED:
        return current_user.permissions.can_view_restricted_articles
    
    # Check specific permissions for edit/delete
    if permission_type == 'edit':
        return (current_user.permissions.can_edit_articles or 
                article.author_id == current_user.id)
    elif permission_type == 'delete':
        return (current_user.permissions.can_delete_articles or 
                article.author_id == current_user.id)
    
    return True

@knowledge_bp.route('/')
@login_required
@permission_required('can_view_knowledge_base')
def index():
    """Main knowledge base page"""
    db = SessionLocal()
    try:
        # Get categories with article counts
        categories = db.query(KnowledgeCategory).filter_by(parent_id=None).order_by(KnowledgeCategory.sort_order).all()
        
        # Get recent articles (last 10)
        recent_articles = db.query(KnowledgeArticle).filter(
            KnowledgeArticle.status == ArticleStatus.PUBLISHED
        ).order_by(desc(KnowledgeArticle.created_at)).limit(10).all()
        
        # Filter articles based on user permissions
        filtered_recent = []
        for article in recent_articles:
            if check_article_permission(article):
                filtered_recent.append(article)
        
        # Get popular articles (most viewed)
        popular_articles = db.query(KnowledgeArticle).filter(
            KnowledgeArticle.status == ArticleStatus.PUBLISHED
        ).order_by(desc(KnowledgeArticle.view_count)).limit(10).all()
        
        # Filter popular articles based on user permissions
        filtered_popular = []
        for article in popular_articles:
            if check_article_permission(article):
                filtered_popular.append(article)
        
        return render_template('knowledge/index.html',
                             categories=categories,
                             recent_articles=filtered_recent,
                             popular_articles=filtered_popular)
    finally:
        db.close()

@knowledge_bp.route('/search')
@login_required
@permission_required('can_view_knowledge_base')
def search():
    """Search knowledge base articles"""
    query = request.args.get('q', '').strip()
    category_id = request.args.get('category')
    page = int(request.args.get('page', 1))
    per_page = 10
    
    if not query:
        return render_template('knowledge/search_results.html',
                             articles=[],
                             query='',
                             total=0,
                             page=page,
                             per_page=per_page,
                             categories=[])
    
    db = SessionLocal()
    try:
        # Build search query
        search_query = db.query(KnowledgeArticle).filter(
            KnowledgeArticle.status == ArticleStatus.PUBLISHED
        )
        
        # Add text search
        search_terms = query.split()
        for term in search_terms:
            search_query = search_query.filter(
                or_(
                    KnowledgeArticle.title.ilike(f'%{term}%'),
                    KnowledgeArticle.content.ilike(f'%{term}%'),
                    KnowledgeArticle.summary.ilike(f'%{term}%')
                )
            )
        
        # Add category filter
        if category_id:
            search_query = search_query.filter(KnowledgeArticle.category_id == category_id)
        
        # Get total count
        total = search_query.count()
        
        # Apply pagination and ordering
        articles = search_query.order_by(
            desc(KnowledgeArticle.view_count),
            desc(KnowledgeArticle.updated_at)
        ).offset((page - 1) * per_page).limit(per_page).all()
        
        # Filter articles based on user permissions
        filtered_articles = []
        for article in articles:
            if check_article_permission(article):
                filtered_articles.append(article)
        
        # Get categories for filter dropdown
        categories = db.query(KnowledgeCategory).order_by(KnowledgeCategory.name).all()
        
        return render_template('knowledge/search_results.html',
                             articles=filtered_articles,
                             query=query,
                             total=total,
                             page=page,
                             per_page=per_page,
                             categories=categories,
                             selected_category=category_id)
    finally:
        db.close()

@knowledge_bp.route('/article/<int:article_id>')
@login_required
@permission_required('can_view_knowledge_base')
def view_article(article_id):
    """View individual article"""
    db = SessionLocal()
    try:
        article = db.query(KnowledgeArticle).options(
            joinedload(KnowledgeArticle.category),
            joinedload(KnowledgeArticle.author),
            joinedload(KnowledgeArticle.tags),
            joinedload(KnowledgeArticle.feedback),
            joinedload(KnowledgeArticle.attachments)
        ).filter_by(id=article_id).first()
        
        if not article or article.status != ArticleStatus.PUBLISHED:
            abort(404)
        
        # Check permissions
        if not check_article_permission(article):
            abort(403)
        
        # Increment view count
        article.increment_view_count()
        db.commit()
        
        # Get related articles (same category)
        related_articles = []
        if article.category:
            related_articles = db.query(KnowledgeArticle).filter(
                and_(
                    KnowledgeArticle.category_id == article.category_id,
                    KnowledgeArticle.id != article_id,
                    KnowledgeArticle.status == ArticleStatus.PUBLISHED
                )
            ).limit(5).all()
            
            # Filter related articles based on permissions
            filtered_related = []
            for related in related_articles:
                if check_article_permission(related):
                    filtered_related.append(related)
            related_articles = filtered_related
        
        return render_template('knowledge/article_detail.html',
                             article=article,
                             related_articles=related_articles)
    finally:
        db.close()

@knowledge_bp.route('/category/<int:category_id>')
@login_required
@permission_required('can_view_knowledge_base')
def view_category(category_id):
    """View articles in a category"""
    db = SessionLocal()
    try:
        category = db.query(KnowledgeCategory).filter_by(id=category_id).first()
        if not category:
            abort(404)
        
        # Get articles in this category
        articles = db.query(KnowledgeArticle).filter(
            and_(
                KnowledgeArticle.category_id == category_id,
                KnowledgeArticle.status == ArticleStatus.PUBLISHED
            )
        ).order_by(desc(KnowledgeArticle.updated_at)).all()
        
        # Filter articles based on user permissions
        filtered_articles = []
        for article in articles:
            if check_article_permission(article):
                filtered_articles.append(article)
        
        # Get subcategories
        subcategories = db.query(KnowledgeCategory).filter_by(parent_id=category_id).order_by(KnowledgeCategory.sort_order).all()
        
        return render_template('knowledge/category_view.html',
                             category=category,
                             articles=filtered_articles,
                             subcategories=subcategories)
    finally:
        db.close()

@knowledge_bp.route('/article/<int:article_id>/feedback', methods=['POST'])
@login_required
@permission_required('can_view_knowledge_base')
def submit_feedback(article_id):
    """Submit feedback for an article"""
    db = SessionLocal()
    try:
        article = db.query(KnowledgeArticle).filter_by(id=article_id).first()
        if not article or article.status != ArticleStatus.PUBLISHED:
            abort(404)
        
        # Check permissions
        if not check_article_permission(article):
            abort(403)
        
        # Check if user already submitted feedback
        existing_feedback = db.query(KnowledgeFeedback).filter_by(
            article_id=article_id,
            user_id=current_user.id
        ).first()
        
        if existing_feedback:
            flash('You have already submitted feedback for this article.', 'warning')
            return redirect(url_for('knowledge.view_article', article_id=article_id))
        
        # Get form data
        rating = request.form.get('rating')
        is_helpful = request.form.get('is_helpful')
        comment = request.form.get('comment', '').strip()
        
        # Create feedback
        feedback = KnowledgeFeedback(
            article_id=article_id,
            user_id=current_user.id,
            rating=int(rating) if rating else None,
            is_helpful=is_helpful == 'true' if is_helpful else None,
            comment=comment if comment else None
        )
        
        # Validate rating
        if feedback.rating:
            feedback.validate_rating()
        
        db.add(feedback)
        db.commit()
        
        flash('Thank you for your feedback!', 'success')
        return redirect(url_for('knowledge.view_article', article_id=article_id))
        
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('knowledge.view_article', article_id=article_id))
    finally:
        db.close()

# API endpoints for AJAX requests
@knowledge_bp.route('/api/search-suggestions')
@login_required
@permission_required('can_view_knowledge_base')
def search_suggestions():
    """Get search suggestions for autocomplete"""
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify([])
    
    db = SessionLocal()
    try:
        # Get article titles that match
        articles = db.query(KnowledgeArticle.title).filter(
            and_(
                KnowledgeArticle.title.ilike(f'%{query}%'),
                KnowledgeArticle.status == ArticleStatus.PUBLISHED
            )
        ).limit(10).all()
        
        # Get tag names that match
        tags = db.query(KnowledgeTag.name).filter(
            KnowledgeTag.name.ilike(f'%{query}%')
        ).limit(5).all()
        
        suggestions = [article.title for article in articles]
        suggestions.extend([tag.name for tag in tags])
        
        return jsonify(suggestions[:10])
    finally:
        db.close()

# Admin routes for article management
@knowledge_bp.route('/admin')
@login_required
@permission_required('can_create_articles')
def admin_dashboard():
    """Admin dashboard for knowledge base management"""
    db = SessionLocal()
    try:
        # Get statistics
        total_articles = db.query(KnowledgeArticle).count()
        published_articles = db.query(KnowledgeArticle).filter_by(status=ArticleStatus.PUBLISHED).count()
        draft_articles = db.query(KnowledgeArticle).filter_by(status=ArticleStatus.DRAFT).count()
        total_categories = db.query(KnowledgeCategory).count()
        
        # Get recent articles
        recent_articles = db.query(KnowledgeArticle).order_by(desc(KnowledgeArticle.created_at)).limit(10).all()
        
        return render_template('knowledge/admin/dashboard.html',
                             total_articles=total_articles,
                             published_articles=published_articles,
                             draft_articles=draft_articles,
                             total_categories=total_categories,
                             recent_articles=recent_articles)
    finally:
        db.close()

@knowledge_bp.route('/admin/articles')
@login_required
@permission_required('can_create_articles')
def admin_manage_articles():
    """Manage articles page"""
    db = SessionLocal()
    try:
        page = int(request.args.get('page', 1))
        per_page = 20
        
        # Build query
        query = db.query(KnowledgeArticle).options(
            joinedload(KnowledgeArticle.category),
            joinedload(KnowledgeArticle.author)
        )
        
        # Filter by status if specified
        status_filter = request.args.get('status')
        if status_filter:
            query = query.filter(KnowledgeArticle.status == status_filter)
        
        # Filter by category if specified
        category_filter = request.args.get('category')
        if category_filter:
            query = query.filter(KnowledgeArticle.category_id == category_filter)
        
        # Get total count
        total = query.count()
        
        # Apply pagination and ordering
        articles = query.order_by(desc(KnowledgeArticle.updated_at)).offset((page - 1) * per_page).limit(per_page).all()
        
        # Get categories for filter
        categories = db.query(KnowledgeCategory).order_by(KnowledgeCategory.name).all()
        
        return render_template('knowledge/admin/manage_articles.html',
                             articles=articles,
                             categories=categories,
                             total=total,
                             page=page,
                             per_page=per_page,
                             status_filter=status_filter,
                             category_filter=category_filter)
    finally:
        db.close()

@knowledge_bp.route('/admin/articles/new')
@login_required
@permission_required('can_create_articles')
def admin_create_article():
    """Create new article form"""
    db = SessionLocal()
    try:
        categories = db.query(KnowledgeCategory).order_by(KnowledgeCategory.name).all()
        tags = db.query(KnowledgeTag).order_by(KnowledgeTag.name).all()
        
        # Get category_id from query params if provided
        category_id = request.args.get('category_id')
        
        return render_template('knowledge/admin/edit_article.html',
                             article=None,
                             categories=categories,
                             tags=tags,
                             category_id=category_id)
    finally:
        db.close()

@knowledge_bp.route('/admin/articles', methods=['POST'])
@login_required
@permission_required('can_create_articles')
def admin_save_article():
    """Save new article"""
    db = SessionLocal()
    try:
        # Get form data
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        summary = request.form.get('summary', '').strip()
        category_id = request.form.get('category_id')
        visibility = request.form.get('visibility', 'internal')
        status = request.form.get('status', 'draft')
        tags_input = request.form.get('tags', '').strip()
        
        # Validate required fields
        if not title or not content:
            flash('Title and content are required.', 'error')
            return redirect(url_for('knowledge.admin_create_article'))
        
        # Create article
        article = KnowledgeArticle(
            title=title,
            content=content,
            summary=summary if summary else None,
            category_id=int(category_id) if category_id else None,
            author_id=current_user.id,
            visibility=ArticleVisibility(visibility),
            status=ArticleStatus(status)
        )
        
        db.add(article)
        db.flush()  # Get the article ID
        
        # Associate uploaded images with this article
        associate_images_with_article(db, article.id, content)
        
        # Handle tags
        if tags_input:
            tag_names = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
            for tag_name in tag_names:
                # Get or create tag
                tag = db.query(KnowledgeTag).filter_by(name=tag_name).first()
                if not tag:
                    tag = KnowledgeTag(name=tag_name)
                    db.add(tag)
                    db.flush()
                
                # Add tag to article
                if tag not in article.tags:
                    article.tags.append(tag)
        
        db.commit()
        flash('Article created successfully!', 'success')
        return redirect(url_for('knowledge.view_article', article_id=article.id))
        
    except Exception as e:
        logger.error(f"Error creating article: {str(e)}")
        db.rollback()
        flash('Error creating article. Please try again.', 'error')
        return redirect(url_for('knowledge.admin_create_article'))
    finally:
        db.close()

@knowledge_bp.route('/admin/articles/<int:article_id>/edit')
@login_required
def admin_edit_article(article_id):
    """Edit article form"""
    db = SessionLocal()
    try:
        article = db.query(KnowledgeArticle).options(
            joinedload(KnowledgeArticle.tags)
        ).filter_by(id=article_id).first()
        
        if not article:
            abort(404)
        
        # Check permissions
        if not (current_user.permissions.can_edit_articles or article.author_id == current_user.id):
            abort(403)
        
        categories = db.query(KnowledgeCategory).order_by(KnowledgeCategory.name).all()
        tags = db.query(KnowledgeTag).order_by(KnowledgeTag.name).all()
        
        return render_template('knowledge/admin/edit_article.html',
                             article=article,
                             categories=categories,
                             tags=tags)
    finally:
        db.close()

@knowledge_bp.route('/admin/articles/<int:article_id>', methods=['PUT', 'POST'])
@login_required
def admin_update_article(article_id):
    """Update article"""
    db = SessionLocal()
    try:
        article = db.query(KnowledgeArticle).filter_by(id=article_id).first()
        
        if not article:
            abort(404)
        
        # Check permissions
        if not (current_user.permissions.can_edit_articles or article.author_id == current_user.id):
            abort(403)
        
        # Get form data
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        summary = request.form.get('summary', '').strip()
        category_id = request.form.get('category_id')
        visibility = request.form.get('visibility', 'internal')
        status = request.form.get('status', 'draft')
        tags_input = request.form.get('tags', '').strip()
        
        # Validate required fields
        if not title or not content:
            flash('Title and content are required.', 'error')
            return redirect(url_for('knowledge.admin_edit_article', article_id=article_id))
        
        # Update article
        article.title = title
        article.content = content
        article.summary = summary if summary else None
        article.category_id = int(category_id) if category_id else None
        article.visibility = ArticleVisibility(visibility)
        article.status = ArticleStatus(status)
        
        # Associate uploaded images with this article
        associate_images_with_article(db, article.id, content)
        
        # Clear existing tags
        article.tags.clear()
        
        # Handle tags
        if tags_input:
            tag_names = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
            for tag_name in tag_names:
                # Get or create tag
                tag = db.query(KnowledgeTag).filter_by(name=tag_name).first()
                if not tag:
                    tag = KnowledgeTag(name=tag_name)
                    db.add(tag)
                    db.flush()
                
                # Add tag to article
                article.tags.append(tag)
        
        db.commit()
        flash('Article updated successfully!', 'success')
        return redirect(url_for('knowledge.view_article', article_id=article.id))
        
    except Exception as e:
        logger.error(f"Error updating article: {str(e)}")
        db.rollback()
        flash('Error updating article. Please try again.', 'error')
        return redirect(url_for('knowledge.admin_edit_article', article_id=article_id))
    finally:
        db.close()

@knowledge_bp.route('/admin/articles/<int:article_id>/delete', methods=['POST'])
@login_required
def admin_delete_article(article_id):
    """Delete article"""
    db = SessionLocal()
    try:
        article = db.query(KnowledgeArticle).filter_by(id=article_id).first()
        
        if not article:
            abort(404)
        
        # Check permissions
        if not (current_user.permissions.can_delete_articles or article.author_id == current_user.id):
            abort(403)
        
        # Soft delete - archive the article
        article.status = ArticleStatus.ARCHIVED
        db.commit()
        
        flash('Article archived successfully!', 'success')
        return redirect(url_for('knowledge.admin_manage_articles'))
        
    except Exception as e:
        logger.error(f"Error deleting article: {str(e)}")
        db.rollback()
        flash('Error deleting article. Please try again.', 'error')
        return redirect(url_for('knowledge.admin_manage_articles'))
    finally:
        db.close()

def associate_images_with_article(db, article_id, content):
    """Associate uploaded images found in content with the article"""
    import re
    from urllib.parse import urlparse
    
    try:
        # Find all image URLs in the content
        image_pattern = r'src="([^"]*uploads/knowledge/images/[^"]*)"'
        image_urls = re.findall(image_pattern, content)
        
        for image_url in image_urls:
            # Extract filename from URL
            parsed_url = urlparse(image_url)
            filename = parsed_url.path.split('/')[-1]
            
            # Find the attachment record and update its article_id
            attachment = db.query(KnowledgeAttachment).filter(
                KnowledgeAttachment.filename == filename,
                KnowledgeAttachment.article_id.is_(None)
            ).first()
            
            if attachment:
                attachment.article_id = article_id
                logger.info(f"Associated image {filename} with article {article_id}")
        
        db.flush()
        
    except Exception as e:
        logger.error(f"Error associating images with article: {str(e)}")

def cleanup_orphaned_images():
    """Clean up images that were uploaded but never associated with an article (older than 24 hours)"""
    import os
    from datetime import datetime, timedelta
    from flask import current_app
    
    db = SessionLocal()
    try:
        # Find orphaned attachments older than 24 hours
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        orphaned_attachments = db.query(KnowledgeAttachment).filter(
            KnowledgeAttachment.article_id.is_(None),
            KnowledgeAttachment.created_at < cutoff_time
        ).all()
        
        for attachment in orphaned_attachments:
            try:
                # Delete the physical file
                file_path = os.path.join(current_app.root_path, attachment.file_path)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Deleted orphaned image file: {attachment.filename}")
                
                # Delete the database record
                db.delete(attachment)
                
            except Exception as e:
                logger.error(f"Error deleting orphaned image {attachment.filename}: {str(e)}")
        
        db.commit()
        logger.info(f"Cleaned up {len(orphaned_attachments)} orphaned images")
        
    except Exception as e:
        logger.error(f"Error during orphaned image cleanup: {str(e)}")
        db.rollback()
    finally:
        db.close()

@knowledge_bp.route('/admin/upload-image', methods=['POST'])
@login_required
@permission_required('can_create_articles')
def upload_image():
    """Upload image for article content"""
    import os
    import uuid
    from werkzeug.utils import secure_filename
    from flask import current_app, send_from_directory
    
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No image file provided'})
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})
        
        # Check if file is an image
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}
        if not ('.' in file.filename and 
                file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
            return jsonify({'success': False, 'error': 'Invalid file type. Only images are allowed.'})
        
        # Check file size (max 5MB)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > 5 * 1024 * 1024:  # 5MB
            return jsonify({'success': False, 'error': 'File too large. Maximum size is 5MB.'})
        
        # Generate unique filename
        file_extension = file.filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
        
        # Create upload directory if it doesn't exist
        upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'knowledge', 'images')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(upload_dir, unique_filename)
        file.save(file_path)
        
        # Create database record
        db = SessionLocal()
        try:
            attachment = KnowledgeAttachment(
                article_id=None,  # Will be set when article is saved
                filename=unique_filename,
                original_filename=secure_filename(file.filename),
                file_path=f"static/uploads/knowledge/images/{unique_filename}",
                file_size=file_size,
                mime_type=file.content_type,
                uploaded_by=current_user.id
            )
            db.add(attachment)
            db.commit()
            
            # Return image URL for editor
            image_url = url_for('static', filename=f'uploads/knowledge/images/{unique_filename}')
            
            return jsonify({
                'success': True,
                'image_url': image_url,
                'attachment_id': attachment.id,
                'filename': attachment.original_filename
            })
            
        except Exception as e:
            logger.error(f"Error saving image attachment: {str(e)}")
            db.rollback()
            # Clean up uploaded file
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({'success': False, 'error': 'Error saving image to database'})
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error uploading image: {str(e)}")
        return jsonify({'success': False, 'error': 'Error uploading image'})

@knowledge_bp.route('/images/<filename>')
def serve_image(filename):
    """Serve uploaded images"""
    from flask import current_app, send_from_directory
    import os
    upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'knowledge', 'images')
    return send_from_directory(upload_dir, filename)