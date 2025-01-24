from models.queue import Queue

class QueueStore:
    def __init__(self):
        self.queues = {}
        # Create default queues
        self.create_queue("Singapore New User Queue", "Queue for new user requests in Singapore")
        self.create_queue("General Support", "General support requests")
        self.create_queue("Hardware Issues", "Hardware-related issues")

    def create_queue(self, name, description=None):
        queue = Queue.create(name, description)
        self.queues[queue.id] = queue
        return queue

    def get_queue(self, queue_id):
        return self.queues.get(queue_id)

    def get_all_queues(self):
        return list(self.queues.values())

    def add_ticket_to_queue(self, queue_id, ticket_id):
        queue = self.get_queue(queue_id)
        if queue and ticket_id not in queue.tickets:
            queue.tickets.append(ticket_id)

    def remove_ticket_from_queue(self, queue_id, ticket_id):
        queue = self.get_queue(queue_id)
        if queue and ticket_id in queue.tickets:
            queue.tickets.remove(ticket_id)

# Create a singleton instance
queue_store = QueueStore() 