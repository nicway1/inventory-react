from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, joinedload
from models.base import Base
from models.company import Company
from models.user import User, UserType
from models.asset import Asset
from models.location import Location
from models.accessory import Accessory
from models.activity import Activity
from models.permission import Permission
from models.ticket import Ticket
from datetime import datetime
import os

class DatabaseManager:
    def __init__(self, db_url=None):
        # Use DATABASE_URL from environment, fallback to SQLite only for local dev
        if db_url is None:
            db_url = os.environ.get('DATABASE_URL', 'sqlite:///inventory.db')

        # Pool settings for MySQL - match database.py settings
        # pool_recycle=280 ensures connections are recycled before MySQL's default 300s timeout
        if 'sqlite' in db_url:
            self.engine = create_engine(db_url)
        else:
            self.engine = create_engine(
                db_url,
                pool_pre_ping=True,
                pool_recycle=280,
                pool_size=10,
                max_overflow=20
            )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        
    def get_session(self):
        return self.Session()

    def __enter__(self):
        self.session = self.get_session()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.session.rollback()
        else:
            self.session.commit()
        self.session.close()

    @staticmethod
    def joinedload(relationship):
        """Helper method to provide joinedload functionality"""
        return joinedload(relationship)
        
    def get_all_assets(self):
        session = self.get_session()
        try:
            return session.query(Asset).all()
        finally:
            session.close()
            
    def get_asset(self, asset_id):
        session = self.get_session()
        try:
            return session.query(Asset).filter(Asset.id == asset_id).first()
        finally:
            session.close()
            
    def create_asset(self, asset_data):
        session = self.get_session()
        try:
            asset = Asset(**asset_data)
            session.add(asset)
            session.commit()
            return asset
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
            
    def update_asset_status(self, asset_id, new_status, notes=None):
        session = self.get_session()
        try:
            asset = session.query(Asset).filter(Asset.id == asset_id).first()
            if asset:
                asset.status = new_status
                if notes:
                    asset.notes = notes
                asset.updated_at = datetime.utcnow()
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    # Company Management
    def get_all_companies(self):
        session = self.get_session()
        try:
            return session.query(Company).all()
        finally:
            session.close()

    def get_company(self, company_id):
        session = self.get_session()
        try:
            return session.query(Company).filter(Company.id == company_id).first()
        finally:
            session.close()

    def create_company(self, company_data):
        session = self.get_session()
        try:
            company = Company(**company_data)
            session.add(company)
            session.commit()
            return company
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def update_company(self, company_id, company_data):
        session = self.get_session()
        try:
            company = session.query(Company).filter(Company.id == company_id).first()
            if company:
                for key, value in company_data.items():
                    setattr(company, key, value)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def delete_company(self, company_id):
        session = self.get_session()
        try:
            company = session.query(Company).filter(Company.id == company_id).first()
            if company:
                session.delete(company)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    # Location Management
    def get_all_locations(self):
        session = self.get_session()
        try:
            return session.query(Location).all()
        finally:
            session.close()

    def create_location(self, location_data):
        session = self.get_session()
        try:
            location = Location(**location_data)
            session.add(location)
            session.commit()
            return location
        finally:
            session.close()

    # Ticket Management
    def get_asset_tickets(self, asset_id):
        session = self.get_session()
        try:
            return session.query(Ticket).filter(Ticket.asset_id == asset_id).all()
        finally:
            session.close()

    def create_ticket(self, ticket_data):
        session = self.get_session()
        try:
            ticket = Ticket(**ticket_data)
            session.add(ticket)
            session.commit()
            return ticket
        finally:
            session.close()

    def get_user(self, user_id):
        session = self.get_session()
        try:
            # Use joinedload to eagerly load the company but not permissions
            return session.query(User).options(
                joinedload(User.company)
            ).filter(User.id == user_id).first()
        finally:
            session.close()

    def get_user_by_username(self, username):
        session = self.get_session()
        try:
            user = session.query(User).options(
                joinedload(User.company)
            ).filter(User.username == username, User.is_deleted == False).first()

            if user:
                # Get permission record for this user's type instead of relying on direct relationship
                permission = session.query(Permission).filter_by(user_type=user.user_type).first()

                if not permission:
                    # Create default permissions if none exist for this user type
                    default_permissions = Permission.get_default_permissions(user.user_type)
                    permission = Permission(user_type=user.user_type, **default_permissions)
                    session.add(permission)
                    session.commit()

            return user
        finally:
            session.close()

    def get_user_permissions(self, user_id):
        session = self.get_session()
        try:
            user = session.query(User).filter(User.id == user_id).first()
            
            if not user:
                return None
                
            # Get permission record for this user's type instead of relying on direct relationship
            permission = session.query(Permission).filter_by(user_type=user.user_type).first()
            
            if not permission:
                # Create default permissions if none exist for this user type
                default_permissions = Permission.get_default_permissions(user.user_type)
                permission = Permission(user_type=user.user_type, **default_permissions)
                session.add(permission)
                session.commit()
            
            return permission
        finally:
            session.close()

    def get_all_users(self, include_deleted=False):
        """Get all users, optionally including deleted ones"""
        session = self.get_session()
        try:
            query = session.query(User).options(joinedload(User.company))
            if not include_deleted:
                query = query.filter(User.is_deleted == False)
            return query.all()
        finally:
            session.close()

    def create_user(self, user_data):
        session = self.get_session()
        try:
            # Convert user_type to enum if it's a string
            if isinstance(user_data.get('user_type'), str):
                user_data['user_type'] = UserType[user_data['user_type']]
            
            user = User(**user_data)
            session.add(user)
            session.commit()
            return user
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_user_by_id(self, user_id):
        session = self.get_session()
        try:
            # Use joinedload to eagerly load the company relationship
            return session.query(User).options(
                joinedload(User.company)
            ).filter(User.id == user_id).first()
        finally:
            session.close()

    def update_user(self, user_id, user_data):
        session = self.get_session()
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if user:
                for key, value in user_data.items():
                    # Ensure datetime fields are datetime objects
                    if key in ['created_at', 'last_login'] and isinstance(value, str):
                        try:
                            value = datetime.fromisoformat(value)
                        except ValueError:
                            continue
                    setattr(user, key, value)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def delete_user(self, user_id):
        """Soft delete a user by setting is_deleted flag"""
        session = self.get_session()
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return False

            # Soft delete - just mark as deleted instead of actually deleting
            user.is_deleted = True
            user.deleted_at = datetime.utcnow()
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def restore_user(self, user_id):
        """Restore a soft-deleted user"""
        session = self.get_session()
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return False

            user.is_deleted = False
            user.deleted_at = None
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    # Activity Management
    def get_user_activities(self, user_id, limit=50):
        """Get recent activities for a user"""
        session = self.get_session()
        try:
            return session.query(Activity).filter(
                Activity.user_id == user_id
            ).order_by(
                Activity.created_at.desc()
            ).limit(limit).all()
        finally:
            session.close()

    def add_activity(self, user_id, type, content, reference_id):
        """Add a new activity for a user"""
        session = self.get_session()
        try:
            activity = Activity.create(user_id, type, content, reference_id)
            session.add(activity)
            session.commit()
            return activity
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def mark_activity_read(self, activity_id):
        """Mark an activity as read"""
        session = self.get_session()
        try:
            activity = session.query(Activity).get(activity_id)
            if activity:
                activity.is_read = True
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_unread_activities_count(self, user_id):
        """Get count of unread activities for a user"""
        session = self.get_session()
        try:
            return session.query(Activity).filter(
                Activity.user_id == user_id,
                Activity.is_read == False
            ).count()
        finally:
            session.close()

    def get_user_assets(self, user_id):
        """Get assets assigned to a user"""
        session = self.get_session()
        try:
            return session.query(Asset).filter(Asset.assigned_to_id == user_id).all()
        finally:
            session.close()

    def update_user_password(self, user_id, new_password):
        """Update user password"""
        session = self.get_session()
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if user:
                user.set_password(new_password)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()