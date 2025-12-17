"""
Import Manager Routes
Centralized dashboard for managing all import operations
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func, desc
import json

from database import SessionLocal
from models.import_session import ImportSession
from models.user_import_permission import UserImportPermission
from models.user import User
from models.enums import UserType

import_manager_bp = Blueprint('import_manager', __name__, url_prefix='/import-manager')


def get_user_allowed_imports(user):
    """Get list of import types the user can access"""
    # SUPER_ADMIN and DEVELOPER can access all imports
    if user.user_type in [UserType.SUPER_ADMIN, UserType.DEVELOPER]:
        return UserImportPermission.VALID_TYPES

    # COUNTRY_ADMIN and SUPERVISOR need explicit permissions
    if user.user_type in [UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
        db_session = SessionLocal()
        try:
            return UserImportPermission.get_user_allowed_types(db_session, user.id)
        finally:
            db_session.close()

    # Other users have no import access
    return []


def can_access_import_manager(user):
    """Check if user can access the Import Manager"""
    # SUPER_ADMIN and DEVELOPER always have access
    if user.user_type in [UserType.SUPER_ADMIN, UserType.DEVELOPER]:
        return True

    # COUNTRY_ADMIN and SUPERVISOR need at least one import permission
    if user.user_type in [UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
        allowed = get_user_allowed_imports(user)
        return len(allowed) > 0

    return False


@import_manager_bp.route('/')
@login_required
def dashboard():
    """Import Manager Dashboard - shows all import sessions"""
    if not can_access_import_manager(current_user):
        flash('You do not have permission to access the Import Manager.', 'error')
        return redirect(url_for('main.index'))

    db_session = SessionLocal()
    try:
        # Get filter parameters
        import_type = request.args.get('type', '')
        status = request.args.get('status', '')
        user_id = request.args.get('user_id', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        page = request.args.get('page', 1, type=int)
        per_page = 20

        # Build query
        query = db_session.query(ImportSession).order_by(desc(ImportSession.started_at))

        # Apply filters
        if import_type:
            query = query.filter(ImportSession.import_type == import_type)
        if status:
            query = query.filter(ImportSession.status == status)
        if user_id:
            query = query.filter(ImportSession.user_id == int(user_id))
        if date_from:
            query = query.filter(ImportSession.started_at >= datetime.strptime(date_from, '%Y-%m-%d'))
        if date_to:
            query = query.filter(ImportSession.started_at <= datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1))

        # For COUNTRY_ADMIN/SUPERVISOR, only show their own imports or imports they have permission for
        if current_user.user_type in [UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
            allowed_types = get_user_allowed_imports(current_user)
            if allowed_types:
                query = query.filter(ImportSession.import_type.in_(allowed_types))
            else:
                # No permissions, show nothing
                query = query.filter(ImportSession.id == -1)

        # Get total count
        total_count = query.count()

        # Paginate
        sessions = query.offset((page - 1) * per_page).limit(per_page).all()

        # Calculate stats
        today = datetime.utcnow().date()
        this_month_start = today.replace(day=1)

        total_imports = db_session.query(func.count(ImportSession.id)).scalar() or 0
        this_month_imports = db_session.query(func.count(ImportSession.id)).filter(
            ImportSession.started_at >= this_month_start
        ).scalar() or 0
        successful_imports = db_session.query(func.count(ImportSession.id)).filter(
            ImportSession.status == 'completed'
        ).scalar() or 0
        failed_imports = db_session.query(func.count(ImportSession.id)).filter(
            ImportSession.status == 'failed'
        ).scalar() or 0

        success_rate = round((successful_imports / total_imports * 100) if total_imports > 0 else 0, 1)

        # Get users for filter dropdown
        users = db_session.query(User).filter(
            User.user_type.in_([UserType.SUPER_ADMIN, UserType.DEVELOPER, UserType.COUNTRY_ADMIN, UserType.SUPERVISOR])
        ).order_by(User.username).all()

        return render_template('import_manager/dashboard.html',
            sessions=sessions,
            total_count=total_count,
            page=page,
            per_page=per_page,
            total_pages=(total_count + per_page - 1) // per_page,
            stats={
                'total': total_imports,
                'this_month': this_month_imports,
                'success_rate': success_rate,
                'failed': failed_imports
            },
            filters={
                'type': import_type,
                'status': status,
                'user_id': user_id,
                'date_from': date_from,
                'date_to': date_to
            },
            import_types=ImportSession.TYPE_NAMES,
            users=users
        )
    finally:
        db_session.close()


@import_manager_bp.route('/select')
@login_required
def select_import():
    """Import Selection Page - shows available import options"""
    if not can_access_import_manager(current_user):
        flash('You do not have permission to access the Import Manager.', 'error')
        return redirect(url_for('main.index'))

    allowed_types = get_user_allowed_imports(current_user)

    # Build list of available imports with their info
    available_imports = []
    for import_type in UserImportPermission.VALID_TYPES:
        if import_type in allowed_types:
            info = UserImportPermission.TYPE_INFO.get(import_type, {})
            available_imports.append({
                'type': import_type,
                'name': info.get('name', import_type),
                'description': info.get('description', ''),
                'icon': info.get('icon', 'fas fa-file-import'),
                'color': info.get('color', 'gray'),
                'route': info.get('route', '')
            })

    return render_template('import_manager/select.html',
        available_imports=available_imports
    )


@import_manager_bp.route('/session/<int:session_id>')
@login_required
def view_session(session_id):
    """View details of a specific import session"""
    if not can_access_import_manager(current_user):
        flash('You do not have permission to access the Import Manager.', 'error')
        return redirect(url_for('main.index'))

    db_session = SessionLocal()
    try:
        import_session = db_session.query(ImportSession).get(session_id)

        if not import_session:
            flash('Import session not found.', 'error')
            return redirect(url_for('import_manager.dashboard'))

        # Check permission for COUNTRY_ADMIN/SUPERVISOR
        if current_user.user_type in [UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
            allowed_types = get_user_allowed_imports(current_user)
            if import_session.import_type not in allowed_types:
                flash('You do not have permission to view this import session.', 'error')
                return redirect(url_for('import_manager.dashboard'))

        # Parse import_data JSON if present
        import_data = None
        if import_session.import_data:
            try:
                import_data = json.loads(import_session.import_data)
            except json.JSONDecodeError:
                import_data = None

        # Parse error_details JSON if present
        error_details = None
        if import_session.error_details:
            try:
                error_details = json.loads(import_session.error_details)
            except json.JSONDecodeError:
                error_details = None

        return render_template('import_manager/session_detail.html',
            import_session=import_session,
            import_data=import_data,
            error_details=error_details
        )
    finally:
        db_session.close()


# API Endpoints for creating/updating import sessions

@import_manager_bp.route('/api/create-session', methods=['POST'])
@login_required
def api_create_session():
    """API to create a new import session"""
    data = request.get_json()

    import_type = data.get('import_type')
    file_name = data.get('file_name')
    notes = data.get('notes')

    if not import_type:
        return jsonify({'success': False, 'error': 'import_type is required'}), 400

    if import_type not in UserImportPermission.VALID_TYPES:
        return jsonify({'success': False, 'error': 'Invalid import_type'}), 400

    db_session = SessionLocal()
    try:
        session = ImportSession.create(
            db_session=db_session,
            import_type=import_type,
            user_id=current_user.id,
            file_name=file_name,
            notes=notes
        )
        db_session.commit()

        return jsonify({
            'success': True,
            'session_id': session.id,
            'display_id': session.display_id
        })
    except Exception as e:
        db_session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@import_manager_bp.route('/api/update-session/<int:session_id>', methods=['POST'])
@login_required
def api_update_session(session_id):
    """API to update an import session"""
    data = request.get_json()

    db_session = SessionLocal()
    try:
        session = db_session.query(ImportSession).get(session_id)

        if not session:
            return jsonify({'success': False, 'error': 'Session not found'}), 404

        # Update fields if provided
        if 'status' in data:
            session.status = data['status']
        if 'success_count' in data:
            session.success_count = data['success_count']
        if 'fail_count' in data:
            session.fail_count = data['fail_count']
        if 'total_rows' in data:
            session.total_rows = data['total_rows']
        if 'import_data' in data:
            session.import_data = json.dumps(data['import_data']) if isinstance(data['import_data'], (dict, list)) else data['import_data']
        if 'error_details' in data:
            session.error_details = json.dumps(data['error_details']) if isinstance(data['error_details'], (dict, list)) else data['error_details']
        if 'completed' in data and data['completed']:
            session.completed_at = datetime.utcnow()

        db_session.commit()

        return jsonify({'success': True, 'session': session.to_dict()})
    except Exception as e:
        db_session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


# Helper function to create import session from other routes
def create_import_session(import_type, user_id, file_name=None, notes=None):
    """Helper function to create an import session from other routes"""
    db_session = SessionLocal()
    try:
        session = ImportSession.create(
            db_session=db_session,
            import_type=import_type,
            user_id=user_id,
            file_name=file_name,
            notes=notes
        )
        db_session.commit()
        return session.id, session.display_id
    except Exception as e:
        db_session.rollback()
        raise e
    finally:
        db_session.close()


def update_import_session(session_id, success_count=0, fail_count=0, import_data=None, error_details=None, status=None):
    """Helper function to update an import session from other routes"""
    import logging
    logger = logging.getLogger(__name__)

    # Debug print to ensure we can see what's happening
    print(f"[IMPORT_DEBUG] update_import_session called: session_id={session_id}, success={success_count}, fail={fail_count}")
    print(f"[IMPORT_DEBUG] import_data type={type(import_data)}, length={len(import_data) if import_data else 0}")
    logger.info(f"update_import_session called: session_id={session_id}, success={success_count}, fail={fail_count}, has_import_data={import_data is not None}, has_errors={error_details is not None}")

    db_session = SessionLocal()
    try:
        session = db_session.query(ImportSession).get(session_id)
        if session:
            if status:
                session.status = status
            else:
                session.status = 'completed' if fail_count == 0 else ('failed' if success_count == 0 else 'completed')

            session.success_count = success_count
            session.fail_count = fail_count
            session.total_rows = success_count + fail_count
            session.completed_at = datetime.utcnow()

            if import_data:
                import_data_json = json.dumps(import_data) if isinstance(import_data, (dict, list)) else import_data
                print(f"[IMPORT_DEBUG] Setting import_data JSON (length={len(import_data_json)})")
                logger.info(f"Setting import_data (length={len(import_data_json) if import_data_json else 0})")
                session.import_data = import_data_json
            else:
                print(f"[IMPORT_DEBUG] import_data is falsy, not setting. Value: {import_data}")
                logger.info("import_data is None or empty, not setting")

            if error_details:
                session.error_details = json.dumps(error_details) if isinstance(error_details, (dict, list)) else error_details

            db_session.commit()
            print(f"[IMPORT_DEBUG] Commit successful for session {session_id}")
            logger.info(f"Import session {session_id} updated successfully")
            return True
        else:
            print(f"[IMPORT_DEBUG] Session {session_id} not found in database!")
            logger.warning(f"Import session {session_id} not found")
        return False
    except Exception as e:
        print(f"[IMPORT_DEBUG] EXCEPTION: {str(e)}")
        logger.error(f"Error updating import session {session_id}: {str(e)}")
        db_session.rollback()
        raise e
    finally:
        db_session.close()
