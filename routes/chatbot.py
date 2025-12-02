"""
Chatbot routes for help assistant
Provides AI-like help for users navigating the application
"""

from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from database import SessionLocal
from models.ticket import Ticket, TicketStatus, TicketPriority
from models.custom_ticket_status import CustomTicketStatus
from models.user import User
import re

chatbot_bp = Blueprint('chatbot', __name__, url_prefix='/chatbot')


# Action patterns for natural language commands
ACTION_PATTERNS = {
    "update_ticket_status": [
        r"(?:update|change|set|mark)\s+ticket\s+#?(\d+)\s+(?:to|as|status)\s+(.+)",
        r"ticket\s+#?(\d+)\s+(?:to|as|status)\s+(.+)",
        r"(?:resolve|close)\s+ticket\s+#?(\d+)",
        r"mark\s+ticket\s+#?(\d+)\s+(?:as\s+)?(.+)",
    ],
    "update_ticket_priority": [
        r"(?:set|change|update)\s+ticket\s+#?(\d+)\s+priority\s+(?:to\s+)?(.+)",
        r"ticket\s+#?(\d+)\s+priority\s+(?:to\s+)?(.+)",
    ],
    "assign_ticket": [
        r"assign\s+ticket\s+#?(\d+)\s+to\s+(.+)",
        r"(?:give|transfer)\s+ticket\s+#?(\d+)\s+to\s+(.+)",
    ],
}

# Status aliases for natural language
STATUS_ALIASES = {
    "resolved": "RESOLVED",
    "resolve": "RESOLVED",
    "done": "RESOLVED",
    "complete": "RESOLVED",
    "completed": "RESOLVED",
    "closed": "RESOLVED",
    "close": "RESOLVED",
    "new": "NEW",
    "open": "NEW",
    "in progress": "IN_PROGRESS",
    "in-progress": "IN_PROGRESS",
    "inprogress": "IN_PROGRESS",
    "working": "IN_PROGRESS",
    "processing": "PROCESSING",
    "on hold": "ON_HOLD",
    "on-hold": "ON_HOLD",
    "onhold": "ON_HOLD",
    "hold": "ON_HOLD",
    "pending": "ON_HOLD",
    "delivered": "RESOLVED_DELIVERED",
}

PRIORITY_ALIASES = {
    "low": "LOW",
    "medium": "MEDIUM",
    "med": "MEDIUM",
    "normal": "MEDIUM",
    "high": "HIGH",
    "critical": "CRITICAL",
    "urgent": "CRITICAL",
}


def parse_action(query):
    """Parse a query to detect if it's an action command"""
    query_lower = query.lower().strip()

    # Check for ticket status update
    for pattern in ACTION_PATTERNS["update_ticket_status"]:
        match = re.search(pattern, query_lower)
        if match:
            groups = match.groups()
            ticket_id = groups[0]

            # Handle "resolve ticket 890" pattern (no status in regex)
            if len(groups) == 1:
                status = "RESOLVED"
            else:
                status_text = groups[1].strip() if groups[1] else "resolved"
                status = STATUS_ALIASES.get(status_text.lower(), status_text.upper())

            return {
                "type": "action",
                "action": "update_ticket_status",
                "ticket_id": int(ticket_id),
                "new_status": status,
                "original_query": query
            }

    # Check for ticket priority update
    for pattern in ACTION_PATTERNS["update_ticket_priority"]:
        match = re.search(pattern, query_lower)
        if match:
            ticket_id = match.group(1)
            priority_text = match.group(2).strip()
            priority = PRIORITY_ALIASES.get(priority_text.lower(), priority_text.upper())

            return {
                "type": "action",
                "action": "update_ticket_priority",
                "ticket_id": int(ticket_id),
                "new_priority": priority,
                "original_query": query
            }

    # Check for ticket assignment
    for pattern in ACTION_PATTERNS["assign_ticket"]:
        match = re.search(pattern, query_lower)
        if match:
            ticket_id = match.group(1)
            assignee = match.group(2).strip()

            return {
                "type": "action",
                "action": "assign_ticket",
                "ticket_id": int(ticket_id),
                "assignee": assignee,
                "original_query": query
            }

    return None

# Knowledge base with questions and answers
KNOWLEDGE_BASE = [
    # Custom Ticket Statuses
    {
        "keywords": ["custom status", "add status", "create status", "ticket status", "new status", "manage status"],
        "question": "How do I add a custom ticket status?",
        "answer": "To add a custom ticket status, go to **Admin → Manage Ticket Statuses** (`/admin/manage-ticket-statuses`). Click 'Add New Status' and fill in:\n\n• **Internal Name** - e.g., UNDER_REVIEW\n• **Display Name** - e.g., Under Review\n• **Color** - Choose from available colors\n• **Active** - Toggle on/off\n\nNote: Only Super Admins can manage custom statuses.",
        "url": "/admin/manage-ticket-statuses",
        "permission": "SUPER_ADMIN"
    },
    {
        "keywords": ["change status", "update status", "edit ticket status", "modify status"],
        "question": "How do I change a ticket's status?",
        "answer": "To change a ticket's status:\n\n1. Open the ticket by clicking on it\n2. Click the **Edit** button or look for the status dropdown\n3. Select the new status from the dropdown\n4. Save changes\n\nYou need the `can_edit_tickets` permission to change ticket statuses.",
        "url": "/tickets",
        "permission": "can_edit_tickets"
    },

    # Tickets
    {
        "keywords": ["create ticket", "new ticket", "add ticket", "submit ticket", "open ticket"],
        "question": "How do I create a new ticket?",
        "answer": "To create a new ticket:\n\n1. Go to **Tickets** in the navigation\n2. Click the **+ New Ticket** button\n3. Select a ticket category (PIN Request, Asset Repair, etc.)\n4. Fill in the required fields\n5. Click **Create Ticket**\n\nYou can also use the quick create from the dashboard.",
        "url": "/tickets/create",
        "permission": "can_create_tickets"
    },
    {
        "keywords": ["view tickets", "find ticket", "ticket list", "my tickets", "search ticket"],
        "question": "Where can I view all tickets?",
        "answer": "You can view tickets at **Tickets → All Tickets** (`/tickets`). Use the filters to:\n\n• Filter by **Status** (New, In Progress, Resolved, etc.)\n• Filter by **Priority** (Low, Medium, High, Critical)\n• Filter by **Category**\n• Search by ticket number or subject",
        "url": "/tickets",
        "permission": "can_view_tickets"
    },
    {
        "keywords": ["tracking", "track shipment", "package tracking", "carrier", "ship24", "tracking number"],
        "question": "How do I track a shipment?",
        "answer": "Shipment tracking is available on ticket detail pages:\n\n1. Open a ticket with shipping information\n2. Look for the **Tracking** section\n3. Click on tracking numbers to see package journey\n\nSupported carriers: SingPost, DHL, UPS, BlueDart, DTDC, and more.\n\nFor bulk tracking, use **Parcel Tracking** (`/parcel-tracking`).",
        "url": "/parcel-tracking",
        "permission": None
    },
    {
        "keywords": ["mass update", "bulk update", "update multiple", "bulk ticket", "mass ticket", "batch update", "update many tickets"],
        "question": "How do I mass update tickets?",
        "answer": "To bulk update tickets:\n\n1. Go to **Tickets → Ticket Manager** (`/tickets/manager`)\n2. Use filters to find the tickets you want to update\n3. Select multiple tickets using checkboxes\n4. Use the **Bulk Actions** dropdown to:\n   • Change status\n   • Change priority\n   • Assign to user\n   • Delete tickets\n5. Confirm the action\n\nYou can also use the SF-style ticket list at `/tickets/sf` for more options.",
        "url": "/tickets/manager",
        "permission": "can_edit_tickets"
    },
    {
        "keywords": ["ticket manager", "manage tickets", "ticket management"],
        "question": "Where is the ticket manager?",
        "answer": "The Ticket Manager is at **Tickets → Manager** (`/tickets/manager`). It provides:\n\n• Advanced filtering and sorting\n• Bulk selection and actions\n• Quick status updates\n• Export capabilities\n\nYou can also use the SF-style view at `/tickets/sf` for a different layout.",
        "url": "/tickets/manager",
        "permission": "can_view_tickets"
    },
    {
        "keywords": ["export ticket", "download ticket", "ticket csv", "ticket excel"],
        "question": "How do I export tickets?",
        "answer": "To export tickets:\n\n1. Go to **Tickets** list or **Ticket Manager**\n2. Apply any filters you want\n3. Click the **Export** button\n4. Choose format (CSV or Excel)\n5. Download the file\n\nRequires `can_export_tickets` permission.",
        "url": "/tickets",
        "permission": "can_export_tickets"
    },
    {
        "keywords": ["assign ticket", "reassign", "transfer ticket", "change owner", "ticket assignment"],
        "question": "How do I assign or transfer a ticket?",
        "answer": "To assign/transfer a ticket:\n\n1. Open the ticket\n2. Click **Edit** or find the **Assigned To** field\n3. Select a new user from the dropdown\n4. Save changes\n\nFor bulk assignment, use the Ticket Manager (`/tickets/manager`) and select multiple tickets.",
        "url": "/tickets",
        "permission": "can_edit_tickets"
    },
    {
        "keywords": ["delete ticket", "remove ticket", "cancel ticket"],
        "question": "How do I delete a ticket?",
        "answer": "To delete a ticket:\n\n1. Open the ticket\n2. Click the **Delete** button (usually in the actions menu)\n3. Confirm deletion\n\nNote: Deleted tickets cannot be recovered. You may need `can_delete_tickets` permission.\n\nAlternatively, you can change the status to 'Cancelled' to keep a record.",
        "url": "/tickets",
        "permission": "can_delete_tickets"
    },
    {
        "keywords": ["comment", "add comment", "ticket comment", "note", "add note"],
        "question": "How do I add a comment to a ticket?",
        "answer": "To add a comment:\n\n1. Open the ticket\n2. Scroll to the **Comments** section\n3. Type your comment in the text box\n4. Click **Add Comment**\n\nComments are visible to all users who can view the ticket. Use @mentions to notify specific users.",
        "url": "/tickets",
        "permission": "can_view_tickets"
    },
    {
        "keywords": ["attachment", "upload file", "add file", "ticket file", "attach"],
        "question": "How do I attach files to a ticket?",
        "answer": "To attach files:\n\n1. Open the ticket\n2. Look for the **Attachments** section or **Upload** button\n3. Click to select files or drag and drop\n4. Files will be uploaded automatically\n\nSupported file types include images, PDFs, and documents.",
        "url": "/tickets",
        "permission": "can_edit_tickets"
    },

    # Inventory
    {
        "keywords": ["add asset", "create asset", "new asset", "register asset"],
        "question": "How do I add a new asset?",
        "answer": "To add a new tech asset:\n\n1. Go to **Inventory → Tech Assets**\n2. Click **+ Add Asset**\n3. Fill in asset details (Name, Asset Tag, Serial Number, etc.)\n4. Select the company and status\n5. Click **Save**\n\nFor bulk import, use **Inventory → Import** with a CSV file.",
        "url": "/inventory/assets/add",
        "permission": "can_create_assets"
    },
    {
        "keywords": ["bulk import", "import csv", "import assets", "upload csv", "mass import"],
        "question": "How do I bulk import assets?",
        "answer": "To bulk import assets:\n\n1. Go to **Inventory → Import** (`/inventory/import`)\n2. Download the CSV template\n3. Fill in your asset data\n4. Upload the completed CSV\n5. Review the preview and confirm import\n\nYou can also use **Admin → CSV Import** for advanced options.",
        "url": "/inventory/import",
        "permission": "can_import_data"
    },
    {
        "keywords": ["checkout asset", "assign asset", "deploy asset", "give asset"],
        "question": "How do I checkout/assign an asset to a user?",
        "answer": "To checkout an asset:\n\n1. Go to **Inventory** and find the asset\n2. Click on the asset to open details\n3. Click **Checkout** or **Assign**\n4. Select the customer user\n5. Add any notes and confirm\n\nThe asset status will change to 'Deployed'.",
        "url": "/inventory",
        "permission": "can_edit_assets"
    },
    {
        "keywords": ["bulk edit", "edit multiple", "mass edit", "batch edit"],
        "question": "How do I bulk edit assets?",
        "answer": "To bulk edit assets:\n\n1. Go to **Inventory → SF View** (`/inventory/sf`)\n2. Select multiple assets using checkboxes\n3. Click **Bulk Edit** button\n4. Choose what to edit (Name, Asset Tag, Serial Number, Status)\n5. Apply changes\n\nThis feature requires appropriate edit permissions.",
        "url": "/inventory/sf",
        "permission": "can_edit_assets"
    },
    {
        "keywords": ["inventory audit", "start audit", "audit assets", "stock take"],
        "question": "How do I start an inventory audit?",
        "answer": "To start an inventory audit:\n\n1. Go to **Inventory → Audit** (`/inventory/audit`)\n2. Click **Start New Audit**\n3. Scan assets using barcode/serial number\n4. Or upload a CSV file with scanned items\n5. Review found/missing items\n6. Generate audit report\n\nRequires `can_start_inventory_audit` permission.",
        "url": "/inventory/audit",
        "permission": "can_start_inventory_audit"
    },

    # Users & Permissions
    {
        "keywords": ["create user", "add user", "new user", "register user"],
        "question": "How do I create a new user?",
        "answer": "To create a new user:\n\n1. Go to **Admin → Users** (`/admin/users`)\n2. Click **+ Create User**\n3. Fill in user details (name, email, password)\n4. Select **User Type** (Super Admin, Developer, Supervisor, etc.)\n5. Assign to a company\n6. Click **Create**\n\nOnly Super Admins can create users.",
        "url": "/admin/users/create",
        "permission": "SUPER_ADMIN"
    },
    {
        "keywords": ["permissions", "user permissions", "access control", "edit permissions", "manage permissions"],
        "question": "How do I manage user permissions?",
        "answer": "To manage permissions:\n\n1. Go to **Admin → Permissions** (`/admin/permissions`)\n2. Select a user type to set default permissions\n3. Or edit individual user permissions at **Admin → Users → Edit User**\n\nPermission categories include:\n• Asset/Inventory permissions\n• Ticket permissions\n• Knowledge Base permissions\n• Admin permissions\n• Report permissions",
        "url": "/admin/permissions",
        "permission": "SUPER_ADMIN"
    },
    {
        "keywords": ["queue permission", "queue access", "who can see queue"],
        "question": "How do I control who can access ticket queues?",
        "answer": "To manage queue permissions:\n\n1. Go to **Admin → Queue Permissions** (`/admin/queue-permissions`)\n2. Select a queue\n3. Choose which users or user types can access it\n4. Save changes\n\nUsers will only see tickets in queues they have access to.",
        "url": "/admin/queue-permissions",
        "permission": "SUPER_ADMIN"
    },

    # Knowledge Base
    {
        "keywords": ["knowledge base", "help article", "documentation", "create article", "write article"],
        "question": "How do I create a knowledge base article?",
        "answer": "To create a knowledge base article:\n\n1. Go to **Knowledge Base → Admin** (`/knowledge/admin`)\n2. Click **New Article**\n3. Enter title, content (supports markdown)\n4. Select category and tags\n5. Set visibility (Public, Internal, Restricted)\n6. Publish the article\n\nRequires `can_create_articles` permission.",
        "url": "/knowledge/admin/articles/new",
        "permission": "can_create_articles"
    },

    # Reports
    {
        "keywords": ["reports", "generate report", "analytics", "statistics", "export data"],
        "question": "How do I generate reports?",
        "answer": "To generate reports:\n\n1. Go to **Reports** (`/reports`)\n2. Choose a report type:\n   • **Cases Report** - Ticket analytics\n   • **Assets Report** - Inventory stats\n   • **Custom Report** - Use Report Builder\n3. Set date range and filters\n4. View or export the data\n\nYou can save custom dashboards for quick access.",
        "url": "/reports",
        "permission": "can_view_reports"
    },

    # Admin & Settings
    {
        "keywords": ["settings", "configuration", "system config", "admin settings"],
        "question": "Where are the system settings?",
        "answer": "System settings are in **Admin → System Configuration** (`/admin/system-config`):\n\n• **Ticket Statuses** - Custom status management\n• **Ticket Categories** - Form configuration\n• **Theme Settings** - UI customization\n• **API Keys** - Integration management\n• **Database** - Backup and restore\n• **Email** - SMTP configuration",
        "url": "/admin/system-config",
        "permission": "SUPER_ADMIN"
    },
    {
        "keywords": ["theme", "colors", "appearance", "dark mode", "customize look"],
        "question": "How do I customize the theme/appearance?",
        "answer": "To customize the theme:\n\n1. Go to **Admin → Theme Settings** (`/admin/theme-settings`)\n2. Choose color scheme\n3. Adjust layout preferences\n4. Save changes\n\nTheme changes apply to all users or can be user-specific.",
        "url": "/admin/theme-settings",
        "permission": "SUPER_ADMIN"
    },
    {
        "keywords": ["backup", "database backup", "restore", "export database"],
        "question": "How do I backup the database?",
        "answer": "To backup the database:\n\n1. Go to **Admin → System Config**\n2. Click **Database Backups** (`/admin/database/backups`)\n3. Click **Create Backup**\n4. Download the backup file\n\nTo restore, upload a previous backup file.",
        "url": "/admin/database/backups",
        "permission": "SUPER_ADMIN"
    },
    {
        "keywords": ["api", "api key", "integration", "api access"],
        "question": "How do I create an API key?",
        "answer": "To create an API key:\n\n1. Go to **Admin → API Management** (`/admin/api-management`)\n2. Click **Create API Key**\n3. Set a name and permissions\n4. Copy the generated key (shown only once)\n\nAPI documentation is at `/admin/api-documentation`.",
        "url": "/admin/api-management",
        "permission": "SUPER_ADMIN"
    },

    # Dashboard
    {
        "keywords": ["dashboard", "home page", "customize dashboard", "widgets"],
        "question": "How do I customize my dashboard?",
        "answer": "To customize your dashboard:\n\n1. Go to **Dashboard** (`/dashboard`)\n2. Drag and drop widgets to rearrange\n3. Add/remove widgets using the settings\n4. Click **Save Layout**\n\nClick **Reset Layout** to restore defaults.",
        "url": "/dashboard",
        "permission": None
    },
    {
        "keywords": ["new dashboard", "switch dashboard", "change dashboard", "modern dashboard", "widget dashboard"],
        "question": "How do I switch to the new dashboard?",
        "answer": "To switch to the new widget-based dashboard:\n\n1. Go to the homepage (`/`)\n2. Look for the **Switch to New Dashboard** button (or gear icon)\n3. Click it to enable the new dashboard\n\nOr go directly to `/dashboard` to access the new dashboard.\n\nThe new dashboard features:\n• Customizable widgets\n• Drag and drop layout\n• Save your preferred layout",
        "url": "/dashboard",
        "permission": None
    },
    {
        "keywords": ["old dashboard", "classic dashboard", "original dashboard", "switch back", "legacy dashboard"],
        "question": "How do I switch back to the classic dashboard?",
        "answer": "To switch back to the classic dashboard:\n\n1. On the new dashboard, look for a **Classic View** or **Switch Back** option\n2. Or go directly to `/` (home) for the classic view\n\nAdmins can set the default dashboard for all users in **Admin → System Config**.",
        "url": "/",
        "permission": None
    },
    {
        "keywords": ["default dashboard", "set dashboard", "dashboard preference", "homepage setting"],
        "question": "How do I set the default dashboard for users?",
        "answer": "To set the default dashboard (Admin only):\n\n1. Go to **Admin → System Configuration** (`/admin/system-config`)\n2. Find **Default Homepage** setting\n3. Choose between:\n   • **New Dashboard** - Widget-based customizable view\n   • **Classic Dashboard** - Original homepage view\n4. Save changes\n\nThis sets the default for all users. Individual users can still switch views.",
        "url": "/admin/system-config",
        "permission": "SUPER_ADMIN"
    },
    {
        "keywords": ["dashboard widgets", "add widget", "remove widget", "available widgets"],
        "question": "What widgets are available on the dashboard?",
        "answer": "Available dashboard widgets include:\n\n• **Ticket Statistics** - Overview of tickets by status\n• **Asset Summary** - Inventory counts and status\n• **Recent Activity** - Latest system activity\n• **Queue Overview** - Tickets by queue\n• **Quick Actions** - Shortcuts to common tasks\n• **Charts** - Visual data representations\n\nTo add widgets, click the **+** or **Add Widget** button on your dashboard.",
        "url": "/dashboard",
        "permission": None
    },

    # Development
    {
        "keywords": ["feature request", "suggest feature", "new feature", "request feature"],
        "question": "How do I submit a feature request?",
        "answer": "To submit a feature request:\n\n1. Go to **Development → Features** (`/development/features`)\n2. Click **+ New Feature Request**\n3. Describe the feature and its benefits\n4. Set priority and category\n5. Submit for review\n\nRequires `can_create_features` permission.",
        "url": "/development/features",
        "permission": "can_create_features"
    },
    {
        "keywords": ["bug report", "report bug", "found bug", "issue", "problem"],
        "question": "How do I report a bug?",
        "answer": "To report a bug:\n\n1. Go to **Development → Bugs** (`/development/bugs`)\n2. Click **+ Report Bug**\n3. Describe the issue with steps to reproduce\n4. Set severity and attach screenshots\n5. Submit the report\n\nRequires `can_create_bugs` permission.",
        "url": "/development/bugs",
        "permission": "can_create_bugs"
    },

    # Customer Users
    {
        "keywords": ["customer user", "end user", "add customer", "customer account"],
        "question": "How do I add a customer user?",
        "answer": "To add a customer user:\n\n1. Go to **Inventory → Customer Users** (`/inventory/customer-users`)\n2. Click **+ Add Customer User**\n3. Enter name, email, and company\n4. Set location/address\n5. Save\n\nCustomer users can have assets checked out to them.",
        "url": "/inventory/customer-users",
        "permission": "can_create_users"
    },

    # Groups
    {
        "keywords": ["groups", "user groups", "team", "group permissions"],
        "question": "How do I create user groups?",
        "answer": "To create user groups:\n\n1. Go to **Admin → Groups** (`/admin/groups`)\n2. Click **Create Group**\n3. Name the group and add description\n4. Add members to the group\n5. Assign group-level permissions\n\nGroups help manage permissions for multiple users at once.",
        "url": "/admin/groups",
        "permission": "SUPER_ADMIN"
    },

    # Ticket Categories
    {
        "keywords": ["ticket category", "ticket type", "add category", "create category", "ticket form"],
        "question": "How do I create a custom ticket category?",
        "answer": "To create a custom ticket category:\n\n1. Go to **Admin → Ticket Categories** (`/admin/ticket-categories`)\n2. Click **Create Category**\n3. Set name and description\n4. Configure form fields\n5. Set which queues can use it\n6. Save the category\n\nOnly Super Admins can manage ticket categories.",
        "url": "/admin/ticket-categories",
        "permission": "SUPER_ADMIN"
    },
]

# Greeting responses
GREETINGS = ["hi", "hello", "hey", "help", "assist", "support"]

# Fallback responses
FALLBACK_RESPONSES = [
    "I'm not sure about that. Try asking about:\n• Custom ticket statuses\n• Creating tickets or assets\n• User permissions\n• Reports and analytics\n• System settings",
    "I couldn't find a specific answer. Common topics include:\n• Adding custom statuses\n• Managing inventory\n• User and permission management\n• Knowledge base articles",
]


def find_best_match(query):
    """Find the best matching knowledge base entry for a query"""
    query_lower = query.lower()

    # Check for greetings
    if any(greet in query_lower for greet in GREETINGS) and len(query_lower) < 20:
        return {
            "type": "greeting",
            "answer": "Hello! I'm the Help Assistant. I can help you with:\n\n• **Tickets** - Creating, editing, tracking\n• **Inventory** - Assets, accessories, audits\n• **Admin** - Users, permissions, settings\n• **Custom Statuses** - Adding ticket statuses\n• **Reports** - Analytics and exports\n\nWhat would you like help with?"
        }

    # Score each knowledge base entry
    best_match = None
    best_score = 0

    for entry in KNOWLEDGE_BASE:
        score = 0

        # Check keywords
        for keyword in entry["keywords"]:
            if keyword in query_lower:
                # Exact phrase match scores higher
                score += 10 if keyword in query_lower else 5

        # Check if query words appear in question
        query_words = query_lower.split()
        for word in query_words:
            if len(word) > 3 and word in entry["question"].lower():
                score += 3

        if score > best_score:
            best_score = score
            best_match = entry

    if best_match and best_score >= 5:
        return {
            "type": "answer",
            "question": best_match["question"],
            "answer": best_match["answer"],
            "url": best_match.get("url"),
            "permission": best_match.get("permission")
        }

    return None


def get_suggested_questions(limit=5):
    """Get a list of suggested questions"""
    import random
    questions = [entry["question"] for entry in KNOWLEDGE_BASE]
    return random.sample(questions, min(limit, len(questions)))


@chatbot_bp.route('/ask', methods=['POST'])
@login_required
def ask():
    """Process a user question and return an answer"""
    data = request.get_json()
    query = data.get('query', '').strip()

    if not query:
        return jsonify({
            "success": False,
            "error": "Please enter a question"
        })

    # First, check if this is an action command
    action = parse_action(query)
    if action:
        # Validate the action and return confirmation prompt
        db_session = SessionLocal()
        try:
            if action["action"] == "update_ticket_status":
                ticket = db_session.query(Ticket).filter_by(id=action["ticket_id"]).first()
                if not ticket:
                    return jsonify({
                        "success": True,
                        "type": "error",
                        "answer": f"Ticket #{action['ticket_id']} not found."
                    })

                # Check for custom status
                custom_status = db_session.query(CustomTicketStatus).filter_by(
                    internal_name=action["new_status"],
                    is_active=True
                ).first()

                status_display = action["new_status"]
                if custom_status:
                    status_display = custom_status.display_name

                return jsonify({
                    "success": True,
                    "type": "action_confirm",
                    "action": action["action"],
                    "ticket_id": action["ticket_id"],
                    "ticket_subject": ticket.subject,
                    "current_status": ticket.status.value if hasattr(ticket.status, 'value') else str(ticket.status),
                    "new_status": action["new_status"],
                    "answer": f"Do you want to update **Ticket #{action['ticket_id']}** status to **{status_display}**?\n\nTicket: {ticket.subject}\nCurrent Status: {ticket.status.value if hasattr(ticket.status, 'value') else ticket.status}"
                })

            elif action["action"] == "update_ticket_priority":
                ticket = db_session.query(Ticket).filter_by(id=action["ticket_id"]).first()
                if not ticket:
                    return jsonify({
                        "success": True,
                        "type": "error",
                        "answer": f"Ticket #{action['ticket_id']} not found."
                    })

                return jsonify({
                    "success": True,
                    "type": "action_confirm",
                    "action": action["action"],
                    "ticket_id": action["ticket_id"],
                    "ticket_subject": ticket.subject,
                    "current_priority": ticket.priority.value if ticket.priority else "None",
                    "new_priority": action["new_priority"],
                    "answer": f"Do you want to change **Ticket #{action['ticket_id']}** priority to **{action['new_priority']}**?\n\nTicket: {ticket.subject}\nCurrent Priority: {ticket.priority.value if ticket.priority else 'None'}"
                })

            elif action["action"] == "assign_ticket":
                ticket = db_session.query(Ticket).filter_by(id=action["ticket_id"]).first()
                if not ticket:
                    return jsonify({
                        "success": True,
                        "type": "error",
                        "answer": f"Ticket #{action['ticket_id']} not found."
                    })

                # Find user by name
                assignee_name = action["assignee"]
                user = db_session.query(User).filter(
                    User.name.ilike(f"%{assignee_name}%")
                ).first()

                if not user:
                    return jsonify({
                        "success": True,
                        "type": "error",
                        "answer": f"User '{assignee_name}' not found. Please check the name and try again."
                    })

                return jsonify({
                    "success": True,
                    "type": "action_confirm",
                    "action": action["action"],
                    "ticket_id": action["ticket_id"],
                    "ticket_subject": ticket.subject,
                    "current_assignee": ticket.assigned_to.name if ticket.assigned_to else "Unassigned",
                    "new_assignee_id": user.id,
                    "new_assignee": user.name,
                    "answer": f"Do you want to assign **Ticket #{action['ticket_id']}** to **{user.name}**?\n\nTicket: {ticket.subject}\nCurrent Assignee: {ticket.assigned_to.name if ticket.assigned_to else 'Unassigned'}"
                })

        finally:
            db_session.close()

    # Find matching answer from knowledge base
    result = find_best_match(query)

    if result:
        response = {
            "success": True,
            "type": result["type"],
            "answer": result["answer"],
        }

        if result["type"] == "answer":
            response["matched_question"] = result.get("question")
            response["url"] = result.get("url")
            response["permission"] = result.get("permission")

            # Add suggestions
            response["suggestions"] = get_suggested_questions(3)

        return jsonify(response)

    # Fallback
    import random
    return jsonify({
        "success": True,
        "type": "fallback",
        "answer": random.choice(FALLBACK_RESPONSES),
        "suggestions": get_suggested_questions(5)
    })


@chatbot_bp.route('/execute', methods=['POST'])
@login_required
def execute_action():
    """Execute a confirmed action"""
    data = request.get_json()
    action = data.get('action')
    ticket_id = data.get('ticket_id')

    if not action or not ticket_id:
        return jsonify({"success": False, "error": "Missing action or ticket_id"})

    db_session = SessionLocal()
    try:
        ticket = db_session.query(Ticket).filter_by(id=ticket_id).first()
        if not ticket:
            return jsonify({"success": False, "error": f"Ticket #{ticket_id} not found"})

        # Check permissions
        user_permissions = current_user.get_permissions(db_session)
        if not user_permissions or not user_permissions.can_edit_tickets:
            return jsonify({"success": False, "error": "You don't have permission to edit tickets"})

        if action == "update_ticket_status":
            new_status = data.get('new_status')
            if not new_status:
                return jsonify({"success": False, "error": "Missing new_status"})

            # Check if it's a system status or custom status
            try:
                ticket.status = TicketStatus(new_status)
            except ValueError:
                # Try custom status
                custom_status = db_session.query(CustomTicketStatus).filter_by(
                    internal_name=new_status,
                    is_active=True
                ).first()
                if custom_status:
                    ticket.custom_status_id = custom_status.id
                    ticket.status = TicketStatus.PROCESSING  # Set base status
                else:
                    return jsonify({"success": False, "error": f"Invalid status: {new_status}"})

            db_session.commit()
            return jsonify({
                "success": True,
                "message": f"Ticket #{ticket_id} status updated to {new_status}",
                "ticket_url": f"/tickets/{ticket_id}"
            })

        elif action == "update_ticket_priority":
            new_priority = data.get('new_priority')
            if not new_priority:
                return jsonify({"success": False, "error": "Missing new_priority"})

            try:
                ticket.priority = TicketPriority(new_priority)
            except ValueError:
                return jsonify({"success": False, "error": f"Invalid priority: {new_priority}"})

            db_session.commit()
            return jsonify({
                "success": True,
                "message": f"Ticket #{ticket_id} priority updated to {new_priority}",
                "ticket_url": f"/tickets/{ticket_id}"
            })

        elif action == "assign_ticket":
            new_assignee_id = data.get('new_assignee_id')
            if not new_assignee_id:
                return jsonify({"success": False, "error": "Missing assignee"})

            user = db_session.query(User).filter_by(id=new_assignee_id).first()
            if not user:
                return jsonify({"success": False, "error": "User not found"})

            ticket.assigned_to_id = user.id
            db_session.commit()
            return jsonify({
                "success": True,
                "message": f"Ticket #{ticket_id} assigned to {user.name}",
                "ticket_url": f"/tickets/{ticket_id}"
            })

        else:
            return jsonify({"success": False, "error": f"Unknown action: {action}"})

    except Exception as e:
        db_session.rollback()
        return jsonify({"success": False, "error": str(e)})
    finally:
        db_session.close()


@chatbot_bp.route('/suggestions', methods=['GET'])
@login_required
def suggestions():
    """Get suggested questions"""
    return jsonify({
        "success": True,
        "suggestions": get_suggested_questions(6)
    })


@chatbot_bp.route('/widget')
@login_required
def widget():
    """Render the chatbot widget (for iframe embedding)"""
    return render_template('chatbot/widget.html')
