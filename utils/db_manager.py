from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, joinedload
from models.database import Base, Asset, Location, Company, Ticket, AssetStatus
from datetime import datetime
from models.user import User, UserType

class DatabaseManager:
    def __init__(self, db_url="sqlite:///inventory.db"):
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        
    def get_session(self):
        return self.Session()
        
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
            return session.query(User).filter(User.id == user_id).first()
        finally:
            session.close()

    def get_user_by_username(self, username):
        session = self.get_session()
        try:
            return session.query(User).filter(User.username == username).first()
        finally:
            session.close()

    def get_all_users(self):
        session = self.get_session()
        try:
            return session.query(User).all()
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
            return session.query(User).options(joinedload(User.company)).filter(User.id == user_id).first()
        finally:
            session.close()

    def update_user(self, user_id, user_data):
        session = self.get_session()
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if user:
                for key, value in user_data.items():
                    setattr(user, key, value)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()