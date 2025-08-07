# Requirements Document

## Introduction

The current @mention notification system has a critical flaw where users receive notifications for their own mentions instead of other users receiving notifications when they are mentioned. This spec addresses fixing the notification system to work correctly for cross-user mentions and improving the testing mechanism.

## Requirements

### Requirement 1

**User Story:** As a user, I want to receive notifications when OTHER users mention me in comments, not when I mention myself.

#### Acceptance Criteria

1. WHEN a user types @username in a comment THEN the mentioned user (not the commenter) SHALL receive a notification
2. WHEN a user mentions themselves (@their_own_username) THEN no notification SHALL be created
3. WHEN a user mentions multiple other users in one comment THEN each mentioned user SHALL receive their own notification
4. WHEN a user mentions a non-existent username THEN no notification SHALL be created and no error SHALL occur

### Requirement 2

**User Story:** As a developer, I want a proper test system that demonstrates cross-user mentions working correctly.

#### Acceptance Criteria

1. WHEN the test notification button is clicked THEN it SHALL create a mention from one user to a different user
2. WHEN testing mentions THEN the system SHALL use at least 2 different users (commenter and mentioned user)
3. WHEN no other users exist THEN the test SHALL create a temporary test user or show an appropriate message
4. WHEN the test runs THEN it SHALL demonstrate the toast notification appearing for the mentioned user

### Requirement 3

**User Story:** As a user, I want to see toast notifications only for mentions directed at me, not for mentions I create.

#### Acceptance Criteria

1. WHEN I mention another user THEN I SHALL NOT see a toast notification
2. WHEN another user mentions me THEN I SHALL see a toast notification within 5 seconds
3. WHEN I am logged in as multiple users in different tabs THEN each user SHALL only see notifications meant for them
4. WHEN a notification is marked as read THEN it SHALL not appear again as a toast

### Requirement 4

**User Story:** As a system administrator, I want the notification system to handle edge cases gracefully.

#### Acceptance Criteria

1. WHEN a user is mentioned but doesn't exist THEN the system SHALL log a warning but continue processing other mentions
2. WHEN a ticket doesn't exist THEN the notification creation SHALL fail gracefully
3. WHEN the database is unavailable THEN the system SHALL handle errors without crashing
4. WHEN multiple users mention the same user simultaneously THEN all notifications SHALL be created correctly

### Requirement 5

**User Story:** As a user, I want to be able to mark all notifications as read with a single click.

#### Acceptance Criteria

1. WHEN I click the "Mark all read" button in the notification dropdown THEN all my unread notifications SHALL be marked as read
2. WHEN all notifications are marked as read THEN the notification badge count SHALL update to 0
3. WHEN the mark all read operation completes THEN the notification dropdown SHALL refresh to show the updated read status
4. WHEN there are no unread notifications THEN the "Mark all read" button SHALL be disabled or hidden

### Requirement 6

**User Story:** As a user, I want to click on a notification to navigate directly to the relevant ticket/case.

#### Acceptance Criteria

1. WHEN I click on a notification in the dropdown THEN I SHALL be navigated to the specific ticket page
2. WHEN I click on a notification THEN it SHALL be automatically marked as read
3. WHEN navigating to a ticket from a notification THEN the page SHALL scroll to the comments section
4. WHEN the ticket reference is invalid THEN I SHALL see an appropriate error message

### Requirement 7

**User Story:** As a user, I want the @mention autocomplete to show other users, not myself.

#### Acceptance Criteria

1. WHEN I type @ in a comment THEN the autocomplete SHALL show other users, not my own username
2. WHEN searching for users THEN the results SHALL exclude the current user
3. WHEN no other users match the search THEN the autocomplete SHALL show "No users found"
4. WHEN I select a user from autocomplete THEN their username SHALL be inserted correctly