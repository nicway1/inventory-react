# Mobile API - Queue Implementation Guide

## Overview

The API has been updated to include full queue support for the mobile app. Tickets can now display their assigned queue, and users can filter tickets by queue.

---

## API Changes Summary

### 1. Enhanced Endpoints (Already Include Queue Data)

#### `GET /api/v1/tickets`
Lists all tickets with pagination and filtering.

**Response includes:**
- `queue_id`: The ID of the queue (integer, nullable)
- `queue_name`: The name of the queue (string, nullable)

**Example Response:**
```json
{
  "success": true,
  "message": "Retrieved 25 tickets",
  "data": [
    {
      "id": 123,
      "subject": "Laptop replacement needed",
      "description": "Employee laptop is broken...",
      "status": "Open",
      "priority": "High",
      "category": "Hardware",
      "queue_id": 2,
      "queue_name": "IT Support",
      "customer_id": 45,
      "customer_name": "John Doe",
      "customer_email": "john@example.com",
      "assigned_to_id": 10,
      "assigned_to_name": "Sarah Tech",
      "created_at": "2025-01-15T10:30:00",
      "updated_at": "2025-01-15T14:20:00",
      "shipping_address": null,
      "shipping_tracking": null,
      "shipping_carrier": null,
      "shipping_status": null
    }
  ],
  "metadata": {
    "pagination": {
      "page": 1,
      "per_page": 50,
      "total": 25,
      "pages": 1
    }
  }
}
```

**Filter by Queue:**
```
GET /api/v1/tickets?queue_id=2
```

---

#### `GET /api/v1/tickets/{ticket_id}`
Get detailed information about a specific ticket.

**Response includes:**
- `queue_id`: The ID of the queue
- `queue_name`: The name of the queue

**Example Response:**
```json
{
  "success": true,
  "message": "Retrieved ticket 123",
  "data": {
    "id": 123,
    "subject": "Laptop replacement needed",
    "description": "Employee laptop is broken...",
    "status": "Open",
    "priority": "High",
    "category": "Hardware",
    "queue_id": 2,
    "queue_name": "IT Support",
    "customer_id": 45,
    "customer_name": "John Doe",
    "customer_email": "john@example.com",
    "customer_phone": "+1234567890",
    "assigned_to_id": 10,
    "assigned_to_name": "Sarah Tech",
    "created_at": "2025-01-15T10:30:00",
    "updated_at": "2025-01-15T14:20:00",
    "comments": [...],
    "attachments": [...]
  }
}
```

---

#### `GET /api/v1/sync/tickets` (UPDATED)
Incremental sync endpoint - now includes queue information.

**New fields added:**
- `queue_name`: The name of the queue
- `category`: The ticket category
- `customer_name`: Customer's full name
- `assigned_to_name`: Assigned user's full name

**Example Response:**
```json
{
  "success": true,
  "message": "Retrieved 10 tickets for sync",
  "data": [
    {
      "id": 123,
      "subject": "Laptop replacement needed",
      "description": "Employee laptop is broken...",
      "status": "Open",
      "priority": "High",
      "category": "Hardware",
      "queue_id": 2,
      "queue_name": "IT Support",
      "customer_id": 45,
      "customer_name": "John Doe",
      "assigned_to_id": 10,
      "assigned_to_name": "Sarah Tech",
      "created_at": "2025-01-15T10:30:00",
      "updated_at": "2025-01-15T14:20:00",
      "sync_timestamp": "2025-01-15T15:00:00"
    }
  ],
  "metadata": {
    "next_sync_timestamp": "2025-01-15T14:20:00",
    "has_more": false
  }
}
```

---

### 2. New Endpoint

#### `GET /api/v1/queues` (NEW)
Get list of all available queues for filtering and display.

**Authentication:** Requires API key with `tickets:read` permission

**Parameters:** None

**Response:**
```json
{
  "success": true,
  "message": "Retrieved 5 queues",
  "data": [
    {
      "id": 1,
      "name": "General Support",
      "description": "General customer support inquiries"
    },
    {
      "id": 2,
      "name": "IT Support",
      "description": "IT and technical support"
    },
    {
      "id": 3,
      "name": "Shipping",
      "description": "Shipping and logistics"
    },
    {
      "id": 4,
      "name": "Returns",
      "description": "Product returns and exchanges"
    },
    {
      "id": 5,
      "name": "Billing",
      "description": "Billing and payment issues"
    }
  ]
}
```

---

## Mobile App Implementation Guide

### Step 1: Fetch Available Queues

Add a service method to fetch the list of queues when the app starts or when the tickets page is loaded.

**Implementation:**

```dart
// In your API service class
Future<List<Queue>> fetchQueues() async {
  final response = await http.get(
    Uri.parse('$baseUrl/api/v1/queues'),
    headers: {
      'Authorization': 'Bearer $apiKey',
      'Content-Type': 'application/json',
    },
  );

  if (response.statusCode == 200) {
    final jsonData = json.decode(response.body);
    if (jsonData['success'] == true) {
      final queuesJson = jsonData['data'] as List;
      return queuesJson.map((json) => Queue.fromJson(json)).toList();
    }
  }

  throw Exception('Failed to load queues');
}
```

**Queue Model:**

```dart
class Queue {
  final int id;
  final String name;
  final String? description;

  Queue({
    required this.id,
    required this.name,
    this.description,
  });

  factory Queue.fromJson(Map<String, dynamic> json) {
    return Queue(
      id: json['id'],
      name: json['name'],
      description: json['description'],
    );
  }
}
```

---

### Step 2: Update Ticket Model

Update your Ticket model to include queue fields:

```dart
class Ticket {
  final int id;
  final String subject;
  final String description;
  final String status;
  final String? priority;
  final String? category;
  final int? queueId;
  final String? queueName;  // NEW
  final int? customerId;
  final String? customerName;
  final String? customerEmail;
  final int? assignedToId;
  final String? assignedToName;
  final DateTime? createdAt;
  final DateTime? updatedAt;
  // ... other fields

  Ticket({
    required this.id,
    required this.subject,
    required this.description,
    required this.status,
    this.priority,
    this.category,
    this.queueId,
    this.queueName,  // NEW
    this.customerId,
    this.customerName,
    this.customerEmail,
    this.assignedToId,
    this.assignedToName,
    this.createdAt,
    this.updatedAt,
  });

  factory Ticket.fromJson(Map<String, dynamic> json) {
    return Ticket(
      id: json['id'],
      subject: json['subject'],
      description: json['description'],
      status: json['status'],
      priority: json['priority'],
      category: json['category'],
      queueId: json['queue_id'],
      queueName: json['queue_name'],  // NEW
      customerId: json['customer_id'],
      customerName: json['customer_name'],
      customerEmail: json['customer_email'],
      assignedToId: json['assigned_to_id'],
      assignedToName: json['assigned_to_name'],
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'])
          : null,
      updatedAt: json['updated_at'] != null
          ? DateTime.parse(json['updated_at'])
          : null,
    );
  }
}
```

---

### Step 3: Add Queue Filter to Tickets Page

Add a dropdown/filter button to allow users to filter tickets by queue.

**UI Implementation Example:**

```dart
class TicketsPage extends StatefulWidget {
  @override
  _TicketsPageState createState() => _TicketsPageState();
}

class _TicketsPageState extends State<TicketsPage> {
  List<Ticket> tickets = [];
  List<Queue> queues = [];
  int? selectedQueueId;
  bool isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadQueues();
    _loadTickets();
  }

  Future<void> _loadQueues() async {
    try {
      final fetchedQueues = await apiService.fetchQueues();
      setState(() {
        queues = fetchedQueues;
      });
    } catch (e) {
      print('Error loading queues: $e');
    }
  }

  Future<void> _loadTickets() async {
    setState(() {
      isLoading = true;
    });

    try {
      final fetchedTickets = await apiService.fetchTickets(
        queueId: selectedQueueId,
      );
      setState(() {
        tickets = fetchedTickets;
        isLoading = false;
      });
    } catch (e) {
      setState(() {
        isLoading = false;
      });
      print('Error loading tickets: $e');
    }
  }

  void _onQueueFilterChanged(int? queueId) {
    setState(() {
      selectedQueueId = queueId;
    });
    _loadTickets();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Tickets'),
        actions: [
          // Queue filter dropdown
          PopupMenuButton<int?>(
            icon: Icon(Icons.filter_list),
            tooltip: 'Filter by Queue',
            onSelected: _onQueueFilterChanged,
            itemBuilder: (context) => [
              PopupMenuItem<int?>(
                value: null,
                child: Text('All Queues'),
              ),
              ...queues.map((queue) => PopupMenuItem<int?>(
                value: queue.id,
                child: Text(queue.name),
              )).toList(),
            ],
          ),
        ],
      ),
      body: isLoading
          ? Center(child: CircularProgressIndicator())
          : ListView.builder(
              itemCount: tickets.length,
              itemBuilder: (context, index) {
                final ticket = tickets[index];
                return TicketListItem(ticket: ticket);
              },
            ),
    );
  }
}
```

---

### Step 4: Display Queue in Ticket List Item

Show the queue name in each ticket list item:

```dart
class TicketListItem extends StatelessWidget {
  final Ticket ticket;

  const TicketListItem({required this.ticket});

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      child: ListTile(
        title: Text(
          ticket.subject,
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(height: 4),
            // Queue badge
            if (ticket.queueName != null)
              Container(
                padding: EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: Colors.blue.shade100,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  ticket.queueName!,
                  style: TextStyle(
                    fontSize: 12,
                    color: Colors.blue.shade900,
                  ),
                ),
              ),
            SizedBox(height: 4),
            Text('Status: ${ticket.status}'),
            if (ticket.customerName != null)
              Text('Customer: ${ticket.customerName}'),
          ],
        ),
        trailing: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            if (ticket.priority != null)
              Container(
                padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: _getPriorityColor(ticket.priority!),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  ticket.priority!,
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
          ],
        ),
        onTap: () {
          // Navigate to ticket details
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => TicketDetailPage(ticketId: ticket.id),
            ),
          );
        },
      ),
    );
  }

  Color _getPriorityColor(String priority) {
    switch (priority.toLowerCase()) {
      case 'high':
      case 'urgent':
        return Colors.red;
      case 'medium':
        return Colors.orange;
      case 'low':
        return Colors.green;
      default:
        return Colors.grey;
    }
  }
}
```

---

### Step 5: Display Queue in Ticket Details

Show queue information on the ticket details page:

```dart
class TicketDetailPage extends StatelessWidget {
  final Ticket ticket;

  const TicketDetailPage({required this.ticket});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Ticket Details'),
      ),
      body: SingleChildScrollView(
        padding: EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Subject
            Text(
              ticket.subject,
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
              ),
            ),
            SizedBox(height: 16),

            // Info cards
            _buildInfoCard(
              'Queue',
              ticket.queueName ?? 'Not assigned',
              Icons.queue,
              Colors.blue,
            ),
            _buildInfoCard(
              'Status',
              ticket.status,
              Icons.info_outline,
              Colors.green,
            ),
            if (ticket.priority != null)
              _buildInfoCard(
                'Priority',
                ticket.priority!,
                Icons.flag,
                Colors.orange,
              ),
            if (ticket.category != null)
              _buildInfoCard(
                'Category',
                ticket.category!,
                Icons.category,
                Colors.purple,
              ),

            SizedBox(height: 16),

            // Description
            Text(
              'Description',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            SizedBox(height: 8),
            Text(ticket.description),

            // ... other ticket details
          ],
        ),
      ),
    );
  }

  Widget _buildInfoCard(String label, String value, IconData icon, Color color) {
    return Card(
      margin: EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: Icon(icon, color: color),
        title: Text(label),
        subtitle: Text(value),
      ),
    );
  }
}
```

---

## API Service Update Example

Update your API service to support queue filtering:

```dart
class ApiService {
  final String baseUrl;
  final String apiKey;

  ApiService({required this.baseUrl, required this.apiKey});

  Future<List<Ticket>> fetchTickets({
    int page = 1,
    int perPage = 50,
    String? status,
    String? priority,
    int? queueId,  // NEW parameter
    int? customerId,
  }) async {
    // Build query parameters
    final queryParams = {
      'page': page.toString(),
      'per_page': perPage.toString(),
      if (status != null) 'status': status,
      if (priority != null) 'priority': priority,
      if (queueId != null) 'queue_id': queueId.toString(),  // NEW
      if (customerId != null) 'customer_id': customerId.toString(),
    };

    final uri = Uri.parse('$baseUrl/api/v1/tickets')
        .replace(queryParameters: queryParams);

    final response = await http.get(
      uri,
      headers: {
        'Authorization': 'Bearer $apiKey',
        'Content-Type': 'application/json',
      },
    );

    if (response.statusCode == 200) {
      final jsonData = json.decode(response.body);
      if (jsonData['success'] == true) {
        final ticketsJson = jsonData['data'] as List;
        return ticketsJson.map((json) => Ticket.fromJson(json)).toList();
      }
    }

    throw Exception('Failed to load tickets');
  }
}
```

---

## Testing

### Test the Queue Endpoint
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     https://your-domain.com/api/v1/queues
```

### Test Queue Filtering
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     https://your-domain.com/api/v1/tickets?queue_id=2
```

### Test Sync with Queue Data
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     "https://your-domain.com/api/v1/sync/tickets?since=2025-01-15T00:00:00"
```

---

## Summary

### What's Available Now:

✅ All ticket endpoints include `queue_id` and `queue_name`
✅ New `/api/v1/queues` endpoint to fetch available queues
✅ Queue filtering support on `/api/v1/tickets` endpoint
✅ Sync endpoint includes queue data

### What You Need to Do in Mobile App:

1. ✅ Add Queue model
2. ✅ Update Ticket model to include queueName
3. ✅ Fetch queues list on app startup or tickets page load
4. ✅ Add queue filter dropdown/button in tickets page
5. ✅ Display queue badge in ticket list items
6. ✅ Show queue info in ticket details page
7. ✅ Update API service to support queue filtering

---

## Questions or Issues?

If you encounter any issues or need additional API endpoints, please let us know!

**API Version:** 1.0.0
**Last Updated:** 2025-01-15
