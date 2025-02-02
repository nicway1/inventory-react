from models.queue import Queue
from utils.db_manager import DatabaseManager

class QueueStore:
    def __init__(self):
        self.db_manager = DatabaseManager()
        # Create default queues if they don't exist
        self._create_default_queues()

    def _create_default_queues(self):
        session = self.db_manager.get_session()
        try:
            # Check if queues already exist
            existing_queues = session.query(Queue).all()
            if not existing_queues:
                default_queues = [
                    Queue(name="Singapore New User Queue", description="Queue for new user requests in Singapore"),
                    Queue(name="General Support", description="General support requests"),
                    Queue(name="Hardware Issues", description="Hardware-related issues")
                ]
                for queue in default_queues:
                    session.add(queue)
                session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def create_queue(self, name, description=None):
        session = self.db_manager.get_session()
        try:
            queue = Queue(name=name, description=description)
            session.add(queue)
            session.commit()
            return queue
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_queue(self, queue_id):
        session = self.db_manager.get_session()
        try:
            return session.query(Queue).get(queue_id)
        finally:
            session.close()

    def get_all_queues(self):
        session = self.db_manager.get_session()
        try:
            return session.query(Queue).all()
        finally:
            session.close()

    def add_ticket_to_queue(self, queue_id, ticket_id):
        session = self.db_manager.get_session()
        try:
            queue = session.query(Queue).get(queue_id)
            if queue:
                from models.ticket import Ticket
                ticket = session.query(Ticket).get(ticket_id)
                if ticket:
                    ticket.queue_id = queue_id
                    session.commit()
                    return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def remove_ticket_from_queue(self, queue_id, ticket_id):
        session = self.db_manager.get_session()
        try:
            queue = session.query(Queue).get(queue_id)
            if queue:
                from models.ticket import Ticket
                ticket = session.query(Ticket).get(ticket_id)
                if ticket and ticket.queue_id == queue_id:
                    ticket.queue_id = None
                    session.commit()
                    return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

# Create a singleton instance
queue_store = QueueStore() 