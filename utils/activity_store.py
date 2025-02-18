import json
import os
from datetime import datetime
from utils.db_manager import DatabaseManager
from models.activity import Activity

class ActivityStore:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.activities = {}
        self.ACTIVITIES_FILE = 'data/activities.json'
        self.load_activities()

    def load_activities(self):
        if os.path.exists(self.ACTIVITIES_FILE):
            with open(self.ACTIVITIES_FILE, 'r') as f:
                activities_data = json.load(f)
                for activity_data in activities_data:
                    activity = Activity(
                        id=activity_data['id'],
                        user_id=activity_data['user_id'],
                        type=activity_data['type'],
                        content=activity_data['content'],
                        reference_id=activity_data['reference_id'],
                        created_at=datetime.fromisoformat(activity_data['created_at'])
                    )
                    activity.is_read = activity_data.get('is_read', False)
                    self.activities[activity.id] = activity

    def save_activities(self):
        os.makedirs(os.path.dirname(self.ACTIVITIES_FILE), exist_ok=True)
        activities_data = []
        for activity in self.activities.values():
            activities_data.append({
                'id': activity.id,
                'user_id': activity.user_id,
                'type': activity.type,
                'content': activity.content,
                'reference_id': activity.reference_id,
                'created_at': activity.created_at.isoformat(),
                'is_read': activity.is_read
            })
        with open(self.ACTIVITIES_FILE, 'w') as f:
            json.dump(activities_data, f, indent=2)

    def get_user_activities(self, user_id, limit=50):
        """Get activities for a specific user"""
        db_session = self.db_manager.get_session()
        try:
            activities = db_session.query(Activity)\
                .filter(Activity.user_id == user_id)\
                .order_by(Activity.created_at.desc())\
                .limit(limit)\
                .all()
            return activities
        finally:
            db_session.close()

    def add_activity(self, user_id, type, content, reference_id=None):
        """Add a new activity"""
        db_session = self.db_manager.get_session()
        try:
            activity = Activity(
                user_id=user_id,
                type=type,
                content=content,
                reference_id=reference_id,
                created_at=datetime.utcnow()
            )
            db_session.add(activity)
            db_session.commit()
            return activity
        finally:
            db_session.close()

    def mark_activity_read(self, activity_id):
        """Mark an activity as read"""
        db_session = self.db_manager.get_session()
        try:
            activity = db_session.query(Activity).get(activity_id)
            if activity:
                activity.is_read = True
                db_session.commit()
                return True
            return False
        finally:
            db_session.close()

    def get_unread_activities_count(self, user_id):
        """Get count of unread activities for a user"""
        db_session = self.db_manager.get_session()
        try:
            count = db_session.query(Activity)\
                .filter(Activity.user_id == user_id)\
                .filter(Activity.is_read == False)\
                .count()
            return count
        finally:
            db_session.close()

    def save_activities(self):
        os.makedirs(os.path.dirname(self.ACTIVITIES_FILE), exist_ok=True)
        activities_data = []
        for activity in self.activities.values():
            activities_data.append({
                'id': activity.id,
                'user_id': activity.user_id,
                'type': activity.type,
                'content': activity.content,
                'reference_id': activity.reference_id,
                'created_at': activity.created_at.isoformat(),
                'is_read': activity.is_read
            })
        with open(self.ACTIVITIES_FILE, 'w') as f:
            json.dump(activities_data, f, indent=2) 