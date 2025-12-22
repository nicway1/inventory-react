"""
Chatbot routes for help assistant
Provides AI-like help for users navigating the application
"""

from flask import Blueprint, request, jsonify, render_template, session
from flask_login import login_required, current_user
from database import SessionLocal
from models.ticket import Ticket, TicketStatus, TicketPriority
from models.custom_ticket_status import CustomTicketStatus
from models.user import User
from models.chat_log import ChatLog
import re
import uuid

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
    "report_bug": [
        r"(?:report|create|submit|log)\s+(?:a\s+)?bug[:\s]+(.+)",
        r"(?:found|there'?s?|i\s+found)\s+(?:a\s+)?bug[:\s]+(.+)",
        r"bug\s+report[:\s]+(.+)",
        r"(?:report|create|submit|log)\s+(?:a\s+)?(?:new\s+)?bug\s+(?:titled?|called|named)[:\s]+(.+)",
    ],
    "user_permissions": [
        r"(?:what|which)\s+permissions?\s+(?:does|do|has|have)\s+(.+?)(?:\s+have|\s+got)?(?:\?|$)",
        r"(.+?)\s+(?:got|has|have)\s+(?:what|which)\s+permissions?",
        r"(?:show|get|list|check)\s+(.+?)(?:'s|s)?\s+permissions?",
        r"permissions?\s+(?:for|of)\s+(.+)",
        r"(?:what|which)\s+(?:can|could)\s+(.+?)\s+(?:do|access)",
        r"(.+?)\s+(?:can|could)\s+(?:do\s+)?what",
    ],
    "user_info": [
        r"(?:who\s+is|tell\s+me\s+about|info\s+(?:on|about|for))\s+(.+)",
        r"(?:show|get)\s+(?:user\s+)?(?:info|details|information)\s+(?:for|on|about)\s+(.+)",
        r"(.+?)\s+(?:user\s+)?(?:info|details|type|role)",
    ],
    "list_users": [
        r"(?:list|show|get|display)\s+(?:all\s+)?(?:the\s+)?users?",
        r"(?:who\s+are\s+)?(?:all\s+)?(?:the\s+)?users?(?:\s+in\s+(?:the\s+)?system)?",
        r"(?:show|list|get)\s+(?:me\s+)?(?:all\s+)?(?:the\s+)?users?\s*(?:list)?",
        r"(?:all|every)\s+users?(?:\s+in\s+(?:the\s+)?system)?",
        r"users?\s+list",
        r"(?:how\s+many|count)\s+users?",
        r"list\s+(?:all\s+)?(?:the\s+)?users?$",
    ],
    "asset_lookup": [
        r"(?:find|search|lookup|look\s+up|get|show|check)\s+(?:asset\s+)?(?:with\s+)?(?:serial|serial\s*number|sn)[:\s]+([A-Za-z0-9\-_]+)",
        r"(?:asset|device)\s+(?:info|information|details)\s+(?:for\s+)?([A-Za-z0-9\-_]+)",
        r"(?:serial|sn)[:\s]*([A-Za-z0-9\-_]+)",
        r"(?:what|which)\s+asset\s+(?:has|is|with)\s+(?:serial\s+)?([A-Za-z0-9\-_]+)",
        r"(?:find|search|get|show|lookup)\s+([A-Za-z0-9\-_]{5,})",
    ],
    "tracking_lookup": [
        r"(?:track|tracking|check|lookup|look\s+up|where\s+is|status\s+of)\s+(?:parcel|package|shipment|tracking)?\s*(?:number|#|no\.?)?\s*(XZ[A-Za-z0-9]+)",
        r"(?:track|tracking)\s+(XZ[A-Za-z0-9]+)",
        r"(XZ[A-Za-z0-9]{6,})\s+(?:track|tracking|status)",
        r"(?:singpost|sp)\s+(?:track|tracking)\s*(XZ[A-Za-z0-9]+)?",
        r"(?:where\s+is|status\s+of)\s+(?:my\s+)?(?:parcel|package)\s*(XZ[A-Za-z0-9]+)?",
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

# Bug severity aliases
BUG_SEVERITY_ALIASES = {
    "low": "Low",
    "minor": "Low",
    "medium": "Medium",
    "normal": "Medium",
    "high": "High",
    "major": "High",
    "critical": "Critical",
    "severe": "Critical",
    "blocker": "Critical",
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

    # Check for bug report
    for pattern in ACTION_PATTERNS["report_bug"]:
        match = re.search(pattern, query_lower)
        if match:
            bug_title = match.group(1).strip()
            # Clean up the title - remove trailing punctuation
            bug_title = bug_title.rstrip('.,!?')

            # Extract severity if mentioned (e.g., "critical bug: title" or "bug title (high)")
            severity = "Medium"  # Default
            severity_match = re.search(r'\b(low|minor|medium|normal|high|major|critical|severe|blocker)\b', query_lower)
            if severity_match:
                severity = BUG_SEVERITY_ALIASES.get(severity_match.group(1), "Medium")
                # Remove severity from title if it was included
                bug_title = re.sub(r'\s*\b(low|minor|medium|normal|high|major|critical|severe|blocker)\b\s*', ' ', bug_title, flags=re.IGNORECASE).strip()

            return {
                "type": "action",
                "action": "report_bug",
                "bug_title": bug_title.capitalize() if bug_title else "Untitled Bug",
                "severity": severity,
                "original_query": query
            }

    # Check for user permissions query
    for pattern in ACTION_PATTERNS["user_permissions"]:
        match = re.search(pattern, query_lower)
        if match:
            username = match.group(1).strip()
            # Clean up common words that might be captured
            username = re.sub(r'\b(user|the|a|an|has|have|had|got|do|does|did|can|could|is|are|was|were)\b', '', username, flags=re.IGNORECASE).strip()
            # Remove any trailing/leading punctuation
            username = re.sub(r'^[?\s]+|[?\s]+$', '', username).strip()
            if username:
                return {
                    "type": "query",
                    "action": "user_permissions",
                    "username": username,
                    "original_query": query
                }

    # Check for user info query
    for pattern in ACTION_PATTERNS["user_info"]:
        match = re.search(pattern, query_lower)
        if match:
            username = match.group(1).strip()
            # Clean up common words
            username = re.sub(r'\b(user|the|a|an|has|have|had|got|do|does|did|can|could|is|are|was|were)\b', '', username, flags=re.IGNORECASE).strip()
            # Remove any trailing/leading punctuation
            username = re.sub(r'^[?\s]+|[?\s]+$', '', username).strip()
            if username:
                return {
                    "type": "query",
                    "action": "user_info",
                    "username": username,
                    "original_query": query
                }

    # Check for list users query
    for pattern in ACTION_PATTERNS["list_users"]:
        match = re.search(pattern, query_lower)
        if match:
            return {
                "type": "query",
                "action": "list_users",
                "original_query": query
            }

    # Check for asset lookup by serial number
    for pattern in ACTION_PATTERNS["asset_lookup"]:
        match = re.search(pattern, query, re.IGNORECASE)  # Use original query to preserve case
        if match:
            serial_number = match.group(1).strip()
            if serial_number and len(serial_number) >= 3:  # Minimum 3 chars for serial
                return {
                    "type": "query",
                    "action": "asset_lookup",
                    "serial_number": serial_number,
                    "original_query": query
                }

    # Check for SingPost tracking lookup
    for pattern in ACTION_PATTERNS["tracking_lookup"]:
        match = re.search(pattern, query, re.IGNORECASE)  # Use original query to preserve case
        if match:
            tracking_number = match.group(1).strip().upper() if match.group(1) else None
            # Also try to find any XZ tracking number in the query if pattern didn't capture it
            if not tracking_number:
                xz_match = re.search(r'(XZ[A-Za-z0-9]{6,})', query, re.IGNORECASE)
                if xz_match:
                    tracking_number = xz_match.group(1).upper()
            if tracking_number and tracking_number.startswith('XZ'):
                return {
                    "type": "query",
                    "action": "tracking_lookup",
                    "tracking_number": tracking_number,
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
        "keywords": ["bug report", "report bug", "found bug", "issue", "problem", "log bug"],
        "question": "How do I report a bug?",
        "answer": "You can report a bug in two ways:\n\n**Quick Method (via Chatbot):**\nJust type: `report bug: your bug description`\nExample: `report bug: Login page not loading`\nYou can also include severity: `report critical bug: system crash`\n\n**Manual Method:**\n1. Go to **Development → Bugs** (`/development/bugs`)\n2. Click **+ Report Bug**\n3. Describe the issue with steps to reproduce\n4. Set severity and attach screenshots\n5. Submit the report",
        "url": "/development/bugs",
        "permission": None
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


def log_chat_interaction(user_id, query, response, response_type, matched_question=None,
                         match_score=None, action_type=None, session_id=None):
    """Log a chat interaction to the database for training purposes"""
    db_session = SessionLocal()
    try:
        # Get or create session ID
        if not session_id:
            session_id = session.get('chat_session_id')
            if not session_id:
                session_id = str(uuid.uuid4())
                session['chat_session_id'] = session_id

        # Get user name to store directly (avoid lazy loading issues later)
        user_name = None
        if current_user and hasattr(current_user, 'username'):
            user_name = current_user.username

        chat_log = ChatLog(
            user_id=user_id,
            user_name=user_name,
            session_id=session_id,
            query=query,
            response=response[:2000] if response and len(response) > 2000 else response,  # Truncate long responses
            response_type=response_type,
            matched_question=matched_question,
            match_score=match_score,
            action_type=action_type,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string[:500] if request.user_agent else None
        )
        db_session.add(chat_log)
        db_session.commit()
        return chat_log.id
    except Exception as e:
        db_session.rollback()
        print(f"Error logging chat: {e}")
        return None
    finally:
        db_session.close()


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

    user_id = current_user.id if current_user else None

    # First, check if this is an action command
    action = parse_action(query)
    if action:
        # Validate the action and return confirmation prompt
        db_session = SessionLocal()
        try:
            if action["action"] == "update_ticket_status":
                ticket = db_session.query(Ticket).filter_by(id=action["ticket_id"]).first()
                if not ticket:
                    answer = f"Ticket #{action['ticket_id']} not found."
                    log_chat_interaction(user_id, query, answer, "error", action_type=action["action"])
                    return jsonify({
                        "success": True,
                        "type": "error",
                        "answer": answer
                    })

                # Check for custom status
                custom_status = db_session.query(CustomTicketStatus).filter_by(
                    name=action["new_status"],
                    is_active=True
                ).first()

                status_display = action["new_status"]
                if custom_status:
                    status_display = custom_status.display_name

                answer = f"Do you want to update **Ticket #{action['ticket_id']}** status to **{status_display}**?\n\nTicket: {ticket.subject}\nCurrent Status: {ticket.status.value if hasattr(ticket.status, 'value') else ticket.status}"
                log_chat_interaction(user_id, query, answer, "action_confirm", action_type=action["action"])
                return jsonify({
                    "success": True,
                    "type": "action_confirm",
                    "action": action["action"],
                    "ticket_id": action["ticket_id"],
                    "ticket_subject": ticket.subject,
                    "current_status": ticket.status.value if hasattr(ticket.status, 'value') else str(ticket.status),
                    "new_status": action["new_status"],
                    "answer": answer
                })

            elif action["action"] == "update_ticket_priority":
                ticket = db_session.query(Ticket).filter_by(id=action["ticket_id"]).first()
                if not ticket:
                    answer = f"Ticket #{action['ticket_id']} not found."
                    log_chat_interaction(user_id, query, answer, "error", action_type=action["action"])
                    return jsonify({
                        "success": True,
                        "type": "error",
                        "answer": answer
                    })

                answer = f"Do you want to change **Ticket #{action['ticket_id']}** priority to **{action['new_priority']}**?\n\nTicket: {ticket.subject}\nCurrent Priority: {ticket.priority.value if ticket.priority else 'None'}"
                log_chat_interaction(user_id, query, answer, "action_confirm", action_type=action["action"])
                return jsonify({
                    "success": True,
                    "type": "action_confirm",
                    "action": action["action"],
                    "ticket_id": action["ticket_id"],
                    "ticket_subject": ticket.subject,
                    "current_priority": ticket.priority.value if ticket.priority else "None",
                    "new_priority": action["new_priority"],
                    "answer": answer
                })

            elif action["action"] == "assign_ticket":
                ticket = db_session.query(Ticket).filter_by(id=action["ticket_id"]).first()
                if not ticket:
                    answer = f"Ticket #{action['ticket_id']} not found."
                    log_chat_interaction(user_id, query, answer, "error", action_type=action["action"])
                    return jsonify({
                        "success": True,
                        "type": "error",
                        "answer": answer
                    })

                # Find user by name
                assignee_name = action["assignee"]
                user = db_session.query(User).filter(
                    User.name.ilike(f"%{assignee_name}%")
                ).first()

                if not user:
                    answer = f"User '{assignee_name}' not found. Please check the name and try again."
                    log_chat_interaction(user_id, query, answer, "error", action_type=action["action"])
                    return jsonify({
                        "success": True,
                        "type": "error",
                        "answer": answer
                    })

                answer = f"Do you want to assign **Ticket #{action['ticket_id']}** to **{user.username}**?\n\nTicket: {ticket.subject}\nCurrent Assignee: {ticket.assigned_to.username if ticket.assigned_to else 'Unassigned'}"
                log_chat_interaction(user_id, query, answer, "action_confirm", action_type=action["action"])
                return jsonify({
                    "success": True,
                    "type": "action_confirm",
                    "action": action["action"],
                    "ticket_id": action["ticket_id"],
                    "ticket_subject": ticket.subject,
                    "current_assignee": ticket.assigned_to.username if ticket.assigned_to else "Unassigned",
                    "new_assignee_id": user.id,
                    "new_assignee": user.username,
                    "answer": answer
                })

            elif action["action"] == "report_bug":
                # Bug report doesn't need to lookup anything, just confirm with user
                answer = f"Do you want to create a bug report?\n\n**Title:** {action['bug_title']}\n**Severity:** {action['severity']}\n\nYou can add more details after creation."
                log_chat_interaction(user_id, query, answer, "action_confirm", action_type=action["action"])
                return jsonify({
                    "success": True,
                    "type": "action_confirm",
                    "action": action["action"],
                    "bug_title": action["bug_title"],
                    "severity": action["severity"],
                    "answer": answer
                })

            elif action["action"] == "user_permissions":
                # Query user permissions - no confirmation needed, return info directly
                username = action["username"]
                from sqlalchemy import or_
                user = db_session.query(User).filter(
                    or_(
                        User.username.ilike(f"%{username}%"),
                        User.email.ilike(f"%{username}%")
                    )
                ).first()

                if not user:
                    answer = f"User '{username}' not found. Please check the name and try again."
                    log_chat_interaction(user_id, query, answer, "error", action_type=action["action"])
                    return jsonify({
                        "success": True,
                        "type": "error",
                        "answer": answer
                    })

                # Build permissions list
                permissions_list = []
                if user.permissions:
                    perm = user.permissions
                    perm_attrs = [
                        ('can_view_tickets', 'View Tickets'),
                        ('can_create_tickets', 'Create Tickets'),
                        ('can_edit_tickets', 'Edit Tickets'),
                        ('can_delete_tickets', 'Delete Tickets'),
                        ('can_view_assets', 'View Assets'),
                        ('can_create_assets', 'Create Assets'),
                        ('can_edit_assets', 'Edit Assets'),
                        ('can_delete_assets', 'Delete Assets'),
                        ('can_export_data', 'Export Data'),
                        ('can_import_data', 'Import Data'),
                        ('can_manage_users', 'Manage Users'),
                        ('can_view_reports', 'View Reports'),
                        ('can_access_admin', 'Admin Access'),
                        ('can_access_inventory_audit', 'Inventory Audit'),
                        ('can_create_bugs', 'Create Bug Reports'),
                        ('can_create_features', 'Create Feature Requests'),
                    ]
                    for attr, label in perm_attrs:
                        if hasattr(perm, attr) and getattr(perm, attr):
                            permissions_list.append(f"✅ {label}")

                if not permissions_list:
                    permissions_list.append("No specific permissions assigned")

                # Get country permissions
                country_perms = []
                if hasattr(user, 'country_permissions') and user.country_permissions:
                    for cp in user.country_permissions:
                        country_perms.append(cp.country.value if hasattr(cp.country, 'value') else str(cp.country))

                answer = f"**User: {user.username}**\n"
                answer += f"**Username:** {user.username}\n"
                answer += f"**Email:** {user.email}\n"
                answer += f"**Type:** {user.user_type.value if user.user_type else 'N/A'}\n"
                if country_perms:
                    answer += f"**Countries:** {', '.join(country_perms)}\n"
                answer += f"\n**Permissions:**\n" + "\n".join(permissions_list)

                log_chat_interaction(user_id, query, answer, "answer", action_type=action["action"])
                return jsonify({
                    "success": True,
                    "type": "answer",
                    "answer": answer,
                    "user_url": f"/admin/users/{user.id}/edit"
                })

            elif action["action"] == "user_info":
                # Query user info - similar to permissions but more basic
                username = action["username"]
                from sqlalchemy import or_
                user = db_session.query(User).filter(
                    or_(
                        User.username.ilike(f"%{username}%"),
                        User.email.ilike(f"%{username}%")
                    )
                ).first()

                if not user:
                    answer = f"User '{username}' not found. Please check the name and try again."
                    log_chat_interaction(user_id, query, answer, "error", action_type=action["action"])
                    return jsonify({
                        "success": True,
                        "type": "error",
                        "answer": answer
                    })

                # Get country permissions
                country_perms = []
                if hasattr(user, 'country_permissions') and user.country_permissions:
                    for cp in user.country_permissions:
                        country_perms.append(cp.country.value if hasattr(cp.country, 'value') else str(cp.country))

                answer = f"**User: {user.username}**\n\n"
                answer += f"• **Username:** {user.username}\n"
                answer += f"• **Email:** {user.email}\n"
                answer += f"• **Type:** {user.user_type.value if user.user_type else 'N/A'}\n"
                answer += f"• **Active:** {'Yes' if user.is_active else 'No'}\n"
                if country_perms:
                    answer += f"• **Countries:** {', '.join(country_perms)}\n"
                if user.company:
                    answer += f"• **Company:** {user.company.name}\n"
                answer += f"\n[View/Edit User](/admin/users/{user.id}/edit)"

                log_chat_interaction(user_id, query, answer, "answer", action_type=action["action"])
                return jsonify({
                    "success": True,
                    "type": "answer",
                    "answer": answer,
                    "user_url": f"/admin/users/{user.id}/edit"
                })

            elif action["action"] == "list_users":
                # List all users in the system
                users = db_session.query(User).filter(User.is_deleted == False).order_by(User.username).all()

                if not users:
                    answer = "No users found in the system."
                    log_chat_interaction(user_id, query, answer, "answer", action_type=action["action"])
                    return jsonify({
                        "success": True,
                        "type": "answer",
                        "answer": answer
                    })

                # Group users by type
                users_by_type = {}
                for user in users:
                    user_type = user.user_type.value if user.user_type else 'Unknown'
                    if user_type not in users_by_type:
                        users_by_type[user_type] = []
                    users_by_type[user_type].append(user)

                answer = f"**Users in System ({len(users)} total)**\n\n"

                for user_type, type_users in sorted(users_by_type.items()):
                    answer += f"**{user_type}** ({len(type_users)}):\n"
                    for u in type_users[:10]:  # Limit to 10 per type to avoid huge responses
                        status = "✓" if u.is_active else "✗"
                        answer += f"• {status} [{u.username}](/admin/users/{u.id}/edit)"
                        if u.email:
                            answer += f" - {u.email}"
                        answer += "\n"
                    if len(type_users) > 10:
                        answer += f"  ... and {len(type_users) - 10} more\n"
                    answer += "\n"

                answer += f"\n[Manage Users](/admin/users)"

                log_chat_interaction(user_id, query, answer, "answer", action_type=action["action"])
                return jsonify({
                    "success": True,
                    "type": "answer",
                    "answer": answer,
                    "url": "/admin/users"
                })

            elif action["action"] == "asset_lookup":
                # Look up asset by serial number
                serial_number = action["serial_number"]
                from models.asset import Asset
                from sqlalchemy import or_

                # Search by serial number or asset tag
                asset = db_session.query(Asset).filter(
                    or_(
                        Asset.serial_num.ilike(f"%{serial_number}%"),
                        Asset.asset_tag.ilike(f"%{serial_number}%")
                    )
                ).first()

                if not asset:
                    answer = f"No asset found with serial number or asset tag matching '{serial_number}'."
                    log_chat_interaction(user_id, query, answer, "error", action_type=action["action"])
                    return jsonify({
                        "success": True,
                        "type": "error",
                        "answer": answer
                    })

                # Build asset info response
                answer = f"**Asset Found**\n\n"
                answer += f"• **Asset Tag:** {asset.asset_tag or 'N/A'}\n"
                answer += f"• **Name:** {asset.name or 'N/A'}\n"
                answer += f"• **Serial Number:** {asset.serial_num or 'N/A'}\n"
                answer += f"• **Status:** {asset.status.value if asset.status else 'N/A'}\n"
                answer += f"• **Category:** {asset.category or 'N/A'}\n"
                answer += f"• **Manufacturer:** {asset.manufacturer or 'N/A'}\n"
                answer += f"• **Model:** {asset.model or 'N/A'}\n"

                if asset.company:
                    answer += f"• **Company:** {asset.company.name}\n"
                if asset.country:
                    answer += f"• **Country:** {asset.country}\n"
                if hasattr(asset, 'location_obj') and asset.location_obj:
                    answer += f"• **Location:** {asset.location_obj.name}\n"
                if asset.assigned_to:
                    answer += f"• **Assigned To:** {asset.assigned_to.username}\n"
                if asset.customer_user:
                    answer += f"• **Customer:** {asset.customer_user.name}\n"

                answer += f"\n[View Asset Details](/inventory/sf/asset/{asset.id})"

                log_chat_interaction(user_id, query, answer, "answer", action_type=action["action"])
                return jsonify({
                    "success": True,
                    "type": "answer",
                    "answer": answer,
                    "url": f"/inventory/sf/asset/{asset.id}"
                })

            elif action["action"] == "tracking_lookup":
                # Look up SingPost tracking number
                tracking_number = action["tracking_number"]

                try:
                    from utils.singpost_tracking import get_singpost_tracking_client

                    singpost_client = get_singpost_tracking_client()

                    if not singpost_client.is_configured():
                        answer = "SingPost Tracking API is not configured. Please contact an administrator."
                        log_chat_interaction(user_id, query, answer, "error", action_type=action["action"])
                        return jsonify({
                            "success": True,
                            "type": "error",
                            "answer": answer
                        })

                    result = singpost_client.track_single(tracking_number)

                    if result and result.get('success'):
                        # Build tracking info response
                        answer = f"**SingPost Tracking: {tracking_number}**\n\n"
                        answer += f"📦 **Status:** {result.get('status', 'Unknown')}\n"

                        was_pushed = result.get('was_pushed', False)
                        if was_pushed:
                            answer += f"✅ **Received by SingPost:** Yes\n"
                        else:
                            answer += f"⏳ **Received by SingPost:** Not yet (Information only)\n"

                        if result.get('origin_country'):
                            answer += f"📍 **Origin:** {result.get('origin_country')}\n"
                        if result.get('destination_country'):
                            answer += f"🎯 **Destination:** {result.get('destination_country')}\n"
                        if result.get('posting_date'):
                            answer += f"📅 **Posting Date:** {result.get('posting_date')}\n"

                        events = result.get('events', [])
                        if events:
                            answer += f"\n**Recent Events:**\n"
                            for i, event in enumerate(events[:5]):  # Show last 5 events
                                event_desc = event.get('description', 'Unknown')
                                event_date = event.get('date', '')
                                event_time = event.get('time', '')
                                answer += f"• {event_desc}"
                                if event_date or event_time:
                                    answer += f" ({event_date} {event_time})"
                                answer += "\n"
                            if len(events) > 5:
                                answer += f"\n_...and {len(events) - 5} more events_"

                        answer += f"\n\n[View in Parcel Tracking](/parcel-tracking)"

                        log_chat_interaction(user_id, query, answer, "answer", action_type=action["action"])
                        return jsonify({
                            "success": True,
                            "type": "answer",
                            "answer": answer,
                            "url": "/parcel-tracking"
                        })
                    else:
                        error_msg = result.get('error', 'Tracking number not found') if result else 'Failed to fetch tracking data'
                        answer = f"Could not find tracking information for **{tracking_number}**.\n\n{error_msg}"
                        log_chat_interaction(user_id, query, answer, "error", action_type=action["action"])
                        return jsonify({
                            "success": True,
                            "type": "error",
                            "answer": answer
                        })

                except Exception as e:
                    answer = f"Error looking up tracking: {str(e)}"
                    log_chat_interaction(user_id, query, answer, "error", action_type=action["action"])
                    return jsonify({
                        "success": True,
                        "type": "error",
                        "answer": answer
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

        # Log the interaction
        log_chat_interaction(
            user_id, query, result["answer"], result["type"],
            matched_question=result.get("question") if result["type"] == "answer" else None
        )

        return jsonify(response)

    # Fallback
    import random
    fallback_answer = random.choice(FALLBACK_RESPONSES)
    log_chat_interaction(user_id, query, fallback_answer, "fallback")
    return jsonify({
        "success": True,
        "type": "fallback",
        "answer": fallback_answer,
        "suggestions": get_suggested_questions(5)
    })


@chatbot_bp.route('/execute', methods=['POST'])
@login_required
def execute_action():
    """Execute a confirmed action"""
    data = request.get_json()
    action = data.get('action')

    if not action:
        return jsonify({"success": False, "error": "Missing action"})

    db_session = SessionLocal()
    try:
        # Handle bug report action (doesn't need ticket_id)
        if action == "report_bug":
            from models.bug_report import BugReport, BugStatus, BugSeverity, BugPriority

            bug_title = data.get('bug_title')
            bug_description = data.get('bug_description', '')
            severity = data.get('severity', 'Medium')

            if not bug_title:
                return jsonify({"success": False, "error": "Missing bug title"})

            # Create the bug report
            try:
                bug = BugReport(
                    title=bug_title,
                    description=bug_description or f"Bug reported via chatbot: {bug_title}",
                    severity=BugSeverity(severity),
                    priority=BugPriority("Medium"),
                    reporter_id=current_user.id,
                    component="Chatbot Report"
                )
                db_session.add(bug)
                db_session.commit()

                return jsonify({
                    "success": True,
                    "message": f"Bug report {bug.display_id} created successfully!",
                    "bug_url": f"/development/bugs/{bug.id}",
                    "bug_id": bug.display_id
                })
            except Exception as e:
                db_session.rollback()
                return jsonify({"success": False, "error": f"Failed to create bug report: {str(e)}"})

        # For ticket-related actions, require ticket_id
        ticket_id = data.get('ticket_id')
        if not ticket_id:
            return jsonify({"success": False, "error": "Missing ticket_id"})

        ticket = db_session.query(Ticket).filter_by(id=ticket_id).first()
        if not ticket:
            return jsonify({"success": False, "error": f"Ticket #{ticket_id} not found"})

        # Check permissions
        user_permissions = current_user.permissions
        if not user_permissions or not user_permissions.can_edit_tickets:
            return jsonify({"success": False, "error": "You don't have permission to edit tickets"})

        if action == "update_ticket_status":
            new_status = data.get('new_status')
            if not new_status:
                return jsonify({"success": False, "error": "Missing new_status"})

            # Check if it's a system status or custom status
            status_set = False

            # First try by enum name (e.g., "RESOLVED")
            if hasattr(TicketStatus, new_status):
                ticket.status = getattr(TicketStatus, new_status)
                status_set = True
            else:
                # Try by enum value (e.g., "Resolved")
                try:
                    ticket.status = TicketStatus(new_status)
                    status_set = True
                except ValueError:
                    pass

            if not status_set:
                # Try custom status
                custom_status = db_session.query(CustomTicketStatus).filter_by(
                    name=new_status,
                    is_active=True
                ).first()
                if custom_status:
                    ticket.custom_status_id = custom_status.id
                    ticket.status = TicketStatus.PROCESSING  # Set base status
                    status_set = True

            if not status_set:
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

            # First try by enum name (e.g., "HIGH")
            if hasattr(TicketPriority, new_priority):
                ticket.priority = getattr(TicketPriority, new_priority)
            else:
                # Try by enum value (e.g., "High")
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
                "message": f"Ticket #{ticket_id} assigned to {user.username}",
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


# ============= Admin Routes for Chat Logs =============

@chatbot_bp.route('/admin/logs')
@login_required
def admin_chat_logs():
    """View chat logs for training purposes"""
    # Check if user is admin
    if not (current_user.is_super_admin or current_user.is_developer):
        return jsonify({"error": "Access denied"}), 403

    return render_template('chatbot/admin_logs.html')


@chatbot_bp.route('/api/logs')
@login_required
def api_get_chat_logs():
    """API to get chat logs with filtering"""
    if not (current_user.is_super_admin or current_user.is_developer):
        return jsonify({"error": "Access denied"}), 403

    db_session = SessionLocal()
    try:
        from sqlalchemy import desc, func
        from datetime import datetime, timedelta

        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        response_type = request.args.get('response_type', '')
        search = request.args.get('search', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')

        # Build query
        query = db_session.query(ChatLog)

        if response_type:
            query = query.filter(ChatLog.response_type == response_type)

        if search:
            query = query.filter(ChatLog.query.ilike(f'%{search}%'))

        if date_from:
            try:
                from_date = datetime.strptime(date_from, '%Y-%m-%d')
                query = query.filter(ChatLog.created_at >= from_date)
            except ValueError:
                pass

        if date_to:
            try:
                to_date = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(ChatLog.created_at < to_date)
            except ValueError:
                pass

        # Get total count
        total = query.count()

        # Get paginated results
        logs = query.order_by(desc(ChatLog.created_at))\
            .offset((page - 1) * per_page)\
            .limit(per_page)\
            .all()

        # Get statistics
        stats = {
            'total_queries': db_session.query(ChatLog).count(),
            'fallback_count': db_session.query(ChatLog).filter(ChatLog.response_type == 'fallback').count(),
            'answer_count': db_session.query(ChatLog).filter(ChatLog.response_type == 'answer').count(),
            'greeting_count': db_session.query(ChatLog).filter(ChatLog.response_type == 'greeting').count(),
            'action_count': db_session.query(ChatLog).filter(ChatLog.response_type == 'action_confirm').count(),
        }

        # Get top unanswered queries (fallbacks)
        top_fallbacks = db_session.query(
            ChatLog.query,
            func.count(ChatLog.id).label('count')
        ).filter(
            ChatLog.response_type == 'fallback'
        ).group_by(ChatLog.query).order_by(desc('count')).limit(10).all()

        return jsonify({
            'success': True,
            'logs': [log.to_dict() for log in logs],
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page,
            'stats': stats,
            'top_fallbacks': [{'query': q, 'count': c} for q, c in top_fallbacks]
        })

    finally:
        db_session.close()


@chatbot_bp.route('/api/logs/export')
@login_required
def api_export_chat_logs():
    """Export chat logs as CSV for training"""
    if not (current_user.is_super_admin or current_user.is_developer):
        return jsonify({"error": "Access denied"}), 403

    db_session = SessionLocal()
    try:
        import csv
        import io
        from flask import Response

        # Get all logs or filtered
        response_type = request.args.get('response_type', '')

        query = db_session.query(ChatLog)
        if response_type:
            query = query.filter(ChatLog.response_type == response_type)

        logs = query.order_by(ChatLog.created_at.desc()).all()

        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            'ID', 'Date', 'User', 'Query', 'Response', 'Response Type',
            'Matched Question', 'Action Type', 'Was Helpful', 'Feedback'
        ])

        # Data
        for log in logs:
            writer.writerow([
                log.id,
                log.created_at.strftime('%Y-%m-%d %H:%M:%S') if log.created_at else '',
                log.user_name or 'Anonymous',
                log.query,
                log.response,
                log.response_type,
                log.matched_question or '',
                log.action_type or '',
                'Yes' if log.was_helpful else ('No' if log.was_helpful is False else ''),
                log.feedback or ''
            ])

        output.seek(0)

        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=chat_logs.csv'}
        )

    finally:
        db_session.close()


@chatbot_bp.route('/api/logs/feedback', methods=['POST'])
@login_required
def api_submit_feedback():
    """Submit feedback for a chat response"""
    data = request.get_json()
    log_id = data.get('log_id')
    was_helpful = data.get('was_helpful')
    feedback = data.get('feedback', '')

    if not log_id:
        return jsonify({"success": False, "error": "Missing log_id"})

    db_session = SessionLocal()
    try:
        log = db_session.query(ChatLog).filter_by(id=log_id).first()
        if not log:
            return jsonify({"success": False, "error": "Log not found"})

        log.was_helpful = was_helpful
        log.feedback = feedback
        db_session.commit()

        return jsonify({"success": True, "message": "Feedback saved"})

    except Exception as e:
        db_session.rollback()
        return jsonify({"success": False, "error": str(e)})
    finally:
        db_session.close()


# ============= Mobile API Routes for iOS App =============
# These routes use JWT token authentication instead of session-based auth

def verify_mobile_token_for_chatbot(token):
    """Verify JWT token and return user for chatbot API"""
    try:
        import jwt
        from flask import current_app
        secret_key = current_app.config.get('SECRET_KEY', 'fallback-secret-key')

        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        user_id = payload['user_id']

        db_session = SessionLocal()
        try:
            user = db_session.query(User).filter(User.id == user_id).first()
            return user
        finally:
            db_session.close()

    except Exception:
        return None


def mobile_chatbot_auth(f):
    """Decorator to require mobile JWT authentication for chatbot"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')

        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing or invalid authorization header'}), 401

        token = auth_header.split(' ')[1]
        user = verify_mobile_token_for_chatbot(token)

        if not user:
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

        # Set current user for the request
        request.mobile_chatbot_user = user
        return f(*args, **kwargs)

    return decorated_function


@chatbot_bp.route('/mobile/ask', methods=['POST'])
@mobile_chatbot_auth
def mobile_ask():
    """
    Mobile API: Process a user question and return an answer

    POST /chatbot/mobile/ask
    Headers: Authorization: Bearer <jwt_token>
    Body: {
        "query": "How do I create a ticket?"
    }

    Response: {
        "success": true,
        "type": "answer",
        "answer": "To create a new ticket...",
        "matched_question": "How do I create a new ticket?",
        "url": "/tickets/create",
        "suggestions": ["...", "..."]
    }
    """
    data = request.get_json()
    query = data.get('query', '').strip() if data else ''

    if not query:
        return jsonify({
            "success": False,
            "error": "Please enter a question"
        })

    user = request.mobile_chatbot_user
    user_id = user.id if user else None

    # First, check if this is an action command
    action = parse_action(query)
    if action:
        # Validate the action and return confirmation prompt
        db_session = SessionLocal()
        try:
            if action["action"] == "update_ticket_status":
                ticket = db_session.query(Ticket).filter_by(id=action["ticket_id"]).first()
                if not ticket:
                    answer = f"Ticket #{action['ticket_id']} not found."
                    log_chat_interaction(user_id, query, answer, "error", action_type=action["action"])
                    return jsonify({
                        "success": True,
                        "type": "error",
                        "answer": answer
                    })

                # Check for custom status
                custom_status = db_session.query(CustomTicketStatus).filter_by(
                    name=action["new_status"],
                    is_active=True
                ).first()

                status_display = action["new_status"]
                if custom_status:
                    status_display = custom_status.display_name

                answer = f"Do you want to update **Ticket #{action['ticket_id']}** status to **{status_display}**?\n\nTicket: {ticket.subject}\nCurrent Status: {ticket.status.value if hasattr(ticket.status, 'value') else ticket.status}"
                log_chat_interaction(user_id, query, answer, "action_confirm", action_type=action["action"])
                return jsonify({
                    "success": True,
                    "type": "action_confirm",
                    "action": action["action"],
                    "ticket_id": action["ticket_id"],
                    "ticket_subject": ticket.subject,
                    "current_status": ticket.status.value if hasattr(ticket.status, 'value') else str(ticket.status),
                    "new_status": action["new_status"],
                    "answer": answer
                })

            elif action["action"] == "update_ticket_priority":
                ticket = db_session.query(Ticket).filter_by(id=action["ticket_id"]).first()
                if not ticket:
                    answer = f"Ticket #{action['ticket_id']} not found."
                    log_chat_interaction(user_id, query, answer, "error", action_type=action["action"])
                    return jsonify({
                        "success": True,
                        "type": "error",
                        "answer": answer
                    })

                answer = f"Do you want to change **Ticket #{action['ticket_id']}** priority to **{action['new_priority']}**?\n\nTicket: {ticket.subject}\nCurrent Priority: {ticket.priority.value if ticket.priority else 'None'}"
                log_chat_interaction(user_id, query, answer, "action_confirm", action_type=action["action"])
                return jsonify({
                    "success": True,
                    "type": "action_confirm",
                    "action": action["action"],
                    "ticket_id": action["ticket_id"],
                    "ticket_subject": ticket.subject,
                    "current_priority": ticket.priority.value if ticket.priority else "None",
                    "new_priority": action["new_priority"],
                    "answer": answer
                })

            elif action["action"] == "assign_ticket":
                ticket = db_session.query(Ticket).filter_by(id=action["ticket_id"]).first()
                if not ticket:
                    answer = f"Ticket #{action['ticket_id']} not found."
                    log_chat_interaction(user_id, query, answer, "error", action_type=action["action"])
                    return jsonify({
                        "success": True,
                        "type": "error",
                        "answer": answer
                    })

                # Find user by name
                assignee_name = action["assignee"]
                assignee_user = db_session.query(User).filter(
                    User.name.ilike(f"%{assignee_name}%")
                ).first()

                if not assignee_user:
                    answer = f"User '{assignee_name}' not found. Please check the name and try again."
                    log_chat_interaction(user_id, query, answer, "error", action_type=action["action"])
                    return jsonify({
                        "success": True,
                        "type": "error",
                        "answer": answer
                    })

                answer = f"Do you want to assign **Ticket #{action['ticket_id']}** to **{assignee_user.username}**?\n\nTicket: {ticket.subject}\nCurrent Assignee: {ticket.assigned_to.username if ticket.assigned_to else 'Unassigned'}"
                log_chat_interaction(user_id, query, answer, "action_confirm", action_type=action["action"])
                return jsonify({
                    "success": True,
                    "type": "action_confirm",
                    "action": action["action"],
                    "ticket_id": action["ticket_id"],
                    "ticket_subject": ticket.subject,
                    "current_assignee": ticket.assigned_to.username if ticket.assigned_to else "Unassigned",
                    "new_assignee_id": assignee_user.id,
                    "new_assignee": assignee_user.username,
                    "answer": answer
                })

            elif action["action"] == "report_bug":
                answer = f"Do you want to create a bug report?\n\n**Title:** {action['bug_title']}\n**Severity:** {action['severity']}\n\nYou can add more details after creation."
                log_chat_interaction(user_id, query, answer, "action_confirm", action_type=action["action"])
                return jsonify({
                    "success": True,
                    "type": "action_confirm",
                    "action": action["action"],
                    "bug_title": action["bug_title"],
                    "severity": action["severity"],
                    "answer": answer
                })

            elif action["action"] == "asset_lookup":
                # Look up asset by serial number
                serial_number = action["serial_number"]
                from models.asset import Asset
                from sqlalchemy import or_

                # Search by serial number or asset tag
                asset = db_session.query(Asset).filter(
                    or_(
                        Asset.serial_num.ilike(f"%{serial_number}%"),
                        Asset.asset_tag.ilike(f"%{serial_number}%")
                    )
                ).first()

                if not asset:
                    answer = f"No asset found with serial number or asset tag matching '{serial_number}'."
                    log_chat_interaction(user_id, query, answer, "error", action_type=action["action"])
                    return jsonify({
                        "success": True,
                        "type": "error",
                        "answer": answer
                    })

                # Build asset info response
                answer = f"**Asset Found**\n\n"
                answer += f"• **Asset Tag:** {asset.asset_tag or 'N/A'}\n"
                answer += f"• **Name:** {asset.name or 'N/A'}\n"
                answer += f"• **Serial Number:** {asset.serial_num or 'N/A'}\n"
                answer += f"• **Status:** {asset.status.value if asset.status else 'N/A'}\n"
                answer += f"• **Model:** {asset.model or 'N/A'}\n"
                answer += f"• **Manufacturer:** {asset.manufacturer or 'N/A'}\n"

                if asset.company:
                    answer += f"• **Company:** {asset.company.name}\n"
                if asset.country:
                    answer += f"• **Country:** {asset.country}\n"

                log_chat_interaction(user_id, query, answer, "answer", action_type=action["action"])
                return jsonify({
                    "success": True,
                    "type": "answer",
                    "answer": answer,
                    "asset": {
                        "id": asset.id,
                        "asset_tag": asset.asset_tag,
                        "name": asset.name,
                        "serial_num": asset.serial_num,
                        "status": asset.status.value if asset.status else None,
                        "model": asset.model,
                        "manufacturer": asset.manufacturer
                    }
                })

            elif action["action"] == "tracking_lookup":
                # Look up SingPost tracking number
                tracking_number = action["tracking_number"]

                try:
                    from utils.singpost_tracking import get_singpost_tracking_client

                    singpost_client = get_singpost_tracking_client()

                    if not singpost_client.is_configured():
                        answer = "SingPost Tracking API is not configured. Please contact an administrator."
                        log_chat_interaction(user_id, query, answer, "error", action_type=action["action"])
                        return jsonify({
                            "success": True,
                            "type": "error",
                            "answer": answer
                        })

                    result = singpost_client.track_single(tracking_number)

                    if result and result.get('success'):
                        # Build tracking info response
                        answer = f"**SingPost Tracking: {tracking_number}**\n\n"
                        answer += f"📦 **Status:** {result.get('status', 'Unknown')}\n"

                        was_pushed = result.get('was_pushed', False)
                        if was_pushed:
                            answer += f"✅ **Received by SingPost:** Yes\n"
                        else:
                            answer += f"⏳ **Received by SingPost:** Not yet (Information only)\n"

                        if result.get('origin_country'):
                            answer += f"📍 **Origin:** {result.get('origin_country')}\n"
                        if result.get('destination_country'):
                            answer += f"🎯 **Destination:** {result.get('destination_country')}\n"
                        if result.get('posting_date'):
                            answer += f"📅 **Posting Date:** {result.get('posting_date')}\n"

                        events = result.get('events', [])
                        if events:
                            answer += f"\n**Recent Events:**\n"
                            for i, event in enumerate(events[:5]):  # Show last 5 events
                                event_desc = event.get('description', 'Unknown')
                                event_date = event.get('date', '')
                                event_time = event.get('time', '')
                                answer += f"• {event_desc}"
                                if event_date or event_time:
                                    answer += f" ({event_date} {event_time})"
                                answer += "\n"
                            if len(events) > 5:
                                answer += f"\n_...and {len(events) - 5} more events_"

                        log_chat_interaction(user_id, query, answer, "answer", action_type=action["action"])
                        return jsonify({
                            "success": True,
                            "type": "answer",
                            "answer": answer,
                            "tracking": {
                                "tracking_number": tracking_number,
                                "carrier": "SingPost",
                                "status": result.get('status'),
                                "was_pushed": was_pushed,
                                "origin_country": result.get('origin_country'),
                                "destination_country": result.get('destination_country'),
                                "events": events
                            }
                        })
                    else:
                        error_msg = result.get('error', 'Tracking number not found') if result else 'Failed to fetch tracking data'
                        answer = f"Could not find tracking information for **{tracking_number}**.\n\n{error_msg}"
                        log_chat_interaction(user_id, query, answer, "error", action_type=action["action"])
                        return jsonify({
                            "success": True,
                            "type": "error",
                            "answer": answer
                        })

                except Exception as e:
                    answer = f"Error looking up tracking: {str(e)}"
                    log_chat_interaction(user_id, query, answer, "error", action_type=action["action"])
                    return jsonify({
                        "success": True,
                        "type": "error",
                        "answer": answer
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
            response["suggestions"] = get_suggested_questions(3)

        # Log the interaction
        log_chat_interaction(
            user_id, query, result["answer"], result["type"],
            matched_question=result.get("question") if result["type"] == "answer" else None
        )

        return jsonify(response)

    # Fallback
    import random
    fallback_answer = random.choice(FALLBACK_RESPONSES)
    log_chat_interaction(user_id, query, fallback_answer, "fallback")
    return jsonify({
        "success": True,
        "type": "fallback",
        "answer": fallback_answer,
        "suggestions": get_suggested_questions(5)
    })


@chatbot_bp.route('/mobile/execute', methods=['POST'])
@mobile_chatbot_auth
def mobile_execute_action():
    """
    Mobile API: Execute a confirmed action

    POST /chatbot/mobile/execute
    Headers: Authorization: Bearer <jwt_token>
    Body: {
        "action": "update_ticket_status",
        "ticket_id": 123,
        "new_status": "RESOLVED"
    }

    Response: {
        "success": true,
        "message": "Ticket #123 status updated to RESOLVED",
        "ticket_url": "/tickets/123"
    }
    """
    data = request.get_json()
    action = data.get('action') if data else None

    if not action:
        return jsonify({"success": False, "error": "Missing action"})

    user = request.mobile_chatbot_user

    db_session = SessionLocal()
    try:
        # Handle bug report action
        if action == "report_bug":
            from models.bug_report import BugReport, BugStatus, BugSeverity, BugPriority

            bug_title = data.get('bug_title')
            bug_description = data.get('bug_description', '')
            severity = data.get('severity', 'Medium')

            if not bug_title:
                return jsonify({"success": False, "error": "Missing bug title"})

            try:
                bug = BugReport(
                    title=bug_title,
                    description=bug_description or f"Bug reported via mobile chatbot: {bug_title}",
                    severity=BugSeverity(severity),
                    priority=BugPriority("Medium"),
                    reporter_id=user.id,
                    component="Mobile Chatbot Report"
                )
                db_session.add(bug)
                db_session.commit()

                return jsonify({
                    "success": True,
                    "message": f"Bug report {bug.display_id} created successfully!",
                    "bug_url": f"/development/bugs/{bug.id}",
                    "bug_id": bug.display_id
                })
            except Exception as e:
                db_session.rollback()
                return jsonify({"success": False, "error": f"Failed to create bug report: {str(e)}"})

        # For ticket-related actions, require ticket_id
        ticket_id = data.get('ticket_id')
        if not ticket_id:
            return jsonify({"success": False, "error": "Missing ticket_id"})

        ticket = db_session.query(Ticket).filter_by(id=ticket_id).first()
        if not ticket:
            return jsonify({"success": False, "error": f"Ticket #{ticket_id} not found"})

        # Check permissions
        user_permissions = user.permissions
        if not user_permissions or not user_permissions.can_edit_tickets:
            return jsonify({"success": False, "error": "You don't have permission to edit tickets"})

        if action == "update_ticket_status":
            new_status = data.get('new_status')
            if not new_status:
                return jsonify({"success": False, "error": "Missing new_status"})

            # Check if it's a system status or custom status
            status_set = False

            if hasattr(TicketStatus, new_status):
                ticket.status = getattr(TicketStatus, new_status)
                status_set = True
            else:
                try:
                    ticket.status = TicketStatus(new_status)
                    status_set = True
                except ValueError:
                    pass

            if not status_set:
                custom_status = db_session.query(CustomTicketStatus).filter_by(
                    name=new_status,
                    is_active=True
                ).first()
                if custom_status:
                    ticket.custom_status_id = custom_status.id
                    ticket.status = TicketStatus.PROCESSING
                    status_set = True

            if not status_set:
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

            if hasattr(TicketPriority, new_priority):
                ticket.priority = getattr(TicketPriority, new_priority)
            else:
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

            assignee = db_session.query(User).filter_by(id=new_assignee_id).first()
            if not assignee:
                return jsonify({"success": False, "error": "User not found"})

            ticket.assigned_to_id = assignee.id
            db_session.commit()
            return jsonify({
                "success": True,
                "message": f"Ticket #{ticket_id} assigned to {assignee.username}",
                "ticket_url": f"/tickets/{ticket_id}"
            })

        else:
            return jsonify({"success": False, "error": f"Unknown action: {action}"})

    except Exception as e:
        db_session.rollback()
        return jsonify({"success": False, "error": str(e)})
    finally:
        db_session.close()


@chatbot_bp.route('/mobile/suggestions', methods=['GET'])
@mobile_chatbot_auth
def mobile_suggestions():
    """
    Mobile API: Get suggested questions

    GET /chatbot/mobile/suggestions
    Headers: Authorization: Bearer <jwt_token>

    Response: {
        "success": true,
        "suggestions": [
            "How do I create a new ticket?",
            "How do I add a new asset?",
            ...
        ]
    }
    """
    return jsonify({
        "success": True,
        "suggestions": get_suggested_questions(6)
    })


@chatbot_bp.route('/mobile/history', methods=['GET'])
@mobile_chatbot_auth
def mobile_chat_history():
    """
    Mobile API: Get user's chat history

    GET /chatbot/mobile/history?limit=20
    Headers: Authorization: Bearer <jwt_token>

    Response: {
        "success": true,
        "history": [
            {
                "id": 1,
                "query": "How do I create a ticket?",
                "response": "To create a new ticket...",
                "response_type": "answer",
                "created_at": "2025-01-01T10:00:00Z"
            },
            ...
        ]
    }
    """
    user = request.mobile_chatbot_user
    limit = request.args.get('limit', 20, type=int)
    limit = min(limit, 100)  # Max 100

    db_session = SessionLocal()
    try:
        from sqlalchemy import desc

        logs = db_session.query(ChatLog).filter(
            ChatLog.user_id == user.id
        ).order_by(desc(ChatLog.created_at)).limit(limit).all()

        history = []
        for log in logs:
            history.append({
                "id": log.id,
                "query": log.query,
                "response": log.response,
                "response_type": log.response_type,
                "matched_question": log.matched_question,
                "action_type": log.action_type,
                "created_at": log.created_at.isoformat() + 'Z' if log.created_at else None
            })

        return jsonify({
            "success": True,
            "history": history
        })

    finally:
        db_session.close()


@chatbot_bp.route('/mobile/capabilities', methods=['GET'])
def mobile_capabilities():
    """
    Mobile API: Get chatbot capabilities and documentation

    GET /chatbot/mobile/capabilities

    Response: {
        "success": true,
        "version": "1.0",
        "capabilities": {
            "knowledge_base": true,
            "ticket_actions": true,
            "asset_lookup": true,
            "bug_reporting": true
        },
        "action_commands": {
            "update_status": "Update ticket #123 to resolved",
            "update_priority": "Set ticket #123 priority to high",
            "assign_ticket": "Assign ticket #123 to John",
            "report_bug": "Report bug: Login page not loading",
            "asset_lookup": "Find asset serial ABC123"
        },
        "sample_queries": [...]
    }
    """
    return jsonify({
        "success": True,
        "version": "1.0",
        "description": "Help Assistant chatbot for inventory management system",
        "capabilities": {
            "knowledge_base": True,
            "ticket_actions": True,
            "asset_lookup": True,
            "bug_reporting": True,
            "user_lookup": True,
            "tracking_lookup": True
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
            },
            "tracking_lookup": {
                "description": "Track a SingPost parcel by tracking number",
                "examples": [
                    "Track XZB123456789",
                    "Where is my parcel XZD987654321",
                    "Check tracking XZB000111222",
                    "SingPost tracking XZB999888777"
                ]
            }
        },
        "sample_queries": get_suggested_questions(10),
        "response_types": {
            "greeting": "Initial greeting response",
            "answer": "Direct answer from knowledge base",
            "action_confirm": "Request confirmation before executing action",
            "error": "Error message (e.g., ticket not found)",
            "fallback": "Could not find matching answer"
        }
    })
