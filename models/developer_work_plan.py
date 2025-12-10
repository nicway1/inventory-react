from sqlalchemy import Column, Integer, Date, ForeignKey, DateTime, Text, String
from sqlalchemy.orm import relationship, backref
from datetime import datetime, date, timedelta
from models.base import Base


class DeveloperWorkPlan(Base):
    """Model to track developer work plans - what they plan to work on"""
    __tablename__ = 'developer_work_plans'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    week_start = Column(Date, nullable=False)  # Monday of the week

    # Work plan description
    plan_summary = Column(Text, nullable=True)  # High-level summary of the week

    # Daily plans (optional - for more detailed planning)
    monday_plan = Column(Text, nullable=True)
    tuesday_plan = Column(Text, nullable=True)
    wednesday_plan = Column(Text, nullable=True)
    thursday_plan = Column(Text, nullable=True)
    friday_plan = Column(Text, nullable=True)

    # Additional notes
    blockers = Column(Text, nullable=True)  # Any blockers or concerns
    notes = Column(Text, nullable=True)  # General notes

    # Status
    status = Column(String(20), default='draft')  # draft, submitted, approved

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    submitted_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", backref=backref("work_plans", cascade="all, delete-orphan"))

    def __repr__(self):
        return f"<DeveloperWorkPlan {self.user_id} - {self.week_start}>"

    @staticmethod
    def get_week_start(target_date=None):
        """Get the Monday of the week for a given date"""
        if target_date is None:
            target_date = date.today()
        # Monday is 0, Sunday is 6
        days_since_monday = target_date.weekday()
        return target_date - timedelta(days=days_since_monday)

    @staticmethod
    def get_week_dates(week_start):
        """Get all weekday dates for a week starting from week_start"""
        return {
            'monday': week_start,
            'tuesday': week_start + timedelta(days=1),
            'wednesday': week_start + timedelta(days=2),
            'thursday': week_start + timedelta(days=3),
            'friday': week_start + timedelta(days=4),
        }

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'week_start': self.week_start.isoformat() if self.week_start else None,
            'plan_summary': self.plan_summary,
            'monday_plan': self.monday_plan,
            'tuesday_plan': self.tuesday_plan,
            'wednesday_plan': self.wednesday_plan,
            'thursday_plan': self.thursday_plan,
            'friday_plan': self.friday_plan,
            'blockers': self.blockers,
            'notes': self.notes,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None
        }
