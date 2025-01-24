from models.user import User, UserType
from models.database import Company
import json
import os
from datetime import datetime

class UserStore:
    def __init__(self):
        self.users = {}
        self.load_users()

    def load_users(self):
        try:
            # Create default admin user if no users exist
            admin = User.create(
                username="admin",
                password="admin123",  # You should hash this in production
                user_type="SUPER_ADMIN",  # Pass as string
                company=None
            )
            self.users[admin.id] = admin

            # Create a test user
            test_user = User.create(
                username="test",
                password="test123",
                user_type="USER",  # Pass as string
                company=None
            )
            self.users[test_user.id] = test_user

        except Exception as e:
            print(f"Error loading users: {str(e)}")

    def get_user_by_id(self, user_id):
        return self.users.get(user_id)

    def get_user_by_username(self, username):
        for user in self.users.values():
            if user.username == username:
                return user
        return None

    def add_user(self, username, password, user_type='user', company=None):
        user = User.create(
            username=username,
            password=password,
            user_type=user_type,
            company=company
        )
        self.users[user.id] = user
        return user

    def authenticate(self, username, password):
        user = self.get_user_by_username(username)
        if user and user.check_password(password):
            return user
        return None

    def save_users(self):
        # In a real application, you would save to a database
        pass

    def get_user(self, username):
        return next((user for user in self.users.values() if user.username == username), None)

    def get_all_users(self):
        return list(self.users.values())

    def create_user(self, username, password, user_type='user', company=None, role=None):
        if self.get_user_by_username(username):
            return None
        
        user = User.create(
            username=username,
            password=password,
            user_type=user_type,
            company=company,
            role=role
        )
        self.users[user.id] = user
        self.save_users()
        return user 