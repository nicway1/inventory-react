from datetime import datetime
from utils.db_manager import DatabaseManager
from models.queue import Queue
from models.queue_folder import QueueFolder


class QueueStore:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.queues = {}
        self.folders = {}
        self.load_queues()
        self.load_folders()

    def load_queues(self):
        """Load queues from the database"""
        db_session = self.db_manager.get_session()
        try:
            queues = db_session.query(Queue).order_by(Queue.display_order).all()
            self.queues = {queue.id: queue for queue in queues}

            # Create default queue if none exists
            if not self.queues:
                default_queue = Queue(
                    name="General",
                    description="Default queue for all tickets",
                    display_order=0
                )
                db_session.add(default_queue)
                db_session.commit()
                self.queues[default_queue.id] = default_queue
        finally:
            db_session.close()

    def load_folders(self):
        """Load queue folders from the database"""
        db_session = self.db_manager.get_session()
        try:
            folders = db_session.query(QueueFolder).order_by(QueueFolder.display_order).all()
            self.folders = {folder.id: folder for folder in folders}
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

    # ============= Folder Methods =============

    def get_all_folders(self):
        """Get all folders"""
        return list(self.folders.values())

    def get_folder(self, folder_id):
        """Get a specific folder"""
        return self.folders.get(folder_id)

    def get_queues_with_folders(self):
        """Get all queues organized by folders for grid display"""
        db_session = self.db_manager.get_session()
        try:
            # Reload to get fresh data
            folders = db_session.query(QueueFolder).order_by(QueueFolder.display_order).all()
            queues = db_session.query(Queue).order_by(Queue.display_order).all()

            folder_data = []
            for folder in folders:
                folder_queues = [q for q in queues if q.folder_id == folder.id]
                folder_data.append({
                    'id': folder.id,
                    'name': folder.name,
                    'color': folder.color,
                    'icon': folder.icon,
                    'display_order': folder.display_order,
                    'queues': [self._queue_to_dict(q, db_session) for q in folder_queues],
                    'queue_count': len(folder_queues)
                })

            unfiled_queues = [q for q in queues if q.folder_id is None]
            unfiled_data = [self._queue_to_dict(q, db_session) for q in unfiled_queues]

            return {
                'folders': folder_data,
                'unfiled_queues': unfiled_data
            }
        finally:
            db_session.close()

    def _queue_to_dict(self, queue, db_session):
        """Convert queue to dict with ticket count"""
        from models.ticket import Ticket, TicketStatus
        open_count = db_session.query(Ticket).filter(
            Ticket.queue_id == queue.id,
            Ticket.status != TicketStatus.RESOLVED,
            Ticket.status != TicketStatus.RESOLVED_DELIVERED
        ).count()
        return {
            'id': queue.id,
            'name': queue.name,
            'description': queue.description,
            'folder_id': queue.folder_id,
            'display_order': queue.display_order,
            'ticket_count': open_count
        }

    def add_folder(self, name, color='blue', icon='folder'):
        """Create a new folder"""
        db_session = self.db_manager.get_session()
        try:
            # Get max display_order
            max_order = db_session.query(QueueFolder).count()
            folder = QueueFolder(
                name=name,
                color=color,
                icon=icon,
                display_order=max_order
            )
            db_session.add(folder)
            db_session.commit()
            self.folders[folder.id] = folder
            return folder
        finally:
            db_session.close()

    def update_folder(self, folder_id, name=None, color=None, icon=None):
        """Update folder details"""
        db_session = self.db_manager.get_session()
        try:
            folder = db_session.query(QueueFolder).get(folder_id)
            if folder:
                if name:
                    folder.name = name
                if color:
                    folder.color = color
                if icon:
                    folder.icon = icon
                folder.updated_at = datetime.utcnow()
                db_session.commit()
                self.folders[folder_id] = folder
                return True
            return False
        finally:
            db_session.close()

    def delete_folder(self, folder_id):
        """Delete a folder and move its queues to unfiled"""
        db_session = self.db_manager.get_session()
        try:
            folder = db_session.query(QueueFolder).get(folder_id)
            if folder:
                # Move all queues in this folder to unfiled
                queues_in_folder = db_session.query(Queue).filter(Queue.folder_id == folder_id).all()
                for queue in queues_in_folder:
                    queue.folder_id = None
                    self.queues[queue.id] = queue

                db_session.delete(folder)
                db_session.commit()
                if folder_id in self.folders:
                    del self.folders[folder_id]
                return True
            return False
        finally:
            db_session.close()

    def move_queue_to_folder(self, queue_id, folder_id):
        """Move queue into a folder (or None to remove from folder)"""
        db_session = self.db_manager.get_session()
        try:
            queue = db_session.query(Queue).get(queue_id)
            if queue:
                queue.folder_id = folder_id
                queue.updated_at = datetime.utcnow()
                db_session.commit()
                self.queues[queue_id] = queue
                return True
            return False
        finally:
            db_session.close()

    def reorder_queues(self, queue_orders):
        """Update display_order for multiple queues
        queue_orders: list of {'id': queue_id, 'display_order': order}
        """
        db_session = self.db_manager.get_session()
        try:
            for item in queue_orders:
                queue = db_session.query(Queue).get(item['id'])
                if queue:
                    queue.display_order = item['display_order']
                    if 'folder_id' in item:
                        queue.folder_id = item['folder_id']
                    self.queues[queue.id] = queue
            db_session.commit()
            return True
        finally:
            db_session.close()

    def reorder_folders(self, folder_orders):
        """Update display_order for multiple folders
        folder_orders: list of {'id': folder_id, 'display_order': order}
        """
        db_session = self.db_manager.get_session()
        try:
            for item in folder_orders:
                folder = db_session.query(QueueFolder).get(item['id'])
                if folder:
                    folder.display_order = item['display_order']
                    self.folders[folder.id] = folder
            db_session.commit()
            return True
        finally:
            db_session.close()


# Create singleton instance
queue_store = QueueStore() 