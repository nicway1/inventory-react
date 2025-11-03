# Mobile App: Implement Inventory Filters

## Task Overview
Implement comprehensive filtering functionality for the inventory screen in the mobile app. Users should be able to filter assets by multiple criteria to quickly find specific items.

## Current API Endpoint
**Endpoint**: `GET /api/mobile/v1/inventory`

**Current Query Parameters**:
- `page` - Page number (default: 1)
- `limit` - Items per page (default: 20, max: 100)
- `status` - Asset status filter (e.g., "DEPLOYED", "IN_STOCK")
- `search` - Text search (searches: name, asset_tag, serial_num, model)

## Required Filter Implementation

### 1. Backend API Enhancement
The backend already supports some filters. You need to add support for additional filter parameters:

**New Query Parameters to Add**:
```
GET /api/mobile/v1/inventory?
  page=1&
  limit=20&
  status=DEPLOYED&
  search=laptop&
  manufacturer=Apple&
  category=Laptop&
  country=Singapore&
  asset_type=Hardware&
  location_id=5&
  has_assignee=true
```

**Filter Parameters**:
- `status` - Asset status (IN_STOCK, READY_TO_DEPLOY, SHIPPED, DEPLOYED, REPAIR, ARCHIVED, DISPOSED)
- `search` - Text search across multiple fields
- `manufacturer` - Filter by manufacturer (e.g., "Apple", "Dell", "HP")
- `category` - Filter by category (e.g., "Laptop", "Desktop", "Monitor")
- `country` - Filter by country
- `asset_type` - Filter by asset type
- `location_id` - Filter by location ID
- `has_assignee` - Boolean, true to show only assigned assets, false for unassigned

### 2. Available Asset Fields for Filtering
Based on the Asset model, these fields are available:

**Core Fields**:
- `status` - Asset status enum (IN_STOCK, READY_TO_DEPLOY, SHIPPED, DEPLOYED, REPAIR, ARCHIVED, DISPOSED)
- `manufacturer` - String (e.g., "Apple", "Dell", "HP", "Lenovo")
- `category` - String (e.g., "Laptop", "Desktop", "Monitor", "Tablet")
- `country` - String (e.g., "Singapore", "USA", "UK")
- `asset_type` - String
- `location_id` - Integer (foreign key to locations table)
- `assigned_to_id` - Integer (foreign key to users table)
- `customer_id` - Integer (foreign key to customer_users table)
- `company_id` - Integer (foreign key to companies table)

**Additional Fields** (can be used for advanced filters):
- `hardware_type` - String
- `condition` - String (e.g., "New", "Good", "Fair", "Poor")
- `keyboard` - String (keyboard layout)
- `cpu_type` - String
- `memory` - String (RAM size)
- `harddrive` - String (storage size)

### 3. Mobile UI Requirements

#### Filter Button
- Add a "Filter" icon button in the app bar of the inventory screen
- Icon: Use a filter/funnel icon
- Position: Top right of the screen, next to search

#### Filter Sheet/Modal
When user taps the filter button, show a bottom sheet or modal with:

**Filter Sections**:

1. **Status** (Dropdown/Chips)
   - All Statuses (default)
   - In Stock
   - Ready to Deploy
   - Shipped
   - Deployed
   - Repair
   - Archived
   - Disposed

2. **Manufacturer** (Dropdown/Autocomplete)
   - Fetch unique manufacturers from API or predefined list:
     - Apple
     - Dell
     - HP
     - Lenovo
     - Microsoft
     - Samsung
     - Asus
     - Acer
     - Other

3. **Category** (Chips/Buttons)
   - All Categories (default)
   - Laptop
   - Desktop
   - Monitor
   - Tablet
   - Phone
   - Accessory
   - Other

4. **Country** (Dropdown)
   - All Countries (default)
   - Singapore
   - USA
   - UK
   - Malaysia
   - India
   - Other (fetch from API if available)

5. **Assignment Status** (Toggle/Switch)
   - All Assets (default)
   - Assigned Only
   - Unassigned Only

6. **Location** (Dropdown - Optional)
   - Fetch from API: `GET /api/mobile/v1/locations`
   - Show location name
   - Store location_id for filtering

**Filter Actions**:
- **Apply Filters** button - Applies selected filters and closes the sheet
- **Clear All** button - Resets all filters to default
- **Close/Cancel** button - Closes sheet without applying changes

#### Active Filter Indicator
- Show badge/chip count on filter button when filters are active
- Display active filters as removable chips below the search bar
- Each chip shows "Field: Value" (e.g., "Status: Deployed")
- Tapping chip removes that specific filter

#### Filter Persistence
- Save filter state locally (SharedPreferences/AsyncStorage)
- Restore filters when user returns to inventory screen
- Clear filters only when user explicitly taps "Clear All"

### 4. Mobile Implementation Guide

#### State Management
```dart
// Example state structure (Flutter/Dart)
class InventoryFilters {
  String? status;
  String? manufacturer;
  String? category;
  String? country;
  String? assetType;
  int? locationId;
  bool? hasAssignee; // null = all, true = assigned only, false = unassigned only

  Map<String, String> toQueryParams() {
    Map<String, String> params = {};
    if (status != null) params['status'] = status!;
    if (manufacturer != null) params['manufacturer'] = manufacturer!;
    if (category != null) params['category'] = category!;
    if (country != null) params['country'] = country!;
    if (assetType != null) params['asset_type'] = assetType!;
    if (locationId != null) params['location_id'] = locationId.toString();
    if (hasAssignee != null) params['has_assignee'] = hasAssignee.toString();
    return params;
  }
}
```

#### API Call Example
```dart
Future<void> fetchInventory({
  int page = 1,
  int limit = 20,
  String? search,
  InventoryFilters? filters,
}) async {
  final queryParams = {
    'page': page.toString(),
    'limit': limit.toString(),
    if (search != null && search.isNotEmpty) 'search': search,
    ...?filters?.toQueryParams(),
  };

  final response = await apiClient.get(
    '/api/mobile/v1/inventory',
    queryParameters: queryParams,
  );

  // Handle response...
}
```

#### UI Components Needed
1. **FilterSheet Widget** - Bottom sheet or modal with all filter options
2. **FilterButton Widget** - App bar button with badge
3. **FilterChip Widget** - Removable chips showing active filters
4. **StatusDropdown** - Dropdown for status selection
5. **ManufacturerDropdown** - Dropdown with autocomplete
6. **CategoryChips** - Horizontal scrollable chips for categories
7. **CountryDropdown** - Country selection dropdown
8. **AssignmentToggle** - Three-state toggle (All/Assigned/Unassigned)

### 5. Backend Code Changes Required

Update `/routes/mobile_api.py` in the `get_inventory()` function:

```python
# Add these additional filter parameters
manufacturer_filter = request.args.get('manufacturer', None)
category_filter = request.args.get('category', None)
country_filter = request.args.get('country', None)
asset_type_filter = request.args.get('asset_type', None)
location_id_filter = request.args.get('location_id', None, type=int)
has_assignee_filter = request.args.get('has_assignee', None)

# Apply manufacturer filter
if manufacturer_filter:
    query = query.filter(Asset.manufacturer.ilike(f"%{manufacturer_filter}%"))

# Apply category filter
if category_filter:
    query = query.filter(Asset.category.ilike(f"%{category_filter}%"))

# Apply country filter
if country_filter:
    query = query.filter(Asset.country == country_filter)

# Apply asset_type filter
if asset_type_filter:
    query = query.filter(Asset.asset_type == asset_type_filter)

# Apply location filter
if location_id_filter:
    query = query.filter(Asset.location_id == location_id_filter)

# Apply assignee filter
if has_assignee_filter is not None:
    if has_assignee_filter.lower() == 'true':
        query = query.filter(Asset.assigned_to_id.isnot(None))
    elif has_assignee_filter.lower() == 'false':
        query = query.filter(Asset.assigned_to_id.is_(None))
```

### 6. Optional Enhancement: Filter Options Endpoint

Create a new endpoint to get available filter options dynamically:

```python
@mobile_api_bp.route('/inventory/filter-options', methods=['GET'])
@mobile_auth_required
def get_inventory_filter_options():
    """
    Get available filter options for inventory

    Response: {
        "success": true,
        "options": {
            "statuses": ["IN_STOCK", "DEPLOYED", ...],
            "manufacturers": ["Apple", "Dell", ...],
            "categories": ["Laptop", "Desktop", ...],
            "countries": ["Singapore", "USA", ...],
            "locations": [{"id": 1, "name": "Warehouse A"}, ...]
        }
    }
    """
```

### 7. User Experience Best Practices

1. **Performance**:
   - Show loading indicator while fetching filtered results
   - Implement debouncing for text search
   - Cache filter options locally

2. **Feedback**:
   - Show "No results found" message when filters return empty
   - Display result count: "Showing 25 of 150 assets"
   - Show active filter count on filter button

3. **Accessibility**:
   - Ensure all filter controls are accessible
   - Provide clear labels for all inputs
   - Support keyboard navigation

4. **Mobile-Friendly**:
   - Use native pickers when appropriate
   - Ensure filter sheet is scrollable on small screens
   - Use chips for easy filter removal
   - Swipe down to dismiss filter sheet

### 8. Testing Checklist

- [ ] Filter by each individual field works correctly
- [ ] Multiple filters can be combined
- [ ] "Clear All" resets all filters
- [ ] Active filters persist across screen navigation
- [ ] Filter badge shows correct count
- [ ] Filter chips can be individually removed
- [ ] Empty state shows when no results match filters
- [ ] Pagination works correctly with filters applied
- [ ] Search works in combination with filters
- [ ] Performance is acceptable with all filters applied

### 9. API Response Format

The response format remains the same as current:

```json
{
  "success": true,
  "assets": [
    {
      "id": 123,
      "asset_tag": "LAP001",
      "name": "MacBook Pro",
      "model": "MacBook Pro 16-inch 2023",
      "serial_num": "ABC123XYZ",
      "status": "DEPLOYED",
      "asset_type": "Hardware",
      "manufacturer": "Apple",
      "location": "Singapore Office",
      "country": "Singapore",
      "assigned_to": {
        "id": 45,
        "name": "John Doe",
        "email": "john@example.com"
      },
      "customer_user": null
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 150,
    "pages": 8
  }
}
```

## Summary

Implement a comprehensive filtering system for the mobile inventory screen that:
1. Adds backend support for multiple filter parameters
2. Creates an intuitive filter UI with bottom sheet/modal
3. Shows active filters as removable chips
4. Persists filter state locally
5. Provides clear visual feedback
6. Maintains good performance with pagination

This will significantly improve the user experience when searching for specific assets in large inventories.
