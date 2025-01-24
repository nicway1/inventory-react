import json
import os
from datetime import datetime
from models.activity import Activity

class ActivityStore:
    def __init__(self):
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

    def add_activity(self, user_id, type, content, reference_id):
        activity = Activity.create(user_id, type, content, reference_id)
        self.activities[activity.id] = activity
        self.save_activities()
        return activity

    def get_user_activities(self, user_id, limit=50):
        """Get recent activities for a user"""
        user_activities = [
            activity for activity in self.activities.values()
            if activity.user_id == user_id
        ]
        return sorted(
            user_activities,
            key=lambda x: x.created_at,
            reverse=True
        )[:limit]

    def mark_as_read(self, activity_id):
        """Mark an activity as read"""
        if activity_id in self.activities:
            self.activities[activity_id].is_read = True
            self.save_activities()

    def get_unread_count(self, user_id):
        """Get count of unread activities for a user"""
        return len([
            activity for activity in self.activities.values()
            if activity.user_id == user_id and not activity.is_read
        ]) 