# Test Case Refactoring Guide

## Overview

The test case functionality has been refactored to use a separate test case management system. Test cases are now created **after** a bug/feature is created, rather than being a single field within the bug report form.

## What Changed

### 1. Database Schema Changes

#### Removed
- `test_case` TEXT field from `bug_reports` table

#### Added
- New `test_cases` table with comprehensive test case tracking:
  - `id` - Primary key
  - `bug_id` - Foreign key to bug_reports
  - `title` - Test case title
  - `description` - Optional description
  - `preconditions` - What needs to be set up before testing
  - `test_steps` - Step-by-step test instructions
  - `expected_result` - Expected outcome
  - `actual_result` - Actual outcome (filled by tester)
  - `status` - Pending, Passed, Failed, Blocked, Skipped
  - `priority` - Low, Medium, High
  - `test_data` - Specific data needed for testing
  - `created_by_id` - User who created the test case
  - `tested_by_id` - User who executed the test
  - Timestamps: `created_at`, `updated_at`, `tested_at`

### 2. Model Changes

**File**: [models/bug_report.py](models/bug_report.py)

- Removed `test_case` column from `BugReport` model (line 72)
- Added `TestCase` model (lines 207-251) with full test case management
- Added `test_cases` relationship to `BugReport` (line 82)

### 3. Route Changes

**File**: [routes/development.py](routes/development.py)

#### Removed
- `test_case` field handling in `new_bug()` route (line 700)
- `test_case` field handling in `edit_bug()` route (line 806)

#### Added (lines 1249-1424)
- `bug_test_cases(bug_id)` - View all test cases for a bug
- `new_test_case(bug_id)` - Create new test case (GET/POST)
- `edit_test_case(id)` - Edit existing test case (GET/POST)
- `execute_test_case(id)` - Execute test and record results (GET/POST)
- `delete_test_case(id)` - Delete a test case (POST)

### 4. Template Changes

#### Modified
- [templates/development/bug_form.html](templates/development/bug_form.html) - Removed test_case textarea field (previously lines 227-238)
- [templates/development/bug_view.html](templates/development/bug_view.html) - Added "Test Cases" button with count badge (lines 27-33)

#### New Templates Created
- [templates/development/test_cases.html](templates/development/test_cases.html) - List all test cases for a bug
- [templates/development/test_case_form.html](templates/development/test_case_form.html) - Create/edit test case form
- [templates/development/execute_test_case.html](templates/development/execute_test_case.html) - Execute test and record results

### 5. Migration Files

#### MySQL
- [migrations/refactor_test_cases.sql](migrations/refactor_test_cases.sql)
  - Drops `test_case` column from `bug_reports` (if exists)
  - Creates `test_cases` table with all fields and indexes
  - **Already executed on `inventory_mysql` database**

#### SQLite
- [migrations/refactor_test_cases_sqlite.py](migrations/refactor_test_cases_sqlite.py)
  - Python script for SQLite migration
  - Creates `test_cases` table
  - Note: SQLite doesn't easily drop columns, so old column is ignored

## How to Use the New Test Case System

### 1. Creating Test Cases

After creating or editing a bug:

1. Go to the bug detail page
2. Click the blue "Test Cases" button (shows count if test cases exist)
3. Click "Create Test Case"
4. Fill in the form:
   - **Title** (required) - Brief description of what's being tested
   - **Description** (optional) - Additional context
   - **Priority** - Low, Medium, or High
   - **Preconditions** - Setup needed before testing
   - **Test Steps** (required) - Step-by-step instructions
   - **Expected Result** (required) - What should happen
   - **Test Data** (optional) - Specific data needed
5. Click "Create Test Case"

### 2. Executing Test Cases

When ready to test:

1. Navigate to bug test cases list
2. Click the green play icon (▶) next to a test case
3. Review the test case details:
   - Preconditions (blue box)
   - Test Steps (green box)
   - Expected Result (purple box)
   - Test Data (orange box)
4. Follow the test steps
5. Fill in:
   - **Actual Result** - What actually happened
   - **Status** - Pending, Passed, Failed, Blocked, or Skipped
6. Click "Save Results"

### 3. Managing Test Cases

**Actions available:**
- ▶ **Execute** - Run the test and record results
- ✏️ **Edit** - Modify test case details
- 🗑️ **Delete** - Remove test case (with confirmation)

**Test Case Statuses:**
- **Pending** - Not yet tested (gray)
- **Passed** - Test executed successfully (green)
- **Failed** - Test did not pass (red)
- **Blocked** - Cannot complete test (orange)
- **Skipped** - Test not executed (yellow)

## Benefits of the New System

1. **Multiple Test Cases Per Bug** - Create as many test cases as needed
2. **Comprehensive Test Documentation** - Separate fields for preconditions, steps, expected results
3. **Test Execution Tracking** - Track who tested, when, and what the results were
4. **Test Case Reusability** - Test cases persist even after bug is resolved
5. **Better Organization** - Test cases don't clutter the bug report form
6. **Status Tracking** - Clear visual status for each test case
7. **Audit Trail** - Track test case creator and tester separately

## Navigation

### From Bug Detail Page
- Click "Test Cases" button to view all test cases for that bug

### From Test Cases List
- Click "Create Test Case" to add new test case
- Click play icon to execute test
- Click edit icon to modify test case
- Click "Back to Bug" to return to bug detail

### From Test Case Execution
- Click "View Bug" to see the related bug
- Click "Edit Test Case" to modify before testing

## API Endpoints

All test case routes require `can_manage_bugs` permission:

- `GET /development/bugs/<bug_id>/test-cases` - List test cases
- `GET /development/bugs/<bug_id>/test-cases/new` - Show create form
- `POST /development/bugs/<bug_id>/test-cases/new` - Create test case
- `GET /development/test-cases/<id>/edit` - Show edit form
- `POST /development/test-cases/<id>/edit` - Update test case
- `GET /development/test-cases/<id>/execute` - Show execution form
- `POST /development/test-cases/<id>/execute` - Save test results
- `POST /development/test-cases/<id>/delete` - Delete test case

## Migration Status

✅ **MySQL (inventory_mysql)** - Migration completed successfully
- test_case column dropped
- test_cases table created
- Indexes created

⚠️ **SQLite (inventory.db)** - Migration script available
- Run: `python3 migrations/refactor_test_cases_sqlite.py`
- Note: Old test_case column will be ignored if not manually removed

## Troubleshooting

### Issue: "Column 'bug_reports.test_case' doesn't exist"
**Solution**: Run the migration script for your database

### Issue: Test cases page shows 404
**Solution**: Ensure Flask server is restarted after code changes

### Issue: Can't see test cases count on bug detail
**Solution**: Make sure bug has test_cases relationship loaded (should be automatic)

### Issue: Old test_case data is lost
**Note**: The old single-field test case data was not migrated automatically. If you need to preserve this data:
1. Export bug reports with test_case field before migration
2. After migration, manually create test cases from the old data
3. Or modify the migration script to copy test_case content to a new test case

## Examples

### Example Test Case for Login Feature

**Title**: Verify successful user login with valid credentials

**Preconditions**:
- User account exists in database
- User is not already logged in
- Login page is accessible

**Test Steps**:
1. Navigate to /login
2. Enter username: test@example.com
3. Enter password: Test123!
4. Click "Login" button
5. Wait for page to load

**Expected Result**:
- User is successfully authenticated
- Redirected to dashboard page
- Welcome message displays: "Welcome, Test User"
- Navigation menu shows user's name
- No error messages appear

**Test Data**:
- Username: test@example.com
- Password: Test123!
- Expected User Name: Test User

**Priority**: High

### Example Test Case for Bug Fix

**Title**: Verify ticket export includes package items

**Preconditions**:
- At least one ticket with package items exists
- User has export permissions
- Export wizard is accessible

**Test Steps**:
1. Navigate to ticket export wizard
2. Select a date range that includes tickets with packages
3. Select CSV format
4. Click "Export" button
5. Open downloaded CSV file
6. Check the package_items column

**Expected Result**:
- Export completes without errors
- CSV file downloads successfully
- package_items column exists
- Package items are listed in JSON format
- All package items from ticket are included

**Priority**: Medium

## Database Schema Reference

### test_cases Table Structure

```sql
CREATE TABLE test_cases (
    id INT PRIMARY KEY AUTO_INCREMENT,
    bug_id INT NOT NULL,                    -- Links to bug_reports.id
    title VARCHAR(200) NOT NULL,            -- Short test case title
    description TEXT,                       -- Optional details
    preconditions TEXT,                     -- Setup required
    test_steps TEXT NOT NULL,               -- How to test
    expected_result TEXT NOT NULL,          -- Expected outcome
    actual_result TEXT,                     -- Actual outcome
    status VARCHAR(20) DEFAULT 'Pending',   -- Test status
    priority VARCHAR(20) DEFAULT 'Medium',  -- Test priority
    test_data TEXT,                         -- Data needed
    created_by_id INT NOT NULL,             -- Creator
    tested_by_id INT,                       -- Tester
    created_at DATETIME DEFAULT NOW(),
    updated_at DATETIME,
    tested_at DATETIME,
    FOREIGN KEY (bug_id) REFERENCES bug_reports(id) ON DELETE CASCADE,
    INDEX idx_bug_id (bug_id),
    INDEX idx_status (status)
);
```

## Future Enhancements

Possible improvements to consider:

1. **Test Case Templates** - Save common test case patterns
2. **Bulk Test Execution** - Execute multiple test cases at once
3. **Test Runs** - Group test case executions into test runs
4. **Test Reports** - Generate reports on test coverage and pass rates
5. **Test Case Import/Export** - Import test cases from CSV or other formats
6. **Screenshot Attachments** - Attach screenshots to test case executions
7. **Test Notifications** - Notify testers when assigned to test cases
8. **Test Case Dependencies** - Mark test cases that depend on others

---

**Last Updated**: 2025-10-28
**Migration Status**: Completed for MySQL, Script available for SQLite
