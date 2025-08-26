# iOS Audit Feature Implementation Prompt

## Overview
You are tasked with implementing a comprehensive Inventory Audit feature for an iOS app. This feature allows users to conduct real-time inventory audits by scanning asset tags/QR codes and tracking progress through a mobile interface.

## Feature Requirements

### 1. Audit Management Screen
Create a main audit screen that displays:
- **Current audit status** (if one is running)
- **Start new audit** functionality with country selection
- **Real-time progress indicators** (completion percentage, asset counts)
- **Quick action buttons** (scan asset, view details, end audit)

### 2. Country Selection
Implement country selection for starting audits:
- Fetch available countries from API based on user permissions
- Present as picker/dropdown interface
- Validate selection before starting audit

### 3. Asset Scanning Interface
Build a barcode/QR code scanning interface:
- **Camera integration** for scanning asset tags and serial numbers
- **Manual input option** for entering asset identifiers
- **Real-time feedback** for scan results (success, already scanned, unexpected)
- **Visual/audio confirmation** for successful scans
- **Progress updates** after each scan

### 4. Progress Dashboard
Create a real-time progress dashboard showing:
- **Completion percentage** with progress bar
- **Asset counters** (total, scanned, missing, unexpected)
- **Visual status indicators** (green for complete, yellow for in-progress)
- **Tap-to-view** detailed asset lists

### 5. Asset Detail Views
Implement detailed asset list screens:
- **All Assets** - Complete expected inventory
- **Scanned Assets** - Successfully found assets
- **Missing Assets** - Not yet scanned expected assets
- **Unexpected Assets** - Found but not in expected inventory
- **Search/filter** functionality within lists

### 6. Audit Completion
Build audit completion workflow:
- **End audit confirmation** dialog
- **Final summary report** with statistics
- **Export/share options** for audit results
- **Navigation back to main screen**

## Technical Implementation

### API Integration
Integrate with the following REST API endpoints:

**Authentication:**
- Use JWT tokens in Authorization header: `Bearer <token>`

**Core Endpoints:**
```
GET /api/v1/audit/status - Get current audit status
GET /api/v1/audit/countries - Get available countries
POST /api/v1/audit/start - Start new audit session
POST /api/v1/audit/scan - Scan asset during audit
POST /api/v1/audit/end - End audit session
GET /api/v1/audit/details/{type} - Get asset details
```

### Data Models
Create Swift models for:

```swift
struct AuditSession {
    let id: String
    let country: String
    let totalAssets: Int
    let scannedCount: Int
    let missingCount: Int
    let unexpectedCount: Int
    let completionPercentage: Double
    let startedAt: Date
    let startedBy: Int
    let isActive: Bool
}

struct Asset {
    let id: Int
    let assetTag: String
    let serialNum: String?
    let name: String
    let model: String?
    let status: String
    let location: String?
    let company: String?
}

struct ScanResult {
    let status: ScanStatus // .foundExpected, .unexpected
    let message: String
    let asset: Asset?
    let progress: AuditProgress
}

struct AuditProgress {
    let totalAssets: Int
    let scannedCount: Int
    let unexpectedCount: Int
    let completionPercentage: Double
}
```

### Network Layer
Implement robust networking:
- **APIClient** with JWT token management
- **Async/await** for API calls
- **Error handling** for network failures and API errors
- **Retry logic** for failed requests
- **Progress tracking** for long-running operations

### UI Components

**Main Audit Screen:**
- Use `NavigationView` with toolbar
- `VStack` layout with status cards
- `Button` components for primary actions
- `ProgressView` for completion percentage

**Scanning Interface:**
- `AVCaptureSession` for camera scanning
- `TextField` for manual input
- `Alert` dialogs for scan feedback
- `HapticFeedback` for user confirmation

**Asset Lists:**
- `List` with `LazyVStack` for performance
- `SearchBar` for filtering
- `Section` headers for grouping
- Pull-to-refresh functionality

**Progress Dashboard:**
- `CircularProgressView` or `ProgressView`
- `HStack` with counter cards
- Tap gestures for navigation
- Real-time updates with `Timer`

### State Management
Use SwiftUI state management:
- `@StateObject` for audit view model
- `@Published` properties for reactive updates
- `@State` for local UI state
- `ObservableObject` protocol for data classes

### Error Handling
Implement comprehensive error handling:
- **Network errors** (no internet, timeout)
- **API errors** (authentication, permissions, validation)
- **Scanning errors** (camera access, invalid codes)
- **User-friendly error messages** with retry options

### Offline Support (Optional)
Consider offline capabilities:
- **Local caching** of audit data
- **Queue failed scans** for retry when online
- **Sync mechanism** when connection restored

## User Experience Guidelines

### Visual Design
- **Clean, professional interface** matching app design system
- **Large touch targets** for easy scanning workflow
- **High contrast colors** for scan result feedback
- **Progress indicators** throughout long operations

### Interactions
- **Intuitive navigation** between screens
- **Swipe gestures** for common actions
- **Voice feedback** for accessibility
- **Confirmation dialogs** for destructive actions

### Performance
- **Smooth animations** for state transitions
- **Lazy loading** for large asset lists
- **Background processing** for API calls
- **Memory management** for camera operations

### Accessibility
- **VoiceOver support** for all UI elements
- **Dynamic Type** support for text scaling
- **High contrast mode** compatibility
- **Reduced motion** support

## Implementation Steps

1. **Setup Project Structure**
   - Create audit feature module
   - Setup API client and models
   - Configure camera permissions

2. **Build Core UI**
   - Main audit screen layout
   - Country selection interface
   - Basic navigation flow

3. **Implement API Integration**
   - Network layer with JWT auth
   - Audit session management
   - Error handling and retries

4. **Add Scanning Functionality**
   - Camera integration
   - Barcode/QR code detection
   - Manual input alternative

5. **Build Progress Tracking**
   - Real-time status updates
   - Progress visualization
   - Asset counter displays

6. **Create Detail Views**
   - Asset list screens
   - Search and filter functionality
   - Navigation between lists

7. **Complete Audit Flow**
   - End audit functionality
   - Summary reports
   - Export capabilities

8. **Testing & Polish**
   - Unit tests for business logic
   - UI tests for critical flows
   - Performance optimization
   - Accessibility validation

## Example API Usage

```swift
class AuditService: ObservableObject {
    @Published var currentAudit: AuditSession?
    @Published var isLoading = false
    
    func startAudit(country: String) async throws {
        isLoading = true
        defer { isLoading = false }
        
        let request = StartAuditRequest(country: country)
        let response = try await apiClient.post("/audit/start", body: request)
        self.currentAudit = response.data.audit
    }
    
    func scanAsset(identifier: String) async throws -> ScanResult {
        let request = ScanAssetRequest(identifier: identifier)
        let response = try await apiClient.post("/audit/scan", body: request)
        return response.data
    }
}
```

## Deliverables

1. **Complete iOS app module** with audit functionality
2. **Unit tests** for business logic and API integration
3. **UI tests** for critical user flows
4. **Documentation** for setup and usage
5. **Demo video** showing complete audit workflow

## Success Criteria

- Users can successfully start, conduct, and complete inventory audits
- Real-time progress tracking works smoothly
- Camera scanning is responsive and accurate
- All API endpoints integrate correctly
- Error handling provides clear user feedback
- Interface is intuitive and accessible
- Performance is smooth on target devices

This feature should provide a seamless, professional inventory auditing experience that integrates perfectly with the existing backend system.