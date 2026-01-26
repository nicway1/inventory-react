from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import current_user
from utils.auth_decorators import login_required, admin_required, permission_required
from utils.db_manager import DatabaseManager
from database import SessionLocal
from models.feature_request import FeatureRequest, FeatureStatus, FeaturePriority, FeatureComment
from models.bug_report import BugReport, BugStatus, BugSeverity, BugPriority, BugComment
from models.release import Release, ReleaseStatus, ReleaseType
from models.changelog_entry import ChangelogEntry, ChangelogEntryType
from models.user import User
from models.dev_blog_entry import DevBlogEntry
from models.enums import UserType
from models.action_item import ActionItem, ActionItemStatus
from sqlalchemy.orm import joinedload
from sqlalchemy import desc, asc, func, or_
from datetime import datetime, date
import logging
from flask_mail import Message
from utils.email_sender import mail
from werkzeug.utils import secure_filename
import os
from version import get_full_version_info

logger = logging.getLogger(__name__)
development_bp = Blueprint('development', __name__)
db_manager = DatabaseManager()

def send_approval_notification_email(feature):
    """Send email notification to the approver for a new feature request"""
    if not feature.approver or not feature.approver.email:
        logger.warning(f"No approver or approver email for feature {feature.display_id}")
        return

    subject = f"New Feature Request Requires Approval - {feature.display_id}"

    body = f"""
Dear {feature.approver.username},

A new feature request has been submitted and requires your approval:

Feature Request: {feature.display_id}
Title: {feature.title}
Priority: {feature.priority.value}
Requester: {feature.requester.username if feature.requester else 'Unknown'}

Description:
{feature.description}

Component: {feature.component or 'Not specified'}
Estimated Effort: {feature.estimated_effort or 'Not specified'}
Business Value: {feature.business_value or 'Not specified'}

Please review and approve/reject this feature request at:
[Feature Request Link - Update this with actual URL when implemented]

Best regards,
Development System
"""

    try:
        msg = Message(
            subject=subject,
            recipients=[feature.approver.email],
            body=body
        )
        mail.send(msg)
        logger.info(f"Approval notification sent to {feature.approver.email} for feature {feature.display_id}")
    except Exception as e:
        logger.error(f"Failed to send approval notification email: {str(e)}")
        raise

def send_approval_decision_email(feature, approved=True, reason=None):
    """Send email notification to the requester about approval decision"""
    if not feature.requester or not feature.requester.email:
        logger.warning(f"No requester or requester email for feature {feature.display_id}")
        return

    if approved:
        subject = f"Feature Request Approved - {feature.display_id}"
        decision_text = "APPROVED"
        decision_color = "✅"
        next_steps = "Your feature request has been approved and will be scheduled for development. You will receive updates as work progresses."
    else:
        subject = f"Feature Request Rejected - {feature.display_id}"
        decision_text = "REJECTED"
        decision_color = "❌"
        next_steps = f"Your feature request was not approved at this time. Reason: {reason or 'No specific reason provided'}"

    body = f"""
Dear {feature.requester.username},

Your feature request has been reviewed and {decision_text}.

{decision_color} Feature Request: {feature.display_id}
Title: {feature.title}
Approver: {feature.approver.username if feature.approver else 'System'}
Decision Date: {datetime.utcnow().strftime('%B %d, %Y at %I:%M %p')}

{next_steps}

You can view the full details of your feature request and any comments at:
[Feature Request Link - Update this with actual URL when implemented]

Best regards,
Development System
"""

    try:
        msg = Message(
            subject=subject,
            recipients=[feature.requester.email],
            body=body
        )
        mail.send(msg)
        logger.info(f"Approval decision notification sent to {feature.requester.email} for feature {feature.display_id}")
    except Exception as e:
        logger.error(f"Failed to send approval decision email: {str(e)}")
        raise

@development_bp.route('/dashboard')
@login_required
@permission_required('can_access_development')
def dashboard():
    """Main development dashboard showing overview of features, bugs, and releases"""
    db_session = SessionLocal()
    try:
        # Get summary statistics
        stats = {
            'features': {
                'total': db_session.query(FeatureRequest).count(),
                'active': db_session.query(FeatureRequest).filter(
                    FeatureRequest.status.in_([
                        FeatureStatus.IN_PLANNING,
                        FeatureStatus.IN_DEVELOPMENT,
                        FeatureStatus.IN_TESTING
                    ])
                ).count(),
                'completed': db_session.query(FeatureRequest).filter(
                    FeatureRequest.status == FeatureStatus.COMPLETED
                ).count()
            },
            'bugs': {
                'total': db_session.query(BugReport).count(),
                'open': db_session.query(BugReport).filter(
                    BugReport.status.in_([
                        BugStatus.OPEN,
                        BugStatus.IN_PROGRESS,
                        BugStatus.TESTING,
                        BugStatus.REOPENED
                    ])
                ).count(),
                'critical': db_session.query(BugReport).filter(
                    BugReport.severity == BugSeverity.CRITICAL,
                    BugReport.status.in_([BugStatus.OPEN, BugStatus.IN_PROGRESS])
                ).count()
            },
            'releases': {
                'total': db_session.query(Release).count(),
                'active': db_session.query(Release).filter(
                    Release.status.in_([
                        ReleaseStatus.PLANNING,
                        ReleaseStatus.IN_DEVELOPMENT,
                        ReleaseStatus.TESTING
                    ])
                ).count(),
                'released': db_session.query(Release).filter(
                    Release.status == ReleaseStatus.RELEASED
                ).count()
            }
        }

        # Get ALL active items (no limit for widescreen dashboard)
        recent_features = db_session.query(FeatureRequest)\
            .options(joinedload(FeatureRequest.requester))\
            .filter(FeatureRequest.requester_id.isnot(None))\
            .filter(FeatureRequest.status.in_([
                FeatureStatus.IN_PLANNING,
                FeatureStatus.IN_DEVELOPMENT,
                FeatureStatus.IN_TESTING,
                FeatureStatus.PENDING_APPROVAL
            ]))\
            .order_by(desc(FeatureRequest.updated_at)).all()

        recent_bugs = db_session.query(BugReport)\
            .options(joinedload(BugReport.reporter))\
            .filter(BugReport.status.in_([BugStatus.OPEN, BugStatus.IN_PROGRESS, BugStatus.REOPENED]))\
            .filter(BugReport.reporter_id.isnot(None))\
            .order_by(desc(BugReport.updated_at)).all()

        active_releases = db_session.query(Release)\
            .filter(Release.status.in_([
                ReleaseStatus.PLANNING,
                ReleaseStatus.IN_DEVELOPMENT,
                ReleaseStatus.TESTING,
                ReleaseStatus.READY
            ]))\
            .order_by(asc(Release.planned_date)).limit(3).all()

        # Get this week's schedule for all developers
        from models.developer_schedule import DeveloperSchedule
        from datetime import timedelta

        today = date.today()
        # Calculate Monday of current week
        monday = today - timedelta(days=today.weekday())
        friday = monday + timedelta(days=4)

        # Get all schedules for this week (only for DEVELOPER users)
        week_schedules = db_session.query(DeveloperSchedule)\
            .options(joinedload(DeveloperSchedule.user))\
            .filter(DeveloperSchedule.user.has(User.user_type == UserType.DEVELOPER))\
            .filter(DeveloperSchedule.work_date >= monday)\
            .filter(DeveloperSchedule.work_date <= friday)\
            .order_by(DeveloperSchedule.work_date)\
            .all()

        # Organize schedules by user
        schedule_by_user = {}
        for schedule in week_schedules:
            user_id = schedule.user_id
            if user_id not in schedule_by_user:
                schedule_by_user[user_id] = {
                    'user': schedule.user,
                    'days': {}
                }
            schedule_by_user[user_id]['days'][schedule.work_date.isoformat()] = {
                'is_working': schedule.is_working,
                'work_location': schedule.work_location,
                'note': schedule.note
            }

        # Generate week days list
        week_days = []
        for i in range(5):
            day = monday + timedelta(days=i)
            week_days.append({
                'date': day.isoformat(),
                'name': day.strftime('%a'),
                'day': day.day,
                'is_today': day == today
            })

        # Get pending approvals for SUPER_ADMIN users
        pending_approvals = []
        if current_user.user_type == UserType.SUPER_ADMIN:
            pending_approvals = db_session.query(FeatureRequest)\
                .options(joinedload(FeatureRequest.requester))\
                .filter(FeatureRequest.status == FeatureStatus.PENDING_APPROVAL)\
                .filter(FeatureRequest.approver_id == current_user.id)\
                .order_by(desc(FeatureRequest.approval_requested_at))\
                .all()

        # Get newly approved features for DEVELOPER users (features that are approved but have no assignee)
        newly_approved = []
        if current_user.user_type == UserType.DEVELOPER:
            newly_approved = db_session.query(FeatureRequest)\
                .options(joinedload(FeatureRequest.requester))\
                .filter(FeatureRequest.status == FeatureStatus.APPROVED)\
                .filter(FeatureRequest.assignee_id.is_(None))\
                .order_by(desc(FeatureRequest.approved_at))\
                .all()

        # Get all action items (not done) for the dashboard
        action_items = db_session.query(ActionItem)\
            .options(joinedload(ActionItem.assigned_to))\
            .options(joinedload(ActionItem.meeting))\
            .filter(ActionItem.status != ActionItemStatus.DONE)\
            .order_by(ActionItem.priority.desc(), ActionItem.created_at.desc())\
            .all()

        return render_template('development/dashboard.html',
                             stats=stats,
                             recent_features=recent_features,
                             recent_bugs=recent_bugs,
                             active_releases=active_releases,
                             schedule_by_user=schedule_by_user,
                             week_days=week_days,
                             pending_approvals=pending_approvals,
                             newly_approved=newly_approved,
                             action_items=action_items,
                             version_info=get_full_version_info())

    finally:
        db_session.close()


@development_bp.route('/changelog')
@login_required
@permission_required('can_access_development')
def dev_changelog():
    """Development changelog / blog showing releases and updates"""
    db_session = SessionLocal()
    try:
        # Get all releases ordered by release date (most recent first)
        releases = db_session.query(Release)\
            .options(joinedload(Release.features))\
            .options(joinedload(Release.fixed_bugs))\
            .options(joinedload(Release.changelog_entries))\
            .options(joinedload(Release.release_manager))\
            .order_by(desc(Release.release_date), desc(Release.created_at))\
            .all()

        # Separate released and upcoming
        released = [r for r in releases if r.status == ReleaseStatus.RELEASED]
        upcoming = [r for r in releases if r.status != ReleaseStatus.RELEASED and r.status != ReleaseStatus.CANCELLED]

        # Get recent dev blog entries (git commits)
        dev_blog_entries = db_session.query(DevBlogEntry)\
            .filter(DevBlogEntry.is_visible == True)\
            .order_by(desc(DevBlogEntry.commit_date))\
            .limit(100)\
            .all()

        return render_template('development/dev_changelog.html',
                             released=released,
                             upcoming=upcoming,
                             dev_blog_entries=dev_blog_entries,
                             version_info=get_full_version_info())
    finally:
        db_session.close()


@development_bp.route('/changelog/sync', methods=['POST'])
@login_required
@permission_required('can_access_development')
def sync_changelog():
    """Manually sync git commits to dev blog"""
    import subprocess
    import os

    try:
        script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scripts', 'sync_git_changelog.py')
        result = subprocess.run(
            ['python', script_path, '--count', '50'],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(__file__))
        )

        if result.returncode == 0:
            return jsonify({'success': True, 'message': result.stdout.strip()})
        else:
            return jsonify({'success': False, 'error': result.stderr.strip()})
    except Exception as e:
        logger.error(f"Error syncing changelog: {e}")
        return jsonify({'success': False, 'error': str(e)})


@development_bp.route('/changelog/api/entries')
@login_required
@permission_required('can_access_development')
def api_dev_blog_entries():
    """API endpoint to get dev blog entries"""
    db_session = SessionLocal()
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        commit_type = request.args.get('type', None)

        query = db_session.query(DevBlogEntry)\
            .filter(DevBlogEntry.is_visible == True)

        if commit_type:
            query = query.filter(DevBlogEntry.commit_type == commit_type)

        total = query.count()
        entries = query.order_by(desc(DevBlogEntry.commit_date))\
            .offset((page - 1) * per_page)\
            .limit(per_page)\
            .all()

        return jsonify({
            'success': True,
            'entries': [e.to_dict() for e in entries],
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        })
    finally:
        db_session.close()


# Feature Routes
@development_bp.route('/features')
@login_required
@permission_required('can_view_features')
def features():
    """List all feature requests with filtering and pagination"""
    db_session = SessionLocal()
    try:
        # Get filters from query parameters
        status_filter = request.args.get('status', 'all')
        priority_filter = request.args.get('priority', 'all')
        assignee_filter = request.args.get('assignee', 'all')
        page = int(request.args.get('page', 1))
        per_page = 20

        # Build query
        query = db_session.query(FeatureRequest)\
            .options(joinedload(FeatureRequest.requester),
                    joinedload(FeatureRequest.assignee),
                    joinedload(FeatureRequest.target_release))

        # Apply filters
        if status_filter != 'all':
            query = query.filter(FeatureRequest.status == FeatureStatus(status_filter))
        if priority_filter != 'all':
            query = query.filter(FeatureRequest.priority == FeaturePriority(priority_filter))
        if assignee_filter != 'all':
            query = query.filter(FeatureRequest.assignee_id == int(assignee_filter))

        # Get total count and paginate
        total = query.count()
        features = query.order_by(desc(FeatureRequest.updated_at))\
            .offset((page - 1) * per_page)\
            .limit(per_page).all()

        # Get filter options
        users = db_session.query(User).filter(User.user_type.in_([UserType.SUPER_ADMIN, UserType.DEVELOPER])).all()

        return render_template('development/features.html',
                             features=features,
                             users=users,
                             total=total,
                             page=page,
                             per_page=per_page,
                             status_filter=status_filter,
                             priority_filter=priority_filter,
                             assignee_filter=assignee_filter,
                             FeatureStatus=FeatureStatus,
                             FeaturePriority=FeaturePriority)

    finally:
        db_session.close()

@development_bp.route('/features/new', methods=['GET', 'POST'])
@login_required
@permission_required('can_create_features')
def new_feature():
    """Create a new feature request"""
    if request.method == 'POST':
        db_session = SessionLocal()
        try:
            feature = FeatureRequest(
                title=request.form['title'],
                description=request.form['description'],
                priority=FeaturePriority(request.form['priority']),
                component=request.form.get('component'),
                estimated_effort=request.form.get('estimated_effort'),
                business_value=request.form.get('business_value'),
                acceptance_criteria=request.form.get('acceptance_criteria'),
                requester_id=current_user.id,
                assignee_id=request.form.get('assignee_id') if request.form.get('assignee_id') else None,
                approver_id=request.form.get('approver_id') if request.form.get('approver_id') else None,
                target_release_id=request.form.get('target_release_id') if request.form.get('target_release_id') else None,
                target_date=datetime.strptime(request.form['target_date'], '%Y-%m-%d').date() if request.form.get('target_date') else None,
                status=FeatureStatus.PENDING_APPROVAL,
                approval_requested_at=datetime.utcnow()
            )

            db_session.add(feature)
            db_session.commit()

            # Handle image uploads
            if 'images' in request.files:
                files = request.files.getlist('images')
                image_paths = []

                for file in files:
                    if file and file.filename:
                        # Secure the filename
                        filename = secure_filename(file.filename)
                        # Create unique filename with timestamp
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                        unique_filename = f"feature_{feature.id}_{timestamp}_{filename}"

                        # Create directory if it doesn't exist
                        os.makedirs('static/uploads/features', exist_ok=True)

                        # Save the file
                        file_path = os.path.join('static', 'uploads', 'features', unique_filename)
                        file.save(file_path)

                        # Store relative path for database
                        image_paths.append(f"uploads/features/{unique_filename}")
                        logger.info(f"Image saved to: {file_path}")

                # Save image paths to database as JSON
                if image_paths:
                    import json
                    feature.images = json.dumps(image_paths)
                    db_session.commit()

            # Send email notification to approver
            if feature.approver:
                try:
                    send_approval_notification_email(feature)
                    flash(f'Feature request {feature.display_id} created successfully! Approval notification sent to {feature.approver.username}.', 'success')
                except Exception as e:
                    logger.error(f"Failed to send approval notification email: {str(e)}")
                    flash(f'Feature request {feature.display_id} created successfully! However, failed to send email notification.', 'warning')
            else:
                flash(f'Feature request {feature.display_id} created successfully!', 'success')

            return redirect(url_for('development.view_feature', id=feature.id))

        except Exception as e:
            db_session.rollback()
            flash(f'Error creating feature request: {str(e)}', 'error')
        finally:
            db_session.close()

    # GET - show form
    db_session = SessionLocal()
    try:
        users = db_session.query(User).filter(User.user_type.in_([UserType.SUPER_ADMIN, UserType.DEVELOPER])).all()
        super_admins = db_session.query(User).filter(User.user_type == UserType.SUPER_ADMIN).all()
        releases = db_session.query(Release).filter(
            Release.status.in_([ReleaseStatus.PLANNING, ReleaseStatus.IN_DEVELOPMENT])
        ).all()

        return render_template('development/feature_form.html',
                             users=users,
                             super_admins=super_admins,
                             releases=releases,
                             FeaturePriority=FeaturePriority)
    finally:
        db_session.close()

@development_bp.route('/features/<int:id>')
@login_required
@permission_required('can_view_features')
def view_feature(id):
    """View a specific feature request"""
    from models.feature_request import FeatureTestCase
    db_session = SessionLocal()
    try:
        feature = db_session.query(FeatureRequest)\
            .options(joinedload(FeatureRequest.requester),
                    joinedload(FeatureRequest.assignee),
                    joinedload(FeatureRequest.target_release),
                    joinedload(FeatureRequest.comments).joinedload(FeatureComment.user),
                    joinedload(FeatureRequest.test_cases).joinedload(FeatureTestCase.created_by),
                    joinedload(FeatureRequest.test_cases).joinedload(FeatureTestCase.tested_by))\
            .filter(FeatureRequest.id == id).first()

        if not feature:
            flash('Feature request not found', 'error')
            return redirect(url_for('development.features'))

        # Get all users for @mentions
        import json
        all_users = db_session.query(User).all()
        users_json = json.dumps([{'id': u.id, 'username': u.username, 'email': u.email} for u in all_users])

        # Get all active testers
        from models.bug_report import Tester
        testers = db_session.query(Tester).filter(Tester.is_active == 'Yes').all()

        return render_template('development/feature_view.html',
                             feature=feature,
                             users_json=users_json,
                             testers=testers,
                             FeatureStatus=FeatureStatus)

    finally:
        db_session.close()

@development_bp.route('/features/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('can_edit_features')
def edit_feature(id):
    """Edit a feature request"""
    db_session = SessionLocal()
    try:
        feature = db_session.query(FeatureRequest)\
            .options(joinedload(FeatureRequest.requester),
                    joinedload(FeatureRequest.assignee),
                    joinedload(FeatureRequest.target_release))\
            .filter(FeatureRequest.id == id).first()

        if not feature:
            flash('Feature request not found', 'error')
            return redirect(url_for('development.features'))

        if request.method == 'POST':
            try:
                feature.title = request.form['title']
                feature.description = request.form['description']
                feature.priority = FeaturePriority(request.form['priority'])
                feature.component = request.form.get('component')
                feature.estimated_effort = request.form.get('estimated_effort')
                feature.business_value = request.form.get('business_value')
                feature.acceptance_criteria = request.form.get('acceptance_criteria')
                feature.assignee_id = request.form.get('assignee_id') if request.form.get('assignee_id') else None
                feature.approver_id = request.form.get('approver_id') if request.form.get('approver_id') else None
                feature.target_release_id = request.form.get('target_release_id') if request.form.get('target_release_id') else None
                feature.target_date = datetime.strptime(request.form['target_date'], '%Y-%m-%d').date() if request.form.get('target_date') else None
                feature.case_progress = int(request.form.get('case_progress', 0))

                if request.form.get('status'):
                    feature.status = FeatureStatus(request.form['status'])
                    if feature.status == FeatureStatus.COMPLETED and not feature.completed_date:
                        feature.completed_date = datetime.utcnow()

                # Handle image uploads
                if 'images' in request.files:
                    files = request.files.getlist('images')
                    import json

                    # Get existing images
                    existing_images = json.loads(feature.images) if feature.images else []

                    for file in files:
                        if file and file.filename:
                            # Secure the filename
                            filename = secure_filename(file.filename)
                            # Create unique filename with timestamp
                            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                            unique_filename = f"feature_{feature.id}_{timestamp}_{filename}"

                            # Create directory if it doesn't exist
                            os.makedirs('static/uploads/features', exist_ok=True)

                            # Save the file
                            file_path = os.path.join('static', 'uploads', 'features', unique_filename)
                            file.save(file_path)

                            # Add to existing images
                            existing_images.append(f"uploads/features/{unique_filename}")
                            logger.info(f"Image saved to: {file_path}")

                    # Save updated image list
                    if existing_images:
                        feature.images = json.dumps(existing_images)

                db_session.commit()
                flash(f'Feature request {feature.display_id} updated successfully!', 'success')
                return redirect(url_for('development.view_feature', id=feature.id))

            except Exception as e:
                db_session.rollback()
                flash(f'Error updating feature request: {str(e)}', 'error')

        # GET - show form
        users = db_session.query(User).filter(User.user_type.in_([UserType.SUPER_ADMIN, UserType.DEVELOPER])).all()
        super_admins = db_session.query(User).filter(User.user_type == UserType.SUPER_ADMIN).all()
        releases = db_session.query(Release).filter(
            Release.status.in_([ReleaseStatus.PLANNING, ReleaseStatus.IN_DEVELOPMENT, ReleaseStatus.TESTING])
        ).all()

        return render_template('development/feature_form.html',
                             feature=feature,
                             users=users,
                             super_admins=super_admins,
                             releases=releases,
                             FeaturePriority=FeaturePriority,
                             FeatureStatus=FeatureStatus)
    finally:
        db_session.close()

@development_bp.route('/features/<int:id>/comment', methods=['POST'])
@login_required
@permission_required('can_edit_features')
def add_feature_comment(id):
    """Add a comment to a feature request"""
    db_session = SessionLocal()
    try:
        feature = db_session.query(FeatureRequest).filter(FeatureRequest.id == id).first()
        if not feature:
            flash('Feature request not found', 'error')
            return redirect(url_for('development.features'))

        content = request.form['content']

        comment = FeatureComment(
            content=content,
            feature_id=feature.id,
            user_id=current_user.id
        )

        db_session.add(comment)
        db_session.commit()

        # Extract @mentions and send email notifications
        import re
        mentions = re.findall(r'@(\w+)', content)
        if mentions:
            logger.info(f"Found {len(mentions)} mentions in comment: {mentions}")
            mentioned_users = db_session.query(User).filter(User.username.in_(mentions)).all()
            logger.info(f"Found {len(mentioned_users)} matching users in database")
            for mentioned_user in mentioned_users:
                if mentioned_user.email and mentioned_user.id != current_user.id:
                    try:
                        logger.info(f"Attempting to send mention email to {mentioned_user.username} ({mentioned_user.email})")
                        success = send_feature_mention_email(mentioned_user, current_user, feature, content)
                        if success:
                            logger.info(f"Mention email sent successfully to {mentioned_user.email}")
                        else:
                            logger.error(f"Failed to send mention email to {mentioned_user.email} (returned False)")
                    except Exception as email_error:
                        logger.error(f"Exception sending mention email to {mentioned_user.email}: {str(email_error)}", exc_info=True)
                else:
                    if not mentioned_user.email:
                        logger.warning(f"User {mentioned_user.username} has no email address")
                    elif mentioned_user.id == current_user.id:
                        logger.info(f"Skipping email to self ({mentioned_user.username})")

        flash('Comment added successfully!', 'success')
        return redirect(url_for('development.view_feature', id=id))

    except Exception as e:
        db_session.rollback()
        flash(f'Error adding comment: {str(e)}', 'error')
        return redirect(url_for('development.view_feature', id=id))
    finally:
        db_session.close()

@development_bp.route('/features/<int:id>/status', methods=['POST'])
@login_required
@permission_required('can_edit_features')
def update_feature_status(id):
    """Update feature request status"""
    db_session = SessionLocal()
    try:
        feature = db_session.query(FeatureRequest).filter(FeatureRequest.id == id).first()
        if not feature:
            flash('Feature request not found', 'error')
            return redirect(url_for('development.features'))

        new_status = request.form.get('status')
        if new_status:
            # Convert by enum name, not value
            feature.status = FeatureStatus[new_status]
            if feature.status == FeatureStatus.COMPLETED and not feature.completed_date:
                feature.completed_date = datetime.utcnow()

            # Auto-update case progress based on status
            status_progress_map = {
                FeatureStatus.REQUESTED: 0,
                FeatureStatus.PENDING_APPROVAL: 10,
                FeatureStatus.APPROVED: 20,
                FeatureStatus.REJECTED: 0,
                FeatureStatus.IN_PLANNING: 30,
                FeatureStatus.IN_DEVELOPMENT: 50,
                FeatureStatus.IN_TESTING: 80,
                FeatureStatus.COMPLETED: 100,
                FeatureStatus.CANCELLED: 0
            }
            feature.case_progress = status_progress_map.get(feature.status, feature.case_progress)

            db_session.commit()
            flash(f'Feature status updated to {feature.status.value}', 'success')

        return redirect(url_for('development.view_feature', id=id))

    except Exception as e:
        db_session.rollback()
        flash(f'Error updating status: {str(e)}', 'error')
        return redirect(url_for('development.view_feature', id=id))
    finally:
        db_session.close()

@development_bp.route('/features/<int:id>/approve', methods=['POST'])
@login_required
@permission_required('can_approve_features')
def approve_feature(id):
    """Approve a feature request"""
    db_session = SessionLocal()
    try:
        feature = db_session.query(FeatureRequest)\
            .options(joinedload(FeatureRequest.requester))\
            .filter(FeatureRequest.id == id).first()

        if not feature:
            flash('Feature request not found', 'error')
            return redirect(url_for('development.features'))

        # Check if user is the assigned approver or super admin
        if feature.approver_id != current_user.id and current_user.user_type != 'SUPER_ADMIN':
            flash('You are not authorized to approve this feature request', 'error')
            return redirect(url_for('development.view_feature', id=id))

        # Update feature status
        feature.status = FeatureStatus.APPROVED
        feature.approved_at = datetime.utcnow()

        # Add approval comment
        approval_comment = FeatureComment(
            content=f"Feature request approved by {current_user.username}",
            feature_id=feature.id,
            user_id=current_user.id,
            created_at=datetime.utcnow()
        )
        db_session.add(approval_comment)

        db_session.commit()

        # Send notification to requester
        try:
            send_approval_decision_email(feature, approved=True)
        except Exception as e:
            logger.error(f"Failed to send approval decision email: {str(e)}")

        flash(f'Feature request {feature.display_id} has been approved!', 'success')
        return redirect(url_for('development.view_feature', id=id))

    except Exception as e:
        db_session.rollback()
        flash(f'Error approving feature request: {str(e)}', 'error')
        return redirect(url_for('development.view_feature', id=id))
    finally:
        db_session.close()

@development_bp.route('/features/<int:id>/reject', methods=['POST'])
@login_required
@permission_required('can_approve_features')
def reject_feature(id):
    """Reject a feature request"""
    db_session = SessionLocal()
    try:
        feature = db_session.query(FeatureRequest)\
            .options(joinedload(FeatureRequest.requester))\
            .filter(FeatureRequest.id == id).first()

        if not feature:
            flash('Feature request not found', 'error')
            return redirect(url_for('development.features'))

        # Check if user is the assigned approver or super admin
        if feature.approver_id != current_user.id and current_user.user_type != 'SUPER_ADMIN':
            flash('You are not authorized to reject this feature request', 'error')
            return redirect(url_for('development.view_feature', id=id))

        # Get rejection reason
        rejection_reason = request.form.get('rejection_reason', 'No reason provided')

        # Update feature status
        feature.status = FeatureStatus.REJECTED

        # Add rejection comment
        rejection_comment = FeatureComment(
            content=f"Feature request rejected by {current_user.username}\n\nReason: {rejection_reason}",
            feature_id=feature.id,
            user_id=current_user.id,
            created_at=datetime.utcnow()
        )
        db_session.add(rejection_comment)

        db_session.commit()

        # Send notification to requester
        try:
            send_approval_decision_email(feature, approved=False, reason=rejection_reason)
        except Exception as e:
            logger.error(f"Failed to send rejection decision email: {str(e)}")

        flash(f'Feature request {feature.display_id} has been rejected.', 'success')
        return redirect(url_for('development.view_feature', id=id))

    except Exception as e:
        db_session.rollback()
        flash(f'Error rejecting feature request: {str(e)}', 'error')
        return redirect(url_for('development.view_feature', id=id))
    finally:
        db_session.close()

@development_bp.route('/features/<int:id>/take-ownership', methods=['POST'])
@login_required
@permission_required('can_access_development')
def take_ownership(id):
    """Take ownership of an approved feature request (for developers)"""
    db_session = SessionLocal()
    try:
        feature = db_session.query(FeatureRequest)\
            .options(joinedload(FeatureRequest.requester))\
            .filter(FeatureRequest.id == id).first()

        if not feature:
            flash('Feature request not found', 'error')
            return redirect(url_for('development.dashboard'))

        # Check if feature is approved and has no assignee
        if feature.status != FeatureStatus.APPROVED:
            flash('This feature is not in an approved state', 'error')
            return redirect(url_for('development.dashboard'))

        if feature.assignee_id is not None:
            flash('This feature already has an assignee', 'error')
            return redirect(url_for('development.dashboard'))

        # Assign to current user and change status to IN_DEVELOPMENT
        feature.assignee_id = current_user.id
        feature.status = FeatureStatus.IN_DEVELOPMENT
        feature.case_progress = 50  # Set progress to 50% (In Development)
        feature.updated_at = datetime.utcnow()

        # Add ownership comment
        ownership_comment = FeatureComment(
            content=f"{current_user.username} took ownership of this feature request and started development.",
            feature_id=feature.id,
            user_id=current_user.id,
            created_at=datetime.utcnow()
        )
        db_session.add(ownership_comment)

        db_session.commit()

        flash(f'You are now the owner of {feature.display_id}. Status changed to In Development.', 'success')
        return redirect(url_for('development.view_feature', id=id))

    except Exception as e:
        db_session.rollback()
        flash(f'Error taking ownership: {str(e)}', 'error')
        return redirect(url_for('development.dashboard'))
    finally:
        db_session.close()

@development_bp.route('/features/<int:id>/delete', methods=['POST'])
@login_required
@permission_required('can_edit_features')
def delete_feature(id):
    """Delete a feature request"""
    db_session = SessionLocal()
    try:
        feature = db_session.query(FeatureRequest).filter(FeatureRequest.id == id).first()
        if not feature:
            flash('Feature request not found', 'error')
            return redirect(url_for('development.features'))

        # Check if user is the case owner or has delete permissions
        if feature.assignee_id != current_user.id and current_user.user_type != UserType.SUPER_ADMIN:
            flash('You are not authorized to delete this feature request', 'error')
            return redirect(url_for('development.view_feature', id=id))

        feature_display_id = feature.display_id
        db_session.delete(feature)
        db_session.commit()

        flash(f'Feature request {feature_display_id} has been deleted successfully', 'success')
        return redirect(url_for('development.features'))

    except Exception as e:
        db_session.rollback()
        flash(f'Error deleting feature request: {str(e)}', 'error')
        return redirect(url_for('development.view_feature', id=id))
    finally:
        db_session.close()


@development_bp.route('/features/<int:id>/delete-image', methods=['POST'])
@login_required
@permission_required('can_edit_features')
def delete_feature_image(id):
    """Delete an image from a feature request"""
    db_session = SessionLocal()
    try:
        feature = db_session.query(FeatureRequest).filter(FeatureRequest.id == id).first()
        if not feature:
            return jsonify({'success': False, 'error': 'Feature request not found'}), 404

        # Get the image path to delete from request body
        data = request.get_json()
        image_path = data.get('image_path')

        if not image_path:
            return jsonify({'success': False, 'error': 'No image path provided'}), 400

        # Load current images
        import json
        current_images = json.loads(feature.images) if feature.images else []

        # Remove the image from the list
        if image_path in current_images:
            current_images.remove(image_path)

            # Delete the physical file
            try:
                file_path = os.path.join('static', image_path)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Deleted image file: {file_path}")
            except Exception as e:
                logger.error(f"Error deleting image file: {str(e)}")

            # Update database
            feature.images = json.dumps(current_images) if current_images else None
            db_session.commit()

            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Image not found in feature'}), 404

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error deleting feature image: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


def send_feature_mention_email(mentioned_user, commenter, feature, comment_content):
    """Send email notification when user is mentioned in a feature comment"""
    from flask import current_app

    try:
        logging.info(f"Attempting to send feature mention notification to {mentioned_user.email}")

        if not mentioned_user.email:
            logging.warning(f"User {mentioned_user.username} has no email address")
            return False

        # Create the feature URL
        feature_url = f"https://inventory.truelog.com.sg/development/features/{feature.id}"

        subject = f"You were mentioned in {feature.display_id}"

        # Get priority color mapping
        priority_colors = {
            'Low': {'bg': '#f3f4f6', 'text': '#6b7280'},
            'Medium': {'bg': '#fef3c7', 'text': '#d97706'},
            'High': {'bg': '#fed7aa', 'text': '#ea580c'},
            'Critical': {'bg': '#fee2e2', 'text': '#dc2626'}
        }
        priority_value = feature.priority.value if feature.priority else 'Medium'
        priority_style = priority_colors.get(priority_value, priority_colors['Medium'])

        # Get status color mapping
        status_colors = {
            'Requested': {'bg': '#dbeafe', 'text': '#2563eb'},
            'Pending Approval': {'bg': '#e0e7ff', 'text': '#4f46e5'},
            'Approved': {'bg': '#d1fae5', 'text': '#059669'},
            'Rejected': {'bg': '#fee2e2', 'text': '#dc2626'},
            'In Planning': {'bg': '#fef3c7', 'text': '#d97706'},
            'In Development': {'bg': '#fed7aa', 'text': '#ea580c'},
            'In Testing': {'bg': '#e9d5ff', 'text': '#9333ea'},
            'Completed': {'bg': '#dcfce7', 'text': '#16a34a'},
            'Cancelled': {'bg': '#fee2e2', 'text': '#dc2626'}
        }
        status_value = feature.status.value if feature.status else 'Requested'
        status_style = status_colors.get(status_value, status_colors['Requested'])

        # HTML email template
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Mention Notification - {feature.display_id}</title>
        </head>
        <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f9;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff;">
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%); padding: 30px 40px; text-align: center;">
                    <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 600;">
                        💬 You Were Mentioned
                    </h1>
                    <p style="color: #bfdbfe; margin: 8px 0 0 0; font-size: 16px;">
                        TrueLog Development System
                    </p>
                </div>

                <!-- Main Content -->
                <div style="padding: 40px;">
                    <div style="background-color: #eff6ff; border-left: 4px solid #2563eb; padding: 20px; margin-bottom: 30px; border-radius: 0 8px 8px 0;">
                        <h2 style="color: #1a202c; margin: 0 0 10px 0; font-size: 20px;">
                            Hello {mentioned_user.username}!
                        </h2>
                        <p style="color: #4a5568; margin: 0; font-size: 16px; line-height: 1.5;">
                            <strong>{commenter.username}</strong> mentioned you in a comment on {feature.display_id}.
                        </p>
                    </div>

                    <!-- Feature Details Card -->
                    <div style="border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; margin-bottom: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <div style="background-color: #2563eb; color: white; padding: 15px 20px;">
                            <h3 style="margin: 0; font-size: 16px; font-weight: 600;">✨ Feature Details</h3>
                        </div>
                        <div style="padding: 20px;">
                            <table style="width: 100%; border-collapse: collapse;">
                                <tr>
                                    <td style="padding: 8px 0; color: #718096; font-weight: 600; width: 120px;">Feature ID:</td>
                                    <td style="padding: 8px 0; color: #2d3748;">{feature.display_id}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0; color: #718096; font-weight: 600;">Title:</td>
                                    <td style="padding: 8px 0; color: #2d3748; font-weight: 600;">{feature.title}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0; color: #718096; font-weight: 600;">Priority:</td>
                                    <td style="padding: 8px 0;">
                                        <span style="background-color: {priority_style['bg']};
                                                     color: {priority_style['text']};
                                                     padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 600;">
                                            {priority_value}
                                        </span>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0; color: #718096; font-weight: 600;">Status:</td>
                                    <td style="padding: 8px 0;">
                                        <span style="background-color: {status_style['bg']};
                                                     color: {status_style['text']};
                                                     padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 600;">
                                            {status_value}
                                        </span>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0; color: #718096; font-weight: 600;">Case Owner:</td>
                                    <td style="padding: 8px 0; color: #2d3748;">{feature.assignee.username if feature.assignee else 'Unassigned'}</td>
                                </tr>
                            </table>
                        </div>
                    </div>

                    <!-- Comment Preview -->
                    <div style="background-color: #f7fafc; border-radius: 8px; padding: 20px; margin-bottom: 30px;">
                        <h4 style="color: #2d3748; margin: 0 0 10px 0; font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">💬 {commenter.username} said:</h4>
                        <p style="color: #4a5568; margin: 0; line-height: 1.6; font-size: 14px; white-space: pre-wrap;">
                            {comment_content}
                        </p>
                    </div>

                    <!-- Action Button -->
                    <div style="text-align: center; margin-bottom: 30px;">
                        <a href="{feature_url}"
                           style="background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
                                  color: white;
                                  text-decoration: none;
                                  padding: 14px 28px;
                                  border-radius: 8px;
                                  font-weight: 600;
                                  font-size: 16px;
                                  display: inline-block;
                                  box-shadow: 0 4px 6px rgba(37, 99, 235, 0.3);
                                  transition: all 0.3s ease;">
                            🔗 View Feature & Reply
                        </a>
                    </div>

                    <!-- Next Steps -->
                    <div style="background-color: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 20px;">
                        <h4 style="color: #1e40af; margin: 0 0 10px 0; font-size: 16px; font-weight: 600;">
                            ✅ What's Next?
                        </h4>
                        <ul style="color: #1e3a8a; margin: 0; padding-left: 20px; line-height: 1.6;">
                            <li>Review the feature details and comment</li>
                            <li>Reply to the comment to continue the conversation</li>
                            <li>Add any additional information or feedback</li>
                            <li>Collaborate with the team on the feature</li>
                        </ul>
                    </div>
                </div>

                <!-- Footer -->
                <div style="background-color: #f7fafc; padding: 30px 40px; text-align: center; border-top: 1px solid #e2e8f0;">
                    <p style="color: #718096; margin: 0 0 10px 0; font-size: 14px;">
                        This notification was sent because you were mentioned in a comment.
                    </p>
                    <p style="color: #a0aec0; margin: 0; font-size: 12px;">
                        TrueLog Development System |
                        <a href="https://inventory.truelog.com.sg" style="color: #2563eb; text-decoration: none;">inventory.truelog.com.sg</a>
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        # Plain text fallback
        plain_body = f"""
Hi {mentioned_user.username},

{commenter.username} mentioned you in a comment on {feature.display_id}.

Feature Details:
- Feature ID: {feature.display_id}
- Title: {feature.title}
- Priority: {priority_value}
- Status: {status_value}
- Case Owner: {feature.assignee.username if feature.assignee else 'Unassigned'}

Comment:
{comment_content}

View the feature and reply: {feature_url}

Best regards,
TrueLog Development System
"""

        # Send email using the email_sender utility
        from utils.email_sender import _send_email_via_method

        success = _send_email_via_method(
            to_emails=mentioned_user.email,
            subject=subject,
            text_body=plain_body,
            html_body=html_body
        )

        if success:
            logging.info(f"Feature mention notification sent successfully to {mentioned_user.email}")
        else:
            logging.error(f"Failed to send feature mention notification to {mentioned_user.email}")

        return success

    except Exception as e:
        logging.error(f"Failed to send feature mention email to {mentioned_user.email}: {str(e)}")
        return False


# ============================================================================
# FEATURE TEST CASE ROUTES
# ============================================================================

@development_bp.route('/features/<int:feature_id>/test-cases')
@login_required
@permission_required('can_view_features')
def feature_test_cases(feature_id):
    """View test cases for a feature"""
    from models.feature_request import FeatureTestCase
    db_session = SessionLocal()
    try:
        feature = db_session.query(FeatureRequest).options(
            joinedload(FeatureRequest.test_cases).joinedload(FeatureTestCase.created_by),
            joinedload(FeatureRequest.test_cases).joinedload(FeatureTestCase.tested_by),
            joinedload(FeatureRequest.requester),
            joinedload(FeatureRequest.assignee)
        ).filter(FeatureRequest.id == feature_id).first()

        if not feature:
            flash('Feature not found', 'error')
            return redirect(url_for('development.features'))

        return render_template('development/feature_test_cases.html', feature=feature)
    finally:
        db_session.close()


@development_bp.route('/features/<int:feature_id>/test-cases/new', methods=['GET', 'POST'])
@login_required
@permission_required('can_edit_features')
def new_feature_test_case(feature_id):
    """Create a new test case for a feature"""
    from models.feature_request import FeatureTestCase
    db_session = SessionLocal()
    try:
        feature = db_session.query(FeatureRequest).filter(FeatureRequest.id == feature_id).first()
        if not feature:
            flash('Feature not found', 'error')
            return redirect(url_for('development.features'))

        if request.method == 'POST':
            test_case = FeatureTestCase(
                feature_id=feature_id,
                title=request.form.get('title'),
                description=request.form.get('description'),
                preconditions=request.form.get('preconditions'),
                test_steps=request.form.get('test_steps'),
                expected_result=request.form.get('expected_result'),
                priority=request.form.get('priority', 'Medium'),
                test_data=request.form.get('test_data'),
                created_by_id=current_user.id
            )

            db_session.add(test_case)
            db_session.commit()

            flash(f'Test case created successfully', 'success')
            return redirect(url_for('development.feature_test_cases', feature_id=feature_id))

        return render_template('development/feature_test_case_form.html', feature=feature, test_case=None)

    except Exception as e:
        db_session.rollback()
        flash(f'Error creating test case: {str(e)}', 'error')
        return redirect(url_for('development.feature_test_cases', feature_id=feature_id))
    finally:
        db_session.close()


@development_bp.route('/feature-test-cases/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('can_edit_features')
def edit_feature_test_case(id):
    """Edit a feature test case"""
    from models.feature_request import FeatureTestCase
    db_session = SessionLocal()
    try:
        test_case = db_session.query(FeatureTestCase).options(
            joinedload(FeatureTestCase.feature)
        ).filter(FeatureTestCase.id == id).first()

        if not test_case:
            flash('Test case not found', 'error')
            return redirect(url_for('development.features'))

        if request.method == 'POST':
            test_case.title = request.form.get('title')
            test_case.description = request.form.get('description')
            test_case.preconditions = request.form.get('preconditions')
            test_case.test_steps = request.form.get('test_steps')
            test_case.expected_result = request.form.get('expected_result')
            test_case.priority = request.form.get('priority', 'Medium')
            test_case.test_data = request.form.get('test_data')
            test_case.updated_at = datetime.utcnow()

            db_session.commit()

            flash(f'Test case updated successfully', 'success')
            return redirect(url_for('development.feature_test_cases', feature_id=test_case.feature_id))

        return render_template('development/feature_test_case_form.html', feature=test_case.feature, test_case=test_case)

    except Exception as e:
        db_session.rollback()
        flash(f'Error updating test case: {str(e)}', 'error')
        return redirect(url_for('development.features'))
    finally:
        db_session.close()


@development_bp.route('/feature-test-cases/<int:id>/execute', methods=['GET', 'POST'])
@login_required
@permission_required('can_edit_features')
def execute_feature_test_case(id):
    """Execute a feature test case (fill in actual results)"""
    from models.feature_request import FeatureTestCase
    db_session = SessionLocal()
    try:
        test_case = db_session.query(FeatureTestCase).options(
            joinedload(FeatureTestCase.feature)
        ).filter(FeatureTestCase.id == id).first()

        if not test_case:
            flash('Test case not found', 'error')
            return redirect(url_for('development.features'))

        if request.method == 'POST':
            test_case.actual_result = request.form.get('actual_result')
            test_case.status = request.form.get('status', 'Pending')
            test_case.tested_by_id = current_user.id
            test_case.tested_at = datetime.utcnow()
            test_case.updated_at = datetime.utcnow()

            db_session.commit()

            flash(f'Test case executed successfully', 'success')
            return redirect(url_for('development.feature_test_cases', feature_id=test_case.feature_id))

        return render_template('development/execute_feature_test_case.html', test_case=test_case)

    except Exception as e:
        db_session.rollback()
        flash(f'Error executing test case: {str(e)}', 'error')
        return redirect(url_for('development.features'))
    finally:
        db_session.close()


@development_bp.route('/feature-test-cases/<int:id>/delete', methods=['POST'])
@login_required
@permission_required('can_edit_features')
def delete_feature_test_case(id):
    """Delete a feature test case"""
    from models.feature_request import FeatureTestCase
    db_session = SessionLocal()
    try:
        test_case = db_session.query(FeatureTestCase).filter(FeatureTestCase.id == id).first()

        if not test_case:
            flash('Test case not found', 'error')
            return redirect(url_for('development.features'))

        feature_id = test_case.feature_id
        db_session.delete(test_case)
        db_session.commit()

        flash(f'Test case deleted successfully', 'success')
        return redirect(url_for('development.feature_test_cases', feature_id=feature_id))

    except Exception as e:
        db_session.rollback()
        flash(f'Error deleting test case: {str(e)}', 'error')
        return redirect(url_for('development.features'))
    finally:
        db_session.close()


@development_bp.route('/features/<int:feature_id>/test-cases/import', methods=['GET', 'POST'])
@login_required
@permission_required('can_edit_features')
def import_feature_test_cases(feature_id):
    """Import test cases from CSV file"""
    import csv
    import io
    from models.feature_request import FeatureTestCase

    db_session = SessionLocal()
    try:
        feature = db_session.query(FeatureRequest).filter(FeatureRequest.id == feature_id).first()
        if not feature:
            flash('Feature not found', 'error')
            return redirect(url_for('development.features'))

        if request.method == 'POST':
            if 'csv_file' not in request.files:
                flash('No file uploaded', 'error')
                return redirect(url_for('development.feature_test_cases', feature_id=feature_id))

            file = request.files['csv_file']
            if file.filename == '':
                flash('No file selected', 'error')
                return redirect(url_for('development.feature_test_cases', feature_id=feature_id))

            if not file.filename.endswith('.csv'):
                flash('File must be a CSV file', 'error')
                return redirect(url_for('development.feature_test_cases', feature_id=feature_id))

            try:
                # Read CSV file
                stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
                csv_reader = csv.DictReader(stream)

                imported_count = 0
                skipped_count = 0
                errors = []

                for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 (header is row 1)
                    try:
                        # Validate required fields
                        if not row.get('title') or not row.get('test_steps') or not row.get('expected_result'):
                            skipped_count += 1
                            errors.append(f"Row {row_num}: Missing required fields (title, test_steps, or expected_result)")
                            continue

                        # Replace | with newlines for multi-line fields
                        preconditions = row.get('preconditions', '').replace('|', '\n') if row.get('preconditions') else None
                        test_steps = row.get('test_steps', '').replace('|', '\n')
                        expected_result = row.get('expected_result', '').replace('|', '\n')
                        test_data = row.get('test_data', '').replace('|', '\n') if row.get('test_data') else None

                        # Create test case
                        test_case = FeatureTestCase(
                            feature_id=feature_id,
                            title=row.get('title'),
                            description=row.get('description'),
                            preconditions=preconditions,
                            test_steps=test_steps,
                            expected_result=expected_result,
                            priority=row.get('priority', 'Medium'),
                            status=row.get('status', 'Pending'),
                            test_data=test_data,
                            created_by_id=current_user.id
                        )

                        db_session.add(test_case)
                        imported_count += 1

                    except Exception as e:
                        skipped_count += 1
                        errors.append(f"Row {row_num}: {str(e)}")

                db_session.commit()

                # Build success message
                message = f'Successfully imported {imported_count} test case(s)'
                if skipped_count > 0:
                    message += f', skipped {skipped_count} row(s)'

                flash(message, 'success')

                # Show errors if any
                if errors:
                    for error in errors[:5]:  # Show first 5 errors
                        flash(error, 'warning')
                    if len(errors) > 5:
                        flash(f'... and {len(errors) - 5} more errors', 'warning')

                return redirect(url_for('development.feature_test_cases', feature_id=feature_id))

            except Exception as e:
                db_session.rollback()
                flash(f'Error importing CSV: {str(e)}', 'error')
                logger.error(f'CSV import error: {str(e)}')
                return redirect(url_for('development.feature_test_cases', feature_id=feature_id))

        # GET request - show template download option
        return redirect(url_for('development.feature_test_cases', feature_id=feature_id))

    finally:
        db_session.close()


# Bug Routes
@development_bp.route('/bugs')
@login_required
@permission_required('can_view_bugs')
def bugs():
    """List all bug reports with filtering and pagination"""
    db_session = SessionLocal()
    try:
        # Get filters from query parameters
        status_filter = request.args.get('status', 'open')
        severity_filter = request.args.get('severity', 'all')
        assignee_filter = request.args.get('assignee', 'all')
        page = int(request.args.get('page', 1))
        per_page = 20

        # Build query
        query = db_session.query(BugReport)\
            .options(joinedload(BugReport.reporter),
                    joinedload(BugReport.assignee),
                    joinedload(BugReport.fixed_in_release))\
            .filter(BugReport.reporter_id.isnot(None))

        # Apply filters
        if status_filter == 'open':
            query = query.filter(BugReport.status.in_([
                BugStatus.OPEN, BugStatus.IN_PROGRESS, BugStatus.TESTING, BugStatus.REOPENED
            ]))
        elif status_filter != 'all':
            query = query.filter(BugReport.status == BugStatus(status_filter))

        if severity_filter != 'all':
            query = query.filter(BugReport.severity == BugSeverity(severity_filter))
        if assignee_filter != 'all':
            query = query.filter(BugReport.assignee_id == int(assignee_filter))

        # Get total count and paginate
        total = query.count()
        bugs = query.order_by(desc(BugReport.updated_at))\
            .offset((page - 1) * per_page)\
            .limit(per_page).all()

        # Get filter options
        users = db_session.query(User).filter(User.user_type.in_([UserType.SUPER_ADMIN, UserType.DEVELOPER])).all()

        return render_template('development/bugs.html',
                             bugs=bugs,
                             users=users,
                             total=total,
                             page=page,
                             per_page=per_page,
                             status_filter=status_filter,
                             severity_filter=severity_filter,
                             assignee_filter=assignee_filter,
                             BugStatus=BugStatus,
                             BugSeverity=BugSeverity,
                             BugPriority=BugPriority)

    finally:
        db_session.close()

# Release Routes
@development_bp.route('/releases')
@login_required
@permission_required('can_view_releases')
def releases():
    """List all releases with filtering"""
    db_session = SessionLocal()
    try:
        status_filter = request.args.get('status', 'active')

        query = db_session.query(Release)\
            .options(joinedload(Release.release_manager))

        if status_filter == 'active':
            query = query.filter(Release.status.in_([
                ReleaseStatus.PLANNING,
                ReleaseStatus.IN_DEVELOPMENT,
                ReleaseStatus.TESTING,
                ReleaseStatus.READY
            ]))
        elif status_filter != 'all':
            query = query.filter(Release.status == ReleaseStatus(status_filter))

        releases = query.order_by(desc(Release.planned_date)).all()

        return render_template('development/releases.html',
                             releases=releases,
                             status_filter=status_filter,
                             ReleaseStatus=ReleaseStatus,
                             ReleaseType=ReleaseType)

    finally:
        db_session.close()

@development_bp.route('/bugs/new', methods=['GET', 'POST'])
@login_required
@permission_required('can_create_bugs')
def new_bug():
    """Create a new bug report"""
    if request.method == 'POST':
        db_session = SessionLocal()
        try:
            # Verify current user exists in database
            user = db_session.query(User).filter(User.id == current_user.id).first()
            if not user:
                flash('Error: Your user account no longer exists. Please log in again.', 'error')
                return redirect(url_for('auth.logout'))

            # Handle screenshot upload
            screenshot_path = None
            if 'screenshot' in request.files:
                screenshot = request.files['screenshot']
                if screenshot and screenshot.filename:
                    # Secure the filename
                    filename = secure_filename(screenshot.filename)
                    # Create unique filename with timestamp
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    unique_filename = f"bug_{timestamp}_{filename}"
                    # Create uploads/bugs directory if it doesn't exist
                    os.makedirs('static/uploads/bugs', exist_ok=True)
                    # Save the file
                    file_path = os.path.join('static', 'uploads', 'bugs', unique_filename)
                    screenshot.save(file_path)
                    # Store relative path for database
                    screenshot_path = f"uploads/bugs/{unique_filename}"
                    logger.info(f"Screenshot saved to: {file_path}")

            bug = BugReport(
                title=request.form['title'],
                description=request.form['description'],
                severity=BugSeverity(request.form.get('severity', 'Medium')),
                priority=BugPriority(request.form.get('priority', 'Medium')),
                steps_to_reproduce=request.form.get('steps_to_reproduce'),
                expected_behavior=request.form.get('expected_behavior'),
                actual_behavior=request.form.get('actual_behavior'),
                component=request.form.get('component'),
                environment=request.form.get('environment'),
                browser_version=request.form.get('browser_version'),
                operating_system=request.form.get('operating_system'),
                reporter_id=current_user.id,
                assignee_id=request.form.get('assignee_id') if request.form.get('assignee_id') else None,
                estimated_fix_time=request.form.get('estimated_fix_time'),
                customer_impact=request.form.get('customer_impact'),
                screenshot_path=screenshot_path
            )

            db_session.add(bug)
            db_session.commit()

            flash(f'Bug report {bug.display_id} created successfully!', 'success')
            return redirect(url_for('development.view_bug', id=bug.id))

        except Exception as e:
            db_session.rollback()
            flash(f'Error creating bug report: {str(e)}', 'error')
            logger.error(f'Error creating bug report: {str(e)}')
        finally:
            db_session.close()

    # GET - show form
    db_session = SessionLocal()
    try:
        from models.bug_report import Tester
        # Only developers can be assigned to bugs
        users = db_session.query(User).filter(User.user_type == UserType.DEVELOPER).all()
        # Get active testers
        testers = db_session.query(Tester).filter(Tester.is_active == 'Yes').all()
        return render_template('development/bug_form.html',
                             users=users,
                             testers=testers,
                             BugSeverity=BugSeverity,
                             BugPriority=BugPriority)
    finally:
        db_session.close()

@development_bp.route('/bugs/<int:id>')
@login_required
@permission_required('can_view_bugs')
def view_bug(id):
    """View a specific bug report"""
    from models.bug_report import Tester, TestCase, BugTesterAssignment
    db_session = SessionLocal()
    try:
        bug = db_session.query(BugReport)\
            .options(joinedload(BugReport.reporter),
                    joinedload(BugReport.assignee),
                    joinedload(BugReport.fixed_in_release),
                    joinedload(BugReport.comments).joinedload(BugComment.user),
                    joinedload(BugReport.tester_assignments).joinedload(BugTesterAssignment.tester).joinedload(Tester.user),
                    joinedload(BugReport.test_cases).joinedload(TestCase.created_by),
                    joinedload(BugReport.test_cases).joinedload(TestCase.tested_by))\
            .filter(BugReport.id == id).first()

        if not bug:
            flash('Bug report not found', 'error')
            return redirect(url_for('development.bugs'))

        # Get all active testers
        testers = db_session.query(Tester)\
            .filter(Tester.is_active == 'Yes')\
            .options(joinedload(Tester.user))\
            .all()

        # Get all users for @mentions
        import json
        all_users = db_session.query(User).all()
        users_json = json.dumps([{'id': u.id, 'username': u.username, 'email': u.email} for u in all_users])

        return render_template('development/bug_view.html', bug=bug, testers=testers, users_json=users_json)

    finally:
        db_session.close()

@development_bp.route('/bugs/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('can_edit_bugs')
def edit_bug(id):
    """Edit a bug report"""
    db_session = SessionLocal()
    try:
        bug = db_session.query(BugReport)\
            .options(joinedload(BugReport.reporter),
                    joinedload(BugReport.assignee))\
            .filter(BugReport.id == id).first()

        if not bug:
            flash('Bug report not found', 'error')
            return redirect(url_for('development.bugs'))

        if request.method == 'POST':
            try:
                # Handle screenshot upload
                if 'screenshot' in request.files:
                    screenshot = request.files['screenshot']
                    if screenshot and screenshot.filename:
                        # Secure the filename
                        filename = secure_filename(screenshot.filename)
                        # Create unique filename with timestamp
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        unique_filename = f"bug_{bug.id}_{timestamp}_{filename}"
                        # Create uploads/bugs directory if it doesn't exist
                        os.makedirs('static/uploads/bugs', exist_ok=True)
                        # Save the file
                        file_path = os.path.join('static', 'uploads', 'bugs', unique_filename)
                        screenshot.save(file_path)
                        # Store relative path for database
                        bug.screenshot_path = f"uploads/bugs/{unique_filename}"
                        logger.info(f"Screenshot saved to: {file_path}")

                bug.title = request.form['title']
                bug.description = request.form['description']
                bug.severity = BugSeverity(request.form['severity'])
                bug.priority = BugPriority(request.form['priority'])
                bug.steps_to_reproduce = request.form.get('steps_to_reproduce')
                bug.expected_behavior = request.form.get('expected_behavior')
                bug.actual_behavior = request.form.get('actual_behavior')
                bug.component = request.form.get('component')
                bug.environment = request.form.get('environment')
                bug.assignee_id = request.form.get('assignee_id') if request.form.get('assignee_id') else None
                bug.case_progress = int(request.form.get('case_progress', 0))

                if request.form.get('status'):
                    bug.status = BugStatus(request.form['status'])
                    if bug.status in [BugStatus.RESOLVED, BugStatus.CLOSED] and not bug.resolution_date:
                        bug.resolution_date = datetime.utcnow()
                        bug.resolution_notes = request.form.get('resolution_notes')

                # Handle tester assignments
                from models.bug_report import BugTesterAssignment
                tester_ids = request.form.getlist('tester_ids')
                notify_testers = request.form.get('notify_testers') == 'yes'

                # Remove old assignments not in new list
                for assignment in bug.tester_assignments:
                    if str(assignment.tester_id) not in tester_ids:
                        db_session.delete(assignment)

                # Add new assignments
                existing_tester_ids = [a.tester_id for a in bug.tester_assignments]
                for tester_id in tester_ids:
                    if int(tester_id) not in existing_tester_ids:
                        assignment = BugTesterAssignment(
                            bug_id=bug.id,
                            tester_id=int(tester_id),
                            notified='Yes' if notify_testers else 'No',
                            notified_at=datetime.utcnow() if notify_testers else None
                        )
                        db_session.add(assignment)

                        # TODO: Send notification to tester if notify_testers is True
                        if notify_testers:
                            logger.info(f"Tester {tester_id} notified about bug {bug.id}")

                db_session.commit()
                flash(f'Bug report {bug.display_id} updated successfully!', 'success')
                return redirect(url_for('development.view_bug', id=bug.id))

            except Exception as e:
                db_session.rollback()
                flash(f'Error updating bug report: {str(e)}', 'error')
                logger.error(f'Error updating bug report: {str(e)}')

        # GET - show form
        from models.bug_report import Tester
        # Only developers can be assigned to bugs
        users = db_session.query(User).filter(User.user_type == UserType.DEVELOPER).all()
        # Get active testers
        testers = db_session.query(Tester).filter(Tester.is_active == 'Yes').all()
        return render_template('development/bug_form.html',
                             bug=bug,
                             users=users,
                             testers=testers,
                             BugSeverity=BugSeverity,
                             BugPriority=BugPriority,
                             BugStatus=BugStatus)
    finally:
        db_session.close()

@development_bp.route('/bugs/<int:id>/comment', methods=['POST'])
@login_required
@permission_required('can_edit_bugs')
def add_bug_comment(id):
    """Add a comment to a bug report"""
    db_session = SessionLocal()
    try:
        bug = db_session.query(BugReport).filter(BugReport.id == id).first()
        if not bug:
            flash('Bug report not found', 'error')
            return redirect(url_for('development.bugs'))

        content = request.form['content']
        comment = BugComment(
            content=content,
            bug_id=bug.id,
            user_id=current_user.id,
            comment_type=request.form.get('comment_type', 'comment')
        )

        db_session.add(comment)
        db_session.commit()

        # Extract @mentions and send email notifications
        import re
        mentions = re.findall(r'@(\w+)', content)
        if mentions:
            logger.info(f"Found {len(mentions)} mentions in comment: {mentions}")
            mentioned_users = db_session.query(User).filter(User.username.in_(mentions)).all()
            logger.info(f"Found {len(mentioned_users)} matching users in database")
            for mentioned_user in mentioned_users:
                if mentioned_user.email and mentioned_user.id != current_user.id:
                    try:
                        logger.info(f"Attempting to send mention email to {mentioned_user.username} ({mentioned_user.email})")
                        success = send_mention_email(mentioned_user, current_user, bug, content)
                        if success:
                            logger.info(f"Mention email sent successfully to {mentioned_user.email}")
                        else:
                            logger.error(f"Failed to send mention email to {mentioned_user.email} (returned False)")
                    except Exception as email_error:
                        logger.error(f"Exception sending mention email to {mentioned_user.email}: {str(email_error)}", exc_info=True)
                else:
                    if not mentioned_user.email:
                        logger.warning(f"User {mentioned_user.username} has no email address")
                    elif mentioned_user.id == current_user.id:
                        logger.info(f"Skipping email to self ({mentioned_user.username})")

        flash('Comment added successfully!', 'success')
        return redirect(url_for('development.view_bug', id=id))

    except Exception as e:
        db_session.rollback()
        flash(f'Error adding comment: {str(e)}', 'error')
        return redirect(url_for('development.view_bug', id=id))
    finally:
        db_session.close()


def send_mention_email(mentioned_user, commenter, bug, comment_content):
    """Send email notification when user is mentioned in a comment"""
    from flask import current_app

    try:
        logging.info(f"Attempting to send mention notification to {mentioned_user.email}")

        if not mentioned_user.email:
            logging.warning(f"User {mentioned_user.username} has no email address")
            return False

        # Create the bug URL
        bug_url = f"https://inventory.truelog.com.sg/development/bugs/{bug.id}"

        subject = f"You were mentioned in {bug.display_id}"

        # Get severity color mapping
        severity_colors = {
            'Low': {'bg': '#dcfce7', 'text': '#16a34a'},
            'Medium': {'bg': '#fef3c7', 'text': '#d97706'},
            'High': {'bg': '#fed7aa', 'text': '#ea580c'},
            'Critical': {'bg': '#fee2e2', 'text': '#dc2626'}
        }
        severity_value = bug.severity.value if bug.severity else 'Medium'
        severity_style = severity_colors.get(severity_value, severity_colors['Medium'])

        # Get status color mapping
        status_colors = {
            'Open': {'bg': '#fee2e2', 'text': '#dc2626'},
            'In Progress': {'bg': '#fef3c7', 'text': '#d97706'},
            'Testing': {'bg': '#dbeafe', 'text': '#2563eb'},
            'Resolved': {'bg': '#dcfce7', 'text': '#16a34a'},
            'Closed': {'bg': '#f3f4f6', 'text': '#6b7280'},
            'Reopened': {'bg': '#fed7aa', 'text': '#ea580c'}
        }
        status_value = bug.status.value if bug.status else 'Open'
        status_style = status_colors.get(status_value, status_colors['Open'])

        # HTML email template
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Mention Notification - {bug.display_id}</title>
        </head>
        <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f9;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff;">
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%); padding: 30px 40px; text-align: center;">
                    <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 600;">
                        💬 You Were Mentioned
                    </h1>
                    <p style="color: #fecaca; margin: 8px 0 0 0; font-size: 16px;">
                        TrueLog Development System
                    </p>
                </div>

                <!-- Main Content -->
                <div style="padding: 40px;">
                    <div style="background-color: #fef2f2; border-left: 4px solid #dc2626; padding: 20px; margin-bottom: 30px; border-radius: 0 8px 8px 0;">
                        <h2 style="color: #1a202c; margin: 0 0 10px 0; font-size: 20px;">
                            Hello {mentioned_user.username}!
                        </h2>
                        <p style="color: #4a5568; margin: 0; font-size: 16px; line-height: 1.5;">
                            <strong>{commenter.username}</strong> mentioned you in a comment on {bug.display_id}.
                        </p>
                    </div>

                    <!-- Bug Details Card -->
                    <div style="border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; margin-bottom: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <div style="background-color: #dc2626; color: white; padding: 15px 20px;">
                            <h3 style="margin: 0; font-size: 16px; font-weight: 600;">🐛 Bug Details</h3>
                        </div>
                        <div style="padding: 20px;">
                            <table style="width: 100%; border-collapse: collapse;">
                                <tr>
                                    <td style="padding: 8px 0; color: #718096; font-weight: 600; width: 120px;">Bug ID:</td>
                                    <td style="padding: 8px 0; color: #2d3748;">{bug.display_id}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0; color: #718096; font-weight: 600;">Title:</td>
                                    <td style="padding: 8px 0; color: #2d3748; font-weight: 600;">{bug.title}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0; color: #718096; font-weight: 600;">Severity:</td>
                                    <td style="padding: 8px 0;">
                                        <span style="background-color: {severity_style['bg']};
                                                     color: {severity_style['text']};
                                                     padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 600;">
                                            {severity_value}
                                        </span>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0; color: #718096; font-weight: 600;">Status:</td>
                                    <td style="padding: 8px 0;">
                                        <span style="background-color: {status_style['bg']};
                                                     color: {status_style['text']};
                                                     padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 600;">
                                            {status_value}
                                        </span>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0; color: #718096; font-weight: 600;">Case Owner:</td>
                                    <td style="padding: 8px 0; color: #2d3748;">{bug.assignee.username if bug.assignee else 'Unassigned'}</td>
                                </tr>
                            </table>
                        </div>
                    </div>

                    <!-- Comment Preview -->
                    <div style="background-color: #f7fafc; border-radius: 8px; padding: 20px; margin-bottom: 30px;">
                        <h4 style="color: #2d3748; margin: 0 0 10px 0; font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">💬 {commenter.username} said:</h4>
                        <p style="color: #4a5568; margin: 0; line-height: 1.6; font-size: 14px; white-space: pre-wrap;">
                            {comment_content}
                        </p>
                    </div>

                    <!-- Action Button -->
                    <div style="text-align: center; margin-bottom: 30px;">
                        <a href="{bug_url}"
                           style="background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%);
                                  color: white;
                                  text-decoration: none;
                                  padding: 14px 28px;
                                  border-radius: 8px;
                                  font-weight: 600;
                                  font-size: 16px;
                                  display: inline-block;
                                  box-shadow: 0 4px 6px rgba(220, 38, 38, 0.3);
                                  transition: all 0.3s ease;">
                            🔗 View Bug & Reply
                        </a>
                    </div>

                    <!-- Next Steps -->
                    <div style="background-color: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 20px;">
                        <h4 style="color: #991b1b; margin: 0 0 10px 0; font-size: 16px; font-weight: 600;">
                            ✅ What's Next?
                        </h4>
                        <ul style="color: #b91c1c; margin: 0; padding-left: 20px; line-height: 1.6;">
                            <li>Review the bug details and comment</li>
                            <li>Reply to the comment to continue the conversation</li>
                            <li>Add any additional information or insights</li>
                            <li>Collaborate with the team to resolve the issue</li>
                        </ul>
                    </div>
                </div>

                <!-- Footer -->
                <div style="background-color: #f7fafc; padding: 30px 40px; text-align: center; border-top: 1px solid #e2e8f0;">
                    <p style="color: #718096; margin: 0 0 10px 0; font-size: 14px;">
                        This notification was sent because you were mentioned in a comment.
                    </p>
                    <p style="color: #a0aec0; margin: 0; font-size: 12px;">
                        TrueLog Development System |
                        <a href="https://inventory.truelog.com.sg" style="color: #dc2626; text-decoration: none;">inventory.truelog.com.sg</a>
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        # Plain text fallback
        plain_body = f"""
Hi {mentioned_user.username},

{commenter.username} mentioned you in a comment on {bug.display_id}.

Bug Details:
- Bug ID: {bug.display_id}
- Title: {bug.title}
- Severity: {severity_value}
- Status: {status_value}
- Case Owner: {bug.assignee.username if bug.assignee else 'Unassigned'}

Comment:
{comment_content}

View the bug and reply: {bug_url}

Best regards,
TrueLog Development System
"""

        # Send email using the email_sender utility
        from utils.email_sender import _send_email_via_method

        success = _send_email_via_method(
            to_emails=mentioned_user.email,
            subject=subject,
            text_body=plain_body,
            html_body=html_body
        )

        if success:
            logging.info(f"Mention notification sent successfully to {mentioned_user.email}")
        else:
            logging.error(f"Failed to send mention notification to {mentioned_user.email}")

        return success

    except Exception as e:
        logging.error(f"Failed to send mention email to {mentioned_user.email}: {str(e)}")
        return False

@development_bp.route('/releases/<int:id>')
@login_required
@permission_required('can_view_releases')
def view_release(id):
    """View a specific release"""
    db_session = SessionLocal()
    try:
        release = db_session.query(Release)\
            .options(joinedload(Release.release_manager),
                    joinedload(Release.features),
                    joinedload(Release.fixed_bugs),
                    joinedload(Release.changelog_entries))\
            .filter(Release.id == id).first()

        if not release:
            flash('Release not found', 'error')
            return redirect(url_for('development.releases'))

        return render_template('development/release_view.html', release=release)

    finally:
        db_session.close()

@development_bp.route('/releases/new', methods=['GET', 'POST'])
@login_required
@permission_required('can_create_releases')
def new_release():
    """Create a new release"""
    if request.method == 'POST':
        db_session = SessionLocal()
        try:
            release = Release(
                version=request.form['version'],
                name=request.form.get('name'),
                description=request.form.get('description'),
                release_type=ReleaseType(request.form['release_type']),
                planned_date=datetime.strptime(request.form['planned_date'], '%Y-%m-%d').date() if request.form.get('planned_date') else None,
                release_manager_id=request.form.get('release_manager_id') if request.form.get('release_manager_id') else None,
                is_pre_release=request.form.get('is_pre_release') == 'on',
                is_hotfix=request.form.get('is_hotfix') == 'on',
                release_notes=request.form.get('release_notes'),
                breaking_changes=request.form.get('breaking_changes'),
                deployment_environment=request.form.get('deployment_environment')
            )

            db_session.add(release)
            db_session.commit()

            flash(f'Release {release.display_version} created successfully!', 'success')
            return redirect(url_for('development.view_release', id=release.id))

        except Exception as e:
            db_session.rollback()
            flash(f'Error creating release: {str(e)}', 'error')
        finally:
            db_session.close()

    # GET - show form
    db_session = SessionLocal()
    try:
        users = db_session.query(User).filter(User.user_type.in_([UserType.SUPER_ADMIN, UserType.DEVELOPER])).all()
        return render_template('development/release_form.html',
                             users=users,
                             ReleaseType=ReleaseType)
    finally:
        db_session.close()

@development_bp.route('/releases/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('can_edit_releases')
def edit_release(id):
    """Edit a release"""
    db_session = SessionLocal()
    try:
        release = db_session.query(Release)\
            .options(joinedload(Release.release_manager))\
            .filter(Release.id == id).first()

        if not release:
            flash('Release not found', 'error')
            return redirect(url_for('development.releases'))

        if request.method == 'POST':
            try:
                release.version = request.form['version']
                release.name = request.form.get('name')
                release.description = request.form.get('description')
                release.release_type = ReleaseType(request.form['release_type'])
                release.planned_date = datetime.strptime(request.form['planned_date'], '%Y-%m-%d').date() if request.form.get('planned_date') else None
                release.release_manager_id = request.form.get('release_manager_id') if request.form.get('release_manager_id') else None
                release.is_pre_release = request.form.get('is_pre_release') == 'on'
                release.is_hotfix = request.form.get('is_hotfix') == 'on'
                release.release_notes = request.form.get('release_notes')
                release.breaking_changes = request.form.get('breaking_changes')
                release.deployment_environment = request.form.get('deployment_environment')

                if request.form.get('status'):
                    release.status = ReleaseStatus(request.form['status'])
                    if release.status == ReleaseStatus.RELEASED and not release.release_date:
                        release.release_date = datetime.utcnow()
                        release.update_metrics()

                db_session.commit()
                flash(f'Release {release.display_version} updated successfully!', 'success')
                return redirect(url_for('development.view_release', id=release.id))

            except Exception as e:
                db_session.rollback()
                flash(f'Error updating release: {str(e)}', 'error')

        # GET - show form
        users = db_session.query(User).filter(User.user_type.in_([UserType.SUPER_ADMIN, UserType.DEVELOPER])).all()
        return render_template('development/release_form.html',
                             release=release,
                             users=users,
                             ReleaseType=ReleaseType,
                             ReleaseStatus=ReleaseStatus)
    finally:
        db_session.close()

@development_bp.route('/releases/<int:id>/status', methods=['POST'])
@login_required
@permission_required('can_edit_releases')
def update_release_status(id):
    """Update release status"""
    db_session = SessionLocal()
    try:
        release = db_session.query(Release).filter(Release.id == id).first()
        if not release:
            flash('Release not found', 'error')
            return redirect(url_for('development.releases'))

        new_status = request.form.get('status')
        if new_status:
            release.status = ReleaseStatus(new_status)
            if release.status == ReleaseStatus.RELEASED and not release.release_date:
                release.release_date = datetime.utcnow()
                release.update_metrics()

            db_session.commit()
            flash(f'Release status updated to {release.status.value}', 'success')

        return redirect(url_for('development.view_release', id=id))

    except Exception as e:
        db_session.rollback()
        flash(f'Error updating status: {str(e)}', 'error')
        return redirect(url_for('development.view_release', id=id))
    finally:
        db_session.close()

@development_bp.route('/releases/<int:id>/changelog')
@login_required
@permission_required('can_view_releases')
def release_changelog(id):
    """Generate and display release changelog"""
    db_session = SessionLocal()
    try:
        release = db_session.query(Release)\
            .options(joinedload(Release.features),
                    joinedload(Release.fixed_bugs),
                    joinedload(Release.changelog_entries))\
            .filter(Release.id == id).first()

        if not release:
            flash('Release not found', 'error')
            return redirect(url_for('development.releases'))

        changelog = release.generate_changelog()

        return render_template('development/changelog.html',
                             release=release,
                             changelog=changelog)

    finally:
        db_session.close()

@development_bp.route('/releases/<int:id>/export')
@login_required
@permission_required('can_view_releases')
def export_changelog(id):
    """Export changelog as markdown file"""
    db_session = SessionLocal()
    try:
        release = db_session.query(Release)\
            .options(joinedload(Release.features),
                    joinedload(Release.fixed_bugs))\
            .filter(Release.id == id).first()

        if not release:
            flash('Release not found', 'error')
            return redirect(url_for('development.releases'))

        changelog = release.generate_changelog()

        from flask import Response

        response = Response(
            changelog,
            mimetype='text/markdown',
            headers={
                'Content-Disposition': f'attachment; filename=changelog-{release.version}.md'
            }
        )

        return response

    finally:
        db_session.close()

@development_bp.route('/bugs/<int:id>/status', methods=['POST'])
@login_required
@permission_required('can_edit_bugs')
def update_bug_status(id):
    """Update bug status"""
    db_session = SessionLocal()
    try:
        bug = db_session.query(BugReport).filter(BugReport.id == id).first()
        if not bug:
            flash('Bug report not found', 'error')
            return redirect(url_for('development.bugs'))

        new_status = request.form.get('status')
        if new_status:
            # Convert string to enum by name (e.g., 'IN_PROGRESS' -> BugStatus.IN_PROGRESS)
            bug.status = BugStatus[new_status]

            # Auto-update case progress based on status
            status_progress_map = {
                BugStatus.OPEN: 0,
                BugStatus.IN_PROGRESS: 25,
                BugStatus.TESTING: 75,
                BugStatus.RESOLVED: 100,
                BugStatus.CLOSED: 100,
                BugStatus.REOPENED: 10
            }
            bug.case_progress = status_progress_map.get(bug.status, bug.case_progress)

            if bug.status in [BugStatus.RESOLVED, BugStatus.CLOSED] and not bug.resolution_date:
                bug.resolution_date = datetime.utcnow()

            db_session.commit()
            flash(f'Bug status updated to {bug.status.value} (Progress: {bug.case_progress}%)', 'success')

        return redirect(url_for('development.view_bug', id=id))

    except Exception as e:
        db_session.rollback()
        flash(f'Error updating status: {str(e)}', 'error')
        return redirect(url_for('development.view_bug', id=id))
    finally:
        db_session.close()

@development_bp.route('/bugs/<int:id>/delete', methods=['POST'])
@login_required
@permission_required('can_edit_bugs')
def delete_bug(id):
    """Delete a bug report"""
    db_session = SessionLocal()
    try:
        bug = db_session.query(BugReport).filter(BugReport.id == id).first()
        if not bug:
            flash('Bug report not found', 'error')
            return redirect(url_for('development.bugs'))

        bug_display_id = bug.display_id
        db_session.delete(bug)
        db_session.commit()

        flash(f'Bug {bug_display_id} deleted successfully', 'success')
        return redirect(url_for('development.bugs'))

    except Exception as e:
        db_session.rollback()
        flash(f'Error deleting bug: {str(e)}', 'error')
        return redirect(url_for('development.view_bug', id=id))
    finally:
        db_session.close()

# ============= TESTER MANAGEMENT =============

@development_bp.route('/testers')
@login_required
@permission_required('can_edit_bugs')
def manage_testers():
    """View and manage testers"""
    from models.bug_report import Tester
    db_session = SessionLocal()
    try:
        testers = db_session.query(Tester).all()
        # Get users who are not already testers
        tester_user_ids = [t.user_id for t in testers]
        available_users = db_session.query(User).filter(~User.id.in_(tester_user_ids)).all()
        return render_template('development/testers.html',
                             testers=testers,
                             available_users=available_users)
    finally:
        db_session.close()

@development_bp.route('/testers/add', methods=['POST'])
@login_required
@permission_required('can_edit_bugs')
def add_tester():
    """Add a new tester"""
    from models.bug_report import Tester
    db_session = SessionLocal()
    try:
        user_id = request.form.get('user_id')
        specialization = request.form.get('specialization')

        # Check if user is already a tester
        existing = db_session.query(Tester).filter(Tester.user_id == user_id).first()
        if existing:
            flash('This user is already a tester', 'error')
            return redirect(url_for('development.manage_testers'))

        tester = Tester(
            user_id=user_id,
            specialization=specialization,
            is_active='Yes'
        )
        db_session.add(tester)
        db_session.commit()

        flash(f'Tester added successfully!', 'success')
        return redirect(url_for('development.manage_testers'))

    except Exception as e:
        db_session.rollback()
        flash(f'Error adding tester: {str(e)}', 'error')
        return redirect(url_for('development.manage_testers'))
    finally:
        db_session.close()

@development_bp.route('/testers/<int:id>/toggle', methods=['POST'])
@login_required
@permission_required('can_edit_bugs')
def toggle_tester(id):
    """Toggle tester active status"""
    from models.bug_report import Tester
    db_session = SessionLocal()
    try:
        tester = db_session.query(Tester).filter(Tester.id == id).first()
        if not tester:
            flash('Tester not found', 'error')
            return redirect(url_for('development.manage_testers'))

        tester.is_active = 'No' if tester.is_active == 'Yes' else 'Yes'
        db_session.commit()

        status = 'activated' if tester.is_active == 'Yes' else 'deactivated'
        flash(f'Tester {status} successfully', 'success')
        return redirect(url_for('development.manage_testers'))

    except Exception as e:
        db_session.rollback()
        flash(f'Error toggling tester status: {str(e)}', 'error')
        return redirect(url_for('development.manage_testers'))
    finally:
        db_session.close()

@development_bp.route('/testers/<int:id>/remove', methods=['POST'])
@login_required
@permission_required('can_edit_bugs')
def remove_tester(id):
    """Remove a tester"""
    from models.bug_report import Tester
    db_session = SessionLocal()
    try:
        tester = db_session.query(Tester).filter(Tester.id == id).first()
        if not tester:
            flash('Tester not found', 'error')
            return redirect(url_for('development.manage_testers'))

        db_session.delete(tester)
        db_session.commit()

        flash(f'Tester removed successfully', 'success')
        return redirect(url_for('development.manage_testers'))

    except Exception as e:
        db_session.rollback()
        flash(f'Error removing tester: {str(e)}', 'error')
        return redirect(url_for('development.manage_testers'))
    finally:
        db_session.close()


# ============================================================================
# TEST CASE MANAGEMENT ROUTES
# ============================================================================

@development_bp.route('/bugs/<int:bug_id>/test-cases')
@login_required
@permission_required('can_view_bugs')
def bug_test_cases(bug_id):
    """View test cases for a bug"""
    from models.bug_report import TestCase
    db_session = SessionLocal()
    try:
        bug = db_session.query(BugReport).options(
            joinedload(BugReport.test_cases).joinedload(TestCase.created_by),
            joinedload(BugReport.test_cases).joinedload(TestCase.tested_by),
            joinedload(BugReport.reporter),
            joinedload(BugReport.assignee)
        ).filter(BugReport.id == bug_id).first()

        if not bug:
            flash('Bug not found', 'error')
            return redirect(url_for('development.bugs'))

        return render_template('development/test_cases.html', bug=bug)
    finally:
        db_session.close()


@development_bp.route('/bugs/<int:bug_id>/test-cases/new', methods=['GET', 'POST'])
@login_required
@permission_required('can_create_bugs')
def new_test_case(bug_id):
    """Create a new test case"""
    from models.bug_report import TestCase
    db_session = SessionLocal()
    try:
        bug = db_session.query(BugReport).filter(BugReport.id == bug_id).first()
        if not bug:
            flash('Bug not found', 'error')
            return redirect(url_for('development.bugs'))

        if request.method == 'POST':
            test_case = TestCase(
                bug_id=bug_id,
                title=request.form.get('title'),
                description=request.form.get('description'),
                preconditions=request.form.get('preconditions'),
                test_steps=request.form.get('test_steps'),
                expected_result=request.form.get('expected_result'),
                priority=request.form.get('priority', 'Medium'),
                test_data=request.form.get('test_data'),
                created_by_id=current_user.id
            )

            db_session.add(test_case)
            db_session.commit()

            flash(f'Test case {test_case.display_id} created successfully', 'success')
            return redirect(url_for('development.bug_test_cases', bug_id=bug_id))

        return render_template('development/test_case_form.html', bug=bug, test_case=None)

    except Exception as e:
        db_session.rollback()
        flash(f'Error creating test case: {str(e)}', 'error')
        return redirect(url_for('development.bug_test_cases', bug_id=bug_id))
    finally:
        db_session.close()


@development_bp.route('/test-cases/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('can_edit_bugs')
def edit_test_case(id):
    """Edit a test case"""
    from models.bug_report import TestCase
    db_session = SessionLocal()
    try:
        test_case = db_session.query(TestCase).options(
            joinedload(TestCase.bug)
        ).filter(TestCase.id == id).first()

        if not test_case:
            flash('Test case not found', 'error')
            return redirect(url_for('development.bugs'))

        if request.method == 'POST':
            test_case.title = request.form.get('title')
            test_case.description = request.form.get('description')
            test_case.preconditions = request.form.get('preconditions')
            test_case.test_steps = request.form.get('test_steps')
            test_case.expected_result = request.form.get('expected_result')
            test_case.priority = request.form.get('priority', 'Medium')
            test_case.test_data = request.form.get('test_data')
            test_case.updated_at = datetime.utcnow()

            db_session.commit()

            flash(f'Test case {test_case.display_id} updated successfully', 'success')
            return redirect(url_for('development.bug_test_cases', bug_id=test_case.bug_id))

        return render_template('development/test_case_form.html', bug=test_case.bug, test_case=test_case)

    except Exception as e:
        db_session.rollback()
        flash(f'Error updating test case: {str(e)}', 'error')
        return redirect(url_for('development.bugs'))
    finally:
        db_session.close()


@development_bp.route('/test-cases/<int:id>/execute', methods=['GET', 'POST'])
@login_required
@permission_required('can_edit_bugs')
def execute_test_case(id):
    """Execute a test case (fill in actual results)"""
    from models.bug_report import TestCase
    db_session = SessionLocal()
    try:
        test_case = db_session.query(TestCase).options(
            joinedload(TestCase.bug)
        ).filter(TestCase.id == id).first()

        if not test_case:
            flash('Test case not found', 'error')
            return redirect(url_for('development.bugs'))

        if request.method == 'POST':
            test_case.actual_result = request.form.get('actual_result')
            test_case.status = request.form.get('status', 'Pending')
            test_case.tested_by_id = current_user.id
            test_case.tested_at = datetime.utcnow()
            test_case.updated_at = datetime.utcnow()

            db_session.commit()

            flash(f'Test case {test_case.display_id} executed successfully', 'success')
            return redirect(url_for('development.bug_test_cases', bug_id=test_case.bug_id))

        return render_template('development/execute_test_case.html', test_case=test_case)

    except Exception as e:
        db_session.rollback()
        flash(f'Error executing test case: {str(e)}', 'error')
        return redirect(url_for('development.bugs'))
    finally:
        db_session.close()


@development_bp.route('/test-cases/<int:id>/delete', methods=['POST'])
@login_required
@permission_required('can_edit_bugs')
def delete_test_case(id):
    """Delete a test case"""
    from models.bug_report import TestCase
    db_session = SessionLocal()
    try:
        test_case = db_session.query(TestCase).filter(TestCase.id == id).first()

        if not test_case:
            flash('Test case not found', 'error')
            return redirect(url_for('development.bugs'))

        bug_id = test_case.bug_id
        db_session.delete(test_case)
        db_session.commit()

        flash(f'Test case deleted successfully', 'success')
        return redirect(url_for('development.bug_test_cases', bug_id=bug_id))

    except Exception as e:
        db_session.rollback()
        flash(f'Error deleting test case: {str(e)}', 'error')
        return redirect(url_for('development.bugs'))
    finally:
        db_session.close()


# ============================================================================
# TESTER ASSIGNMENT TO BUGS
# ============================================================================

@development_bp.route('/bugs/<int:bug_id>/assign-testers', methods=['POST'])
@login_required
@permission_required('can_edit_bugs')
def assign_testers_to_bug(bug_id):
    """Assign testers to a bug"""
    from models.bug_report import BugTesterAssignment
    db_session = SessionLocal()
    try:
        bug = db_session.query(BugReport).filter(BugReport.id == bug_id).first()
        if not bug:
            flash('Bug not found', 'error')
            return redirect(url_for('development.bugs'))

        tester_ids = request.form.getlist('tester_ids')
        notify_testers = request.form.get('notify_testers') == 'yes'

        # Remove assignments not in the new list
        for assignment in bug.tester_assignments:
            if str(assignment.tester_id) not in tester_ids:
                db_session.delete(assignment)

        # Add new assignments
        existing_tester_ids = [a.tester_id for a in bug.tester_assignments]
        for tester_id in tester_ids:
            if int(tester_id) not in existing_tester_ids:
                assignment = BugTesterAssignment(
                    bug_id=bug_id,
                    tester_id=int(tester_id),
                    notified='Yes' if notify_testers else 'No',
                    notified_at=datetime.utcnow() if notify_testers else None
                )
                db_session.add(assignment)
                logger.info(f"Assigned tester {tester_id} to bug {bug_id}")
                if notify_testers:
                    logger.info(f"Tester {tester_id} notified for bug {bug_id}")

        db_session.commit()

        if tester_ids:
            flash(f'{len(tester_ids)} tester(s) assigned successfully', 'success')
        else:
            flash('All testers removed', 'success')

        return redirect(url_for('development.view_bug', id=bug_id))

    except Exception as e:
        db_session.rollback()
        flash(f'Error assigning testers: {str(e)}', 'error')
        return redirect(url_for('development.view_bug', id=bug_id))
    finally:
        db_session.close()


@development_bp.route('/bugs/<int:bug_id>/remove-tester/<int:assignment_id>', methods=['POST'])
@login_required
@permission_required('can_edit_bugs')
def remove_tester_from_bug(bug_id, assignment_id):
    """Remove a tester assignment from a bug"""
    from models.bug_report import BugTesterAssignment
    db_session = SessionLocal()
    try:
        assignment = db_session.query(BugTesterAssignment).filter(
            BugTesterAssignment.id == assignment_id,
            BugTesterAssignment.bug_id == bug_id
        ).first()

        if not assignment:
            flash('Tester assignment not found', 'error')
            return redirect(url_for('development.view_bug', id=bug_id))

        db_session.delete(assignment)
        db_session.commit()

        flash('Tester removed successfully', 'success')
        return redirect(url_for('development.view_bug', id=bug_id))

    except Exception as e:
        db_session.rollback()
        flash(f'Error removing tester: {str(e)}', 'error')
        return redirect(url_for('development.view_bug', id=bug_id))
    finally:
        db_session.close()

@development_bp.route('/features/<int:feature_id>/assign-testers', methods=['POST'])
@login_required
@permission_required('can_edit_features')
def assign_testers_to_feature(feature_id):
    """Assign testers to a feature"""
    from models.feature_request import FeatureTesterAssignment
    db_session = SessionLocal()
    try:
        feature = db_session.query(FeatureRequest).filter(FeatureRequest.id == feature_id).first()
        if not feature:
            flash('Feature not found', 'error')
            return redirect(url_for('development.features'))

        tester_ids = request.form.getlist('tester_ids')
        notify_testers = request.form.get('notify_testers') == 'yes'

        # Remove assignments not in the new list
        for assignment in feature.tester_assignments:
            if str(assignment.tester_id) not in tester_ids:
                db_session.delete(assignment)

        # Add new assignments
        existing_tester_ids = [a.tester_id for a in feature.tester_assignments]
        for tester_id in tester_ids:
            if int(tester_id) not in existing_tester_ids:
                assignment = FeatureTesterAssignment(
                    feature_id=feature_id,
                    tester_id=int(tester_id),
                    notified='Yes' if notify_testers else 'No',
                    notified_at=datetime.utcnow() if notify_testers else None
                )
                db_session.add(assignment)
                logger.info(f"Assigned tester {tester_id} to feature {feature_id}")
                if notify_testers:
                    logger.info(f"Tester {tester_id} notified for feature {feature_id}")

        db_session.commit()

        if tester_ids:
            flash(f'{len(tester_ids)} tester(s) assigned successfully', 'success')
        else:
            flash('All testers removed', 'success')

        return redirect(url_for('development.view_feature', id=feature_id))

    except Exception as e:
        db_session.rollback()
        flash(f'Error assigning testers: {str(e)}', 'error')
        return redirect(url_for('development.view_feature', id=feature_id))
    finally:
        db_session.close()


@development_bp.route('/features/<int:feature_id>/remove-tester/<int:assignment_id>', methods=['POST'])
@login_required
@permission_required('can_edit_features')
def remove_tester_from_feature(feature_id, assignment_id):
    """Remove a tester assignment from a feature"""
    from models.feature_request import FeatureTesterAssignment
    db_session = SessionLocal()
    try:
        assignment = db_session.query(FeatureTesterAssignment).filter(
            FeatureTesterAssignment.id == assignment_id,
            FeatureTesterAssignment.feature_id == feature_id
        ).first()

        if not assignment:
            flash('Tester assignment not found', 'error')
            return redirect(url_for('development.view_feature', id=feature_id))

        db_session.delete(assignment)
        db_session.commit()

        flash('Tester removed successfully', 'success')
        return redirect(url_for('development.view_feature', id=feature_id))

    except Exception as e:
        db_session.rollback()
        flash(f'Error removing tester: {str(e)}', 'error')
        return redirect(url_for('development.view_feature', id=feature_id))
    finally:
        db_session.close()


# ============================================
# Developer Schedule Routes
# ============================================

@development_bp.route('/schedule')
@login_required
@permission_required('can_access_development')
def schedule():
    """Display the developer schedule calendar"""
    return render_template('development/schedule.html')


@development_bp.route('/schedule/events')
@login_required
@permission_required('can_access_development')
def get_schedule_events():
    """Get all schedule events for the current user (API endpoint for calendar)"""
    from models.developer_schedule import DeveloperSchedule

    db_session = SessionLocal()
    try:
        # Get start and end dates from request (for filtering)
        start_str = request.args.get('start')
        end_str = request.args.get('end')

        query = db_session.query(DeveloperSchedule).filter(
            DeveloperSchedule.user_id == current_user.id
        )

        # Helper function to parse dates from FullCalendar
        # FullCalendar may send dates like "2025-10-26T00:00:00 08:00" (space before timezone)
        # instead of standard ISO format "2025-10-26T00:00:00+08:00"
        def parse_fullcalendar_date(date_str):
            import re
            if not date_str:
                return None
            # Replace Z with +00:00
            clean_date = date_str.replace('Z', '+00:00')
            # Fix space before timezone offset (e.g., " 08:00" -> "+08:00")
            clean_date = re.sub(r'(\d{2}:\d{2}:\d{2}) (\d{2}:\d{2})$', r'\1+\2', clean_date)
            return datetime.fromisoformat(clean_date).date()

        if start_str:
            start_date = parse_fullcalendar_date(start_str)
            query = query.filter(DeveloperSchedule.work_date >= start_date)

        if end_str:
            end_date = parse_fullcalendar_date(end_str)
            query = query.filter(DeveloperSchedule.work_date <= end_date)

        schedules = query.all()

        # Convert to FullCalendar event format
        events = []
        for schedule in schedules:
            # Determine color based on status and location
            if not schedule.is_working:
                bg_color = '#dc3545'  # Red for day off
                title = schedule.note if schedule.note else 'Off'
            elif schedule.work_location == 'WFH':
                bg_color = '#17a2b8'  # Blue for WFH
                title = schedule.note if schedule.note else 'WFH'
            else:
                bg_color = '#28a745'  # Green for WFO
                title = schedule.note if schedule.note else 'WFO'

            events.append({
                'id': schedule.id,
                'title': title,
                'start': schedule.work_date.isoformat(),
                'allDay': True,
                'backgroundColor': bg_color,
                'borderColor': bg_color,
                'extendedProps': {
                    'is_working': schedule.is_working,
                    'work_location': schedule.work_location,
                    'note': schedule.note
                }
            })

        return jsonify(events)

    except Exception as e:
        logger.error(f"Error fetching schedule events: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        db_session.close()


@development_bp.route('/schedule/toggle', methods=['POST'])
@login_required
@permission_required('can_access_development')
def toggle_schedule_day():
    """Toggle a working day on/off or update note"""
    from models.developer_schedule import DeveloperSchedule

    db_session = SessionLocal()
    try:
        data = request.get_json()
        work_date_str = data.get('date')
        note = data.get('note', '')
        is_working = data.get('is_working', True)
        work_location = data.get('work_location', 'WFO')

        if not work_date_str:
            return jsonify({'error': 'Date is required'}), 400

        work_date = datetime.strptime(work_date_str, '%Y-%m-%d').date()

        # Check if entry exists for this date
        existing = db_session.query(DeveloperSchedule).filter(
            DeveloperSchedule.user_id == current_user.id,
            DeveloperSchedule.work_date == work_date
        ).first()

        if existing:
            # Toggle or update existing entry
            if data.get('action') == 'delete':
                db_session.delete(existing)
                db_session.commit()
                return jsonify({'success': True, 'action': 'deleted'})
            else:
                existing.is_working = is_working
                existing.work_location = work_location
                existing.note = note
                existing.updated_at = datetime.utcnow()
                db_session.commit()
                return jsonify({
                    'success': True,
                    'action': 'updated',
                    'event': existing.to_dict()
                })
        else:
            # Create new entry
            new_schedule = DeveloperSchedule(
                user_id=current_user.id,
                work_date=work_date,
                is_working=is_working,
                work_location=work_location,
                note=note
            )
            db_session.add(new_schedule)
            db_session.commit()
            return jsonify({
                'success': True,
                'action': 'created',
                'event': new_schedule.to_dict()
            })

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error toggling schedule day: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        db_session.close()


@development_bp.route('/schedule/bulk', methods=['POST'])
@login_required
@permission_required('can_access_development')
def bulk_schedule_update():
    """Bulk update schedule - mark multiple days as working or off"""
    from models.developer_schedule import DeveloperSchedule

    db_session = SessionLocal()
    try:
        data = request.get_json()
        dates = data.get('dates', [])
        is_working = data.get('is_working', True)
        work_location = data.get('work_location', 'WFO')
        note = data.get('note', '')

        if not dates:
            return jsonify({'error': 'No dates provided'}), 400

        created = 0
        updated = 0

        for date_str in dates:
            work_date = datetime.strptime(date_str, '%Y-%m-%d').date()

            existing = db_session.query(DeveloperSchedule).filter(
                DeveloperSchedule.user_id == current_user.id,
                DeveloperSchedule.work_date == work_date
            ).first()

            if existing:
                existing.is_working = is_working
                existing.work_location = work_location
                existing.note = note
                existing.updated_at = datetime.utcnow()
                updated += 1
            else:
                new_schedule = DeveloperSchedule(
                    user_id=current_user.id,
                    work_date=work_date,
                    is_working=is_working,
                    work_location=work_location,
                    note=note
                )
                db_session.add(new_schedule)
                created += 1

        db_session.commit()
        return jsonify({
            'success': True,
            'created': created,
            'updated': updated
        })

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error in bulk schedule update: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        db_session.close()


# ============================================
# Admin Schedule View (Super Admin Only)
# ============================================

@development_bp.route('/schedule/admin')
@login_required
@permission_required('can_access_development')
def admin_schedule():
    """Display all developers' schedules - Super Admin only"""
    # Check if user is super admin
    if current_user.user_type != UserType.SUPER_ADMIN:
        flash('Access denied. Super Admin only.', 'error')
        return redirect(url_for('development.dashboard'))

    db_session = SessionLocal()
    try:
        # Get only developers (not super admins)
        developers = db_session.query(User).filter(
            User.user_type == UserType.DEVELOPER
        ).order_by(User.username).all()

        return render_template('development/admin_schedule.html', developers=developers)

    except Exception as e:
        logger.error(f"Error loading admin schedule: {str(e)}")
        flash('Error loading schedule view', 'error')
        return redirect(url_for('development.dashboard'))
    finally:
        db_session.close()


@development_bp.route('/schedule/admin/events')
@login_required
@permission_required('can_access_development')
def get_all_schedule_events():
    """Get all schedule events for all developers (API endpoint for calendar) - Super Admin only"""
    from models.developer_schedule import DeveloperSchedule

    # Check if user is super admin
    if current_user.user_type != UserType.SUPER_ADMIN:
        return jsonify({'error': 'Access denied'}), 403

    db_session = SessionLocal()
    try:
        # Get start and end dates from request (for filtering)
        start_str = request.args.get('start')
        end_str = request.args.get('end')
        user_id = request.args.get('user_id')  # Optional filter by user

        # Only get schedules for DEVELOPER users (not super admins)
        query = db_session.query(DeveloperSchedule).options(
            joinedload(DeveloperSchedule.user)
        ).filter(DeveloperSchedule.user.has(User.user_type == UserType.DEVELOPER))

        if user_id:
            query = query.filter(DeveloperSchedule.user_id == int(user_id))

        # Helper function to parse dates from FullCalendar
        # FullCalendar may send dates like "2025-10-26T00:00:00 08:00" (space before timezone)
        # instead of standard ISO format "2025-10-26T00:00:00+08:00"
        def parse_fullcalendar_date(date_str):
            import re
            if not date_str:
                return None
            # Replace Z with +00:00
            clean_date = date_str.replace('Z', '+00:00')
            # Fix space before timezone offset (e.g., " 08:00" -> "+08:00")
            clean_date = re.sub(r'(\d{2}:\d{2}:\d{2}) (\d{2}:\d{2})$', r'\1+\2', clean_date)
            return datetime.fromisoformat(clean_date).date()

        if start_str:
            start_date = parse_fullcalendar_date(start_str)
            query = query.filter(DeveloperSchedule.work_date >= start_date)

        if end_str:
            end_date = parse_fullcalendar_date(end_str)
            query = query.filter(DeveloperSchedule.work_date <= end_date)

        schedules = query.all()

        # Convert to FullCalendar event format with user info
        events = []
        for schedule in schedules:
            # Determine color based on status and location
            if not schedule.is_working:
                bg_color = '#dc3545'  # Red for day off
                title_prefix = 'Off'
            elif schedule.work_location == 'WFH':
                bg_color = '#17a2b8'  # Blue for WFH
                title_prefix = 'WFH'
            else:
                bg_color = '#28a745'  # Green for WFO
                title_prefix = 'WFO'

            # Include username in title
            username = schedule.user.username if schedule.user else 'Unknown'
            title = f"{username}: {title_prefix}"
            if schedule.note:
                title += f" - {schedule.note}"

            events.append({
                'id': schedule.id,
                'title': title,
                'start': schedule.work_date.isoformat(),
                'allDay': True,
                'backgroundColor': bg_color,
                'borderColor': bg_color,
                'extendedProps': {
                    'user_id': schedule.user_id,
                    'username': username,
                    'is_working': schedule.is_working,
                    'work_location': schedule.work_location,
                    'note': schedule.note
                }
            })

        return jsonify(events)

    except Exception as e:
        logger.error(f"Error fetching all schedule events: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        db_session.close()


# ============================================
# Developer Work Plan Routes
# ============================================

@development_bp.route('/work-plan')
@login_required
@permission_required('can_access_development')
def work_plan():
    """Display the developer work plan page"""
    from models.developer_work_plan import DeveloperWorkPlan
    from datetime import date, timedelta

    db_session = SessionLocal()
    try:
        # Get the current week's Monday
        today = date.today()
        week_start = DeveloperWorkPlan.get_week_start(today)

        # Get the work plan for current week
        current_plan = db_session.query(DeveloperWorkPlan).filter(
            DeveloperWorkPlan.user_id == current_user.id,
            DeveloperWorkPlan.week_start == week_start
        ).first()

        # Get next week's plan too
        next_week_start = week_start + timedelta(days=7)
        next_plan = db_session.query(DeveloperWorkPlan).filter(
            DeveloperWorkPlan.user_id == current_user.id,
            DeveloperWorkPlan.week_start == next_week_start
        ).first()

        # Get week dates for display
        week_dates = DeveloperWorkPlan.get_week_dates(week_start)
        next_week_dates = DeveloperWorkPlan.get_week_dates(next_week_start)

        return render_template('development/work_plan.html',
                               current_plan=current_plan,
                               next_plan=next_plan,
                               week_start=week_start,
                               next_week_start=next_week_start,
                               week_dates=week_dates,
                               next_week_dates=next_week_dates,
                               today=today)

    except Exception as e:
        logger.error(f"Error loading work plan: {str(e)}")
        flash('Error loading work plan', 'error')
        return redirect(url_for('development.dashboard'))
    finally:
        db_session.close()


@development_bp.route('/work-plan/save', methods=['POST'])
@login_required
@permission_required('can_access_development')
def save_work_plan():
    """Save or update a work plan"""
    from models.developer_work_plan import DeveloperWorkPlan
    from datetime import datetime

    db_session = SessionLocal()
    try:
        data = request.get_json()
        week_start_str = data.get('week_start')

        if not week_start_str:
            return jsonify({'error': 'Week start date is required'}), 400

        week_start = datetime.strptime(week_start_str, '%Y-%m-%d').date()

        # Find existing plan or create new one
        plan = db_session.query(DeveloperWorkPlan).filter(
            DeveloperWorkPlan.user_id == current_user.id,
            DeveloperWorkPlan.week_start == week_start
        ).first()

        if not plan:
            plan = DeveloperWorkPlan(
                user_id=current_user.id,
                week_start=week_start
            )
            db_session.add(plan)

        # Update fields
        plan.plan_summary = data.get('plan_summary', '')
        plan.monday_plan = data.get('monday_plan', '')
        plan.tuesday_plan = data.get('tuesday_plan', '')
        plan.wednesday_plan = data.get('wednesday_plan', '')
        plan.thursday_plan = data.get('thursday_plan', '')
        plan.friday_plan = data.get('friday_plan', '')
        plan.blockers = data.get('blockers', '')
        plan.notes = data.get('notes', '')
        plan.updated_at = datetime.utcnow()

        # Handle submission
        if data.get('submit'):
            plan.status = 'submitted'
            plan.submitted_at = datetime.utcnow()

        db_session.commit()

        return jsonify({
            'success': True,
            'message': 'Work plan saved successfully',
            'plan': plan.to_dict()
        })

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error saving work plan: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        db_session.close()


@development_bp.route('/work-plan/admin')
@login_required
@permission_required('can_access_development')
def admin_work_plan():
    """Display all developers' work plans - Super Admin only"""
    from models.developer_work_plan import DeveloperWorkPlan
    from datetime import date, timedelta

    # Check if user is super admin
    if current_user.user_type != UserType.SUPER_ADMIN:
        flash('Access denied. Super Admin only.', 'error')
        return redirect(url_for('development.dashboard'))

    db_session = SessionLocal()
    try:
        # Get the current week's Monday
        today = date.today()
        week_start = DeveloperWorkPlan.get_week_start(today)

        # Get week offset from query params (for navigation)
        week_offset = request.args.get('week', 0, type=int)
        selected_week_start = week_start + timedelta(weeks=week_offset)

        # Get all developers
        developers = db_session.query(User).filter(
            User.user_type == UserType.DEVELOPER
        ).order_by(User.username).all()

        # Get all work plans for the selected week
        work_plans = db_session.query(DeveloperWorkPlan).options(
            joinedload(DeveloperWorkPlan.user)
        ).filter(
            DeveloperWorkPlan.week_start == selected_week_start
        ).all()

        # Create a dict for easy lookup
        plans_by_user = {plan.user_id: plan for plan in work_plans}

        # Get week dates for display
        week_dates = DeveloperWorkPlan.get_week_dates(selected_week_start)

        return render_template('development/admin_work_plan.html',
                               developers=developers,
                               plans_by_user=plans_by_user,
                               week_start=selected_week_start,
                               week_dates=week_dates,
                               week_offset=week_offset,
                               today=today)

    except Exception as e:
        logger.error(f"Error loading admin work plan: {str(e)}")
        flash('Error loading work plans', 'error')
        return redirect(url_for('development.dashboard'))
    finally:
        db_session.close()


@development_bp.route('/work-plan/get/<int:user_id>')
@login_required
@permission_required('can_access_development')
def get_work_plan(user_id):
    """Get a specific user's work plan (API endpoint)"""
    from models.developer_work_plan import DeveloperWorkPlan
    from datetime import datetime

    # Only super admin can view other users' plans
    if current_user.user_type != UserType.SUPER_ADMIN and current_user.id != user_id:
        return jsonify({'error': 'Access denied'}), 403

    db_session = SessionLocal()
    try:
        week_start_str = request.args.get('week_start')
        if not week_start_str:
            week_start = DeveloperWorkPlan.get_week_start()
        else:
            week_start = datetime.strptime(week_start_str, '%Y-%m-%d').date()

        plan = db_session.query(DeveloperWorkPlan).filter(
            DeveloperWorkPlan.user_id == user_id,
            DeveloperWorkPlan.week_start == week_start
        ).first()

        if plan:
            return jsonify({'success': True, 'plan': plan.to_dict()})
        else:
            return jsonify({'success': True, 'plan': None})

    except Exception as e:
        logger.error(f"Error getting work plan: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        db_session.close()


# ============================================
# USER ANALYTICS ROUTES
# ============================================

@development_bp.route('/analytics')
@login_required
@permission_required('can_access_development')
def user_analytics():
    """Developer analytics dashboard showing user activity and sessions"""
    from models.user_session import UserSession
    from models.activity import Activity
    from datetime import timedelta

    db_session = SessionLocal()
    try:
        now = datetime.utcnow()
        today = now.date()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        # Get all users
        users = db_session.query(User).order_by(User.username).all()

        # Current active sessions (last 15 minutes activity)
        active_threshold = now - timedelta(minutes=15)
        active_sessions = db_session.query(UserSession).filter(
            UserSession.is_active == True,
            UserSession.last_activity_at >= active_threshold
        ).all()

        # Today's logins
        today_start = datetime.combine(today, datetime.min.time())
        today_logins = db_session.query(UserSession).filter(
            UserSession.login_at >= today_start
        ).count()

        # This week's logins
        week_logins = db_session.query(UserSession).filter(
            UserSession.login_at >= week_ago
        ).count()

        # Total sessions
        total_sessions = db_session.query(UserSession).count()

        # Unique users this week
        unique_users_week = db_session.query(func.count(func.distinct(UserSession.user_id))).filter(
            UserSession.login_at >= week_ago
        ).scalar() or 0

        # Recent sessions (last 50)
        recent_sessions = db_session.query(UserSession).options(
            joinedload(UserSession.user)
        ).order_by(desc(UserSession.login_at)).limit(50).all()

        # Sessions per user (top 10 this month)
        sessions_per_user = db_session.query(
            User.id,
            User.username,
            func.count(UserSession.id).label('session_count'),
            func.sum(
                func.coalesce(
                    func.extract('epoch', UserSession.logout_at) - func.extract('epoch', UserSession.login_at),
                    func.extract('epoch', func.now()) - func.extract('epoch', UserSession.login_at)
                )
            ).label('total_duration')
        ).join(UserSession, User.id == UserSession.user_id).filter(
            UserSession.login_at >= month_ago
        ).group_by(User.id, User.username).order_by(desc('session_count')).limit(10).all()

        # Sessions by day (last 7 days)
        sessions_by_day = []
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            day_start = datetime.combine(day, datetime.min.time())
            day_end = datetime.combine(day, datetime.max.time())
            count = db_session.query(UserSession).filter(
                UserSession.login_at >= day_start,
                UserSession.login_at <= day_end
            ).count()
            sessions_by_day.append({
                'date': day.strftime('%a %m/%d'),
                'count': count
            })

        # Sessions by hour (today)
        sessions_by_hour = []
        for hour in range(24):
            hour_start = today_start + timedelta(hours=hour)
            hour_end = hour_start + timedelta(hours=1)
            count = db_session.query(UserSession).filter(
                UserSession.login_at >= hour_start,
                UserSession.login_at < hour_end
            ).count()
            sessions_by_hour.append({
                'hour': f'{hour:02d}:00',
                'count': count
            })

        # Device breakdown
        device_stats = db_session.query(
            UserSession.device_type,
            func.count(UserSession.id).label('count')
        ).filter(
            UserSession.login_at >= month_ago
        ).group_by(UserSession.device_type).all()

        # Browser breakdown
        browser_stats = db_session.query(
            UserSession.browser,
            func.count(UserSession.id).label('count')
        ).filter(
            UserSession.login_at >= month_ago
        ).group_by(UserSession.browser).all()

        # OS breakdown
        os_stats = db_session.query(
            UserSession.os,
            func.count(UserSession.id).label('count')
        ).filter(
            UserSession.login_at >= month_ago
        ).group_by(UserSession.os).all()

        return render_template('development/analytics.html',
            users=users,
            active_sessions=active_sessions,
            today_logins=today_logins,
            week_logins=week_logins,
            total_sessions=total_sessions,
            unique_users_week=unique_users_week,
            recent_sessions=recent_sessions,
            sessions_per_user=sessions_per_user,
            sessions_by_day=sessions_by_day,
            sessions_by_hour=sessions_by_hour,
            device_stats=device_stats,
            browser_stats=browser_stats,
            os_stats=os_stats
        )

    except Exception as e:
        logger.error(f"Error loading analytics: {str(e)}")
        flash('Error loading analytics dashboard', 'error')
        return redirect(url_for('development.dashboard'))
    finally:
        db_session.close()


@development_bp.route('/analytics/api/sessions')
@login_required
@permission_required('can_access_development')
def api_sessions():
    """API endpoint for session data"""
    from models.user_session import UserSession
    from datetime import timedelta

    db_session = SessionLocal()
    try:
        # Filter parameters
        user_id = request.args.get('user_id', type=int)
        days = request.args.get('days', 7, type=int)
        limit = request.args.get('limit', 100, type=int)

        query = db_session.query(UserSession).options(joinedload(UserSession.user))

        if user_id:
            query = query.filter(UserSession.user_id == user_id)

        if days:
            cutoff = datetime.utcnow() - timedelta(days=days)
            query = query.filter(UserSession.login_at >= cutoff)

        sessions = query.order_by(desc(UserSession.login_at)).limit(limit).all()

        return jsonify({
            'success': True,
            'sessions': [s.to_dict() for s in sessions]
        })

    except Exception as e:
        logger.error(f"Error fetching sessions: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        db_session.close()


@development_bp.route('/analytics/api/active-users')
@login_required
@permission_required('can_access_development')
def api_active_users():
    """API endpoint for currently active users"""
    from models.user_session import UserSession
    from datetime import timedelta

    db_session = SessionLocal()
    try:
        active_threshold = datetime.utcnow() - timedelta(minutes=15)
        active_sessions = db_session.query(UserSession).options(
            joinedload(UserSession.user)
        ).filter(
            UserSession.is_active == True,
            UserSession.last_activity_at >= active_threshold
        ).all()

        return jsonify({
            'success': True,
            'active_count': len(active_sessions),
            'users': [{
                'user_id': s.user_id,
                'username': s.user.username if s.user else 'Unknown',
                'last_activity': s.last_activity_at.isoformat() if s.last_activity_at else None,
                'last_page': s.last_page,
                'duration': s.duration_formatted
            } for s in active_sessions]
        })

    except Exception as e:
        logger.error(f"Error fetching active users: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        db_session.close()


@development_bp.route('/analytics/user/<int:user_id>')
@login_required
@permission_required('can_access_development')
def user_activity_detail(user_id):
    """Detailed activity view for a specific user"""
    from models.user_session import UserSession
    from models.activity import Activity
    from datetime import timedelta

    db_session = SessionLocal()
    try:
        user = db_session.query(User).filter_by(id=user_id).first()
        if not user:
            flash('User not found', 'error')
            return redirect(url_for('development.user_analytics'))

        now = datetime.utcnow()
        month_ago = now - timedelta(days=30)

        # User's sessions (last 30 days)
        sessions = db_session.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.login_at >= month_ago
        ).order_by(desc(UserSession.login_at)).all()

        # Calculate stats
        total_sessions = len(sessions)
        total_duration = sum(s.duration_seconds for s in sessions)
        avg_duration = total_duration // total_sessions if total_sessions > 0 else 0

        # Format total duration
        hours = total_duration // 3600
        minutes = (total_duration % 3600) // 60
        total_duration_formatted = f"{hours}h {minutes}m"

        avg_hours = avg_duration // 3600
        avg_minutes = (avg_duration % 3600) // 60
        avg_duration_formatted = f"{avg_hours}h {avg_minutes}m" if avg_hours > 0 else f"{avg_minutes}m"

        # Recent activities
        activities = db_session.query(Activity).filter(
            Activity.user_id == user_id
        ).order_by(desc(Activity.created_at)).limit(50).all()

        return render_template('development/user_activity.html',
            user=user,
            sessions=sessions,
            total_sessions=total_sessions,
            total_duration=total_duration_formatted,
            avg_duration=avg_duration_formatted,
            activities=activities
        )

    except Exception as e:
        logger.error(f"Error loading user activity: {str(e)}")
        flash('Error loading user activity', 'error')
        return redirect(url_for('development.user_analytics'))
    finally:
        db_session.close()
