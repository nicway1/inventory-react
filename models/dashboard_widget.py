"""
Dashboard Widget System

This module provides a registry-based widget system for the customizable dashboard.
Developers can register new widgets by adding them to the WIDGET_REGISTRY.
"""

from dataclasses import dataclass
from typing import Callable, Dict, Any, List, Optional
from enum import Enum


class WidgetSize(str, Enum):
    """Widget size options for grid layout"""
    SMALL = "small"      # 1 column
    MEDIUM = "medium"    # 2 columns
    LARGE = "large"      # 3 columns
    FULL = "full"        # Full width (4 columns)


class WidgetCategory(str, Enum):
    """Widget categories for organization"""
    STATS = "stats"
    CHARTS = "charts"
    LISTS = "lists"
    ACTIONS = "actions"
    SYSTEM = "system"


@dataclass
class WidgetDefinition:
    """Definition for a dashboard widget"""
    id: str                          # Unique identifier (e.g., 'inventory_stats')
    name: str                        # Display name
    description: str                 # Brief description
    category: WidgetCategory         # Category for grouping
    default_size: WidgetSize         # Default size
    min_size: WidgetSize             # Minimum allowed size
    template: str                    # Jinja2 template path or inline template name
    icon: str                        # Font Awesome icon class (e.g., 'fas fa-box')
    color: str                       # Gradient color scheme (e.g., 'blue', 'green', 'purple')
    required_permissions: List[str]  # List of permission attributes needed
    required_user_types: List[str]   # List of user types that can see this widget
    data_loader: Optional[str]       # Name of function to load widget data
    refreshable: bool = True         # Whether widget supports refresh
    configurable: bool = False       # Whether widget has settings
    default_config: Dict[str, Any] = None  # Default configuration options

    def __post_init__(self):
        if self.default_config is None:
            self.default_config = {}


# Widget Registry - Developers add new widgets here
WIDGET_REGISTRY: Dict[str, WidgetDefinition] = {}


def register_widget(widget: WidgetDefinition):
    """Register a widget in the registry"""
    WIDGET_REGISTRY[widget.id] = widget
    return widget


def get_widget(widget_id: str) -> Optional[WidgetDefinition]:
    """Get a widget definition by ID"""
    return WIDGET_REGISTRY.get(widget_id)


def get_all_widgets() -> List[WidgetDefinition]:
    """Get all registered widgets"""
    return list(WIDGET_REGISTRY.values())


def get_widgets_by_category(category: WidgetCategory) -> List[WidgetDefinition]:
    """Get widgets filtered by category"""
    return [w for w in WIDGET_REGISTRY.values() if w.category == category]


def get_available_widgets_for_user(user) -> List[WidgetDefinition]:
    """Get widgets available for a specific user based on permissions"""
    from database import SessionLocal
    from models.permission import Permission

    available = []

    # Look up the permission record for this user's type
    user_permissions = None
    if user.user_type:
        db = SessionLocal()
        try:
            user_permissions = db.query(Permission).filter_by(user_type=user.user_type).first()
        finally:
            db.close()

    for widget in WIDGET_REGISTRY.values():
        # Check user type restriction
        if widget.required_user_types:
            if user.user_type.value not in widget.required_user_types:
                continue

        # Check permission restrictions
        if widget.required_permissions:
            has_all_perms = True
            for perm in widget.required_permissions:
                # Check permission from the Permission table
                if user_permissions:
                    if not getattr(user_permissions, perm, False):
                        has_all_perms = False
                        break
                else:
                    # No permissions record found - deny access
                    has_all_perms = False
                    break
            if not has_all_perms:
                continue

        available.append(widget)

    return available


# ============================================================================
# DEFAULT WIDGET DEFINITIONS
# Developers can add new widgets by calling register_widget() below
# ============================================================================

# Stats Widgets
register_widget(WidgetDefinition(
    id='inventory_stats',
    name='Inventory Overview',
    description='Total assets and inventory counts',
    category=WidgetCategory.STATS,
    default_size=WidgetSize.SMALL,
    min_size=WidgetSize.SMALL,
    template='widgets/inventory_stats.html',
    icon='fas fa-box',
    color='purple',
    required_permissions=[],
    required_user_types=['SUPER_ADMIN', 'DEVELOPER', 'SUPERVISOR', 'COUNTRY_ADMIN'],
    data_loader='load_inventory_stats'
))

register_widget(WidgetDefinition(
    id='ticket_stats',
    name='Ticket Overview',
    description='Open and total ticket counts',
    category=WidgetCategory.STATS,
    default_size=WidgetSize.SMALL,
    min_size=WidgetSize.SMALL,
    template='widgets/ticket_stats.html',
    icon='fas fa-ticket-alt',
    color='green',
    required_permissions=[],
    required_user_types=['SUPER_ADMIN', 'DEVELOPER', 'CLIENT'],  # Hidden for COUNTRY_ADMIN and SUPERVISOR
    data_loader='load_ticket_stats'
))

register_widget(WidgetDefinition(
    id='customer_stats',
    name='Customer Overview',
    description='Total registered customers',
    category=WidgetCategory.STATS,
    default_size=WidgetSize.SMALL,
    min_size=WidgetSize.SMALL,
    template='widgets/customer_stats.html',
    icon='fas fa-users',
    color='blue',
    required_permissions=[],
    required_user_types=['SUPER_ADMIN', 'DEVELOPER', 'SUPERVISOR'],
    data_loader='load_customer_stats'
))

register_widget(WidgetDefinition(
    id='queue_stats',
    name='Support Queues',
    description='Queue ticket counts and status',
    category=WidgetCategory.STATS,
    default_size=WidgetSize.MEDIUM,
    min_size=WidgetSize.SMALL,
    template='widgets/queue_stats.html',
    icon='fas fa-layer-group',
    color='orange',
    required_permissions=[],
    required_user_types=['SUPER_ADMIN', 'DEVELOPER', 'CLIENT'],  # Hidden for COUNTRY_ADMIN and SUPERVISOR
    data_loader='load_queue_stats'
))

# Chart Widgets
register_widget(WidgetDefinition(
    id='weekly_tickets_chart',
    name='Weekly Tickets',
    description='Ticket creation trend for the week',
    category=WidgetCategory.CHARTS,
    default_size=WidgetSize.MEDIUM,
    min_size=WidgetSize.MEDIUM,
    template='widgets/weekly_tickets_chart.html',
    icon='fas fa-chart-bar',
    color='indigo',
    required_permissions=[],
    required_user_types=['SUPER_ADMIN', 'DEVELOPER', 'CLIENT'],  # Hidden for COUNTRY_ADMIN and SUPERVISOR
    data_loader='load_weekly_ticket_data'
))

register_widget(WidgetDefinition(
    id='asset_status_chart',
    name='Asset Status',
    description='Distribution of assets by status',
    category=WidgetCategory.CHARTS,
    default_size=WidgetSize.MEDIUM,
    min_size=WidgetSize.SMALL,
    template='widgets/asset_status_chart.html',
    icon='fas fa-chart-pie',
    color='cyan',
    required_permissions=[],
    required_user_types=['SUPER_ADMIN', 'DEVELOPER', 'SUPERVISOR', 'COUNTRY_ADMIN'],
    data_loader='load_asset_status_data',
    configurable=True,
    default_config={'chart_type': 'doughnut'}
))

# List Widgets
register_widget(WidgetDefinition(
    id='recent_activities',
    name='Recent Activities',
    description='Latest system activities',
    category=WidgetCategory.LISTS,
    default_size=WidgetSize.MEDIUM,
    min_size=WidgetSize.SMALL,
    template='widgets/recent_activities.html',
    icon='fas fa-history',
    color='gray',
    required_permissions=[],
    required_user_types=['SUPER_ADMIN', 'DEVELOPER', 'SUPERVISOR', 'COUNTRY_ADMIN'],
    data_loader='load_recent_activities',
    configurable=True,
    default_config={'limit': 5}
))

register_widget(WidgetDefinition(
    id='shipments_list',
    name='Active Shipments',
    description='List of shipments with tracking',
    category=WidgetCategory.LISTS,
    default_size=WidgetSize.LARGE,
    min_size=WidgetSize.MEDIUM,
    template='widgets/shipments_list.html',
    icon='fas fa-shipping-fast',
    color='red',
    required_permissions=[],
    required_user_types=['SUPER_ADMIN', 'DEVELOPER', 'SUPERVISOR', 'COUNTRY_ADMIN'],
    data_loader='load_shipments_data',
    configurable=True,
    default_config={'limit': 10}
))

# Action Widgets
register_widget(WidgetDefinition(
    id='quick_actions',
    name='Quick Actions',
    description='Common actions and shortcuts',
    category=WidgetCategory.ACTIONS,
    default_size=WidgetSize.SMALL,
    min_size=WidgetSize.SMALL,
    template='widgets/quick_actions.html',
    icon='fas fa-bolt',
    color='yellow',
    required_permissions=[],
    required_user_types=['SUPER_ADMIN', 'DEVELOPER', 'SUPERVISOR', 'COUNTRY_ADMIN'],
    data_loader=None
))

register_widget(WidgetDefinition(
    id='import_tickets',
    name='Import Tickets',
    description='Upload CSV to import tickets',
    category=WidgetCategory.ACTIONS,
    default_size=WidgetSize.SMALL,
    min_size=WidgetSize.SMALL,
    template='widgets/import_tickets.html',
    icon='fas fa-file-import',
    color='purple',
    required_permissions=[],
    required_user_types=['SUPER_ADMIN', 'DEVELOPER', 'SUPERVISOR', 'COUNTRY_ADMIN'],
    data_loader=None
))

register_widget(WidgetDefinition(
    id='import_assets',
    name='Import Assets',
    description='Upload file to import assets',
    category=WidgetCategory.ACTIONS,
    default_size=WidgetSize.SMALL,
    min_size=WidgetSize.SMALL,
    template='widgets/import_assets.html',
    icon='fas fa-file-upload',
    color='teal',
    required_permissions=[],
    required_user_types=['SUPER_ADMIN', 'DEVELOPER', 'COUNTRY_ADMIN'],
    data_loader=None
))

# System Widgets
register_widget(WidgetDefinition(
    id='system_management',
    name='System Management',
    description='Admin tools and settings',
    category=WidgetCategory.SYSTEM,
    default_size=WidgetSize.LARGE,
    min_size=WidgetSize.MEDIUM,
    template='widgets/system_management.html',
    icon='fas fa-cog',
    color='blue',
    required_permissions=[],
    required_user_types=['SUPER_ADMIN', 'DEVELOPER'],
    data_loader=None
))

register_widget(WidgetDefinition(
    id='development_console',
    name='Development Console',
    description='Feature and bug tracking',
    category=WidgetCategory.SYSTEM,
    default_size=WidgetSize.SMALL,
    min_size=WidgetSize.SMALL,
    template='widgets/development_console.html',
    icon='fas fa-laptop-code',
    color='blue',
    required_permissions=[],
    required_user_types=['SUPER_ADMIN', 'DEVELOPER', 'SUPERVISOR'],
    data_loader=None
))

register_widget(WidgetDefinition(
    id='inventory_audit',
    name='Inventory Audit',
    description='Manage inventory audits',
    category=WidgetCategory.ACTIONS,
    default_size=WidgetSize.SMALL,
    min_size=WidgetSize.SMALL,
    template='widgets/inventory_audit.html',
    icon='fas fa-clipboard-check',
    color='indigo',
    required_permissions=['can_access_inventory_audit'],
    required_user_types=['SUPER_ADMIN', 'DEVELOPER', 'SUPERVISOR', 'COUNTRY_ADMIN'],
    data_loader='load_audit_data'
))

register_widget(WidgetDefinition(
    id='clock_widget',
    name='Clock',
    description='Analog clock display (GMT+8)',
    category=WidgetCategory.STATS,
    default_size=WidgetSize.SMALL,
    min_size=WidgetSize.SMALL,
    template='widgets/clock.html',
    icon='fas fa-clock',
    color='gray',
    required_permissions=[],
    required_user_types=['SUPER_ADMIN', 'DEVELOPER', 'SUPERVISOR', 'COUNTRY_ADMIN', 'CLIENT'],
    data_loader=None,
    refreshable=False
))

register_widget(WidgetDefinition(
    id='reports_link',
    name='Reports',
    description='Analytics and insights',
    category=WidgetCategory.ACTIONS,
    default_size=WidgetSize.SMALL,
    min_size=WidgetSize.SMALL,
    template='widgets/reports_link.html',
    icon='fas fa-chart-line',
    color='indigo',
    required_permissions=['can_view_reports'],
    required_user_types=['SUPER_ADMIN', 'DEVELOPER', 'SUPERVISOR', 'COUNTRY_ADMIN'],
    data_loader=None
))

register_widget(WidgetDefinition(
    id='knowledge_base_link',
    name='Knowledge Base',
    description='Documentation and guides',
    category=WidgetCategory.ACTIONS,
    default_size=WidgetSize.SMALL,
    min_size=WidgetSize.SMALL,
    template='widgets/knowledge_base_link.html',
    icon='fas fa-book',
    color='blue',
    required_permissions=['can_view_knowledge_base'],
    required_user_types=['SUPER_ADMIN', 'DEVELOPER', 'SUPERVISOR', 'COUNTRY_ADMIN', 'CLIENT'],
    data_loader=None
))

register_widget(WidgetDefinition(
    id='documents_link',
    name='Documents',
    description='Commercial invoices and packing lists',
    category=WidgetCategory.ACTIONS,
    default_size=WidgetSize.SMALL,
    min_size=WidgetSize.SMALL,
    template='widgets/documents_link.html',
    icon='fas fa-file-alt',
    color='orange',
    required_permissions=['can_access_documents'],
    required_user_types=['SUPER_ADMIN', 'DEVELOPER', 'SUPERVISOR'],
    data_loader=None
))

register_widget(WidgetDefinition(
    id='billing_generator',
    name='Billing Generator',
    description='Create invoices and billing reports',
    category=WidgetCategory.ACTIONS,
    default_size=WidgetSize.SMALL,
    min_size=WidgetSize.SMALL,
    template='widgets/billing_generator.html',
    icon='fas fa-calculator',
    color='green',
    required_permissions=[],
    required_user_types=['SUPER_ADMIN', 'DEVELOPER'],
    data_loader=None
))

register_widget(WidgetDefinition(
    id='view_inventory',
    name='View Inventory',
    description='Quick access to inventory management',
    category=WidgetCategory.ACTIONS,
    default_size=WidgetSize.SMALL,
    min_size=WidgetSize.SMALL,
    template='widgets/view_inventory.html',
    icon='fas fa-boxes',
    color='purple',
    required_permissions=[],
    required_user_types=['SUPER_ADMIN', 'DEVELOPER', 'SUPERVISOR', 'COUNTRY_ADMIN'],
    data_loader=None
))

register_widget(WidgetDefinition(
    id='view_tickets',
    name='View Tickets',
    description='Quick access to ticket management',
    category=WidgetCategory.ACTIONS,
    default_size=WidgetSize.SMALL,
    min_size=WidgetSize.SMALL,
    template='widgets/view_tickets.html',
    icon='fas fa-ticket-alt',
    color='green',
    required_permissions=[],
    required_user_types=['SUPER_ADMIN', 'DEVELOPER', 'SUPERVISOR', 'COUNTRY_ADMIN', 'CLIENT'],
    data_loader=None
))

register_widget(WidgetDefinition(
    id='view_customers',
    name='View Customers',
    description='Quick access to customer management',
    category=WidgetCategory.ACTIONS,
    default_size=WidgetSize.SMALL,
    min_size=WidgetSize.SMALL,
    template='widgets/view_customers.html',
    icon='fas fa-users',
    color='blue',
    required_permissions=[],
    required_user_types=['SUPER_ADMIN', 'DEVELOPER', 'SUPERVISOR'],
    data_loader=None
))

register_widget(WidgetDefinition(
    id='launchpad',
    name='App Launcher',
    description='macOS-style launcher with all features',
    category=WidgetCategory.ACTIONS,
    default_size=WidgetSize.LARGE,
    min_size=WidgetSize.MEDIUM,
    template='widgets/launchpad.html',
    icon='fas fa-th',
    color='indigo',
    required_permissions=[],
    required_user_types=['SUPER_ADMIN', 'DEVELOPER', 'SUPERVISOR', 'COUNTRY_ADMIN'],
    data_loader=None,
    refreshable=False
))


# Default layout for new users
DEFAULT_DASHBOARD_LAYOUT = {
    'DEVELOPER': [
        {'widget_id': 'inventory_stats', 'position': 0, 'size': 'small', 'config': {}},
        {'widget_id': 'ticket_stats', 'position': 1, 'size': 'small', 'config': {}},
        {'widget_id': 'customer_stats', 'position': 2, 'size': 'small', 'config': {}},
        {'widget_id': 'clock_widget', 'position': 3, 'size': 'small', 'config': {}},
        {'widget_id': 'quick_actions', 'position': 4, 'size': 'small', 'config': {}},
        {'widget_id': 'view_inventory', 'position': 5, 'size': 'small', 'config': {}},
        {'widget_id': 'weekly_tickets_chart', 'position': 6, 'size': 'medium', 'config': {}},
        {'widget_id': 'asset_status_chart', 'position': 7, 'size': 'medium', 'config': {}},
        {'widget_id': 'recent_activities', 'position': 8, 'size': 'medium', 'config': {}},
        {'widget_id': 'shipments_list', 'position': 9, 'size': 'large', 'config': {}},
        {'widget_id': 'system_management', 'position': 10, 'size': 'large', 'config': {}},
    ],
    'SUPER_ADMIN': [
        {'widget_id': 'inventory_stats', 'position': 0, 'size': 'small', 'config': {}},
        {'widget_id': 'ticket_stats', 'position': 1, 'size': 'small', 'config': {}},
        {'widget_id': 'customer_stats', 'position': 2, 'size': 'small', 'config': {}},
        {'widget_id': 'clock_widget', 'position': 3, 'size': 'small', 'config': {}},
        {'widget_id': 'quick_actions', 'position': 4, 'size': 'small', 'config': {}},
        {'widget_id': 'view_inventory', 'position': 5, 'size': 'small', 'config': {}},
        {'widget_id': 'weekly_tickets_chart', 'position': 6, 'size': 'medium', 'config': {}},
        {'widget_id': 'queue_stats', 'position': 7, 'size': 'medium', 'config': {}},
        {'widget_id': 'recent_activities', 'position': 8, 'size': 'medium', 'config': {}},
        {'widget_id': 'shipments_list', 'position': 9, 'size': 'large', 'config': {}},
        {'widget_id': 'system_management', 'position': 10, 'size': 'large', 'config': {}},
    ],
    'SUPERVISOR': [
        {'widget_id': 'inventory_stats', 'position': 0, 'size': 'small', 'config': {}},
        {'widget_id': 'customer_stats', 'position': 1, 'size': 'small', 'config': {}},
        {'widget_id': 'clock_widget', 'position': 2, 'size': 'small', 'config': {}},
        {'widget_id': 'quick_actions', 'position': 3, 'size': 'small', 'config': {}},
        {'widget_id': 'view_inventory', 'position': 4, 'size': 'small', 'config': {}},
        {'widget_id': 'asset_status_chart', 'position': 5, 'size': 'medium', 'config': {}},
        {'widget_id': 'shipments_list', 'position': 6, 'size': 'large', 'config': {}},
        {'widget_id': 'import_tickets', 'position': 7, 'size': 'small', 'config': {}},
    ],
    'COUNTRY_ADMIN': [
        {'widget_id': 'inventory_stats', 'position': 0, 'size': 'small', 'config': {}},
        {'widget_id': 'clock_widget', 'position': 1, 'size': 'small', 'config': {}},
        {'widget_id': 'quick_actions', 'position': 2, 'size': 'small', 'config': {}},
        {'widget_id': 'view_inventory', 'position': 3, 'size': 'small', 'config': {}},
        {'widget_id': 'asset_status_chart', 'position': 4, 'size': 'medium', 'config': {}},
        {'widget_id': 'shipments_list', 'position': 5, 'size': 'large', 'config': {}},
    ],
    'CLIENT': [
        {'widget_id': 'ticket_stats', 'position': 0, 'size': 'small', 'config': {}},
        {'widget_id': 'clock_widget', 'position': 1, 'size': 'small', 'config': {}},
        {'widget_id': 'knowledge_base_link', 'position': 2, 'size': 'small', 'config': {}},
    ]
}


def get_default_layout_for_user(user) -> list:
    """Get the default dashboard layout for a user based on their type"""
    user_type = user.user_type.value if hasattr(user.user_type, 'value') else str(user.user_type)
    return DEFAULT_DASHBOARD_LAYOUT.get(user_type, DEFAULT_DASHBOARD_LAYOUT['SUPERVISOR'])
