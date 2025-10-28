#!/usr/bin/env python3
"""
Add a new release to track today's deployment
"""

from database import SessionLocal
from models.release import Release, ReleaseType, ReleaseStatus
from models.changelog_entry import ChangelogEntry, ChangelogEntryType
from models.user import User
from datetime import datetime, date
import sys

def create_release():
    """Create a new release for the feature enhancements"""
    db_session = SessionLocal()
    
    try:
        # Get current user (or system user)
        current_user = db_session.query(User).first()
        if not current_user:
            print("✗ No users found in database")
            return None
        
        # Check if release already exists
        existing = db_session.query(Release).filter(Release.version == "1.8.0").first()
        if existing:
            print(f"✓ Release v1.8.0 already exists (Status: {existing.status.value})")
            return existing.id
        
        # Create new release
        release = Release(
            version="1.8.0",
            name="Bug & Feature Enhancement Release",
            description="Comprehensive enhancements to bug tracking and feature management systems",
            release_type=ReleaseType.MINOR,
            status=ReleaseStatus.RELEASED,
            planned_date=date.today(),
            release_date=datetime.utcnow(),
            is_pre_release=False,
            is_hotfix=False,
            deployment_environment="production",
            git_branch="main",
            git_tag="v1.8.0",
            release_manager_id=current_user.id,
            total_features=8,
            total_bugs_fixed=0,
            release_notes="""# Release v1.8.0 - Bug & Feature Enhancement Release

## 🎯 Major Features

### Case Management Improvements
- **Case Progress Tracking**: Added 0-100% progress tracking with visual progress bars
- **Case Owner Terminology**: Renamed "Assignee" to "Case Owner" for clarity
- **Auto-Progress Updates**: Status changes automatically update case progress

### Communication Enhancements
- **Messenger-Style Comments**: Modern chat interface with bubble design
- **@Mention Functionality**: Real-time autocomplete for mentioning team members
- **Email Notifications**: Beautiful HTML emails for @mentions with gradient headers

### Test Case Management
- **Separate Test Cases**: Test cases now created after bug/feature creation
- **Full CRUD Operations**: Create, Read, Update, Delete, and Execute test cases
- **Test Case Templates**: Professional forms for managing test scenarios

### Quick Actions
- **Owner-Only Actions**: Quick Actions restricted to case owners
- **Status Change Modal**: Easy status updates with dropdown modal
- **Delete Functionality**: Safely delete bugs and features with confirmation

## 🐛 Bug Tracking Enhancements
- Case Progress field with auto-update on status change
- Messenger-style comment UI with chat bubbles
- @mention autocomplete with user filtering
- Email notifications using ticket template style
- Progress mapping: Open(0%), In Progress(25%), Testing(75%), Resolved(100%)

## ✨ Feature Request Enhancements
- All bug enhancements replicated for feature requests
- Case Progress tracking and auto-update
- Messenger-style comments with @mentions
- Email notifications with blue gradient theme
- Quick Actions for feature owners
- Test case management with 5 routes

## 📊 Database Changes
- Added `case_progress` to `bug_reports` and `feature_requests`
- Created `test_cases` table for bugs
- Created `feature_test_cases` table for features
- Both SQLite and MySQL migration scripts included

## 🛠️ Technical Improvements
- 10 new routes added (5 for bugs, 5 for features)
- 6 new templates created for test case management
- JavaScript for @mention autocomplete
- Status change modals
- Email notification system integration

## 📚 Documentation
- Created DEPLOYMENT.md for PythonAnywhere deployment
- Created automated migration runner (run_migrations.py)
- All migrations compatible with SQLite and MySQL

## 🚀 Deployment
- Production deployment: October 28, 2025
- Environment: PythonAnywhere
- Database: MySQL (inventory_mysql)
""",
            breaking_changes="None - Backward compatible",
            upgrade_instructions="""## Upgrade Instructions

### For Local Development:
1. Pull latest code: `git pull origin main`
2. Run migrations: `python run_migrations.py`
3. Restart Flask app

### For PythonAnywhere:
1. SSH to PythonAnywhere console
2. `cd ~/inventory && git pull origin main`
3. `source venv/bin/activate`
4. `python run_migrations.py`
5. Reload web app from dashboard

### Database Migrations Required:
- `add_case_progress.sql` - Adds progress tracking
- `create_feature_test_cases_table.sql` - Creates test case table

No breaking changes - all existing functionality preserved.
"""
        )
        
        db_session.add(release)
        db_session.flush()  # Get the release ID
        
        # Add changelog entries
        changelog_entries = [
            {
                'title': 'Case Progress Tracking',
                'description': 'Added visual progress tracking (0-100%) with auto-update on status changes',
                'entry_type': ChangelogEntryType.FEATURE,
            },
            {
                'title': 'Case Owner Terminology',
                'description': 'Renamed "Assignee" to "Case Owner" across all bugs and features for clarity',
                'entry_type': ChangelogEntryType.IMPROVEMENT,
            },
            {
                'title': 'Messenger-Style Comments',
                'description': 'Redesigned comment interface with chat bubbles and modern messenger layout',
                'entry_type': ChangelogEntryType.FEATURE,
            },
            {
                'title': '@Mention Functionality',
                'description': 'Added real-time @mention autocomplete with email notifications',
                'entry_type': ChangelogEntryType.FEATURE,
            },
            {
                'title': 'Email Notifications for Mentions',
                'description': 'Beautiful HTML email notifications when users are mentioned in comments',
                'entry_type': ChangelogEntryType.FEATURE,
            },
            {
                'title': 'Test Case Management',
                'description': 'Separate test case management with create, edit, execute, and delete operations',
                'entry_type': ChangelogEntryType.FEATURE,
            },
            {
                'title': 'Quick Actions Section',
                'description': 'Owner-only Quick Actions with Change Status and Delete functionality',
                'entry_type': ChangelogEntryType.FEATURE,
            },
            {
                'title': 'Feature Parity with Bugs',
                'description': 'All bug tracking enhancements now available for feature requests',
                'entry_type': ChangelogEntryType.IMPROVEMENT,
            },
            {
                'title': 'Automated Migration Runner',
                'description': 'Created run_migrations.py for easy deployment and database updates',
                'entry_type': ChangelogEntryType.IMPROVEMENT,
            },
            {
                'title': 'Deployment Documentation',
                'description': 'Comprehensive DEPLOYMENT.md guide for PythonAnywhere deployment',
                'entry_type': ChangelogEntryType.DOCUMENTATION,
            }
        ]
        
        for idx, entry_data in enumerate(changelog_entries):
            entry = ChangelogEntry(
                release_id=release.id,
                created_by_id=current_user.id,
                sort_order=idx,
                **entry_data
            )
            db_session.add(entry)
        
        db_session.commit()
        
        print(f"✓ Release v1.8.0 created successfully!")
        print(f"  - ID: {release.id}")
        print(f"  - Status: {release.status.value}")
        print(f"  - Changelog entries: {len(changelog_entries)}")
        return release.id
        
    except Exception as e:
        db_session.rollback()
        print(f"✗ Error creating release: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        db_session.close()

if __name__ == '__main__':
    print("Creating Release v1.8.0...")
    release_id = create_release()
    sys.exit(0 if release_id else 1)
