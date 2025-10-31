from sqlalchemy import Column, Integer, String, Boolean
from models.base import Base

class SystemSettings(Base):
    __tablename__ = 'system_settings'

    id = Column(Integer, primary_key=True)
    setting_key = Column(String(100), unique=True, nullable=False)
    setting_value = Column(String(500))
    setting_type = Column(String(20), default='string')  # string, boolean, integer
    description = Column(String(500))

    def get_value(self):
        """Convert setting_value to appropriate type"""
        if self.setting_type == 'boolean':
            return self.setting_value.lower() in ('true', '1', 'yes')
        elif self.setting_type == 'integer':
            try:
                return int(self.setting_value)
            except (ValueError, TypeError):
                return 0
        return self.setting_value

    def to_dict(self):
        return {
            'id': self.id,
            'setting_key': self.setting_key,
            'setting_value': self.setting_value,
            'setting_type': self.setting_type,
            'description': self.description
        }
