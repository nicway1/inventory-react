# Design Document

## Overview

This design addresses the critical issues in the @mention notification system where users were receiving notifications for their own mentions instead of the intended recipients. The solution involves fixing the notification logic, improving the test system, and enhancing the user experience.

## Architecture

### Current Issues
1. **Self-notification bug**: Test endpoint creates notifications where `mentioned_user_id == commenter_user_id`
2. **Poor test coverage**: No realistic cross-user testing
3. **Autocomplete includes self**: Users can mention themselves
4. **No validation**: System doesn't prevent self-mentions

### Proposed Solution
1. **Fix notification logic**: Ensure notifications go to mentioned users, not commenters
2. **Improve test system**: Create realistic cross-user scenarios
3. **Add validation**: Prevent self-mentions and invalid usernames
4. **Enhance autocomplete**: Exclude current user from suggestions

## Components and Interfaces

### 1. Notification Service Updates
- **Method**: `create_mention_notification()`
- **Change**: Add validation to prevent `mentioned_user_id == commenter_user_id`
- **Interface**: Same parameters, but with validation logic

### 2. Test Endpoint Improvements
- **Endpoint**: `/tickets/test-notification`
- **Change**: Use different users for commenter and mentioned user
- **Logic**: Find or create a second user for realistic testing

### 3. User Search API Updates
- **Endpoint**: `/tickets/users/search`
- **Change**: Exclude current user from search results
- **Filter**: Add `WHERE user_id != current_user_id`

### 4. Comment Processing
- **Component**: `CommentStore._notify_mentions()`
- **Change**: Add logging and validation for mention processing
- **Enhancement**: Better error handling for invalid mentions

## Data Models

### Notification Model (No changes needed)
```python
class Notification:
    user_id: int          # The user who receives the notification
    type: str             # 'mention'
    title: str            # 'X mentioned you'
    message: str          # Full message content
    reference_type: str   # 'ticket'
    reference_id: int     # Ticket ID
    is_read: bool         # Read status
    created_at: datetime  # When created
```

### Comment Model (No changes needed)
```python
class Comment:
    @property
    def mentions(self) -> List[str]:
        # Extract @mentions from content
        # Returns list of usernames
```

## Error Handling

### Self-Mention Prevention
```python
def create_mention_notification(mentioned_user_id, commenter_user_id, ...):
    if mentioned_user_id == commenter_user_id:
        logger.info(f"Skipping self-mention for user {commenter_user_id}")
        return True  # Not an error, just skip
```

### Invalid User Handling
```python
def _notify_mentions(comment):
    for username in comment.mentions:
        mentioned_user = find_user_by_username(username)
        if not mentioned_user:
            logger.warning(f"User {username} not found for mention")
            continue  # Skip invalid users, don't fail
```

### Database Error Handling
```python
try:
    notification_service.create_mention_notification(...)
except DatabaseError as e:
    logger.error(f"Database error creating notification: {e}")
    # Don't fail comment creation due to notification issues
```

## Testing Strategy

### Unit Tests
1. **Test self-mention prevention**: Verify no notification created when `mentioned_user_id == commenter_user_id`
2. **Test cross-user mentions**: Verify notification created for different users
3. **Test invalid usernames**: Verify graceful handling of non-existent users
4. **Test multiple mentions**: Verify each user gets their own notification

### Integration Tests
1. **End-to-end mention flow**: Comment creation → mention detection → notification → toast display
2. **Cross-user scenarios**: Multiple users in different sessions
3. **Database failure scenarios**: Test error handling

### Manual Testing
1. **Two-user test**: Login as User A, mention User B, verify User B gets notification
2. **Self-mention test**: Try to mention yourself, verify no notification
3. **Toast display test**: Verify toasts appear for correct users
4. **Autocomplete test**: Verify current user excluded from suggestions

## Implementation Plan

### Phase 1: Fix Core Logic
1. Update `create_mention_notification()` to prevent self-mentions
2. Fix test endpoint to use different users
3. Update user search to exclude current user

### Phase 2: Improve Testing
1. Create realistic test scenarios
2. Add proper test users if needed
3. Enhance test endpoint with better user selection

### Phase 3: Enhance User Experience
1. Improve autocomplete filtering
2. Add better error messages
3. Enhance toast notification targeting

### Phase 4: Fix Notification Interaction Issues
1. Fix "Mark all read" button functionality
2. Implement click-to-navigate for notifications
3. Add proper notification state management

### Phase 5: Validation & Cleanup
1. Add comprehensive logging
2. Improve error handling
3. Add validation for edge cases

## Notification Interaction Design

### Mark All Read Functionality
```javascript
async function markAllAsRead() {
    try {
        const response = await fetch('/tickets/notifications/mark-all-read', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (response.ok) {
            loadNotifications(); // Refresh dropdown
            updateUnreadCount(); // Update badge
        }
    } catch (error) {
        console.error('Error marking all as read:', error);
    }
}
```

### Click-to-Navigate Functionality
```javascript
function handleNotificationClick(notification) {
    // Mark as read
    markAsRead(notification.id);
    
    // Navigate to ticket
    if (notification.reference_type === 'ticket') {
        window.location.href = `/tickets/${notification.reference_id}#comments`;
    }
}
```