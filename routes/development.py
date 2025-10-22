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
from models.enums import UserType
from sqlalchemy.orm import joinedload
from sqlalchemy import desc, asc, func, or_
from datetime import datetime, date
import logging
from flask_mail import Message
from utils.email_sender import mail
from werkzeug.utils import secure_filename
import os

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
Dear {feature.approver.name},

A new feature request has been submitted and requires your approval:

Feature Request: {feature.display_id}
Title: {feature.title}
Priority: {feature.priority.value}
Requester: {feature.requester.name if feature.requester else 'Unknown'}

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
Dear {feature.requester.name},

Your feature request has been reviewed and {decision_text}.

{decision_color} Feature Request: {feature.display_id}
Title: {feature.title}
Approver: {feature.approver.name if feature.approver else 'System'}
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

        # Get recent items
        recent_features = db_session.query(FeatureRequest)\
            .options(joinedload(FeatureRequest.requester))\
            .filter(FeatureRequest.requester_id.isnot(None))\
            .order_by(desc(FeatureRequest.updated_at)).limit(5).all()

        recent_bugs = db_session.query(BugReport)\
            .options(joinedload(BugReport.reporter))\
            .filter(BugReport.status.in_([BugStatus.OPEN, BugStatus.IN_PROGRESS]))\
            .filter(BugReport.reporter_id.isnot(None))\
            .order_by(desc(BugReport.updated_at)).limit(5).all()

        active_releases = db_session.query(Release)\
            .filter(Release.status.in_([
                ReleaseStatus.PLANNING,
                ReleaseStatus.IN_DEVELOPMENT,
                ReleaseStatus.TESTING,
                ReleaseStatus.READY
            ]))\
            .order_by(asc(Release.planned_date)).limit(3).all()

        return render_template('development/dashboard.html',
                             stats=stats,
                             recent_features=recent_features,
                             recent_bugs=recent_bugs,
                             active_releases=active_releases)

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

            # Send email notification to approver
            if feature.approver:
                try:
                    send_approval_notification_email(feature)
                    flash(f'Feature request {feature.display_id} created successfully! Approval notification sent to {feature.approver.name}.', 'success')
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
    db_session = SessionLocal()
    try:
        feature = db_session.query(FeatureRequest)\
            .options(joinedload(FeatureRequest.requester),
                    joinedload(FeatureRequest.assignee),
                    joinedload(FeatureRequest.target_release),
                    joinedload(FeatureRequest.comments).joinedload(FeatureComment.user))\
            .filter(FeatureRequest.id == id).first()

        if not feature:
            flash('Feature request not found', 'error')
            return redirect(url_for('development.features'))

        return render_template('development/feature_view.html', feature=feature)

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

                if request.form.get('status'):
                    feature.status = FeatureStatus(request.form['status'])
                    if feature.status == FeatureStatus.COMPLETED and not feature.completed_date:
                        feature.completed_date = datetime.utcnow()

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

        comment = FeatureComment(
            content=request.form['content'],
            feature_id=feature.id,
            user_id=current_user.id
        )

        db_session.add(comment)
        db_session.commit()

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
            feature.status = FeatureStatus(new_status)
            if feature.status == FeatureStatus.COMPLETED and not feature.completed_date:
                feature.completed_date = datetime.utcnow()

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
            content=f"Feature request approved by {current_user.name}",
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
            content=f"Feature request rejected by {current_user.name}\n\nReason: {rejection_reason}",
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
        users = db_session.query(User).filter(User.user_type.in_([UserType.SUPER_ADMIN, UserType.DEVELOPER])).all()
        return render_template('development/bug_form.html',
                             users=users,
                             BugSeverity=BugSeverity,
                             BugPriority=BugPriority)
    finally:
        db_session.close()

@development_bp.route('/bugs/<int:id>')
@login_required
@permission_required('can_view_bugs')
def view_bug(id):
    """View a specific bug report"""
    db_session = SessionLocal()
    try:
        bug = db_session.query(BugReport)\
            .options(joinedload(BugReport.reporter),
                    joinedload(BugReport.assignee),
                    joinedload(BugReport.fixed_in_release),
                    joinedload(BugReport.comments).joinedload(BugComment.user))\
            .filter(BugReport.id == id).first()

        if not bug:
            flash('Bug report not found', 'error')
            return redirect(url_for('development.bugs'))

        return render_template('development/bug_view.html', bug=bug)

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

                if request.form.get('status'):
                    bug.status = BugStatus(request.form['status'])
                    if bug.status in [BugStatus.RESOLVED, BugStatus.CLOSED] and not bug.resolution_date:
                        bug.resolution_date = datetime.utcnow()
                        bug.resolution_notes = request.form.get('resolution_notes')

                db_session.commit()
                flash(f'Bug report {bug.display_id} updated successfully!', 'success')
                return redirect(url_for('development.view_bug', id=bug.id))

            except Exception as e:
                db_session.rollback()
                flash(f'Error updating bug report: {str(e)}', 'error')
                logger.error(f'Error updating bug report: {str(e)}')

        # GET - show form
        users = db_session.query(User).filter(User.user_type.in_([UserType.SUPER_ADMIN, UserType.DEVELOPER])).all()
        return render_template('development/bug_form.html',
                             bug=bug,
                             users=users,
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

        comment = BugComment(
            content=request.form['content'],
            bug_id=bug.id,
            user_id=current_user.id,
            comment_type=request.form.get('comment_type', 'comment')
        )

        db_session.add(comment)
        db_session.commit()

        flash('Comment added successfully!', 'success')
        return redirect(url_for('development.view_bug', id=id))

    except Exception as e:
        db_session.rollback()
        flash(f'Error adding comment: {str(e)}', 'error')
        return redirect(url_for('development.view_bug', id=id))
    finally:
        db_session.close()

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
            bug.status = BugStatus(new_status)
            if bug.status in [BugStatus.RESOLVED, BugStatus.CLOSED] and not bug.resolution_date:
                bug.resolution_date = datetime.utcnow()

            db_session.commit()
            flash(f'Bug status updated to {bug.status.value}', 'success')

        return redirect(url_for('development.view_bug', id=id))

    except Exception as e:
        db_session.rollback()
        flash(f'Error updating status: {str(e)}', 'error')
        return redirect(url_for('development.view_bug', id=id))
    finally:
        db_session.close()