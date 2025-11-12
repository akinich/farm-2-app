"""
Inventory Management Module - Master Controller
Complete inventory system with batch tracking, FIFO, expiry management, and cost tracking

VERSION HISTORY:
3.0.0 - 2025-01-12 - Modular architecture refactoring
      MAJOR CHANGES:
      - Split monolithic 3000+ line file into 12 separate tab modules
      - Created public API for cross-module communication (biofloc → inventory)
      - Improved code organization, maintainability, and testability
      - Shared utilities (utils.py) and constants (constants.py)
      - Performance optimizations with caching and N+1 query fixes

      MODULES CREATED:
      - dashboard_tab.py: KPIs, alerts, recent activity
      - current_stock_tab.py: Stock viewing with filters
      - add_stock_tab.py: Batch tracking and stock addition
      - adjustments_tab.py: Stock corrections
      - po_tab.py: Multi-item purchase orders (invoice-style)
      - alerts_tab.py: Low stock and expiry monitoring
      - history_tab.py: Transaction history
      - item_master_tab.py: Item template management (admin)
      - categories_tab.py: Category management (admin)
      - suppliers_tab.py: Supplier CRUD (admin)
      - analytics_tab.py: Reports and analytics (admin)

      BENEFITS:
      - Easier to maintain individual features
      - Better code organization (DRY principle)
      - Cross-module API enables biofloc/RAS to use inventory
      - Faster development and debugging
      - Cleaner git history per feature

2.2.2 - 2025-01-11 - Fixed Excel download and enhanced PO UI
      - Editable auto-generated PO number field
      - Fixed Excel download in PO list
      - Better UX for Excel export functionality

2.2.1 - 2025-01-11 - Enhanced PO UI with dynamic unit display
      - Unit cost label shows unit dynamically (₹/kg, ₹/g, ₹/L)
      - Fixed unit display from selected item

2.2.0 - 2025-01-11 - Fixed purchase order creation and activity logging
      - Fixed PO creation error (user_id instead of username)
      - Added explicit user_email to ActivityLogger
      - Purchase orders save correctly with proper user tracking

2.1.0 - 2025-01-10 - Complete rewrite for schema v2.0.0 compatibility
      - Compatible with item_master and inventory_batches tables
      - FIFO stock deduction with batch tracking
      - Role-based access (7 tabs for users, 4 admin tabs)

ACCESS CONTROL:
- All Users: 7 operational tabs (Dashboard, Current Stock, Add Stock, Adjustments, POs, Alerts, History)
- Admin: Additional 4 configuration tabs (Item Master, Categories, Suppliers, Analytics)
- Two-row layout: User Operations (top) + Admin Configuration (bottom for admins only)

PUBLIC API FOR CROSS-MODULE COMMUNICATION:
This module exports functions that other modules (biofloc, RAS, etc.) can use:

    from modules.inventory import use_stock_item, get_stock_level

    # Check stock before using
    stock = get_stock_level(item_id=42)
    if stock['total_qty'] >= 5.0:
        result = use_stock_item(
            item_id=42,
            quantity=5.0,
            user_id=current_user_id,
            purpose="Fish feeding - Pond A"
        )

See modules/inventory/api.py for full API documentation.
"""

import streamlit as st

# Import from app structure
from auth.session import SessionManager

# Import all tab functions from modular inventory package
from .inventory.dashboard_tab import show_dashboard_tab
from .inventory.current_stock_tab import show_current_stock_tab
from .inventory.add_stock_tab import show_add_stock_tab
from .inventory.adjustments_tab import show_adjustments_tab
from .inventory.po_tab import show_purchase_orders_tab
from .inventory.alerts_tab import show_alerts_tab
from .inventory.history_tab import show_history_tab
from .inventory.item_master_tab import show_item_master_tab
from .inventory.categories_tab import show_categories_tab
from .inventory.suppliers_tab import show_suppliers_tab
from .inventory.analytics_tab import show_analytics_tab


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
