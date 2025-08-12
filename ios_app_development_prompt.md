# iOS App Development Prompt: Inventory Management System

## Project Overview
Create a native iOS app using SwiftUI and UIKit that integrates with our existing Flask-based inventory management system. The app should provide mobile access to user authentication, tickets, and inventory management functionality.

## Core Features Required

### 1. User Authentication & Profile
- **Login Screen**: Clean, professional login interface
- **User Profile Display**: Show logged-in user's name and role prominently
- **JWT Token Management**: Secure token storage and automatic refresh
- **Logout Functionality**: Clear session and return to login

### 2. Dashboard
- **Welcome Screen**: Display user name and role after login
- **Quick Stats**: Show ticket counts and inventory summary
- **Navigation Cards**: Easy access to main app sections

### 3. Ticket Management
- **Ticket List**: Browse all accessible tickets with pagination
- **Ticket Details**: View comprehensive ticket information
- **Status Filtering**: Filter tickets by status (OPEN, IN_PROGRESS, RESOLVED, etc.)
- **Search Functionality**: Search tickets by subject or description

### 4. Inventory Access
- **Asset List**: Browse inventory items with search and filtering
- **Asset Details**: View detailed asset information
- **Status Filtering**: Filter by asset status (DEPLOYED, READY_TO_DEPLOY, etc.)
- **Search Functionality**: Search by asset tag, name, model, or serial number

## API Endpoints Documentation

### Base URL
```
Production: https://inventory.truelog.com.sg
Development: http://127.0.0.1:5006
```

### API Authentication
All API requests require an API key header:
```
X-API-Key: xAQhm3__ZH6MvRIPMIBSDRAsIa1w2Slh5uaCtc4NurM
Authorization: Bearer <jwt_token>  (for authenticated endpoints)
```

### Authentication Endpoints

#### 1. Mobile Login
**POST** `/auth/login`

**Headers:**
```
X-API-Key: xAQhm3__ZH6MvRIPMIBSDRAsIa1w2Slh5uaCtc4NurM
Content-Type: application/json
```

**Request Body:**
```json
{
    "username": "user@example.com",
    "password": "password123"
}
```

**Success Response (200):**
```json
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "user": {
        "id": 1,
        "username": "user@example.com",
        "email": "user@example.com",
        "role": "supervisor",
        "first_name": "John",
        "last_name": "Doe",
        "is_active": true,
        "created_at": "2025-01-15T10:30:00.000Z",
        "last_login": "2025-01-15T15:45:00.000Z"
    }
}
```

**Error Response (401):**
```json
{
    "error": "Invalid credentials"
}
```

#### 2. Get Current User Info
**GET** `/auth/me`

**Headers:**
```
X-API-Key: xAQhm3__ZH6MvRIPMIBSDRAsIa1w2Slh5uaCtc4NurM
Authorization: Bearer <jwt_token>
```

**Success Response (200):**
```json
{
    "id": 1,
    "username": "user@example.com",
    "email": "user@example.com",
    "role": "supervisor",
    "first_name": "John",
    "last_name": "Doe",
    "is_active": true,
    "created_at": "2025-01-15T10:30:00.000Z",
    "last_login": "2025-01-15T15:45:00.000Z"
}
```

### Ticket Management Endpoints

#### 3. Get User Tickets
**GET** `/tickets?page=1&limit=20&status=open`

**Headers:**
```
X-API-Key: xAQhm3__ZH6MvRIPMIBSDRAsIa1w2Slh5uaCtc4NurM
Authorization: Bearer <jwt_token>
```

**Query Parameters:**
- `page` (optional): Page number (default: 1)
- `limit` (optional): Items per page (default: 20)
- `status` (optional): Filter by status (open, in_progress, resolved, etc.)

**Success Response (200):**
```json
{
    "tickets": [
        {
            "id": 123,
            "title": "Laptop replacement request",
            "description": "Need replacement for damaged laptop...",
            "status": "open",
            "priority": "high",
            "category": "hardware",
            "assigned_to": 1,
            "assigned_to_name": "John Doe",
            "created_by": 2,
            "created_by_name": "Jane Smith",
            "created_at": "2025-01-15T10:30:00.000Z",
            "updated_at": "2025-01-15T15:45:00.000Z",
            "due_date": "2025-01-20T17:00:00.000Z",
            "resolved_at": null,
            "tags": ["urgent", "hardware"]
        }
    ],
    "total": 45,
    "page": 1,
    "per_page": 20,
    "total_pages": 3
}
```

### Inventory Management Endpoints

#### 4. Get Inventory Assets
**GET** `/inventory?page=1&limit=20&category=computers&search=laptop`

**Headers:**
```
X-API-Key: xAQhm3__ZH6MvRIPMIBSDRAsIa1w2Slh5uaCtc4NurM
Authorization: Bearer <jwt_token>
```

**Query Parameters:**
- `page` (optional): Page number (default: 1)
- `limit` (optional): Items per page (default: 20)
- `search` (optional): Search term for name, description, serial number
- `category` (optional): Filter by asset category

**Success Response (200):**
```json
{
    "assets": [
        {
            "id": 456,
            "name": "MacBook Pro 16\"",
            "description": "Latest MacBook Pro for development work",
            "serial_number": "C02XD123LVDL",
            "model": "MacBook Pro 16-inch",
            "manufacturer": "Apple",
            "category": "computers",
            "status": "assigned",
            "location": "New York Office",
            "assigned_to": 2,
            "assigned_to_name": "Jane Smith",
            "purchase_date": "2024-01-15",
            "purchase_price": 2499.99,
            "warranty_expiry": "2026-01-15",
            "created_at": "2024-01-15T10:30:00.000Z",
            "updated_at": "2024-01-15T15:45:00.000Z",
            "tags": ["development", "high-priority"]
        }
    ],
    "total": 150,
    "page": 1,
    "per_page": 20,
    "total_pages": 8
}
```

### Dashboard Endpoint

#### 5. Get Dashboard Statistics
**GET** `/dashboard`

**Headers:**
```
X-API-Key: xAQhm3__ZH6MvRIPMIBSDRAsIa1w2Slh5uaCtc4NurM
Authorization: Bearer <jwt_token>
```

**Success Response (200):**
```json
{
    "total_tickets": 50,
    "open_tickets": 25,
    "in_progress_tickets": 15,
    "resolved_tickets": 10,
    "total_assets": 100,
    "available_assets": 60,
    "assigned_assets": 35,
    "maintenance_assets": 5,
    "recent_activity": [
        {
            "id": 1,
            "type": "ticket_created",
            "title": "New laptop request",
            "user": "Jane Smith",
            "timestamp": "2025-01-15T10:30:00.000Z"
        },
        {
            "id": 2,
            "type": "asset_assigned",
            "title": "MacBook Pro assigned to John Doe",
            "user": "Admin",
            "timestamp": "2025-01-15T09:15:00.000Z"
        }
    ]
}
```

## Technical Implementation Guidelines

### Architecture
- **MVVM Pattern**: Use Model-View-ViewModel architecture
- **SwiftUI**: Primary UI framework for modern interface
- **Combine**: For reactive programming and data binding
- **Core Data**: For local data persistence and offline support

### Security Requirements
- **Keychain Storage**: Store JWT tokens securely in iOS Keychain
- **SSL Pinning**: Implement certificate pinning for production
- **Token Refresh**: Automatic token refresh before expiration
- **Logout Cleanup**: Clear all stored credentials on logout

### Networking
- **URLSession**: Use native networking with proper error handling
- **JSON Codable**: Implement Codable protocols for all API models
- **Pagination**: Handle paginated responses efficiently
- **Offline Support**: Cache data for offline viewing

### UI/UX Guidelines
- **iOS Design Guidelines**: Follow Apple's Human Interface Guidelines
- **Dark Mode**: Support both light and dark themes
- **Accessibility**: Full VoiceOver and accessibility support
- **Loading States**: Show appropriate loading indicators
- **Error Handling**: User-friendly error messages

### Code Structure
```
InventoryApp/
├── Models/
│   ├── User.swift
│   ├── Ticket.swift
│   ├── Asset.swift
│   └── APIResponse.swift
├── ViewModels/
│   ├── AuthViewModel.swift
│   ├── TicketViewModel.swift
│   └── InventoryViewModel.swift
├── Views/
│   ├── LoginView.swift
│   ├── DashboardView.swift
│   ├── TicketListView.swift
│   └── InventoryView.swift
├── Services/
│   ├── APIService.swift
│   ├── AuthService.swift
│   └── KeychainService.swift
└── Utils/
    ├── Constants.swift
    └── Extensions.swift
```

### Sample API Service Implementation

#### APIService.swift
```swift
import Foundation

class APIService: ObservableObject {
    static let shared = APIService()
    private let baseURL = "https://inventory.truelog.com.sg"
    private let apiKey = "xAQhm3__ZH6MvRIPMIBSDRAsIa1w2Slh5uaCtc4NurM"
    
    private init() {}
    
    // MARK: - Authentication
    func login(username: String, password: String) async throws -> LoginResponse {
        let url = URL(string: "\(baseURL)/auth/login")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.addValue(apiKey, forHTTPHeaderField: "X-API-Key")
        request.addValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let loginData = ["username": username, "password": password]
        request.httpBody = try JSONSerialization.data(withJSONObject: loginData)
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        
        if httpResponse.statusCode == 401 {
            throw APIError.invalidCredentials
        }
        
        guard httpResponse.statusCode == 200 else {
            throw APIError.serverError(httpResponse.statusCode)
        }
        
        return try JSONDecoder().decode(LoginResponse.self, from: data)
    }
    
    func getCurrentUser() async throws -> User {
        guard let token = KeychainService.shared.getToken() else {
            throw APIError.noToken
        }
        
        let url = URL(string: "\(baseURL)/auth/me")!
        var request = URLRequest(url: url)
        request.addValue(apiKey, forHTTPHeaderField: "X-API-Key")
        request.addValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        
        guard httpResponse.statusCode == 200 else {
            throw APIError.serverError(httpResponse.statusCode)
        }
        
        return try JSONDecoder().decode(User.self, from: data)
    }
    
    // MARK: - Tickets
    func getTickets(page: Int = 1, limit: Int = 20, status: String? = nil) async throws -> TicketsResponse {
        var urlComponents = URLComponents(string: "\(baseURL)/tickets")!
        urlComponents.queryItems = [
            URLQueryItem(name: "page", value: "\(page)"),
            URLQueryItem(name: "limit", value: "\(limit)")
        ]
        
        if let status = status {
            urlComponents.queryItems?.append(URLQueryItem(name: "status", value: status))
        }
        
        guard let url = urlComponents.url else {
            throw APIError.invalidURL
        }
        
        var request = URLRequest(url: url)
        request.addValue(apiKey, forHTTPHeaderField: "X-API-Key")
        request.addValue("Bearer \(KeychainService.shared.getToken() ?? "")", forHTTPHeaderField: "Authorization")
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        
        guard httpResponse.statusCode == 200 else {
            throw APIError.serverError(httpResponse.statusCode)
        }
        
        return try JSONDecoder().decode(TicketsResponse.self, from: data)
    }
    
    // MARK: - Assets
    func getAssets(page: Int = 1, limit: Int = 20, search: String? = nil, category: String? = nil) async throws -> AssetsResponse {
        var urlComponents = URLComponents(string: "\(baseURL)/inventory")!
        urlComponents.queryItems = [
            URLQueryItem(name: "page", value: "\(page)"),
            URLQueryItem(name: "limit", value: "\(limit)")
        ]
        
        if let search = search, !search.isEmpty {
            urlComponents.queryItems?.append(URLQueryItem(name: "search", value: search))
        }
        
        if let category = category {
            urlComponents.queryItems?.append(URLQueryItem(name: "category", value: category))
        }
        
        guard let url = urlComponents.url else {
            throw APIError.invalidURL
        }
        
        var request = URLRequest(url: url)
        request.addValue(apiKey, forHTTPHeaderField: "X-API-Key")
        request.addValue("Bearer \(KeychainService.shared.getToken() ?? "")", forHTTPHeaderField: "Authorization")
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        
        guard httpResponse.statusCode == 200 else {
            throw APIError.serverError(httpResponse.statusCode)
        }
        
        return try JSONDecoder().decode(AssetsResponse.self, from: data)
    }
    
    // MARK: - Dashboard
    func getDashboard() async throws -> DashboardResponse {
        let url = URL(string: "\(baseURL)/dashboard")!
        var request = URLRequest(url: url)
        request.addValue(apiKey, forHTTPHeaderField: "X-API-Key")
        request.addValue("Bearer \(KeychainService.shared.getToken() ?? "")", forHTTPHeaderField: "Authorization")
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        
        guard httpResponse.statusCode == 200 else {
            throw APIError.serverError(httpResponse.statusCode)
        }
        
        return try JSONDecoder().decode(DashboardResponse.self, from: data)
    }
}

// MARK: - API Error Types
enum APIError: Error, LocalizedError {
    case invalidURL
    case invalidResponse
    case invalidCredentials
    case noToken
    case serverError(Int)
    case decodingError
    
    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid URL"
        case .invalidResponse:
            return "Invalid response from server"
        case .invalidCredentials:
            return "Invalid username or password"
        case .noToken:
            return "No authentication token found"
        case .serverError(let code):
            return "Server error with code: \(code)"
        case .decodingError:
            return "Failed to decode server response"
        }
    }
}
```

#### KeychainService.swift
```swift
import Foundation
import Security

class KeychainService {
    static let shared = KeychainService()
    private let service = "InventoryApp"
    private let accessTokenKey = "access_token"
    private let refreshTokenKey = "refresh_token"
    
    private init() {}
    
    func saveTokens(accessToken: String, refreshToken: String) {
        saveToKeychain(key: accessTokenKey, value: accessToken)
        saveToKeychain(key: refreshTokenKey, value: refreshToken)
    }
    
    func getToken() -> String? {
        return getFromKeychain(key: accessTokenKey)
    }
    
    func getRefreshToken() -> String? {
        return getFromKeychain(key: refreshTokenKey)
    }
    
    func clearTokens() {
        deleteFromKeychain(key: accessTokenKey)
        deleteFromKeychain(key: refreshTokenKey)
    }
    
    private func saveToKeychain(key: String, value: String) {
        let data = value.data(using: .utf8)!
        
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key,
            kSecValueData as String: data
        ]
        
        SecItemDelete(query as CFDictionary)
        SecItemAdd(query as CFDictionary, nil)
    }
    
    private func getFromKeychain(key: String) -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key,
            kSecReturnData as String: true
        ]
        
        var result: AnyObject?
        SecItemCopyMatching(query as CFDictionary, &result)
        
        if let data = result as? Data {
            return String(data: data, encoding: .utf8)
        }
        
        return nil
    }
    
    private func deleteFromKeychain(key: String) {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key
        ]
        
        SecItemDelete(query as CFDictionary)
    }
}
```

### Sample Models

#### User Model
```swift
struct LoginResponse: Codable {
    let accessToken: String
    let refreshToken: String
    let user: User
    
    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case refreshToken = "refresh_token"
        case user
    }
}

struct User: Codable, Identifiable {
    let id: Int
    let username: String
    let email: String
    let role: String
    let firstName: String?
    let lastName: String?
    let isActive: Bool
    let createdAt: String
    let lastLogin: String?
    
    enum CodingKeys: String, CodingKey {
        case id, username, email, role
        case firstName = "first_name"
        case lastName = "last_name"
        case isActive = "is_active"
        case createdAt = "created_at"
        case lastLogin = "last_login"
    }
    
    var fullName: String {
        return [firstName, lastName]
            .compactMap { $0 }
            .joined(separator: " ")
    }
}
```

#### Ticket Model
```swift
struct TicketsResponse: Codable {
    let tickets: [Ticket]
    let total: Int
    let page: Int
    let perPage: Int
    let totalPages: Int
    
    enum CodingKeys: String, CodingKey {
        case tickets, total, page
        case perPage = "per_page"
        case totalPages = "total_pages"
    }
}

struct Ticket: Codable, Identifiable {
    let id: Int
    let title: String
    let description: String
    let status: String
    let priority: String
    let category: String
    let assignedTo: Int?
    let assignedToName: String?
    let createdBy: Int
    let createdByName: String
    let createdAt: String
    let updatedAt: String
    let dueDate: String?
    let resolvedAt: String?
    let tags: [String]
    
    enum CodingKeys: String, CodingKey {
        case id, title, description, status, priority, category, tags
        case assignedTo = "assigned_to"
        case assignedToName = "assigned_to_name"
        case createdBy = "created_by"
        case createdByName = "created_by_name"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
        case dueDate = "due_date"
        case resolvedAt = "resolved_at"
    }
}
```

#### Asset Model
```swift
struct AssetsResponse: Codable {
    let assets: [Asset]
    let total: Int
    let page: Int
    let perPage: Int
    let totalPages: Int
    
    enum CodingKeys: String, CodingKey {
        case assets, total, page
        case perPage = "per_page"
        case totalPages = "total_pages"
    }
}

struct Asset: Codable, Identifiable {
    let id: Int
    let name: String
    let description: String
    let serialNumber: String
    let model: String
    let manufacturer: String
    let category: String
    let status: String
    let location: String
    let assignedTo: Int?
    let assignedToName: String?
    let purchaseDate: String?
    let purchasePrice: Double?
    let warrantyExpiry: String?
    let createdAt: String
    let updatedAt: String
    let tags: [String]
    
    enum CodingKeys: String, CodingKey {
        case id, name, description, model, manufacturer, category, status, location, tags
        case serialNumber = "serial_number"
        case assignedTo = "assigned_to"
        case assignedToName = "assigned_to_name"
        case purchaseDate = "purchase_date"
        case purchasePrice = "purchase_price"
        case warrantyExpiry = "warranty_expiry"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }
}
```

#### Dashboard Model
```swift
struct DashboardResponse: Codable {
    let totalTickets: Int
    let openTickets: Int
    let inProgressTickets: Int
    let resolvedTickets: Int
    let totalAssets: Int
    let availableAssets: Int
    let assignedAssets: Int
    let maintenanceAssets: Int
    let recentActivity: [ActivityItem]
    
    enum CodingKeys: String, CodingKey {
        case totalTickets = "total_tickets"
        case openTickets = "open_tickets"
        case inProgressTickets = "in_progress_tickets"
        case resolvedTickets = "resolved_tickets"
        case totalAssets = "total_assets"
        case availableAssets = "available_assets"
        case assignedAssets = "assigned_assets"
        case maintenanceAssets = "maintenance_assets"
        case recentActivity = "recent_activity"
    }
}

struct ActivityItem: Codable, Identifiable {
    let id: Int
    let type: String
    let title: String
    let user: String
    let timestamp: String
}
```

### Authentication Flow
1. **Login Screen**: User enters credentials
2. **API Call**: POST to `/auth/login` with API key header
3. **Token Storage**: Store access_token and refresh_token in Keychain
4. **User Info**: Extract user data from login response
5. **Dashboard**: Navigate to main app interface
6. **Token Validation**: Check token on app launch
7. **Auto-Login**: Skip login if valid token exists
8. **API Headers**: Include both X-API-Key and Authorization headers in all requests

### Error Handling
- **Network Errors**: Handle connectivity issues gracefully
- **API Errors**: Parse and display server error messages
- **Token Expiry**: Automatic logout and re-login prompt
- **Validation**: Client-side input validation

### Testing Requirements
- **Unit Tests**: Test all ViewModels and Services
- **Integration Tests**: Test API integration
- **UI Tests**: Test critical user flows
- **Performance Tests**: Test app performance with large datasets

## Development Phases

### Phase 1: Core Authentication
- Login/logout functionality
- Token management
- User profile display

### Phase 2: Basic Navigation
- Dashboard with user info
- Main navigation structure
- Settings screen

### Phase 3: Ticket Management
- Ticket list with pagination
- Ticket detail view
- Search and filtering

### Phase 4: Inventory Access
- Asset list with pagination
- Asset detail view
- Search and filtering

### Phase 5: Polish & Testing
- Error handling refinement
- Performance optimization
- Comprehensive testing
- App Store preparation

## Success Criteria
- ✅ Secure authentication with JWT tokens
- ✅ Display user name and role prominently
- ✅ Browse and search tickets effectively
- ✅ Access and browse inventory assets
- ✅ Responsive UI following iOS guidelines
- ✅ Proper error handling and loading states
- ✅ Offline data caching where appropriate
- ✅ Full accessibility support

This comprehensive guide provides everything needed to develop a professional iOS app that integrates seamlessly with your existing inventory management system.