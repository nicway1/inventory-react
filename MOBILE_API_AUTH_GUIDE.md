# Mobile API Authentication Guide

## **Issue Resolution: 401 Unauthorized Errors**

**Root Cause:** The mobile API uses a **different authentication system** than regular API endpoints.

---

## **Mobile API Authentication (CORRECT METHOD)**

### **Step 1: Get Mobile JWT Token**
**Endpoint:** `POST /api/mobile/v1/auth/login`

**Request:**
```json
{
  "username": "user@example.com",
  "password": "userpassword"
}
```

**Response:**
```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 123,
    "username": "user@example.com",
    "name": "user@example.com",
    "user_type": "SUPERVISOR",
    "email": "user@example.com",
    "is_admin": false,
    "is_supervisor": true,
    "permissions": {
      "can_view_inventory": true,
      "can_edit_tickets": true,
      "can_delete_tickets": false
    }
  }
}
```

### **Step 2: Use JWT Token for All Mobile API Calls**
**Headers for ALL mobile API endpoints:**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json
```

**❌ INCORRECT (What you were using):**
```
Authorization: Bearer xAQhm3__ZH6MvRIPMIBSDRAsIa1w2Slh5uaCtc4NurM
X-User-Token: Bearer {user_session_token}
```

**❌ ALSO INCORRECT:**
```
X-API-Key: xAQhm3__ZH6MvRIPMIBSDRAsIa1w2Slh5uaCtc4NurM
Authorization: Bearer {user_session_token}
```

**✅ CORRECT:**
```
Authorization: Bearer {JWT_TOKEN_FROM_MOBILE_LOGIN}
```

---

## **Complete Authentication Flow Example**

### **1. Login to Get JWT Token**
```bash
curl -X POST https://inventory.truelog.com.sg/api/mobile/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'
```

**Response:**
```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJ1c2VybmFtZSI6ImFkbWluIiwidXNlcl90eXBlIjoiU1VQRVJfQURNSU4iLCJleHAiOjE3MzUxMjQzNjAsImlhdCI6MTczMjUzMjM2MH0.xyz123",
  "user": { ... }
}
```

### **2. Use JWT Token for Ticket Requests**
```bash
curl -X GET https://inventory.truelog.com.sg/api/mobile/v1/tickets \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJ1c2VybmFtZSI6ImFkbWluIiwidXNlcl90eXBlIjoiU1VQRVJfQURNSU4iLCJleHAiOjE3MzUxMjQzNjAsImlhdCI6MTczMjUzMjM2MH0.xyz123"
```

### **3. Get Ticket Details**
```bash
curl -X GET https://inventory.truelog.com.sg/api/mobile/v1/tickets/123 \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJ1c2VybmFtZSI6ImFkbWluIiwidXNlcl90eXBlIjoiU1VQRVJfQURNSU4iLCJleHAiOjE3MzUxMjQzNjAsImlhdCI6MTczMjUzMjM2MH0.xyz123"
```

---

## **Mobile vs Regular API Authentication**

| **API Type** | **Authentication Method** | **Header Format** |
|--------------|---------------------------|-------------------|
| **Mobile API** (`/api/mobile/v1/*`) | JWT Token from mobile login | `Authorization: Bearer {JWT_TOKEN}` |
| **Regular API** (`/api/*`) | API Key + Session Token | `X-API-Key: {API_KEY}` + `Authorization: Bearer {SESSION}` |
| **Web Interface** | Session Cookies | `Cookie: session=...` |

---

## **JWT Token Details**

- **Expiry:** 30 days from login
- **Algorithm:** HS256
- **Contains:** user_id, username, user_type, expiration
- **Refresh:** Login again when expired (no refresh endpoint yet)

---

## **iOS Implementation Guide**

### **1. Login Manager**
```swift
class MobileAuthManager {
    private let baseURL = "https://inventory.truelog.com.sg/api/mobile/v1"
    private var jwtToken: String?

    func login(username: String, password: String) async throws -> User {
        let url = URL(string: "\(baseURL)/auth/login")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let body = ["username": username, "password": password]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw AuthError.loginFailed
        }

        let loginResponse = try JSONDecoder().decode(LoginResponse.self, from: data)
        self.jwtToken = loginResponse.token

        return loginResponse.user
    }
}
```

### **2. API Request Helper**
```swift
extension MobileAuthManager {
    func authenticatedRequest(url: URL) -> URLRequest {
        var request = URLRequest(url: url)
        if let token = jwtToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        return request
    }
}
```

### **3. Ticket API Calls**
```swift
class TicketService {
    private let authManager: MobileAuthManager
    private let baseURL = "https://inventory.truelog.com.sg/api/mobile/v1"

    func getTickets() async throws -> [Ticket] {
        let url = URL(string: "\(baseURL)/tickets")!
        let request = authManager.authenticatedRequest(url: url)

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw APIError.unauthorized
        }

        let response = try JSONDecoder().decode(TicketsResponse.self, from: data)
        return response.tickets
    }

    func getTicketDetail(id: Int) async throws -> Ticket {
        let url = URL(string: "\(baseURL)/tickets/\(id)")!
        let request = authManager.authenticatedRequest(url: url)

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw APIError.unauthorized
        }

        let response = try JSONDecoder().decode(TicketDetailResponse.self, from: data)
        return response.ticket
    }
}
```

---

## **Error Handling**

### **Common 401 Errors:**
1. **Missing Authorization header** → Add `Authorization: Bearer {token}`
2. **Invalid JWT format** → Use token from mobile login response
3. **Expired JWT** → Login again to get new token
4. **Wrong authentication method** → Don't use API keys for mobile endpoints

### **Error Response:**
```json
{
  "error": "Missing or invalid authorization header"
}
```

---

## **Testing Commands**

### **Test Mobile Login:**
```bash
curl -X POST https://inventory.truelog.com.sg/api/mobile/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}' \
  | jq .
```

### **Test with JWT Token:**
```bash
# Replace TOKEN with actual JWT from login response
curl -X GET https://inventory.truelog.com.sg/api/mobile/v1/tickets \
  -H "Authorization: Bearer TOKEN" \
  | jq .
```

---

## **Summary for iOS Developer**

✅ **What you need to change:**

1. **Remove:** API key authentication for mobile endpoints
2. **Add:** Mobile login call to get JWT token
3. **Update:** All mobile API calls to use JWT Bearer token
4. **Store:** JWT token securely for subsequent requests

✅ **Correct flow:**
1. User logs in → Get JWT token
2. Store JWT token
3. Use JWT token for all `/api/mobile/v1/*` endpoints
4. Handle 401 errors by re-authenticating

The mobile API endpoints are working correctly - they just require the proper JWT authentication instead of API keys.

---

**API Team**