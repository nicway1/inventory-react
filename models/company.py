from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from models.base import Base

class Company(Base):
    __tablename__ = 'companies'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    address = Column(String, nullable=True)
    contact_name = Column(String(100), nullable=True)
    contact_email = Column(String(100), nullable=True)
    logo_path = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    users = relationship("User", back_populates="company", lazy="dynamic", viewonly=True)
    assets = relationship("Asset", back_populates="company", lazy="dynamic", viewonly=True)
    sales = relationship("Sale", back_populates="company", lazy="dynamic", viewonly=True)

    @property
    def total_sales(self):
        """Calculate total sales amount for the company"""
        return sum(sale.selling_price for sale in self.sales)

    @property
    def total_profit(self):
        """Calculate total profit for the company"""
        return sum(sale.profit for sale in self.sales if sale.profit is not None)

    def get_sales_by_period(self, start_date, end_date):
        """Get company sales within a specific date range"""
        from models.sale import Sale
        return self.sales.filter(
            Sale.sale_date >= start_date,
            Sale.sale_date <= end_date
        ).all()

    def get_top_salespeople(self, limit=5):
        """Get top performing salespeople"""
        user_sales = {}
        for sale in self.sales:
            if sale.user_id not in user_sales:
                user_sales[sale.user_id] = {
                    'user': sale.user,
                    'total_sales': 0,
                    'total_profit': 0
                }
            user_sales[sale.user_id]['total_sales'] += sale.selling_price
            user_sales[sale.user_id]['total_profit'] += (sale.profit or 0)
        
        # Sort by total sales and return top performers
        sorted_users = sorted(
            user_sales.values(),
            key=lambda x: x['total_sales'],
            reverse=True
        )
        return sorted_users[:limit]

    @property
    def logo_url(self):
        """Return the URL for the company logo"""
        if self.logo_path:
            return f'/static/company_logos/{self.logo_path}'
        return '/static/images/default-company.png'  # Default logo path 