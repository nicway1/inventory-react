from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from utils.auth_decorators import login_required
from utils.db_manager import DatabaseManager
from models.action_item import ActionItem, ActionItemStatus, ActionItemPriority, ActionItemComment
from models.weekly_meeting import WeeklyMeeting
from models.user import User
from sqlalchemy.orm import joinedload
from sqlalchemy import desc, asc
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)
action_items_bp = Blueprint('action_items', __name__)
db_manager = DatabaseManager()


@action_items_bp.route('/action-items')
@login_required
def index():
    """Display the list of weekly meetings"""
    user_type = session.get('user_type')

    # Only allow DEVELOPER and SUPER_ADMIN
    if user_type not in ['DEVELOPER', 'SUPER_ADMIN']:
        flash('Access denied', 'error')
        return redirect(url_for('main.home'))

    db_session = db_manager.get_session()
    try:
        # Get all meetings ordered by date desc with their action items
        meetings = db_session.query(WeeklyMeeting)\
            .options(joinedload(WeeklyMeeting.action_items))\
            .order_by(WeeklyMeeting.meeting_date.desc())\
            .all()

        return render_template(
            'development/meetings_list.html',
            meetings=meetings,
            today=date.today()
        )
    finally:
        db_session.close()


@action_items_bp.route('/action-items/meeting/<int:meeting_id>')
@login_required
def meeting_detail(meeting_id):
    """Display the Kanban board for a specific meeting's action items"""
    user_type = session.get('user_type')

    # Only allow DEVELOPER and SUPER_ADMIN
    if user_type not in ['DEVELOPER', 'SUPER_ADMIN']:
        flash('Access denied', 'error')
        return redirect(url_for('main.home'))

    db_session = db_manager.get_session()
    try:
        # Get the specific meeting
        active_meeting = db_session.query(WeeklyMeeting).get(meeting_id)
        if not active_meeting:
            flash('Meeting not found', 'error')
            return redirect(url_for('action_items.index'))

        # Get all meetings for the sidebar/selector
        meetings = db_session.query(WeeklyMeeting)\
            .order_by(WeeklyMeeting.meeting_date.desc())\
            .all()

        # Build query for action items
        items_query = db_session.query(ActionItem)\
            .options(joinedload(ActionItem.created_by))\
            .options(joinedload(ActionItem.assigned_to))\
            .options(joinedload(ActionItem.tester))\
            .options(joinedload(ActionItem.comments))\
            .filter(ActionItem.meeting_id == active_meeting.id)

        items = items_query.order_by(ActionItem.item_number, ActionItem.position, ActionItem.created_at.desc()).all()

        # Group by status for Kanban columns
        columns = {
            'NOT_STARTED': [],
            'IN_PROGRESS': [],
            'PENDING_TESTING': [],
            'BLOCKED': [],
            'DONE': []
        }

        for item in items:
            status_key = item.status.name if item.status else 'NOT_STARTED'
            if status_key in columns:
                columns[status_key].append(item)

        # Get users for assignment dropdown
        users = db_session.query(User).filter(
            User.user_type.in_(['DEVELOPER', 'SUPER_ADMIN'])
        ).order_by(User.username).all()

        return render_template(
            'development/action_items.html',
            columns=columns,
            users=users,
            meetings=meetings,
            active_meeting=active_meeting,
            priorities=ActionItemPriority,
            statuses=ActionItemStatus,
            today=date.today()
        )
    finally:
        db_session.close()


@action_items_bp.route('/action-items/api/create', methods=['POST'])
@login_required
def api_create():
    """Create a new action item"""
    user_type = session.get('user_type')
    user_id = session.get('user_id')

    if user_type not in ['DEVELOPER', 'SUPER_ADMIN']:
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400

    title = data.get('title', '').strip()
    if not title:
        return jsonify({'success': False, 'error': 'Title is required'}), 400

    db_session = db_manager.get_session()
    try:
        # Get max position for NOT_STARTED column
        max_pos = db_session.query(ActionItem)\
            .filter(ActionItem.status == ActionItemStatus.NOT_STARTED)\
            .count()

        item = ActionItem(
            title=title,
            description=data.get('description', '').strip() or None,
            status=ActionItemStatus.NOT_STARTED,
            priority=ActionItemPriority(data.get('priority', 'Medium')),
            created_by_id=user_id,
            assigned_to_id=data.get('assigned_to_id') or None,
            due_date=datetime.strptime(data['due_date'], '%Y-%m-%d').date() if data.get('due_date') else None,
            meeting_id=data.get('meeting_id') or None,
            meeting_date=datetime.strptime(data['meeting_date'], '%Y-%m-%d').date() if data.get('meeting_date') else None,
            position=max_pos
        )

        db_session.add(item)
        db_session.commit()

        return jsonify({
            'success': True,
            'item': item.to_dict(),
            'message': 'Action item created successfully'
        })
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error creating action item: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@action_items_bp.route('/action-items/api/bulk-create', methods=['POST'])
@login_required
def api_bulk_create():
    """Create multiple action items from pasted text"""
    user_type = session.get('user_type')
    user_id = session.get('user_id')

    if user_type not in ['DEVELOPER', 'SUPER_ADMIN']:
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400

    text = data.get('text', '').strip()
    meeting_date = data.get('meeting_date')
    meeting_id = data.get('meeting_id')

    if not text:
        return jsonify({'success': False, 'error': 'No text provided'}), 400

    # Parse text into lines
    lines = [line.strip() for line in text.split('\n') if line.strip()]

    if not lines:
        return jsonify({'success': False, 'error': 'No items found in text'}), 400

    db_session = db_manager.get_session()
    try:
        # Get max position for NOT_STARTED column
        max_pos = db_session.query(ActionItem)\
            .filter(ActionItem.status == ActionItemStatus.NOT_STARTED)\
            .count()

        # Get max item_number for this meeting
        from sqlalchemy import func
        item_num_query = db_session.query(func.max(ActionItem.item_number))
        if meeting_id:
            item_num_query = item_num_query.filter(ActionItem.meeting_id == meeting_id)
        max_item_num = item_num_query.scalar() or 0

        created_items = []
        meeting_dt = datetime.strptime(meeting_date, '%Y-%m-%d').date() if meeting_date else date.today()

        for i, line in enumerate(lines):
            # Parse the line - check for notes after "—" or "-"
            title = line
            description = None

            # Check for em-dash or double hyphen followed by notes
            for separator in [' — ', ' -- ', ' - ']:
                if separator in line:
                    parts = line.split(separator, 1)
                    title = parts[0].strip()
                    description = parts[1].strip() if len(parts) > 1 else None
                    break

            item = ActionItem(
                title=title,
                description=description,
                status=ActionItemStatus.NOT_STARTED,
                priority=ActionItemPriority.MEDIUM,
                created_by_id=user_id,
                meeting_id=meeting_id or None,
                meeting_date=meeting_dt,
                position=max_pos + i,
                item_number=max_item_num + i + 1  # Auto-assign item number
            )

            db_session.add(item)
            created_items.append(item)

        db_session.commit()

        return jsonify({
            'success': True,
            'count': len(created_items),
            'message': f'Created {len(created_items)} action items'
        })
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error bulk creating action items: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@action_items_bp.route('/action-items/api/update/<int:item_id>', methods=['POST'])
@login_required
def api_update(item_id):
    """Update an action item"""
    user_type = session.get('user_type')

    if user_type not in ['DEVELOPER', 'SUPER_ADMIN']:
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400

    db_session = db_manager.get_session()
    try:
        item = db_session.query(ActionItem).get(item_id)
        if not item:
            return jsonify({'success': False, 'error': 'Item not found'}), 404

        # Update fields if provided
        if 'title' in data:
            item.title = data['title'].strip()

        if 'description' in data:
            item.description = data['description'].strip() or None

        if 'status' in data:
            old_status = item.status
            item.status = ActionItemStatus(data['status'])

            # Set completed_at when marking as done
            if item.status == ActionItemStatus.DONE and old_status != ActionItemStatus.DONE:
                item.completed_at = datetime.utcnow()
            elif item.status != ActionItemStatus.DONE:
                item.completed_at = None

        if 'priority' in data:
            item.priority = ActionItemPriority(data['priority'])

        if 'assigned_to_id' in data:
            item.assigned_to_id = data['assigned_to_id'] or None

        if 'tester_id' in data:
            item.tester_id = data['tester_id'] or None

        if 'due_date' in data:
            item.due_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date() if data['due_date'] else None

        if 'position' in data:
            item.position = data['position']

        if 'item_number' in data:
            item.item_number = data['item_number'] or None

        item.updated_at = datetime.utcnow()
        db_session.commit()

        return jsonify({
            'success': True,
            'item': item.to_dict(),
            'message': 'Action item updated'
        })
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error updating action item: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@action_items_bp.route('/action-items/api/move', methods=['POST'])
@login_required
def api_move():
    """Move an action item to a different status column"""
    user_type = session.get('user_type')

    if user_type not in ['DEVELOPER', 'SUPER_ADMIN']:
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400

    item_id = data.get('item_id')
    new_status = data.get('status')
    new_position = data.get('position', 0)

    if not item_id or not new_status:
        return jsonify({'success': False, 'error': 'Missing item_id or status'}), 400

    db_session = db_manager.get_session()
    try:
        item = db_session.query(ActionItem).get(item_id)
        if not item:
            return jsonify({'success': False, 'error': 'Item not found'}), 404

        old_status = item.status
        item.status = ActionItemStatus(new_status)
        item.position = new_position

        # Set completed_at when marking as done
        if item.status == ActionItemStatus.DONE and old_status != ActionItemStatus.DONE:
            item.completed_at = datetime.utcnow()
        elif item.status != ActionItemStatus.DONE:
            item.completed_at = None

        item.updated_at = datetime.utcnow()
        db_session.commit()

        return jsonify({
            'success': True,
            'item': item.to_dict(),
            'message': f'Moved to {new_status}'
        })
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error moving action item: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@action_items_bp.route('/action-items/api/delete/<int:item_id>', methods=['DELETE'])
@login_required
def api_delete(item_id):
    """Delete an action item"""
    user_type = session.get('user_type')

    if user_type not in ['DEVELOPER', 'SUPER_ADMIN']:
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    db_session = db_manager.get_session()
    try:
        item = db_session.query(ActionItem).get(item_id)
        if not item:
            return jsonify({'success': False, 'error': 'Item not found'}), 404

        db_session.delete(item)
        db_session.commit()

        return jsonify({
            'success': True,
            'message': 'Action item deleted'
        })
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error deleting action item: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@action_items_bp.route('/action-items/api/clear-done', methods=['POST'])
@login_required
def api_clear_done():
    """Clear all completed action items for a specific meeting"""
    user_type = session.get('user_type')

    if user_type not in ['DEVELOPER', 'SUPER_ADMIN']:
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    data = request.get_json() or {}
    meeting_id = data.get('meeting_id')

    db_session = db_manager.get_session()
    try:
        query = db_session.query(ActionItem)\
            .filter(ActionItem.status == ActionItemStatus.DONE)

        if meeting_id:
            query = query.filter(ActionItem.meeting_id == meeting_id)

        count = query.delete()

        db_session.commit()

        return jsonify({
            'success': True,
            'count': count,
            'message': f'Cleared {count} completed items'
        })
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error clearing done items: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@action_items_bp.route('/action-items/api/assign-tester', methods=['POST'])
@login_required
def api_assign_tester():
    """Assign a tester to action items by item numbers"""
    user_type = session.get('user_type')

    if user_type not in ['DEVELOPER', 'SUPER_ADMIN']:
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400

    item_numbers = data.get('item_numbers', [])  # List of item numbers
    tester_id = data.get('tester_id')
    meeting_id = data.get('meeting_id')

    if not item_numbers:
        return jsonify({'success': False, 'error': 'No item numbers provided'}), 400

    if not tester_id:
        return jsonify({'success': False, 'error': 'No tester selected'}), 400

    db_session = db_manager.get_session()
    try:
        # Update all items with matching item_numbers
        query = db_session.query(ActionItem)\
            .filter(ActionItem.item_number.in_(item_numbers))

        if meeting_id:
            query = query.filter(ActionItem.meeting_id == meeting_id)

        count = query.update({ActionItem.tester_id: tester_id, ActionItem.updated_at: datetime.utcnow()},
                   synchronize_session=False)

        db_session.commit()

        # Get tester name for message
        tester = db_session.query(User).get(tester_id)
        tester_name = tester.username if tester else 'Unknown'

        return jsonify({
            'success': True,
            'count': count,
            'message': f'Assigned {tester_name} to test {count} item(s)'
        })
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error assigning tester: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@action_items_bp.route('/action-items/api/renumber', methods=['POST'])
@login_required
def api_renumber():
    """Renumber all action items sequentially for a specific meeting"""
    user_type = session.get('user_type')

    if user_type not in ['DEVELOPER', 'SUPER_ADMIN']:
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    data = request.get_json() or {}
    meeting_id = data.get('meeting_id')

    db_session = db_manager.get_session()
    try:
        # Get all non-done items ordered by current item_number or created_at
        query = db_session.query(ActionItem)\
            .filter(ActionItem.status != ActionItemStatus.DONE)

        if meeting_id:
            query = query.filter(ActionItem.meeting_id == meeting_id)

        items = query.order_by(ActionItem.item_number.nullsfirst(), ActionItem.created_at).all()

        # Renumber sequentially starting from 1
        for i, item in enumerate(items, start=1):
            item.item_number = i

        db_session.commit()

        return jsonify({
            'success': True,
            'count': len(items),
            'message': f'Renumbered {len(items)} items'
        })
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error renumbering items: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@action_items_bp.route('/action-items/api/item/<int:item_id>', methods=['GET'])
@login_required
def api_get_item(item_id):
    """Get full details of an action item including comments"""
    user_type = session.get('user_type')

    if user_type not in ['DEVELOPER', 'SUPER_ADMIN']:
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    db_session = db_manager.get_session()
    try:
        item = db_session.query(ActionItem)\
            .options(joinedload(ActionItem.created_by))\
            .options(joinedload(ActionItem.assigned_to))\
            .options(joinedload(ActionItem.tester))\
            .options(joinedload(ActionItem.comments).joinedload(ActionItemComment.user))\
            .filter(ActionItem.id == item_id)\
            .first()

        if not item:
            return jsonify({'success': False, 'error': 'Item not found'}), 404

        item_dict = item.to_dict()
        item_dict['created_by_name'] = item.created_by.username if item.created_by else None
        item_dict['comments'] = [c.to_dict() for c in item.comments]

        return jsonify({
            'success': True,
            'item': item_dict
        })
    except Exception as e:
        logger.error(f"Error getting action item: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@action_items_bp.route('/action-items/api/item/<int:item_id>/comments', methods=['POST'])
@login_required
def api_add_comment(item_id):
    """Add a comment to an action item"""
    user_type = session.get('user_type')
    user_id = session.get('user_id')

    if user_type not in ['DEVELOPER', 'SUPER_ADMIN']:
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400

    content = data.get('content', '').strip()
    if not content:
        return jsonify({'success': False, 'error': 'Comment content is required'}), 400

    db_session = db_manager.get_session()
    try:
        item = db_session.query(ActionItem).get(item_id)
        if not item:
            return jsonify({'success': False, 'error': 'Item not found'}), 404

        comment = ActionItemComment(
            action_item_id=item_id,
            user_id=user_id,
            content=content
        )
        db_session.add(comment)
        db_session.commit()

        # Reload to get user relationship
        db_session.refresh(comment)

        return jsonify({
            'success': True,
            'comment': comment.to_dict(),
            'message': 'Comment added'
        })
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error adding comment: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@action_items_bp.route('/action-items/api/comments/<int:comment_id>', methods=['DELETE'])
@login_required
def api_delete_comment(comment_id):
    """Delete a comment"""
    user_type = session.get('user_type')
    user_id = session.get('user_id')

    if user_type not in ['DEVELOPER', 'SUPER_ADMIN']:
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    db_session = db_manager.get_session()
    try:
        comment = db_session.query(ActionItemComment).get(comment_id)
        if not comment:
            return jsonify({'success': False, 'error': 'Comment not found'}), 404

        # Only allow deleting own comments (or super admin)
        if comment.user_id != user_id and user_type != 'SUPER_ADMIN':
            return jsonify({'success': False, 'error': 'Cannot delete another user\'s comment'}), 403

        db_session.delete(comment)
        db_session.commit()

        return jsonify({
            'success': True,
            'message': 'Comment deleted'
        })
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error deleting comment: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


# ==================== MEETING ENDPOINTS ====================

@action_items_bp.route('/action-items/api/meetings', methods=['GET'])
@login_required
def api_get_meetings():
    """Get all meetings"""
    user_type = session.get('user_type')

    if user_type not in ['DEVELOPER', 'SUPER_ADMIN']:
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    db_session = db_manager.get_session()
    try:
        meetings = db_session.query(WeeklyMeeting)\
            .order_by(WeeklyMeeting.meeting_date.desc())\
            .all()

        return jsonify({
            'success': True,
            'meetings': [m.to_dict() for m in meetings]
        })
    except Exception as e:
        logger.error(f"Error getting meetings: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@action_items_bp.route('/action-items/api/meetings/create', methods=['POST'])
@login_required
def api_create_meeting():
    """Create a new weekly meeting"""
    user_type = session.get('user_type')
    user_id = session.get('user_id')

    if user_type not in ['DEVELOPER', 'SUPER_ADMIN']:
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400

    name = data.get('name', '').strip()
    meeting_date = data.get('meeting_date')

    if not name:
        return jsonify({'success': False, 'error': 'Meeting name is required'}), 400

    if not meeting_date:
        return jsonify({'success': False, 'error': 'Meeting date is required'}), 400

    db_session = db_manager.get_session()
    try:
        # Deactivate all other meetings
        db_session.query(WeeklyMeeting).update({WeeklyMeeting.is_active: False})

        meeting = WeeklyMeeting(
            name=name,
            meeting_date=datetime.strptime(meeting_date, '%Y-%m-%d').date(),
            notes=data.get('notes', '').strip() or None,
            is_active=True,
            created_by_id=user_id
        )

        db_session.add(meeting)
        db_session.commit()

        return jsonify({
            'success': True,
            'meeting': meeting.to_dict(),
            'message': f'Meeting "{name}" created successfully'
        })
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error creating meeting: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@action_items_bp.route('/action-items/api/meetings/<int:meeting_id>', methods=['POST'])
@login_required
def api_update_meeting(meeting_id):
    """Update a weekly meeting"""
    user_type = session.get('user_type')

    if user_type not in ['DEVELOPER', 'SUPER_ADMIN']:
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400

    db_session = db_manager.get_session()
    try:
        meeting = db_session.query(WeeklyMeeting).get(meeting_id)
        if not meeting:
            return jsonify({'success': False, 'error': 'Meeting not found'}), 404

        if 'name' in data:
            meeting.name = data['name'].strip()

        if 'meeting_date' in data:
            meeting.meeting_date = datetime.strptime(data['meeting_date'], '%Y-%m-%d').date()

        if 'notes' in data:
            meeting.notes = data['notes'].strip() or None

        meeting.updated_at = datetime.utcnow()
        db_session.commit()

        return jsonify({
            'success': True,
            'meeting': meeting.to_dict(),
            'message': 'Meeting updated'
        })
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error updating meeting: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@action_items_bp.route('/action-items/api/meetings/<int:meeting_id>/select', methods=['POST'])
@login_required
def api_select_meeting(meeting_id):
    """Select a meeting as active"""
    user_type = session.get('user_type')

    if user_type not in ['DEVELOPER', 'SUPER_ADMIN']:
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    db_session = db_manager.get_session()
    try:
        meeting = db_session.query(WeeklyMeeting).get(meeting_id)
        if not meeting:
            return jsonify({'success': False, 'error': 'Meeting not found'}), 404

        # Deactivate all other meetings
        db_session.query(WeeklyMeeting).update({WeeklyMeeting.is_active: False})

        # Activate this meeting
        meeting.is_active = True
        db_session.commit()

        return jsonify({
            'success': True,
            'meeting': meeting.to_dict(),
            'message': f'Selected meeting: {meeting.name}'
        })
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error selecting meeting: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@action_items_bp.route('/action-items/api/meetings/<int:meeting_id>', methods=['DELETE'])
@login_required
def api_delete_meeting(meeting_id):
    """Delete a meeting (and its action items)"""
    user_type = session.get('user_type')

    if user_type not in ['DEVELOPER', 'SUPER_ADMIN']:
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    db_session = db_manager.get_session()
    try:
        meeting = db_session.query(WeeklyMeeting).get(meeting_id)
        if not meeting:
            return jsonify({'success': False, 'error': 'Meeting not found'}), 404

        # Delete all action items for this meeting
        db_session.query(ActionItem).filter(ActionItem.meeting_id == meeting_id).delete()

        db_session.delete(meeting)
        db_session.commit()

        return jsonify({
            'success': True,
            'message': 'Meeting and its action items deleted'
        })
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error deleting meeting: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()
