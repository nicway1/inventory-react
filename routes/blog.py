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


@blog_bp.route('/api/admin/blog/import-truelog', methods=['POST'])
@login_required
@admin_required
def api_admin_import_truelog():
    """Import TrueLog blog posts from scraped data"""
    db = SessionLocal()
    try:
        # All scraped blog posts from truelog.com.sg/blog/
        BLOG_POSTS = [
            {
                "title": "Understanding XO Permits and How to Speed Up the Process",
                "date": "2025-10-28",
                "excerpt": "Singapore's position as a global logistics and technology hub means that exports move in and out of the country every second. This guide explains what XO permits are, the four permit types, and strategies to accelerate the approval process.",
                "content": """<h2>What Are XO Permits?</h2>
<p>Singapore's position as a global logistics and technology hub means that exports move in and out of the country every second. But for products that fall under strategic goods controls, exporters must obtain XO permits before shipment.</p>
<p>XO permits authorize exports of controlled items including electronics and semiconductors, aerospace components, and other strategic goods.</p>
<h2>Four XO Permit Types</h2>
<ol>
<li><strong>Individual XO Permit</strong> — For single shipments (5-7 working days processing)</li>
<li><strong>Blanket Permit</strong> — For frequent exporters with pre-approved end-users</li>
<li><strong>Transshipment (XP) Permit</strong> — For goods passing through Singapore</li>
<li><strong>Multi-Use (BKT) Declarations</strong> — For recurring shipments to consistent clients</li>
</ol>
<h2>How to Speed Up the Process</h2>
<p>Approval speed depends on documentation quality, company compliance history, and goods classification. Key acceleration strategies include strengthening internal compliance programs, improving TradeFIRST ratings, and partnering with experienced logistics providers like TrueLog.</p>""",
                "featured_image": "https://truelog.com.sg/wp-content/uploads/2025/10/image.jpeg"
            },
            {
                "title": "A Complete Guide to Singapore's Export Control System and XO Permits",
                "date": "2025-10-13",
                "excerpt": "Singapore is one of the world's most trusted trading and logistics hubs. This comprehensive guide explains the Strategic Goods (Control) Act and XO permit requirements for exporters.",
                "content": """<h2>What Are Export Controls?</h2>
<p>Export controls regulate the movement of products, software, and technology that could be utilized for military applications. They protect international peace and security rather than restricting legitimate trade.</p>
<h2>Strategic Goods (Control) Act</h2>
<p>The SGCA mandates that exporters obtain permits before moving controlled goods outside Singapore. It aligns with international frameworks including the Nuclear Suppliers Group, Wassenaar Arrangement, Australia Group, and Missile Technology Control Regime.</p>
<h2>Three Main Permit Types</h2>
<ul>
<li><strong>XO Permit</strong> — Export of strategic goods</li>
<li><strong>TL Permit</strong> — Transshipment through Singapore</li>
<li><strong>ST Permit</strong> — Storage/handling in transit</li>
</ul>
<h2>Controlled Item Categories</h2>
<p>The Strategic Goods (Control) List includes electronics and semiconductors, computers and sensors, lasers and aerospace technology, and encryption products.</p>"""
            },
            {
                "title": "TrueLog Expands IT Asset Management (ITAM) Services to China and South Korea",
                "date": "2025-08-26",
                "excerpt": "Both nations host advanced digital economies but face intricate logistics demands requiring specialized solutions. TrueLog's expansion brings comprehensive ITAM services to these key markets.",
                "content": """<h2>Expansion to Key Asian Markets</h2>
<p>TrueLog is pleased to announce the expansion of our IT Asset Management (ITAM) services to China and South Korea. Both nations host advanced digital economies but face intricate logistics demands requiring specialized solutions.</p>
<h2>Services Offered</h2>
<ul>
<li>End-to-end IT asset lifecycle management</li>
<li>Secure data destruction and certification</li>
<li>Compliance with local regulations</li>
<li>Reverse logistics and disposition</li>
</ul>"""
            },
            {
                "title": "IOR/EOR Compliance in Emerging Markets: What 2025 Tells Us About Risk and Readiness",
                "date": "2025-08-26",
                "excerpt": "Growing regulatory complexity and geopolitical uncertainty characterize emerging market trade landscapes. Understanding IOR/EOR compliance is crucial for successful market entry.",
                "content": """<h2>The 2025 Compliance Landscape</h2>
<p>Growing regulatory complexity and geopolitical uncertainty characterize emerging market trade landscapes. Companies expanding into new territories must navigate an increasingly complex web of import and export regulations.</p>
<h2>Key Challenges</h2>
<ul>
<li>Varying customs requirements across jurisdictions</li>
<li>Changing tariff structures and trade agreements</li>
<li>Local entity requirements for import licenses</li>
<li>Documentation and certification needs</li>
</ul>"""
            },
            {
                "title": "Navigating India's New Logistics Policy: VAT, Customs & Licensing Implications for ICT Imports",
                "date": "2025-08-26",
                "excerpt": "India introduced forward-looking logistics policies addressing congestion, warehousing capacity, and environmental sustainability. Here's what ICT importers need to know.",
                "content": """<h2>India's Evolving Logistics Framework</h2>
<p>India introduced forward-looking logistics policies addressing congestion, warehousing capacity, and environmental sustainability. For ICT importers, understanding these changes is essential for smooth operations.</p>
<h2>Key Policy Changes</h2>
<ul>
<li>Updated GST/VAT structures for technology imports</li>
<li>New customs clearance procedures</li>
<li>Revised licensing requirements for IT equipment</li>
<li>Environmental compliance for e-waste</li>
</ul>"""
            },
            {
                "title": "TrueLog Launches IOR & EOR Services into La Reunion",
                "date": "2025-08-01",
                "excerpt": "Island location in the Indian Ocean evolves into regional digital and logistics growth center. TrueLog now offers comprehensive import/export services.",
                "content": """<h2>Expanding to La Reunion</h2>
<p>TrueLog is excited to announce our service expansion to La Reunion. This French overseas territory in the Indian Ocean is evolving into a regional digital and logistics growth center.</p>
<h2>Services Available</h2>
<ul>
<li>Importer of Record (IOR) services</li>
<li>Exporter of Record (EOR) services</li>
<li>Customs clearance and documentation</li>
<li>IT asset logistics management</li>
</ul>"""
            },
            {
                "title": "Navigating U.S. Tariff Volatility: What ICT Logistics Leaders Need to Know",
                "date": "2025-08-01",
                "excerpt": "In late July 2025, the U.S. government announced sweeping measures aimed at curbing tariff evasion via transshipment. Here's what ICT logistics leaders need to understand.",
                "content": """<h2>Recent U.S. Tariff Changes</h2>
<p>In late July 2025, the U.S. government announced sweeping measures aimed at curbing tariff evasion via transshipment. These changes have significant implications for ICT logistics operations.</p>
<h2>Strategies for Compliance</h2>
<ul>
<li>Review supply chain routing for tariff implications</li>
<li>Ensure robust country-of-origin documentation</li>
<li>Consider duty drawback opportunities</li>
<li>Work with experienced customs brokers</li>
</ul>"""
            },
            {
                "title": "How Geo-Economic Shifts Are Reshaping ICT Supply Chains in 2025",
                "date": "2025-08-01",
                "excerpt": "Global ICT supply chains are facing an inflexion point. According to a July 2025 PwC report, telecom and tech firms are accelerating de-risking efforts.",
                "content": """<h2>The Changing Landscape</h2>
<p>Global ICT supply chains are facing an inflexion point. According to a July 2025 PwC report, telecom and tech firms are accelerating de-risking efforts in response to geopolitical tensions.</p>
<h2>Key Trends</h2>
<ul>
<li>Diversification away from single-source suppliers</li>
<li>Nearshoring and friend-shoring strategies</li>
<li>Increased inventory buffers for critical components</li>
<li>Investment in supply chain visibility tools</li>
</ul>"""
            },
            {
                "title": "Kazakhstan's Middle Corridor: What It Means for ICT Logistics in Eurasia",
                "date": "2025-07-15",
                "excerpt": "The Middle Corridor trade route presents new opportunities for ICT logistics across Eurasia. Understanding this emerging route is crucial for logistics planning.",
                "content": """<h2>The Middle Corridor Opportunity</h2>
<p>Kazakhstan's Middle Corridor has emerged as a significant alternative trade route connecting Asia and Europe. For ICT logistics, this presents both opportunities and considerations.</p>
<h2>Route Advantages</h2>
<ul>
<li>Diversification from traditional routes</li>
<li>Reduced transit times for certain markets</li>
<li>Growing infrastructure investment</li>
<li>Favorable customs arrangements</li>
</ul>"""
            },
            {
                "title": "TrueLog Expands to Jordan",
                "date": "2025-07-15",
                "excerpt": "Service expansion announcement strengthening Middle East ICT logistics network. TrueLog now provides comprehensive IOR/EOR services in Jordan.",
                "content": """<h2>New Country Unlocked: Jordan</h2>
<p>TrueLog is pleased to announce the expansion of our services to Jordan, further strengthening our Middle East ICT logistics network.</p>
<h2>Services Offered</h2>
<ul>
<li>Importer of Record (IOR)</li>
<li>Exporter of Record (EOR)</li>
<li>Customs clearance</li>
<li>IT asset management</li>
<li>Reverse logistics</li>
</ul>"""
            },
            {
                "title": "ATA Carnet for Broadcasting & Professional Equipment: Why Pre-Planning Is Crucial",
                "date": "2025-07-15",
                "excerpt": "Guidance on international equipment movement compliance. ATA Carnets enable temporary duty-free import of professional equipment, but careful planning is essential.",
                "content": """<h2>Understanding ATA Carnets</h2>
<p>ATA Carnets enable temporary duty-free import of professional equipment across 87+ countries. For broadcasting and professional equipment, proper planning is essential.</p>
<h2>Pre-Planning Requirements</h2>
<ul>
<li>Detailed equipment inventory with serial numbers</li>
<li>Accurate valuation documentation</li>
<li>Understanding of destination country requirements</li>
<li>Sufficient lead time for processing (minimum 2-3 weeks)</li>
</ul>"""
            },
            {
                "title": "Expansion Update: Solomon Islands",
                "date": "2025-06-04",
                "excerpt": "TrueLog expands logistics services to the Solomon Islands, addressing unique infrastructure challenges in this Pacific nation.",
                "content": """<h2>Reaching the Solomon Islands</h2>
<p>TrueLog is proud to announce the expansion of our services to the Solomon Islands, addressing the unique infrastructure challenges of this Pacific nation.</p>
<h2>Services Available</h2>
<ul>
<li>IOR/EOR services</li>
<li>Customs clearance</li>
<li>Air and sea freight coordination</li>
<li>IT equipment deployment support</li>
</ul>"""
            },
            {
                "title": "DP World's $2.5B Bet on UAE Logistics - What It Means for ICT Deployments",
                "date": "2025-06-04",
                "excerpt": "DP World's significant investment in UAE logistics infrastructure has major implications for ICT sector expansion in the region.",
                "content": """<h2>Major Infrastructure Investment</h2>
<p>DP World's $2.5 billion investment in UAE logistics infrastructure signals a significant commitment to positioning the region as a global logistics hub.</p>
<h2>Impact on ICT Logistics</h2>
<ul>
<li>Enhanced port and free zone capabilities</li>
<li>Improved connectivity for technology deployments</li>
<li>Faster customs clearance processes</li>
<li>Better warehousing for sensitive equipment</li>
</ul>"""
            },
            {
                "title": "India's Logistics Infrastructure: Hosur's Emerging ICT Corridor",
                "date": "2025-06-04",
                "excerpt": "Panattoni's EUR100 million industrial and logistics park development in Tamil Nadu signals the emergence of a new ICT logistics corridor.",
                "content": """<h2>Hosur's Transformation</h2>
<p>Panattoni's EUR100 million investment in an industrial and logistics park in Tamil Nadu is transforming Hosur into an emerging ICT corridor connecting Bangalore and Chennai.</p>
<h2>Strategic Advantages</h2>
<ul>
<li>Proximity to major tech hubs</li>
<li>Excellent road and rail connectivity</li>
<li>Competitive land and labor costs</li>
<li>Supportive state government policies</li>
</ul>"""
            },
            {
                "title": "UK-EU Trade Reset - A New Era for ICT Logistics",
                "date": "2025-06-04",
                "excerpt": "The May 19, 2025 UK-EU trade agreement creates new opportunities and considerations for cross-border ICT logistics.",
                "content": """<h2>The Trade Reset</h2>
<p>The May 19, 2025 UK-EU trade agreement marks a significant shift in cross-border trade relations, with important implications for ICT logistics.</p>
<h2>Key Changes</h2>
<ul>
<li>Simplified customs procedures for certain goods</li>
<li>Mutual recognition of certifications</li>
<li>Improved data flow arrangements</li>
<li>Streamlined documentation requirements</li>
</ul>"""
            },
            {
                "title": "WiseTech's e2open Acquisition - A Signal for Digital Supply Chain Maturity",
                "date": "2025-06-04",
                "excerpt": "WiseTech Global's $3.25 billion acquisition of e2open signals the maturation of digital supply chain platforms.",
                "content": """<h2>Industry Consolidation</h2>
<p>WiseTech Global's $3.25 billion acquisition of e2open represents significant consolidation in the digital supply chain platform space.</p>
<h2>What This Means</h2>
<ul>
<li>Increased integration of logistics technology</li>
<li>More comprehensive end-to-end visibility</li>
<li>Potential for improved automation</li>
<li>Greater data standardization across platforms</li>
</ul>"""
            },
            {
                "title": "New Coverage Alert: American Samoa",
                "date": "2025-06-03",
                "excerpt": "TrueLog announces service expansion to American Samoa, bringing IOR/EOR capabilities to this U.S. territory in the Pacific.",
                "content": """<h2>Expanding to American Samoa</h2>
<p>TrueLog is pleased to announce the expansion of our services to American Samoa, a U.S. territory in the South Pacific.</p>
<h2>Service Capabilities</h2>
<ul>
<li>Importer of Record services</li>
<li>Exporter of Record services</li>
<li>U.S. customs compliance</li>
<li>IT equipment deployment</li>
</ul>"""
            },
            {
                "title": "Why TrueLog's Airport FTZ Presence Is a Game Changer for ICT Logistics in Singapore",
                "date": "2025-06-03",
                "excerpt": "Singapore's logistics sector continues to grow, and TrueLog's strategic positioning in the Airport Free Trade Zone offers unique advantages.",
                "content": """<h2>Strategic FTZ Positioning</h2>
<p>TrueLog's presence in Singapore's Airport Free Trade Zone (FTZ) provides significant advantages for ICT logistics operations.</p>
<h2>Key Benefits</h2>
<ul>
<li>Duty suspension for goods in transit</li>
<li>Simplified customs procedures</li>
<li>Faster turnaround times</li>
<li>Secure storage for high-value equipment</li>
<li>24/7 operations capability</li>
</ul>"""
            },
            {
                "title": "Huawei's Malaysia GPU Centre: A Strategic Shift and What It Means for ICT Supply Chains",
                "date": "2025-05-23",
                "excerpt": "Huawei's announcement to open a GPU centre in Malaysia marks a strategic investment in Southeast Asia's growing role in global tech infrastructure.",
                "content": """<h2>Strategic Investment in Malaysia</h2>
<p>Huawei's recent announcement to open a GPU centre in Malaysia marks a strategic investment in Southeast Asia's growing role in the global tech infrastructure.</p>
<h2>What This Means for Logistics</h2>
<ul>
<li>Need for secure, climate-controlled transport</li>
<li>Specialized customs handling for sensitive technology</li>
<li>Increased regional connectivity requirements</li>
<li>Opportunities for value-added services</li>
</ul>"""
            },
            {
                "title": "Exporter of Record (EOR) for IT & Telecom: Why It's Critical for Global Sales",
                "date": "2025-05-15",
                "excerpt": "EOR services enable IT companies to expand internationally without establishing local entities. Understanding when and why to use EOR is crucial for global growth.",
                "content": """<h2>What Is Exporter of Record?</h2>
<p>An Exporter of Record (EOR) is a third party that takes responsibility for export compliance, documentation, and customs requirements on behalf of a company.</p>
<h2>Benefits for IT & Telecom Companies</h2>
<ul>
<li>Faster market entry</li>
<li>Reduced compliance risk</li>
<li>Lower operational costs</li>
<li>Expert navigation of regulations</li>
</ul>"""
            },
            {
                "title": "Understanding Compliance & Regulatory Requirements for IT Equipment Imports",
                "date": "2025-04-17",
                "excerpt": "Major global regulations including FCC, CE, and BIS require careful navigation. This guide explores compliance strategies across regions.",
                "content": """<h2>Global Compliance Landscape</h2>
<p>Importing IT equipment requires compliance with various regional regulations including FCC (US), CE (EU), and BIS (India).</p>
<h2>Key Regulatory Frameworks</h2>
<ul>
<li><strong>FCC (US)</strong> - Federal Communications Commission certifications</li>
<li><strong>CE (EU)</strong> - European conformity marking</li>
<li><strong>BIS (India)</strong> - Bureau of Indian Standards compliance</li>
<li><strong>CCC (China)</strong> - China Compulsory Certification</li>
</ul>"""
            },
            {
                "title": "The Future of IT & Telecom Supply Chains: Trends & Challenges in 2025",
                "date": "2025-04-17",
                "excerpt": "AI-driven logistics, digital customs clearance, and supply chain security developments are reshaping IT and telecom supply chains.",
                "content": """<h2>2025 Supply Chain Trends</h2>
<p>The IT and telecom supply chain landscape is being transformed by several key trends in 2025.</p>
<h2>Key Trends</h2>
<ul>
<li><strong>AI-Driven Logistics</strong> - Predictive analytics and automated decision-making</li>
<li><strong>Digital Customs</strong> - Electronic documentation and automated clearance</li>
<li><strong>Supply Chain Security</strong> - Enhanced tracking and verification</li>
<li><strong>Sustainability</strong> - Green logistics and circular economy initiatives</li>
</ul>"""
            },
            {
                "title": "IOR vs. Traditional Importing: What IT & Telecom Companies Need to Know",
                "date": "2025-04-15",
                "excerpt": "Understanding the differences between using an Importer of Record service versus traditional importing methods is crucial for IT companies expanding globally.",
                "content": """<h2>Traditional Importing vs. IOR</h2>
<p>When expanding internationally, IT and telecom companies face a choice between establishing their own import operations or using an Importer of Record (IOR) service.</p>
<h2>IOR Service Benefits</h2>
<ul>
<li>No local entity required</li>
<li>Immediate market access</li>
<li>Expert compliance handling</li>
<li>Reduced administrative burden</li>
</ul>"""
            },
            {
                "title": "How to Overcome Customs Challenges When Shipping IT Equipment Internationally",
                "date": "2025-04-15",
                "excerpt": "Navigating customs challenges is essential for successful IT equipment deployments. Learn strategies to overcome common obstacles.",
                "content": """<h2>Common Customs Challenges</h2>
<p>Shipping IT equipment internationally presents unique customs challenges that require careful planning and expertise.</p>
<h2>Strategies for Success</h2>
<ul>
<li>Accurate product classification upfront</li>
<li>Complete documentation packages</li>
<li>Pre-clearance communication with customs</li>
<li>Working with experienced customs brokers</li>
<li>Understanding local regulations</li>
</ul>"""
            },
            {
                "title": "How Current U.S. Tariffs Are Shaping the Future of IT Asset Logistics",
                "date": "2025-04-15",
                "excerpt": "Tariff shifts are significantly impacting IT asset management. Understanding these changes helps companies adapt their logistics strategies.",
                "content": """<h2>Tariff Impact on IT Logistics</h2>
<p>Current U.S. tariff policies are having a significant impact on IT asset logistics, requiring companies to rethink their supply chain strategies.</p>
<h2>Adaptation Strategies</h2>
<ul>
<li>Review product classifications for tariff optimization</li>
<li>Explore free trade agreement benefits</li>
<li>Consider bonded warehouse strategies</li>
<li>Evaluate alternative supply sources</li>
</ul>"""
            },
            {
                "title": "The Role of Importer of Record (IOR) in Global IT & Telecom Expansion",
                "date": "2025-04-09",
                "excerpt": "IT and telecom companies require dependable IOR services for navigating international regulations in today's connected marketplace.",
                "content": """<h2>IOR in Global Expansion</h2>
<p>As IT and telecom companies expand globally, the Importer of Record (IOR) function becomes increasingly critical for successful market entry.</p>
<h2>Benefits for IT & Telecom</h2>
<ul>
<li>Rapid market entry without local entity</li>
<li>Reduced compliance risk</li>
<li>Cost-effective expansion</li>
<li>Expert regulatory navigation</li>
</ul>"""
            },
            {
                "title": "Global Shipping Solutions at Competitive Rates",
                "date": "2024-08-06",
                "excerpt": "TrueLog's commitment to safety and compliance while managing diverse cargo types through specialized transportation services.",
                "content": """<h2>Comprehensive Shipping Solutions</h2>
<p>TrueLog offers global shipping solutions designed to meet the diverse needs of IT and technology companies while maintaining competitive rates.</p>
<h2>Our Commitment</h2>
<ul>
<li>Safety and security of all cargo</li>
<li>Full regulatory compliance</li>
<li>Transparent pricing</li>
<li>Real-time tracking and updates</li>
</ul>"""
            },
            {
                "title": "Leveraging Technology for Seamless Logistics Documentation",
                "date": "2024-08-06",
                "excerpt": "Cutting-edge technology streamlines documentation processes to ensure operational efficiency in logistics operations.",
                "content": """<h2>Digital Documentation Solutions</h2>
<p>TrueLog leverages cutting-edge technology to streamline logistics documentation, ensuring accuracy and efficiency throughout the supply chain.</p>
<h2>Supported Documents</h2>
<ul>
<li>Commercial invoices</li>
<li>Packing lists</li>
<li>Certificates of origin</li>
<li>Customs declarations</li>
<li>Compliance certifications</li>
</ul>"""
            },
            {
                "title": "Navigating Compliance with Lithium Ion Battery Shipments",
                "date": "2024-08-06",
                "excerpt": "Stringent compliance requirements for shipping lithium ion batteries under UN classifications require careful attention to regulations.",
                "content": """<h2>Lithium Battery Shipping Compliance</h2>
<p>Shipping lithium ion batteries requires strict adherence to international regulations and safety standards.</p>
<h2>Key Regulations</h2>
<ul>
<li>UN 3481 - Lithium ion batteries packed with equipment</li>
<li>UN 3480 - Lithium ion batteries alone</li>
<li>IATA Dangerous Goods Regulations</li>
<li>IMDG Code for sea freight</li>
</ul>"""
            },
            {
                "title": "Efficient Breakbulk Services: Ensuring Seamless Logistics",
                "date": "2024-08-06",
                "excerpt": "Comprehensive breakbulk logistics solutions including specialized handling and transportation methods for oversized and heavy cargo.",
                "content": """<h2>Breakbulk Logistics Solutions</h2>
<p>TrueLog provides comprehensive breakbulk services for cargo that cannot be containerized, ensuring safe and efficient handling.</p>
<h2>Service Features</h2>
<ul>
<li>Expert planning and engineering</li>
<li>Specialized handling equipment</li>
<li>Route surveys and feasibility studies</li>
<li>Customs clearance support</li>
</ul>"""
            },
        ]

        imported = 0
        skipped = 0

        for post_data in BLOG_POSTS:
            # Generate slug from title
            slug = slugify(post_data['title'])

            # Check if post already exists
            existing = db.query(BlogPost).filter(BlogPost.slug == slug).first()
            if existing:
                skipped += 1
                continue

            # Parse date
            published_date = datetime.strptime(post_data['date'], '%Y-%m-%d')

            # Create blog post
            post = BlogPost(
                title=post_data['title'],
                slug=slug,
                content=post_data['content'],
                excerpt=post_data['excerpt'],
                featured_image=post_data.get('featured_image'),
                status=BlogPostStatus.PUBLISHED,
                meta_title=post_data['title'],
                meta_description=post_data['excerpt'],
                published_at=published_date,
                created_at=published_date,
            )

            db.add(post)
            imported += 1

        db.commit()

        return jsonify({
            'success': True,
            'message': f'Import complete: {imported} imported, {skipped} skipped (already exist)',
            'imported': imported,
            'skipped': skipped
        })

    except Exception as e:
        db.rollback()
        logger.error(f"Error importing TrueLog blog posts: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()
