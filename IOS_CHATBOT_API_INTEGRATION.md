# iOS Chatbot API Integration Guide

---

## Implementation Prompt for iOS Developer

**Task:** Implement a Help Assistant Chatbot feature in the iOS app with a Claude/ChatGPT-style conversational UI.

**What to Build:**
1. A new "Help Assistant" chat screen accessible from the app's main navigation or settings
2. Modern chat interface with:
   - User messages (blue bubbles, right-aligned)
   - Assistant messages (gray cards, left-aligned with avatar)
   - Animated typing indicator (3 bouncing dots)
   - Floating input bar with send button
   - Suggestion chips for quick actions
   - Welcome screen with sample questions when chat is empty
3. Integration with the chatbot API endpoints (documented below)
4. Support for action confirmations (e.g., "Update ticket #123 to resolved?" with Confirm/Cancel buttons)
5. Chat history persistence (optional - API provides history endpoint)

**Authentication:** Use the same JWT token from user login (`/api/mobile/v1/auth/login`). Pass it as `Authorization: Bearer <token>` header.

**API Base Path:** `/chatbot/mobile/`

**Key Features:**
- Ask questions about tickets, assets, users, and system usage
- Execute actions via natural language (e.g., "Resolve ticket #123", "Assign ticket #456 to John")
- Look up assets by serial number
- Report bugs directly from chat
- Get contextual suggestions

**Design Reference:** Claude/ChatGPT style - clean, minimal, with smooth animations and markdown-style text rendering.

---

## Overview

This document provides complete instructions for integrating the Help Assistant Chatbot into the iOS application. The chatbot uses the same JWT authentication as the existing mobile API.

---

## Base URL

```
Production: https://your-server.com
Development: http://localhost:5000
```

---

## Authentication

The chatbot API uses JWT Bearer token authentication. Use the same token obtained from `/api/mobile/v1/auth/login`.

```
Authorization: Bearer <jwt_token>
```

---

## API Endpoints

### 1. Ask a Question

Send a user query and receive an intelligent response.

**Endpoint:** `POST /chatbot/mobile/ask`

**Headers:**
```
Content-Type: application/json
Authorization: Bearer <jwt_token>
```

**Request Body:**
```json
{
    "query": "How do I create a ticket?"
}
```

**Response Types:**

1. **Knowledge Base Answer:**
```json
{
    "success": true,
    "type": "answer",
    "answer": "To create a new ticket:\n\n1. Go to **Tickets** in the navigation\n2. Click the **+ New Ticket** button\n3. Select a ticket category (PIN Request, Asset Repair, etc.)\n4. Fill in the required fields\n5. Click **Create Ticket**",
    "matched_question": "How do I create a new ticket?",
    "url": "/tickets/create",
    "permission": "can_create_tickets",
    "suggestions": ["How do I view all tickets?", "How do I add a new asset?", "How do I report a bug?"]
}
```

2. **Action Confirmation (requires user confirmation before execution):**
```json
{
    "success": true,
    "type": "action_confirm",
    "action": "update_ticket_status",
    "ticket_id": 123,
    "ticket_subject": "Laptop keyboard not working",
    "current_status": "NEW",
    "new_status": "RESOLVED",
    "answer": "Do you want to update **Ticket #123** status to **RESOLVED**?\n\nTicket: Laptop keyboard not working\nCurrent Status: NEW"
}
```

3. **Greeting Response:**
```json
{
    "success": true,
    "type": "greeting",
    "answer": "Hello! I'm the Help Assistant. I can help you with:\n\n• **Tickets** - Creating, editing, tracking\n• **Inventory** - Assets, accessories, audits\n• **Admin** - Users, permissions, settings\n\nWhat would you like help with?"
}
```

4. **Asset Lookup Result:**
```json
{
    "success": true,
    "type": "answer",
    "answer": "**Asset Found**\n\n• **Asset Tag:** AT001\n• **Name:** MacBook Pro\n• **Serial Number:** ABC123\n• **Status:** DEPLOYED\n• **Model:** MacBook Pro 14\n• **Manufacturer:** Apple",
    "asset": {
        "id": 45,
        "asset_tag": "AT001",
        "name": "MacBook Pro",
        "serial_num": "ABC123",
        "status": "DEPLOYED",
        "model": "MacBook Pro 14",
        "manufacturer": "Apple"
    }
}
```

5. **Fallback (no matching answer):**
```json
{
    "success": true,
    "type": "fallback",
    "answer": "I'm not sure about that. Try asking about:\n• Custom ticket statuses\n• Creating tickets or assets\n• User permissions\n• Reports and analytics\n• System settings",
    "suggestions": ["How do I create a ticket?", "How do I add an asset?", "How do I report a bug?", "How do I view reports?", "Where are settings?"]
}
```

6. **Error Response:**
```json
{
    "success": true,
    "type": "error",
    "answer": "Ticket #999 not found."
}
```

---

### 2. Execute Action

After receiving an `action_confirm` response, use this endpoint to execute the action with user confirmation.

**Endpoint:** `POST /chatbot/mobile/execute`

**Headers:**
```
Content-Type: application/json
Authorization: Bearer <jwt_token>
```

**Request Body Examples:**

**Update Ticket Status:**
```json
{
    "action": "update_ticket_status",
    "ticket_id": 123,
    "new_status": "RESOLVED"
}
```

**Update Ticket Priority:**
```json
{
    "action": "update_ticket_priority",
    "ticket_id": 123,
    "new_priority": "HIGH"
}
```

**Assign Ticket:**
```json
{
    "action": "assign_ticket",
    "ticket_id": 123,
    "new_assignee_id": 45
}
```

**Report Bug:**
```json
{
    "action": "report_bug",
    "bug_title": "Login page not loading",
    "severity": "High",
    "bug_description": "Optional detailed description"
}
```

**Response:**
```json
{
    "success": true,
    "message": "Ticket #123 status updated to RESOLVED",
    "ticket_url": "/tickets/123"
}
```

---

### 3. Get Suggestions

Get a list of suggested questions to display as quick actions.

**Endpoint:** `GET /chatbot/mobile/suggestions`

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
    "success": true,
    "suggestions": [
        "How do I create a new ticket?",
        "How do I add a new asset?",
        "How do I view all tickets?",
        "How do I report a bug?",
        "How do I manage user permissions?",
        "Where are the system settings?"
    ]
}
```

---

### 4. Get Chat History

Retrieve the user's previous chat interactions.

**Endpoint:** `GET /chatbot/mobile/history?limit=20`

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Query Parameters:**
- `limit` (optional): Number of history items to return (default: 20, max: 100)

**Response:**
```json
{
    "success": true,
    "history": [
        {
            "id": 156,
            "query": "How do I create a ticket?",
            "response": "To create a new ticket...",
            "response_type": "answer",
            "matched_question": "How do I create a new ticket?",
            "action_type": null,
            "created_at": "2025-01-15T10:30:00Z"
        },
        {
            "id": 155,
            "query": "Update ticket #123 to resolved",
            "response": "Do you want to update...",
            "response_type": "action_confirm",
            "matched_question": null,
            "action_type": "update_ticket_status",
            "created_at": "2025-01-15T10:25:00Z"
        }
    ]
}
```

---

### 5. Get Capabilities (No Auth Required)

Get chatbot capabilities and documentation. Useful for building the UI.

**Endpoint:** `GET /chatbot/mobile/capabilities`

**Response:**
```json
{
    "success": true,
    "version": "1.0",
    "description": "Help Assistant chatbot for inventory management system",
    "capabilities": {
        "knowledge_base": true,
        "ticket_actions": true,
        "asset_lookup": true,
        "bug_reporting": true,
        "user_lookup": true
    },
    "action_commands": {
        "update_status": {
            "description": "Update a ticket's status",
            "examples": [
                "Update ticket #123 to resolved",
                "Mark ticket #456 as in progress",
                "Resolve ticket #789"
            ]
        },
        "update_priority": {
            "description": "Change a ticket's priority",
            "examples": [
                "Set ticket #123 priority to high",
                "Change ticket #456 priority to critical"
            ]
        },
        "assign_ticket": {
            "description": "Assign a ticket to a user",
            "examples": [
                "Assign ticket #123 to John",
                "Transfer ticket #456 to Sarah"
            ]
        },
        "report_bug": {
            "description": "Report a bug in the system",
            "examples": [
                "Report bug: Login page not loading",
                "Report critical bug: System crash on submit"
            ]
        },
        "asset_lookup": {
            "description": "Look up an asset by serial number or asset tag",
            "examples": [
                "Find asset serial ABC123",
                "Lookup SN: XYZ789",
                "Check asset tag AT001"
            ]
        }
    },
    "sample_queries": [...],
    "response_types": {
        "greeting": "Initial greeting response",
        "answer": "Direct answer from knowledge base",
        "action_confirm": "Request confirmation before executing action",
        "error": "Error message (e.g., ticket not found)",
        "fallback": "Could not find matching answer"
    }
}
```

---

## Swift Implementation Example

### ChatbotService.swift

```swift
import Foundation

// MARK: - Models

struct ChatbotAskRequest: Codable {
    let query: String
}

struct ChatbotResponse: Codable {
    let success: Bool
    let type: String?
    let answer: String?
    let error: String?
    let matchedQuestion: String?
    let url: String?
    let permission: String?
    let suggestions: [String]?

    // Action-specific fields
    let action: String?
    let ticketId: Int?
    let ticketSubject: String?
    let currentStatus: String?
    let newStatus: String?
    let currentPriority: String?
    let newPriority: String?
    let currentAssignee: String?
    let newAssigneeId: Int?
    let newAssignee: String?
    let bugTitle: String?
    let severity: String?

    // Asset lookup
    let asset: AssetInfo?

    enum CodingKeys: String, CodingKey {
        case success, type, answer, error, url, permission, suggestions, action, severity
        case matchedQuestion = "matched_question"
        case ticketId = "ticket_id"
        case ticketSubject = "ticket_subject"
        case currentStatus = "current_status"
        case newStatus = "new_status"
        case currentPriority = "current_priority"
        case newPriority = "new_priority"
        case currentAssignee = "current_assignee"
        case newAssigneeId = "new_assignee_id"
        case newAssignee = "new_assignee"
        case bugTitle = "bug_title"
        case asset
    }
}

struct AssetInfo: Codable {
    let id: Int
    let assetTag: String?
    let name: String?
    let serialNum: String?
    let status: String?
    let model: String?
    let manufacturer: String?

    enum CodingKeys: String, CodingKey {
        case id, name, status, model, manufacturer
        case assetTag = "asset_tag"
        case serialNum = "serial_num"
    }
}

struct ChatbotExecuteRequest: Codable {
    let action: String
    let ticketId: Int?
    let newStatus: String?
    let newPriority: String?
    let newAssigneeId: Int?
    let bugTitle: String?
    let bugDescription: String?
    let severity: String?

    enum CodingKeys: String, CodingKey {
        case action, severity
        case ticketId = "ticket_id"
        case newStatus = "new_status"
        case newPriority = "new_priority"
        case newAssigneeId = "new_assignee_id"
        case bugTitle = "bug_title"
        case bugDescription = "bug_description"
    }
}

struct ChatbotExecuteResponse: Codable {
    let success: Bool
    let message: String?
    let error: String?
    let ticketUrl: String?
    let bugUrl: String?
    let bugId: String?

    enum CodingKeys: String, CodingKey {
        case success, message, error
        case ticketUrl = "ticket_url"
        case bugUrl = "bug_url"
        case bugId = "bug_id"
    }
}

struct SuggestionsResponse: Codable {
    let success: Bool
    let suggestions: [String]
}

struct ChatHistoryItem: Codable {
    let id: Int
    let query: String
    let response: String?
    let responseType: String?
    let matchedQuestion: String?
    let actionType: String?
    let createdAt: String?

    enum CodingKeys: String, CodingKey {
        case id, query, response
        case responseType = "response_type"
        case matchedQuestion = "matched_question"
        case actionType = "action_type"
        case createdAt = "created_at"
    }
}

struct ChatHistoryResponse: Codable {
    let success: Bool
    let history: [ChatHistoryItem]
}

// MARK: - ChatbotService

class ChatbotService {
    static let shared = ChatbotService()

    private let baseURL: String
    private var authToken: String?

    private init() {
        // Configure your base URL
        self.baseURL = "https://your-server.com"
    }

    func setAuthToken(_ token: String) {
        self.authToken = token
    }

    // MARK: - API Methods

    func ask(query: String, completion: @escaping (Result<ChatbotResponse, Error>) -> Void) {
        guard let token = authToken else {
            completion(.failure(ChatbotError.notAuthenticated))
            return
        }

        let url = URL(string: "\(baseURL)/chatbot/mobile/ask")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

        let body = ChatbotAskRequest(query: query)
        request.httpBody = try? JSONEncoder().encode(body)

        URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error {
                completion(.failure(error))
                return
            }

            guard let data = data else {
                completion(.failure(ChatbotError.noData))
                return
            }

            do {
                let decoder = JSONDecoder()
                let response = try decoder.decode(ChatbotResponse.self, from: data)
                completion(.success(response))
            } catch {
                completion(.failure(error))
            }
        }.resume()
    }

    func executeAction(_ request: ChatbotExecuteRequest, completion: @escaping (Result<ChatbotExecuteResponse, Error>) -> Void) {
        guard let token = authToken else {
            completion(.failure(ChatbotError.notAuthenticated))
            return
        }

        let url = URL(string: "\(baseURL)/chatbot/mobile/execute")!
        var urlRequest = URLRequest(url: url)
        urlRequest.httpMethod = "POST"
        urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
        urlRequest.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        urlRequest.httpBody = try? JSONEncoder().encode(request)

        URLSession.shared.dataTask(with: urlRequest) { data, response, error in
            if let error = error {
                completion(.failure(error))
                return
            }

            guard let data = data else {
                completion(.failure(ChatbotError.noData))
                return
            }

            do {
                let decoder = JSONDecoder()
                let response = try decoder.decode(ChatbotExecuteResponse.self, from: data)
                completion(.success(response))
            } catch {
                completion(.failure(error))
            }
        }.resume()
    }

    func getSuggestions(completion: @escaping (Result<[String], Error>) -> Void) {
        guard let token = authToken else {
            completion(.failure(ChatbotError.notAuthenticated))
            return
        }

        let url = URL(string: "\(baseURL)/chatbot/mobile/suggestions")!
        var request = URLRequest(url: url)
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

        URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error {
                completion(.failure(error))
                return
            }

            guard let data = data else {
                completion(.failure(ChatbotError.noData))
                return
            }

            do {
                let decoder = JSONDecoder()
                let response = try decoder.decode(SuggestionsResponse.self, from: data)
                completion(.success(response.suggestions))
            } catch {
                completion(.failure(error))
            }
        }.resume()
    }

    func getChatHistory(limit: Int = 20, completion: @escaping (Result<[ChatHistoryItem], Error>) -> Void) {
        guard let token = authToken else {
            completion(.failure(ChatbotError.notAuthenticated))
            return
        }

        let url = URL(string: "\(baseURL)/chatbot/mobile/history?limit=\(limit)")!
        var request = URLRequest(url: url)
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

        URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error {
                completion(.failure(error))
                return
            }

            guard let data = data else {
                completion(.failure(ChatbotError.noData))
                return
            }

            do {
                let decoder = JSONDecoder()
                let response = try decoder.decode(ChatHistoryResponse.self, from: data)
                completion(.success(response.history))
            } catch {
                completion(.failure(error))
            }
        }.resume()
    }
}

enum ChatbotError: Error {
    case notAuthenticated
    case noData
    case invalidResponse
}
```

### ChatbotView.swift - Claude/ChatGPT Style UI

Build a modern, clean chat interface similar to Claude or ChatGPT with the following design principles:

**Design Requirements:**
- Clean white/light gray background
- User messages: Right-aligned, colored bubble (blue/purple gradient)
- Assistant messages: Left-aligned, light gray background, full-width card style
- Typing indicator with animated dots
- Smooth scroll-to-bottom animation
- Suggestion chips at bottom
- Floating input bar with rounded corners
- Support for markdown-style formatting in responses

```swift
import SwiftUI

// MARK: - Models

struct ChatMessage: Identifiable, Equatable {
    let id = UUID()
    let isUser: Bool
    let text: String
    let type: String?
    let actionData: ChatbotResponse?
    let timestamp: Date

    static func == (lhs: ChatMessage, rhs: ChatMessage) -> Bool {
        lhs.id == rhs.id
    }
}

// MARK: - Main Chat View (Claude/ChatGPT Style)

struct ChatbotView: View {
    @StateObject private var viewModel = ChatbotViewModel()
    @FocusState private var isInputFocused: Bool

    var body: some View {
        ZStack {
            // Background
            Color(UIColor.systemGroupedBackground)
                .ignoresSafeArea()

            VStack(spacing: 0) {
                // Chat Messages
                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(spacing: 0) {
                            // Welcome message if empty
                            if viewModel.messages.isEmpty {
                                WelcomeView(suggestions: viewModel.suggestions) { suggestion in
                                    viewModel.sendMessage(suggestion)
                                }
                                .padding(.top, 40)
                            }

                            // Messages
                            ForEach(viewModel.messages) { message in
                                MessageBubble(message: message, onActionConfirm: { action in
                                    viewModel.executeAction(action)
                                }, onActionCancel: {
                                    // Handle cancel if needed
                                })
                                .id(message.id)
                            }

                            // Typing indicator
                            if viewModel.isLoading {
                                TypingIndicator()
                                    .id("typing")
                            }

                            // Bottom spacer for suggestions
                            Color.clear.frame(height: 80)
                        }
                        .padding(.horizontal, 16)
                    }
                    .onChange(of: viewModel.messages.count) { _ in
                        withAnimation(.easeOut(duration: 0.3)) {
                            if viewModel.isLoading {
                                proxy.scrollTo("typing", anchor: .bottom)
                            } else if let lastMessage = viewModel.messages.last {
                                proxy.scrollTo(lastMessage.id, anchor: .bottom)
                            }
                        }
                    }
                }

                // Suggestion chips (shown after responses)
                if !viewModel.suggestions.isEmpty && !viewModel.messages.isEmpty {
                    SuggestionChips(suggestions: viewModel.suggestions) { suggestion in
                        viewModel.sendMessage(suggestion)
                    }
                }

                // Input Bar
                ChatInputBar(
                    text: $viewModel.inputText,
                    isLoading: viewModel.isLoading,
                    onSend: {
                        viewModel.sendMessage(viewModel.inputText)
                    }
                )
                .focused($isInputFocused)
            }
        }
        .navigationTitle("Help Assistant")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .navigationBarTrailing) {
                Button(action: { viewModel.clearChat() }) {
                    Image(systemName: "trash")
                        .foregroundColor(.secondary)
                }
            }
        }
        .onAppear {
            viewModel.loadSuggestions()
        }
    }
}

// MARK: - Welcome View (Empty State)

struct WelcomeView: View {
    let suggestions: [String]
    let onSelect: (String) -> Void

    var body: some View {
        VStack(spacing: 24) {
            // Logo/Icon
            ZStack {
                Circle()
                    .fill(LinearGradient(
                        colors: [Color.blue, Color.purple],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    ))
                    .frame(width: 80, height: 80)

                Image(systemName: "bubble.left.and.bubble.right.fill")
                    .font(.system(size: 32))
                    .foregroundColor(.white)
            }

            VStack(spacing: 8) {
                Text("Help Assistant")
                    .font(.title2)
                    .fontWeight(.bold)

                Text("Ask me anything about tickets, assets, or how to use the system")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 32)
            }

            // Quick action cards
            VStack(spacing: 12) {
                Text("Try asking:")
                    .font(.caption)
                    .foregroundColor(.secondary)

                ForEach(suggestions.prefix(4), id: \.self) { suggestion in
                    Button(action: { onSelect(suggestion) }) {
                        HStack {
                            Image(systemName: "lightbulb.fill")
                                .foregroundColor(.orange)
                            Text(suggestion)
                                .font(.subheadline)
                                .foregroundColor(.primary)
                                .lineLimit(2)
                            Spacer()
                            Image(systemName: "arrow.right")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                        .padding(12)
                        .background(Color(UIColor.secondarySystemGroupedBackground))
                        .cornerRadius(12)
                    }
                }
            }
            .padding(.horizontal, 16)
        }
    }
}

// MARK: - Message Bubble (Claude/ChatGPT Style)

struct MessageBubble: View {
    let message: ChatMessage
    let onActionConfirm: (ChatbotResponse) -> Void
    let onActionCancel: () -> Void

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            if message.isUser {
                Spacer(minLength: 60)
            } else {
                // Assistant avatar
                ZStack {
                    Circle()
                        .fill(LinearGradient(
                            colors: [Color.blue, Color.purple],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        ))
                        .frame(width: 32, height: 32)

                    Image(systemName: "sparkles")
                        .font(.system(size: 14))
                        .foregroundColor(.white)
                }
            }

            VStack(alignment: message.isUser ? .trailing : .leading, spacing: 4) {
                // Message content
                if message.isUser {
                    // User message - bubble style
                    Text(message.text)
                        .padding(.horizontal, 16)
                        .padding(.vertical, 12)
                        .background(
                            LinearGradient(
                                colors: [Color.blue, Color.blue.opacity(0.8)],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            )
                        )
                        .foregroundColor(.white)
                        .cornerRadius(20)
                        .cornerRadius(4, corners: [.bottomTrailing])
                } else {
                    // Assistant message - card style
                    VStack(alignment: .leading, spacing: 12) {
                        // Render markdown-style text
                        MarkdownText(text: message.text)

                        // Action confirmation buttons
                        if message.type == "action_confirm", let actionData = message.actionData {
                            ActionConfirmCard(
                                action: actionData,
                                onConfirm: { onActionConfirm(actionData) },
                                onCancel: onActionCancel
                            )
                        }
                    }
                    .padding(16)
                    .background(Color(UIColor.secondarySystemGroupedBackground))
                    .cornerRadius(16)
                    .cornerRadius(4, corners: [.topLeading])
                }

                // Timestamp
                Text(message.timestamp, style: .time)
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }

            if !message.isUser {
                Spacer(minLength: 40)
            } else {
                // User avatar
                ZStack {
                    Circle()
                        .fill(Color.gray.opacity(0.3))
                        .frame(width: 32, height: 32)

                    Image(systemName: "person.fill")
                        .font(.system(size: 14))
                        .foregroundColor(.gray)
                }
            }
        }
        .padding(.vertical, 8)
    }
}

// MARK: - Markdown Text Renderer

struct MarkdownText: View {
    let text: String

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            ForEach(parseMarkdown(text), id: \.self) { line in
                if line.hasPrefix("• ") || line.hasPrefix("- ") {
                    HStack(alignment: .top, spacing: 8) {
                        Text("•")
                            .foregroundColor(.secondary)
                        Text(line.dropFirst(2))
                            .fixedSize(horizontal: false, vertical: true)
                    }
                } else if line.hasPrefix("**") && line.hasSuffix("**") {
                    Text(line.dropFirst(2).dropLast(2))
                        .fontWeight(.semibold)
                } else if line.isEmpty {
                    Spacer().frame(height: 4)
                } else {
                    Text(parseBoldText(line))
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
        .font(.body)
        .foregroundColor(.primary)
    }

    private func parseMarkdown(_ text: String) -> [String] {
        return text.components(separatedBy: "\n")
    }

    private func parseBoldText(_ text: String) -> AttributedString {
        var result = AttributedString(text)
        // Simple bold parsing for **text**
        // In production, use a proper markdown parser
        return result
    }
}

// MARK: - Action Confirmation Card

struct ActionConfirmCard: View {
    let action: ChatbotResponse
    let onConfirm: () -> Void
    let onCancel: () -> Void

    var body: some View {
        VStack(spacing: 12) {
            Divider()

            HStack(spacing: 12) {
                Button(action: onCancel) {
                    Text("Cancel")
                        .font(.subheadline)
                        .fontWeight(.medium)
                        .foregroundColor(.secondary)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 10)
                        .background(Color(UIColor.systemGray5))
                        .cornerRadius(8)
                }

                Button(action: onConfirm) {
                    Text("Confirm")
                        .font(.subheadline)
                        .fontWeight(.semibold)
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 10)
                        .background(Color.blue)
                        .cornerRadius(8)
                }
            }
        }
    }
}

// MARK: - Typing Indicator (Animated Dots)

struct TypingIndicator: View {
    @State private var animationOffset: CGFloat = 0

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            // Avatar
            ZStack {
                Circle()
                    .fill(LinearGradient(
                        colors: [Color.blue, Color.purple],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    ))
                    .frame(width: 32, height: 32)

                Image(systemName: "sparkles")
                    .font(.system(size: 14))
                    .foregroundColor(.white)
            }

            // Dots
            HStack(spacing: 4) {
                ForEach(0..<3) { index in
                    Circle()
                        .fill(Color.gray)
                        .frame(width: 8, height: 8)
                        .offset(y: animationOffset(for: index))
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 16)
            .background(Color(UIColor.secondarySystemGroupedBackground))
            .cornerRadius(16)
            .cornerRadius(4, corners: [.topLeading])

            Spacer()
        }
        .padding(.vertical, 8)
        .onAppear {
            withAnimation(.easeInOut(duration: 0.6).repeatForever()) {
                animationOffset = 1
            }
        }
    }

    private func animationOffset(for index: Int) -> CGFloat {
        let delay = Double(index) * 0.2
        return animationOffset * sin((Double(animationOffset) + delay) * .pi) * 6
    }
}

// MARK: - Suggestion Chips

struct SuggestionChips: View {
    let suggestions: [String]
    let onSelect: (String) -> Void

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ForEach(suggestions.prefix(5), id: \.self) { suggestion in
                    Button(action: { onSelect(suggestion) }) {
                        Text(suggestion)
                            .font(.caption)
                            .lineLimit(1)
                            .padding(.horizontal, 12)
                            .padding(.vertical, 8)
                            .background(Color(UIColor.secondarySystemGroupedBackground))
                            .foregroundColor(.primary)
                            .cornerRadius(16)
                            .overlay(
                                RoundedRectangle(cornerRadius: 16)
                                    .stroke(Color.gray.opacity(0.3), lineWidth: 1)
                            )
                    }
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 8)
        }
        .background(Color(UIColor.systemGroupedBackground))
    }
}

// MARK: - Chat Input Bar (Floating Style)

struct ChatInputBar: View {
    @Binding var text: String
    let isLoading: Bool
    let onSend: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            // Text field
            HStack {
                TextField("Message Help Assistant...", text: $text, axis: .vertical)
                    .lineLimit(1...5)
                    .padding(.horizontal, 16)
                    .padding(.vertical, 12)
                    .disabled(isLoading)
            }
            .background(Color(UIColor.secondarySystemGroupedBackground))
            .cornerRadius(24)
            .overlay(
                RoundedRectangle(cornerRadius: 24)
                    .stroke(Color.gray.opacity(0.2), lineWidth: 1)
            )

            // Send button
            Button(action: onSend) {
                ZStack {
                    Circle()
                        .fill(text.isEmpty || isLoading ? Color.gray.opacity(0.3) : Color.blue)
                        .frame(width: 44, height: 44)

                    if isLoading {
                        ProgressView()
                            .progressViewStyle(CircularProgressViewStyle(tint: .white))
                            .scaleEffect(0.8)
                    } else {
                        Image(systemName: "arrow.up")
                            .font(.system(size: 18, weight: .semibold))
                            .foregroundColor(.white)
                    }
                }
            }
            .disabled(text.isEmpty || isLoading)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
        .background(
            Color(UIColor.systemGroupedBackground)
                .shadow(color: .black.opacity(0.05), radius: 8, y: -4)
        )
    }
}

// MARK: - Corner Radius Extension

extension View {
    func cornerRadius(_ radius: CGFloat, corners: UIRectCorner) -> some View {
        clipShape(RoundedCorner(radius: radius, corners: corners))
    }
}

struct RoundedCorner: Shape {
    var radius: CGFloat = .infinity
    var corners: UIRectCorner = .allCorners

    func path(in rect: CGRect) -> Path {
        let path = UIBezierPath(
            roundedRect: rect,
            byRoundingCorners: corners,
            cornerRadii: CGSize(width: radius, height: radius)
        )
        return Path(path.cgPath)
    }
}

// MARK: - View Model

class ChatbotViewModel: ObservableObject {
    @Published var messages: [ChatMessage] = []
    @Published var inputText: String = ""
    @Published var suggestions: [String] = []
    @Published var isLoading: Bool = false

    func loadSuggestions() {
        ChatbotService.shared.getSuggestions { [weak self] result in
            DispatchQueue.main.async {
                if case .success(let suggestions) = result {
                    self?.suggestions = suggestions
                }
            }
        }
    }

    func sendMessage(_ text: String) {
        guard !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return }

        let userMessage = ChatMessage(
            isUser: true,
            text: text.trimmingCharacters(in: .whitespacesAndNewlines),
            type: nil,
            actionData: nil,
            timestamp: Date()
        )
        messages.append(userMessage)
        inputText = ""
        isLoading = true

        ChatbotService.shared.ask(query: text) { [weak self] result in
            DispatchQueue.main.async {
                self?.isLoading = false

                switch result {
                case .success(let response):
                    let assistantMessage = ChatMessage(
                        isUser: false,
                        text: response.answer ?? response.error ?? "No response",
                        type: response.type,
                        actionData: response.type == "action_confirm" ? response : nil,
                        timestamp: Date()
                    )
                    self?.messages.append(assistantMessage)

                    if let newSuggestions = response.suggestions {
                        self?.suggestions = newSuggestions
                    }

                case .failure(let error):
                    let errorMessage = ChatMessage(
                        isUser: false,
                        text: "Sorry, something went wrong. Please try again.",
                        type: "error",
                        actionData: nil,
                        timestamp: Date()
                    )
                    self?.messages.append(errorMessage)
                }
            }
        }
    }

    func executeAction(_ action: ChatbotResponse) {
        guard let actionType = action.action else { return }

        var request: ChatbotExecuteRequest

        switch actionType {
        case "update_ticket_status":
            request = ChatbotExecuteRequest(
                action: actionType,
                ticketId: action.ticketId,
                newStatus: action.newStatus,
                newPriority: nil,
                newAssigneeId: nil,
                bugTitle: nil,
                bugDescription: nil,
                severity: nil
            )
        case "update_ticket_priority":
            request = ChatbotExecuteRequest(
                action: actionType,
                ticketId: action.ticketId,
                newStatus: nil,
                newPriority: action.newPriority,
                newAssigneeId: nil,
                bugTitle: nil,
                bugDescription: nil,
                severity: nil
            )
        case "assign_ticket":
            request = ChatbotExecuteRequest(
                action: actionType,
                ticketId: action.ticketId,
                newStatus: nil,
                newPriority: nil,
                newAssigneeId: action.newAssigneeId,
                bugTitle: nil,
                bugDescription: nil,
                severity: nil
            )
        case "report_bug":
            request = ChatbotExecuteRequest(
                action: actionType,
                ticketId: nil,
                newStatus: nil,
                newPriority: nil,
                newAssigneeId: nil,
                bugTitle: action.bugTitle,
                bugDescription: nil,
                severity: action.severity
            )
        default:
            return
        }

        isLoading = true

        ChatbotService.shared.executeAction(request) { [weak self] result in
            DispatchQueue.main.async {
                self?.isLoading = false

                switch result {
                case .success(let response):
                    let successMessage = ChatMessage(
                        isUser: false,
                        text: response.message ?? "Action completed successfully!",
                        type: "success",
                        actionData: nil,
                        timestamp: Date()
                    )
                    self?.messages.append(successMessage)

                case .failure(let error):
                    let errorMessage = ChatMessage(
                        isUser: false,
                        text: "Failed to execute action: \(error.localizedDescription)",
                        type: "error",
                        actionData: nil,
                        timestamp: Date()
                    )
                    self?.messages.append(errorMessage)
                }
            }
        }
    }

    func clearChat() {
        messages.removeAll()
        loadSuggestions()
    }
}
```

### UI Design Specifications

| Element | Specification |
|---------|---------------|
| **Background** | `systemGroupedBackground` (light gray) |
| **User Bubble** | Blue gradient, right-aligned, rounded corners (20px), bottom-right corner squared (4px) |
| **Assistant Card** | `secondarySystemGroupedBackground`, left-aligned, full width, rounded corners (16px), top-left corner squared (4px) |
| **Avatar Size** | 32x32 points |
| **User Avatar** | Gray circle with person icon |
| **Assistant Avatar** | Blue-purple gradient with sparkles icon |
| **Input Bar** | Floating style, 24px corner radius, shadow on top |
| **Send Button** | 44x44 circle, blue when active, gray when disabled |
| **Typing Indicator** | 3 animated dots bouncing vertically |
| **Suggestion Chips** | Horizontal scroll, 16px corner radius, gray border |
| **Font** | System font, body size for messages |
| **Spacing** | 8px vertical between messages, 12px horizontal padding |

---

## Natural Language Commands

The chatbot supports natural language commands for common actions. Users can type:

| Action | Example Commands |
|--------|------------------|
| Update Status | "Update ticket #123 to resolved", "Mark ticket #456 as in progress", "Resolve ticket #789", "Close ticket #100" |
| Update Priority | "Set ticket #123 priority to high", "Change ticket #456 priority to critical" |
| Assign Ticket | "Assign ticket #123 to John", "Transfer ticket #456 to Sarah" |
| Report Bug | "Report bug: Login page not loading", "Report critical bug: System crash" |
| Asset Lookup | "Find asset serial ABC123", "Lookup SN: XYZ789", "Check asset tag AT001" |

---

## Response Type Handling

| Type | Description | Action |
|------|-------------|--------|
| `greeting` | Initial greeting | Display welcome message |
| `answer` | Knowledge base answer | Display answer, show URL if provided |
| `action_confirm` | Action requires confirmation | Show confirmation dialog, then call `/execute` |
| `error` | Error occurred | Display error message |
| `fallback` | No matching answer | Display fallback message, show suggestions |

---

## Error Handling

**HTTP Status Codes:**
- `200` - Success
- `401` - Unauthorized (invalid or expired token)
- `403` - Forbidden (insufficient permissions)
- `500` - Server error

**Error Response Format:**
```json
{
    "success": false,
    "error": "Error description"
}
```

---

## Integration Checklist

- [ ] Set up `ChatbotService` with correct base URL
- [ ] Pass JWT token after user login: `ChatbotService.shared.setAuthToken(token)`
- [ ] Implement chat UI with message bubbles
- [ ] Handle all response types (`greeting`, `answer`, `action_confirm`, `error`, `fallback`)
- [ ] Show confirmation dialog for `action_confirm` responses
- [ ] Display suggestions as quick action buttons
- [ ] Handle loading states during API calls
- [ ] Implement error handling and display
- [ ] Test with various natural language commands
- [ ] Add chat history feature (optional)

---

## Testing

Test the following scenarios:

1. **Greeting:** Send "Hello" or "Hi" and verify greeting response
2. **Knowledge Query:** Ask "How do I create a ticket?" and verify answer
3. **Ticket Action:** Send "Update ticket #123 to resolved" and verify confirmation flow
4. **Asset Lookup:** Send "Find asset serial ABC123" and verify asset info
5. **Bug Report:** Send "Report bug: Test issue" and verify confirmation
6. **Invalid Query:** Send random text and verify fallback response
7. **Token Expiry:** Test with expired token and verify 401 response

---

## Deliverables Summary

### Files to Create

| File | Description |
|------|-------------|
| `ChatbotService.swift` | API service class for chatbot endpoints |
| `ChatbotModels.swift` | Data models (ChatMessage, ChatbotResponse, etc.) |
| `ChatbotView.swift` | Main chat screen (SwiftUI) |
| `ChatbotViewModel.swift` | View model with business logic |
| `MessageBubble.swift` | User/Assistant message bubble component |
| `TypingIndicator.swift` | Animated loading indicator |
| `SuggestionChips.swift` | Quick action suggestion buttons |
| `ChatInputBar.swift` | Text input with send button |
| `WelcomeView.swift` | Empty state with suggestions |

### Navigation Integration

Add entry point to Help Assistant from:
- Settings screen (recommended)
- Main tab bar or side menu
- Or floating action button on relevant screens

### Acceptance Criteria

1. User can open Help Assistant chat screen
2. Welcome screen displays with sample questions when chat is empty
3. User can type questions and receive answers
4. Typing indicator shows while waiting for response
5. Messages display correctly (user right, assistant left)
6. Suggestion chips appear after responses
7. Action commands show confirmation dialog (Cancel/Confirm)
8. Confirmed actions execute and show success/error message
9. Chat clears properly with trash button
10. Authentication errors redirect to login or show appropriate message
