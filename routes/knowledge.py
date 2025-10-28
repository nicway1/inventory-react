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

@knowledge_bp.route('/admin/process-pdf', methods=['POST'])
@login_required
@permission_required('can_create_articles')
def admin_process_pdf():
    """Process uploaded PDF and extract text and images"""
    import os
    import tempfile
    from werkzeug.utils import secure_filename

    try:
        if 'pdf' not in request.files:
            return jsonify({'success': False, 'error': 'No PDF file uploaded'}), 400

        pdf_file = request.files['pdf']
        if pdf_file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400

        if not pdf_file.filename.lower().endswith('.pdf'):
            return jsonify({'success': False, 'error': 'File must be a PDF'}), 400

        # Save PDF to temporary file
        filename = secure_filename(pdf_file.filename)
        temp_pdf_path = os.path.join(tempfile.gettempdir(), filename)
        pdf_file.save(temp_pdf_path)

        try:
            # Try to import PyPDF2 for text extraction
            try:
                import PyPDF2
                has_pypdf2 = True
            except ImportError:
                has_pypdf2 = False

            # Try to import fitz (PyMuPDF) for image extraction
            try:
                import fitz  # PyMuPDF
                has_pymupdf = True
            except ImportError:
                has_pymupdf = False

            extracted_text = ""
            extracted_images = []
            decorative_images = []  # Store header/footer/branding images separately
            logger.info("Starting PDF processing - decorative_images initialized")

            # Try PyMuPDF first for better text extraction
            if has_pymupdf:
                try:
                    pdf_document = fitz.open(temp_pdf_path)

                    # Extract text from all pages
                    for page in pdf_document:
                        text = page.get_text()
                        if text:
                            extracted_text += text + "\n\n"

                    # Extract images
                    upload_folder = os.path.join('static', 'uploads', 'knowledge', 'pdf_images')
                    os.makedirs(upload_folder, exist_ok=True)

                    for page_num in range(len(pdf_document)):
                        page = pdf_document[page_num]
                        image_list = page.get_images()
                        page_rect = page.rect  # Get page dimensions

                        for img_index, img in enumerate(image_list):
                            xref = img[0]
                            base_image = pdf_document.extract_image(xref)
                            image_bytes = base_image["image"]
                            image_ext = base_image["ext"]
                            image_width = base_image.get("width", 0)
                            image_height = base_image.get("height", 0)

                            # Filter out only truly decorative images
                            # Skip VERY small images (tiny icons, bullets)
                            if image_width < 50 or image_height < 50:
                                logger.info(f"Skipping tiny image: {image_width}x{image_height}")
                                continue

                            # Calculate aspect ratio
                            aspect_ratio = image_width / image_height if image_height > 0 else 0

                            # Skip EXTREMELY wide or tall images (decorative sidebars)
                            if aspect_ratio > 5 or aspect_ratio < 0.2:
                                logger.info(f"Skipping extreme aspect ratio: {aspect_ratio:.2f}")
                                continue

                            # Categorize image as decorative or content
                            is_decorative = False
                            is_header_banner = False

                            # First check: Is this a repeating image across pages? (logo/branding)
                            try:
                                if page_num < len(pdf_document) - 1:
                                    next_page = pdf_document[page_num + 1]
                                    next_page_images = next_page.get_images()
                                    next_page_xrefs = [img[0] for img in next_page_images]
                                    if xref in next_page_xrefs:
                                        logger.info(f"Repeating image detected across pages {page_num + 1} and {page_num + 2} - treating as decorative banner")
                                        is_header_banner = True
                                        is_decorative = True
                            except Exception as e:
                                logger.warning(f"Could not check for repeating images: {e}")

                            # Position-based check: Only skip full-page backgrounds
                            if not is_decorative:
                                try:
                                    # Get all instances of this image on the page
                                    image_instances = page.get_image_rects(xref)
                                    if image_instances:
                                        for img_rect in image_instances:
                                            img_area = abs(img_rect.width * img_rect.height)
                                            page_area = abs(page_rect.width * page_rect.height)
                                            coverage = img_area / page_area if page_area > 0 else 0

                                            # Only skip if image covers more than 90% of page (full background)
                                            if coverage > 0.9:
                                                logger.info(f"Skipping full page background: {coverage:.2%} coverage")
                                                is_decorative = True
                                                break

                                except Exception as e:
                                    logger.warning(f"Could not check image position: {e}")

                            # Save all images but categorize them
                            image_filename = f"{os.path.splitext(filename)[0]}_page{page_num + 1}_img{img_index + 1}.{image_ext}"
                            image_path = os.path.join(upload_folder, image_filename)

                            with open(image_path, "wb") as image_file:
                                image_file.write(image_bytes)

                            web_path = f"/static/uploads/knowledge/pdf_images/{image_filename}"

                            if is_decorative:
                                if is_header_banner:
                                    # Save as decorative header/banner
                                    decorative_images.append({
                                        'path': web_path,
                                        'type': 'banner',
                                        'page': page_num + 1
                                    })
                                    logger.info(f"Saved as decorative banner: {image_filename}")
                                # Otherwise just skip it (footer, tiny icon, etc)
                                continue

                            # This is a content image - add to extracted_images
                            extracted_images.append(web_path)
                            logger.info(f"Added content image: {image_filename} ({image_width}x{image_height})")

                    pdf_document.close()
                    logger.info(f"Image processing complete: {len(extracted_images)} content images, {len(decorative_images)} decorative images")
                except Exception as e:
                    logger.error(f"Error extracting with PyMuPDF: {str(e)}")

            # Fallback to PyPDF2 if PyMuPDF failed or not available
            if has_pypdf2 and not extracted_text:
                try:
                    with open(temp_pdf_path, 'rb') as file:
                        pdf_reader = PyPDF2.PdfReader(file)
                        for page in pdf_reader.pages:
                            text = page.extract_text()
                            if text:
                                extracted_text += text + "\n\n"
                except Exception as e:
                    logger.error(f"Error extracting text with PyPDF2: {str(e)}")

            # If no libraries available, return error
            if not has_pypdf2 and not has_pymupdf:
                return jsonify({
                    'success': False,
                    'error': 'PDF processing libraries not installed. Please install PyPDF2 and PyMuPDF.'
                }), 500

            # Clean up extracted text
            if extracted_text:
                import re

                # Remove excessive spacing between characters (common PDF issue)
                # Pattern: single char followed by space(s), repeated
                if re.search(r'(\w\s){5,}', extracted_text):
                    # Text has spaced characters, try to fix
                    lines = extracted_text.split('\n')
                    cleaned_lines = []
                    for line in lines:
                        # If line has pattern like "T E X T", join them
                        if re.search(r'^(\w\s){3,}', line):
                            # Remove spaces between single characters
                            cleaned_line = re.sub(r'(\w)\s+(?=\w\s|\w$)', r'\1', line)
                            cleaned_lines.append(cleaned_line)
                        else:
                            cleaned_lines.append(line)
                    extracted_text = '\n'.join(cleaned_lines)

                # Remove multiple consecutive blank lines
                extracted_text = re.sub(r'\n{3,}', '\n\n', extracted_text)

                # Remove lines with only special characters or very short
                lines = extracted_text.split('\n')
                cleaned_lines = [line for line in lines if len(line.strip()) > 2 or line.strip() == '']
                extracted_text = '\n'.join(cleaned_lines)

                # Remove ALL document metadata headers completely
                # These are always at the top of each page and just clutter the content
                lines = extracted_text.split('\n')
                metadata_patterns = [
                    r'DOC\s+TYPE\s*-\s*DOC',  # DOC TYPE - DOC. # - REV. # - DEPT.
                    r'WRITTEN\s+BY:',
                    r'APPROVED\s+BY:',
                    r'APPROVED\s+ON:',
                    r'PROCEDURE\s+[A-Z]',  # PROCEDURE APPLE, etc.
                    r'SOP-\d+-\d+-[A-Z]+$'  # SOP-0036-001-OPS
                ]

                # Remove all lines matching metadata patterns
                cleaned_lines = []
                for line in lines:
                    stripped = line.strip()
                    # Check if this line matches any metadata pattern
                    is_metadata = any(re.search(pattern, stripped, re.IGNORECASE) for pattern in metadata_patterns)
                    if not is_metadata:
                        cleaned_lines.append(line)

                extracted_text = '\n'.join(cleaned_lines)
                logger.info(f"Removed all metadata headers from extracted text")

            # Format content with beautiful HTML styling
            formatted_content = ""

            # Create simple header with logo
            if decorative_images and extracted_text:
                first_banner = decorative_images[0]

                formatted_content += f'''
<div style="text-align: center; margin-bottom: 2rem; padding: 1rem 0; border-bottom: 2px solid #e5e5e5;">
    <img src="{first_banner['path']}" alt="Document Logo" style="max-width: 300px; height: auto; display: inline-block;">
</div>
'''
                logger.info(f"Added simple header with logo")

            if extracted_text:
                # Split into paragraphs (double line breaks)
                paragraphs = extracted_text.split('\n\n')

                # Calculate where to insert images (distribute throughout content)
                num_paragraphs = len([p for p in paragraphs if p.strip() and len(p.strip()) > 2])
                images_per_section = len(extracted_images) / max(num_paragraphs, 1) if extracted_images else 0
                image_index = 0
                para_count = 0

                for para in paragraphs:
                    para = para.strip()
                    if para and len(para) > 2:  # Skip very short paragraphs
                        # Escape HTML entities
                        para = para.replace('<', '&lt;').replace('>', '&gt;')

                        # Replace single line breaks with spaces (join lines in same paragraph)
                        # But keep intentional breaks (lines that end with punctuation or are short)
                        lines = para.split('\n')
                        formatted_lines = []
                        section_title = None

                        for i, line in enumerate(lines):
                            line = line.strip()
                            if line:
                                # Check if this is a section heading (all caps, short, ends with certain words)
                                if line.isupper() and len(line) < 60 and i == 0:
                                    section_title = line
                                elif line.isupper() or len(line) < 50:
                                    formatted_lines.append(f'<strong style="color: #1e3c72;">{line}</strong><br>')
                                else:
                                    # Regular line - join with space
                                    formatted_lines.append(line + ' ')

                        para_content = ''.join(formatted_lines).strip()

                        # If we have a section title, create a styled section
                        if section_title:
                            formatted_content += f'''
<div style="background: linear-gradient(to right, #f8f9fa, #ffffff); border-left: 4px solid #1e3c72; padding: 1.5rem; margin: 2rem 0 1.5rem 0; border-radius: 0.5rem;">
    <h3 style="color: #1e3c72; font-size: 1.25rem; font-weight: 700; margin: 0 0 1rem 0; text-transform: uppercase; letter-spacing: 0.5px;">{section_title}</h3>
    <p style="margin: 0; line-height: 1.8; color: #2c3e50;">{para_content}</p>
</div>
'''
                        else:
                            formatted_content += f'<p style="line-height: 1.8; color: #2c3e50; margin-bottom: 1.25rem;">{para_content}</p>\n'

                        para_count += 1

                        # Auto-insert images after every few paragraphs
                        if extracted_images and image_index < len(extracted_images):
                            # Insert images after every 3-4 paragraphs
                            if para_count % 4 == 0 or (para_count == 2 and image_index == 0):
                                # Insert image with beautiful styling
                                if image_index < len(extracted_images):
                                    img_path = extracted_images[image_index]
                                    formatted_content += f'''
<div style="background: #f8f9fa; padding: 2rem; margin: 2.5rem 0; border-radius: 0.75rem; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
    <div style="background: white; padding: 1rem; border-radius: 0.5rem; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
        <img src="{img_path}" alt="Figure {image_index + 1}" style="width: 100%; height: auto; display: block; border-radius: 0.25rem;">
    </div>
    <p style="text-align: center; color: #6c757d; font-size: 0.875rem; margin: 1rem 0 0 0; font-style: italic;">Figure {image_index + 1}</p>
</div>
'''
                                    image_index += 1

                # Add any remaining images at the end in a gallery style
                if image_index < len(extracted_images):
                    formatted_content += '<div style="margin-top: 3rem; padding-top: 2rem; border-top: 2px solid #e9ecef;"><h3 style="color: #1e3c72; font-size: 1.25rem; font-weight: 600; margin-bottom: 2rem;">Additional Figures</h3></div>'
                    while image_index < len(extracted_images):
                        img_path = extracted_images[image_index]
                        formatted_content += f'''
<div style="background: #f8f9fa; padding: 2rem; margin: 1.5rem 0; border-radius: 0.75rem; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
    <div style="background: white; padding: 1rem; border-radius: 0.5rem; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
        <img src="{img_path}" alt="Figure {image_index + 1}" style="width: 100%; height: auto; display: block; border-radius: 0.25rem;">
    </div>
    <p style="text-align: center; color: #6c757d; font-size: 0.875rem; margin: 1rem 0 0 0; font-style: italic;">Figure {image_index + 1}</p>
</div>
'''
                        image_index += 1

            # Generate title from filename or first line of text
            title = os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ').title()
            if extracted_text and len(extracted_text) > 10:
                first_line = extracted_text.split('\n')[0].strip()
                # Clean the first line for title
                first_line = first_line.replace('\n', ' ').strip()
                if len(first_line) < 100 and len(first_line) > 5:
                    title = first_line

            # Generate summary (first 200 chars of clean text)
            summary = ""
            if extracted_text:
                clean_text = extracted_text.strip().replace('\n', ' ')
                # Remove extra spaces
                clean_text = ' '.join(clean_text.split())
                summary = clean_text[:200] + "..." if len(clean_text) > 200 else clean_text

            return jsonify({
                'success': True,
                'title': title[:255],  # Limit to 255 chars
                'content': formatted_content,
                'summary': summary,
                'images': extracted_images,
                'message': f'Successfully extracted {len(extracted_images)} images from PDF'
            })

        finally:
            # Clean up temporary PDF file
            if os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)

    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        return jsonify({'success': False, 'error': f'Error processing PDF: {str(e)}'}), 500

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

        # Get the author_id from current_user
        author_id = current_user.id

        logger.info(f"Creating article with author_id: {author_id}")

        # Verify user exists in this session to avoid foreign key errors
        from models.user import User
        user_exists = db.query(User).filter_by(id=author_id).first()
        if not user_exists:
            logger.error(f"User ID {author_id} not found in database. Current database: {db.bind.url}")

            # Try to find admin user as fallback
            admin_user = db.query(User).filter_by(username='admin').first()
            if admin_user:
                logger.warning(f"Using admin user (ID: {admin_user.id}) as fallback author for user {author_id}")
                author_id = admin_user.id
                flash(f'Note: Your user account was not found in the database. Article will be created under admin account. Please contact administrator to sync your account.', 'warning')
            else:
                # No admin fallback available
                flash(f'User session error: User ID {author_id} not found in database and no admin fallback available. Please log out and log in again, or contact administrator.', 'error')
                return redirect(url_for('knowledge.admin_create_article'))

        # Create article
        article = KnowledgeArticle(
            title=title,
            content=content,
            summary=summary if summary else None,
            category_id=int(category_id) if category_id else None,
            author_id=author_id,
            visibility=ArticleVisibility(visibility),
            status=ArticleStatus(status)
        )
        
        db.add(article)
        try:
            db.flush()  # Get the article ID - this will trigger the foreign key check
        except Exception as flush_error:
            logger.error(f"Error flushing article (likely foreign key issue): {flush_error}")
            # If foreign key error, it means the author_id doesn't exist in this database
            if 'foreign key constraint' in str(flush_error).lower():
                flash(f'Database error: The user account (ID: {author_id}) is not properly synchronized. Please contact administrator.', 'error')
            raise
        
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

        # Redirect based on article status
        if article.status == ArticleStatus.PUBLISHED:
            flash('Article created and published successfully!', 'success')
            return redirect(url_for('knowledge.view_article', article_id=article.id))
        else:
            flash('Article created successfully as draft!', 'success')
            return redirect(url_for('knowledge.admin_edit_article', article_id=article.id))
        
    except Exception as e:
        import traceback
        logger.error(f"Error creating article: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        db.rollback()
        flash(f'Error creating article: {str(e)}', 'error')
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