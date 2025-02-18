from datetime import datetime
from utils.db_manager import DatabaseManager
from models.queue import Queue

class QueueStore:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.queues = {}
        self.load_queues()
    
    def load_queues(self):
        """Load queues from the database"""
        db_session = self.db_manager.get_session()
        try:
            queues = db_session.query(Queue).all()
            self.queues = {queue.id: queue for queue in queues}
            
            # Create default queue if none exists
            if not self.queues:
                default_queue = Queue(
                    name="General",
                    description="Default queue for all tickets"
                )
                db_session.add(default_queue)
                db_session.commit()
                self.queues[default_queue.id] = default_queue
        finally:
            db_session.close()
    
    def get_all_queues(self):
        """Get all queues"""
        return list(self.queues.values())
    
    def get_queue(self, queue_id):
        """Get a specific queue"""
        return self.queues.get(queue_id)
    
    def add_queue(self, name, description=None):
        """Add a new queue"""
        db_session = self.db_manager.get_session()
        try:
            queue = Queue(
                name=name,
                description=description
            )
            db_session.add(queue)
            db_session.commit()
            self.queues[queue.id] = queue
            return queue
        finally:
            db_session.close()
    
    def update_queue(self, queue_id, name=None, description=None):
        """Update queue details"""
        queue = self.queues.get(queue_id)
        if queue:
            db_session = self.db_manager.get_session()
            try:
                if name:
                    queue.name = name
                if description:
                    queue.description = description
                queue.updated_at = datetime.utcnow()
                db_session.commit()
                return True
            finally:
                db_session.close()
        return False
    
    def delete_queue(self, queue_id):
        """Delete a queue"""
        queue = self.queues.get(queue_id)
        if queue:
            db_session = self.db_manager.get_session()
            try:
                db_session.delete(queue)
                db_session.commit()
                del self.queues[queue_id]
                return True
            finally:
                db_session.close()
        return False

# Create singleton instance
queue_store = QueueStore() 