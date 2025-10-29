from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user
from utils.auth_decorators import login_required
from database import SessionLocal
from models.bug_report import BugReport, BugStatus, BugSeverity, BugPriority
from models.user import UserType
from werkzeug.utils import secure_filename
from datetime import datetime
import logging
import os

feedback_bp = Blueprint('feedback', __name__, url_prefix='/feedback')
logger = logging.getLogger(__name__)


@feedback_bp.route('/report-bug', methods=['GET', 'POST'])
@login_required
def report_bug():
    """Report a bug - accessible to country admins, clients, and supervisors"""
    # Check if user has permission (not regular users)
    if current_user.user_type not in [UserType.SUPER_ADMIN, UserType.COUNTRY_ADMIN, UserType.CLIENT, UserType.SUPERVISOR, UserType.DEVELOPER]:
        flash('You do not have permission to report bugs', 'error')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        db_session = SessionLocal()
        try:
            # Verify user exists in database
            from models.user import User
            user = db_session.query(User).filter(User.id == current_user.id).first()
            if not user:
                flash('Your user account is not found in the database. Please log out and log back in. If the problem persists, contact support.', 'error')
                logger.error(f"User ID {current_user.id} from session not found in database. User may have been deleted or database was restored.")
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
                    unique_filename = f"feedback_{timestamp}_{filename}"

                    # Create directory if it doesn't exist
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
                severity=BugSeverity(request.form['severity']),
                priority=BugPriority(request.form.get('priority', 'MEDIUM')),
                status=BugStatus.OPEN,
                reporter_id=current_user.id,
                component=request.form.get('component'),
                environment=request.form.get('environment'),
                steps_to_reproduce=request.form.get('steps_to_reproduce'),
                expected_behavior=request.form.get('expected_behavior'),
                actual_behavior=request.form.get('actual_behavior'),
                screenshot_path=screenshot_path
            )

            db_session.add(bug)
            db_session.commit()

            flash(f'Bug report {bug.display_id} submitted successfully! Our development team will review it.', 'success')
            return redirect(url_for('feedback.my_reports'))

        except Exception as e:
            db_session.rollback()
            logger.error(f"Error creating bug report: {str(e)}")
            flash(f'Error submitting bug report: {str(e)}', 'error')
        finally:
            db_session.close()

    return render_template('feedback/report_bug.html',
                         BugSeverity=BugSeverity,
                         BugPriority=BugPriority)


@feedback_bp.route('/my-reports')
@login_required
def my_reports():
    """View user's own bug reports"""
    if current_user.user_type not in [UserType.SUPER_ADMIN, UserType.COUNTRY_ADMIN, UserType.CLIENT, UserType.SUPERVISOR, UserType.DEVELOPER]:
        flash('You do not have permission to view bug reports', 'error')
        return redirect(url_for('main.index'))

    db_session = SessionLocal()
    try:
        # Verify user exists in database
        from models.user import User
        user = db_session.query(User).filter(User.id == current_user.id).first()
        if not user:
            flash('Your user account is not found in the database. Please log out and log back in.', 'error')
            logger.error(f"User ID {current_user.id} from session not found in database.")
            return redirect(url_for('auth.logout'))

        # Users can only see their own reports (unless they're super admin/developer)
        if current_user.user_type in [UserType.SUPER_ADMIN, UserType.DEVELOPER]:
            # Super admins and developers see all bugs (they use development.bugs route)
            return redirect(url_for('development.bugs'))
        else:
            # Regular users only see their own reports
            bugs = db_session.query(BugReport)\
                .filter(BugReport.reporter_id == current_user.id)\
                .order_by(BugReport.created_at.desc())\
                .all()

        return render_template('feedback/my_reports.html',
                             bugs=bugs,
                             BugStatus=BugStatus,
                             BugSeverity=BugSeverity)
    finally:
        db_session.close()


@feedback_bp.route('/bug/<int:id>')
@login_required
def view_bug(id):
    """View a specific bug report - users can only view their own"""
    db_session = SessionLocal()
    try:
        # Verify user exists in database
        from models.user import User
        user = db_session.query(User).filter(User.id == current_user.id).first()
        if not user:
            flash('Your user account is not found in the database. Please log out and log back in.', 'error')
            logger.error(f"User ID {current_user.id} from session not found in database.")
            return redirect(url_for('auth.logout'))

        bug = db_session.query(BugReport).filter(BugReport.id == id).first()

        if not bug:
            flash('Bug report not found', 'error')
            return redirect(url_for('feedback.my_reports'))

        # Check if user can view this bug
        if bug.reporter_id != current_user.id and current_user.user_type not in [UserType.SUPER_ADMIN, UserType.DEVELOPER]:
            flash('You do not have permission to view this bug report', 'error')
            return redirect(url_for('feedback.my_reports'))

        return render_template('feedback/view_bug.html',
                             bug=bug,
                             BugStatus=BugStatus,
                             BugSeverity=BugSeverity)
    finally:
        db_session.close()
