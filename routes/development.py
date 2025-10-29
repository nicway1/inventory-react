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
            mentioned_users = db_session.query(User).filter(User.username.in_(mentions)).all()
            for mentioned_user in mentioned_users:
                if mentioned_user.email and mentioned_user.id != current_user.id:
                    try:
                        send_feature_mention_email(mentioned_user, current_user, feature, content)
                    except Exception as email_error:
                        logging.error(f"Failed to send mention email: {str(email_error)}")

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
            mentioned_users = db_session.query(User).filter(User.username.in_(mentions)).all()
            for mentioned_user in mentioned_users:
                if mentioned_user.email and mentioned_user.id != current_user.id:
                    try:
                        send_mention_email(mentioned_user, current_user, bug, content)
                        logger.info(f"Mention email sent to {mentioned_user.email}")
                    except Exception as email_error:
                        logger.error(f"Failed to send mention email: {str(email_error)}")

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
