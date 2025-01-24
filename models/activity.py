from datetime import datetime

class Activity:
    def __init__(self, id, user_id, type, content, reference_id, created_at=None):
        self.id = id
        self.user_id = user_id
        self.type = type  # e.g., 'mention', 'ticket_assigned', etc.
        self.content = content
        self.reference_id = reference_id  # e.g., ticket_id
        self.created_at = created_at or datetime.now()
        self.is_read = False

    @staticmethod
    def create(user_id, type, content, reference_id):
        import random
        activity_id = random.randint(1000, 9999)
        return Activity(activity_id, user_id, type, content, reference_id) 