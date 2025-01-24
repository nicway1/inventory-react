import json
import os
from datetime import datetime

class Company:
    def __init__(self, name, description=None, contact_email=None, phone=None):
        self.name = name
        self.description = description
        self.contact_email = contact_email
        self.phone = phone
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at

    def to_dict(self):
        return {
            'name': self.name,
            'description': self.description,
            'contact_email': self.contact_email,
            'phone': self.phone,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @staticmethod
    def from_dict(data):
        company = Company(
            name=data['name'],
            description=data.get('description'),
            contact_email=data.get('contact_email'),
            phone=data.get('phone')
        )
        company.created_at = data.get('created_at', company.created_at)
        company.updated_at = data.get('updated_at', company.updated_at)
        return company

    def save(self):
        companies = Company.get_all()
        # Update existing company or add new one
        found = False
        for i, comp in enumerate(companies):
            if comp['name'] == self.name:
                companies[i] = self.to_dict()
                found = True
                break
        if not found:
            companies.append(self.to_dict())

        # Save to file
        os.makedirs('data', exist_ok=True)
        with open('data/companies.json', 'w') as f:
            json.dump(companies, f, indent=4)

    @staticmethod
    def get_all():
        try:
            with open('data/companies.json', 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    @staticmethod
    def get_by_name(name):
        companies = Company.get_all()
        for company in companies:
            if company['name'] == name:
                return Company.from_dict(company)
        return None

    def delete(self):
        companies = Company.get_all()
        companies = [comp for comp in companies if comp['name'] != self.name]
        with open('data/companies.json', 'w') as f:
            json.dump(companies, f, indent=4) 