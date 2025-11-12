"""
Inventory Management Module
Complete inventory system with batch tracking, FIFO, expiry management, and cost tracking

VERSION HISTORY:
3.0.0 - 2025-01-12 - Modular architecture refactoring
      - Split monolithic inventory.py into separate tab modules
      - Created public API for cross-module communication
      - Improved code organization and maintainability
      - Shared utilities and constants for DRY principle

PUBLIC API for cross-module communication:
- use_stock_item(): Deduct stock from inventory
- add_stock_item(): Add stock to inventory
- get_stock_level(): Get current stock level
- get_item_by_name(): Find item by name
- get_all_active_items(): Get list of all active items
- get_low_stock_items(): Get items needing reorder
- get_expiring_items(): Get items expiring soon
- get_item_transaction_history(): Get transaction history

Example usage from another module (e.g., biofloc):
    from modules.inventory import use_stock_item, get_stock_level

    # Check stock level
    stock = get_stock_level(item_id=42)
    if stock['total_qty'] >= 5.0:
        # Use stock
        result = use_stock_item(
            item_id=42,
            quantity=5.0,
            user_id=current_user_id,
            purpose="Fish feeding - Pond A"
        )
        if result['success']:
            print("Stock used successfully")
"""

import streamlit as st

# Import from app structure
from auth.session import SessionManager

# Export public API functions
from .api import (
    use_stock_item,
    add_stock_item,
    get_stock_level,
    get_item_by_name,
    get_all_active_items,
    get_low_stock_items,
    get_expiring_items,
    get_item_transaction_history
)

# Import all tab functions
from .dashboard_tab import show_dashboard_tab
from .current_stock_tab import show_current_stock_tab
from .add_stock_tab import show_add_stock_tab
from .adjustments_tab import show_adjustments_tab
from .po_tab import show_purchase_orders_tab
from .alerts_tab import show_alerts_tab
from .history_tab import show_history_tab
from .item_master_tab import show_item_master_tab
from .categories_tab import show_categories_tab
from .suppliers_tab import show_suppliers_tab
from .analytics_tab import show_analytics_tab

# Version
__version__ = "3.0.0"

# Public API list (for documentation)
__all__ = [
    'show',
    'use_stock_item',
    'add_stock_item',
    'get_stock_level',
    'get_item_by_name',
    'get_all_active_items',
    'get_low_stock_items',
    'get_expiring_items',
    'get_item_transaction_history',
]


def show():
    """Main entry point for the Inventory Management module"""

    # Check module access
    SessionManager.require_module_access('inventory')

    # Get user info
    user = SessionManager.get_user()
    profile = SessionManager.get_user_profile()
    is_admin = SessionManager.is_admin()
    username = profile.get('full_name', user.get('email', 'Unknown'))
    role_name = profile.get('role_name', 'User')

    # Module header
    st.title("📦 Inventory Management")
    st.caption(f"👤 {username} | Role: {role_name}")
    st.markdown("---")

    # Initialize session state
    if 'inv_refresh_trigger' not in st.session_state:
        st.session_state.inv_refresh_trigger = 0

    # Create tabs based on user role
    # User tabs (available to all)
    st.markdown("### 👤 User Operations")
    user_tabs = st.tabs([
        "📊 Dashboard",
        "📦 Current Stock",
        "➕ Add Stock",
        "🔄 Adjustments",
        "🛒 Purchase Orders",
        "🔔 Alerts",
        "📜 History"
    ])

    with user_tabs[0]:
        show_dashboard_tab(username, is_admin)
    with user_tabs[1]:
        show_current_stock_tab(username, is_admin)
    with user_tabs[2]:
        show_add_stock_tab(username)
    with user_tabs[3]:
        show_adjustments_tab(username)
    with user_tabs[4]:
        show_purchase_orders_tab(username, is_admin)
    with user_tabs[5]:
        show_alerts_tab(username)
    with user_tabs[6]:
        show_history_tab(username, is_admin)

    # Admin-only tabs (second row)
    if is_admin:
        st.markdown("---")
        st.markdown("### 🔐 Admin Configuration")
        admin_tabs = st.tabs([
            "📋 Item Master List",
            "🏷️ Categories",
            "👥 Suppliers",
            "📈 Analytics"
        ])

        with admin_tabs[0]:
            show_item_master_tab(username)
        with admin_tabs[1]:
            show_categories_tab(username)
        with admin_tabs[2]:
            show_suppliers_tab(username)
        with admin_tabs[3]:
            show_analytics_tab(username)
