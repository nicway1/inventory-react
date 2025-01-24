from datetime import datetime

class Queue:
    def __init__(self, id, name, description=None):
        self.id = id
        self.name = name
        self.description = description
        self.created_at = datetime.now()
        self.tickets = []  # List of ticket IDs in this queue

    @staticmethod
    def create(name, description=None):
        import random
        queue_id = random.randint(1, 10000)
        return Queue(queue_id, name, description) 