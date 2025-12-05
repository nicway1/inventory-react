#!/usr/bin/env python3
"""
Migration script to convert all company names to uppercase and merge duplicates.
Run: python migrations/uppercase_company_names.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db_manager import DatabaseManager
from models.company import Company
from models.customer_user import CustomerUser
from models.asset import Asset
from models.user import User
from models.company_customer_permission import CompanyCustomerPermission
from models.user_company_permission import UserCompanyPermission

def run_migration():
    db = DatabaseManager()
    session = db.get_session()
    session.autoflush = False

    print("Starting company name uppercase migration...")

    # Get all companies
    all_companies = session.query(Company).all()
    print(f"Total companies: {len(all_companies)}")

    # Group by normalized (uppercase + stripped) name
    name_groups = {}
    for company in all_companies:
        normalized = company.name.upper().strip()
        if normalized not in name_groups:
            name_groups[normalized] = []
        name_groups[normalized].append(company)

    # Find duplicates
    duplicates = {name: companies for name, companies in name_groups.items() if len(companies) > 1}
    print(f"Found {len(duplicates)} duplicate groups to merge")

    # Merge duplicates
    for normalized_name, companies in duplicates.items():
        sorted_companies = sorted(companies, key=lambda c: c.id)
        keep_company = sorted_companies[0]
        dup_companies = sorted_companies[1:]

        print(f"\nMerging '{normalized_name}': keeping id={keep_company.id}")

        for dup_company in dup_companies:
            print(f"  Merging id={dup_company.id} '{dup_company.name}'")

            # Update CustomerUser references
            session.query(CustomerUser).filter(
                CustomerUser.company_id == dup_company.id
            ).update({CustomerUser.company_id: keep_company.id}, synchronize_session='fetch')

            # Update Asset references
            session.query(Asset).filter(
                Asset.company_id == dup_company.id
            ).update({Asset.company_id: keep_company.id}, synchronize_session='fetch')

            # Update User references
            session.query(User).filter(
                User.company_id == dup_company.id
            ).update({User.company_id: keep_company.id}, synchronize_session='fetch')

            # Delete UserCompanyPermission (to avoid duplicates)
            session.query(UserCompanyPermission).filter(
                UserCompanyPermission.company_id == dup_company.id
            ).delete(synchronize_session='fetch')

            # Delete CompanyCustomerPermission references
            session.query(CompanyCustomerPermission).filter(
                CompanyCustomerPermission.company_id == dup_company.id
            ).delete(synchronize_session='fetch')
            session.query(CompanyCustomerPermission).filter(
                CompanyCustomerPermission.customer_company_id == dup_company.id
            ).delete(synchronize_session='fetch')

            # Delete the duplicate company
            session.delete(dup_company)

    session.flush()

    # Update all remaining companies to uppercase
    print("\nUpdating all company names to uppercase...")
    updated_count = 0
    for company in session.query(Company).all():
        normalized = company.name.upper().strip()
        if company.name != normalized:
            company.name = normalized
            updated_count += 1

    print(f"Updated {updated_count} company names")

    # Commit
    session.commit()
    session.close()

    print(f"\nMigration complete!")

if __name__ == '__main__':
    run_migration()
