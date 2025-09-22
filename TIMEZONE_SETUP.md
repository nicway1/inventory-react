# Singapore Timezone Configuration

This document explains how Singapore timezone support has been implemented in the inventory system.

## Overview

All timestamps in the system now display in Singapore time (Asia/Singapore timezone) for better user experience, while internally storing data in UTC for consistency.

## Implementation

### 1. Timezone Utilities (`utils/timezone_utils.py`)

- `now_singapore()` - Get current Singapore time
- `singapore_now_as_utc()` - Get Singapore time converted to UTC (replacement for `datetime.utcnow()`)
- `utc_to_singapore()` - Convert UTC datetime to Singapore time
- `format_singapore_time()` - Format datetime in Singapore timezone

### 2. Backend Changes

- Updated `routes/auth.py` to use Singapore time for login timestamps
- Updated `routes/inventory.py` to use Singapore time for all operations
- Added Singapore timezone filter to Flask app (`app.py`)

### 3. Template Changes

Templates now use the `singapore_time` filter to display times in Singapore timezone:

```html
<!-- Before -->
{{ user.last_login.strftime('%Y-%m-%d %H:%M') }}

<!-- After -->
{{ user.last_login | singapore_time | default('N/A') }}
```

### 4. Usage in Templates

To display any datetime field in Singapore time, use the filter:

```html
{{ datetime_field | singapore_time }}
```

This will automatically convert UTC stored times to Singapore timezone for display.

## Benefits

1. **User-friendly**: All times shown match Singapore local time
2. **Consistent**: Data stored in UTC maintains database consistency
3. **Automatic**: Template filter handles conversion transparently
4. **Backward compatible**: Existing UTC data works with new timezone handling

## Testing

Run `test_timezone.py` to verify timezone functionality is working correctly.