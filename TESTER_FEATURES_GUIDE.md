# Test Case & Tester Management Features

## Overview
Added comprehensive testing features to the bug reporting system, including test case documentation and tester assignment with notifications.

## New Features

### 1. Test Case Field
- **Location**: Bug Report form (both create and edit)
- **Purpose**: Document step-by-step test cases for verifying bug fixes or new features
- **Usage**: Enter test steps that testers should follow to verify the bug/feature

### 2. Tester Management System
- **Manage Testers Page**: `/development/testers`
- **Features**:
  - Add users as testers
  - Assign specializations (Frontend, Backend, Mobile, API, etc.)
  - Activate/deactivate testers
  - Remove testers
  - View number of active bug assignments per tester

### 3. Tester Assignment on Bugs
- **Location**: Edit Bug Report page
- **Features**:
  - Select multiple testers to assign to a bug
  - Option to notify testers immediately upon assignment
  - View which testers are already assigned
  - Track testing status (Pending, In Progress, Passed, Failed)

## Database Schema

### New Tables

#### `testers`
- `id`: Primary key
- `user_id`: Foreign key to users table (unique)
- `specialization`: Optional specialization (e.g., "Frontend", "Backend")
- `is_active`: 'Yes' or 'No'
- `created_at`, `updated_at`: Timestamps

#### `bug_tester_assignments`
- `id`: Primary key
- `bug_id`: Foreign key to bug_reports
- `tester_id`: Foreign key to testers
- `assigned_at`: When tester was assigned
- `notified`: 'Yes' or 'No'
- `notified_at`: When notification was sent
- `test_status`: 'Pending', 'In Progress', 'Passed', 'Failed'
- `test_notes`: Optional notes from testing
- `tested_at`: When testing was completed

### Modified Tables

#### `bug_reports`
- Added `test_case` field (TEXT): Test case steps for verifying the bug/feature

## Installation Steps

### 1. Run Database Migration
```bash
cd /Users/user/invK/inventory
python3 migrations/add_tester_test_case.py
```

This will:
- Add `test_case` column to `bug_reports` table
- Create `testers` table
- Create `bug_tester_assignments` table

### 2. Restart Flask
```bash
python3 app.py
```

## Usage Guide

### Adding Testers

1. Navigate to **Development > Manage Testers** (or `/development/testers`)
2. Select a user from the dropdown
3. Optionally add their specialization
4. Click "Add Tester"

### Assigning Testers to Bugs

1. Edit an existing bug report
2. Scroll to the "Assign Testers" section
3. Check the boxes next to testers you want to assign
4. Optionally check "Notify assigned testers immediately"
5. Click "Update Bug Report"

### Adding Test Cases

1. When creating or editing a bug report
2. Fill in the "Test Case" field with steps like:
   ```
   1. Navigate to login page
   2. Enter valid credentials
   3. Click login button
   4. Verify user is redirected to dashboard
   5. Verify user menu shows correct username
   ```

### Tester Workflow

**When a tester is assigned:**
1. They receive a notification (if "notify" was checked)
2. The assignment appears in their assigned bugs list
3. They can update `test_status` to:
   - **Pending**: Not started testing
   - **In Progress**: Currently testing
   - **Passed**: Tests passed successfully
   - **Failed**: Tests failed, bug still exists
4. They can add test notes documenting their findings

## API Endpoints

### Tester Management
- `GET /development/testers` - View all testers
- `POST /development/testers/add` - Add new tester
- `POST /development/testers/<id>/toggle` - Activate/deactivate tester
- `POST /development/testers/<id>/remove` - Remove tester

### Bug Report (Updated)
- `GET /development/bugs/new` - Create bug (now includes test_case field and tester list)
- `POST /development/bugs/new` - Submit bug (saves test_case)
- `GET /development/bugs/<id>/edit` - Edit bug (shows assigned testers)
- `POST /development/bugs/<id>/edit` - Update bug (handles tester assignments)

## Notification System (TODO)

Currently, when "Notify assigned testers immediately" is checked:
- The `notified` field is set to 'Yes'
- The `notified_at` timestamp is recorded
- A log entry is created

**Future Enhancement**: Implement actual email/in-app notifications to testers

## Permissions

The following permission is required for tester management:
- `can_manage_bugs`: Required to access tester management and assign testers

## Models

### Tester Model
```python
class Tester(Base):
    user_id: int  # Link to User
    specialization: str  # Optional
    is_active: str  # 'Yes' or 'No'
    bug_assignments: List[BugTesterAssignment]
```

### BugTesterAssignment Model
```python
class BugTesterAssignment(Base):
    bug_id: int
    tester_id: int
    assigned_at: datetime
    notified: str  # 'Yes' or 'No'
    notified_at: datetime
    test_status: str  # 'Pending', 'In Progress', 'Passed', 'Failed'
    test_notes: str
    tested_at: datetime
```

## File Changes

### Modified Files
- `models/bug_report.py` - Added Tester and BugTesterAssignment models, test_case field
- `routes/development.py` - Added tester management routes, updated bug routes
- `templates/development/bug_form.html` - Added test case field and tester assignment UI

### New Files
- `migrations/add_tester_test_case.py` - Database migration script
- `templates/development/testers.html` - Tester management interface
- `TESTER_FEATURES_GUIDE.md` - This guide

## Troubleshooting

### Migration fails
- Check that SQLite database exists
- Ensure no other processes are accessing the database
- Try running migration with `python3` explicitly

### Testers dropdown is empty
- Make sure you've added testers via the Manage Testers page first
- Check that testers are marked as "Active"

### Assignee dropdown shows SUPER_ADMINs
- Fixed: Now only shows DEVELOPER user type
- Check that admin user has user_type = 'DEVELOPER'

## Future Enhancements

1. **Email Notifications**: Send actual emails to testers when assigned
2. **In-App Notifications**: Show notification bell with new assignments
3. **Tester Dashboard**: Dedicated page showing all assigned bugs for a tester
4. **Test Result Reporting**: Enhanced UI for testers to report results
5. **Test Metrics**: Track testing time, pass/fail rates per tester
6. **Automated Test Integration**: Link to automated test suites
