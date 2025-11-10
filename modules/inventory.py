"""
Inventory Management Module
Complete inventory system with batch tracking, FIFO, expiry management, and cost tracking

VERSION HISTORY:
2.2.0 - Fixed purchase order creation and activity logging - 10/11/25
      FIXES:
      - Fixed PO creation error by passing user_id (UUID) instead of display name to created_by field
      - Added explicit user_email to ActivityLogger calls for better tracking
      CHANGES:
      - create_purchase_order now receives user_id instead of username string
      - ActivityLogger.log calls now pass user_email explicitly from session state
      IMPROVEMENTS:
      - Purchase orders now save correctly with proper user tracking
      - Activity logs will show actual email addresses instead of "Unknown"

2.1.9 - Enhanced history tab and removed unit cost from current stock - 10/11/25
      ADDITIONS:
      - Added 'Unit' column to transaction history tab
      - Added 'Total Cost' column to transaction history (calculated from unit_cost * quantity)
      CHANGES:
      - Removed 'Unit Cost' column from Current Stock tab (cleaner view)
      - Updated history column order for better readability
      IMPROVEMENTS:
      - Better cost visibility in history with both unit and total costs
      - Cleaner current stock view without pricing details

2.1.8 - Reorganized UI and added supplier edit/delete - 10/11/25
      UI IMPROVEMENTS:
      - Split tabs into two rows: User Operations and Admin Configuration
      - Cleaner organization with logical grouping
      - First row: 7 operational tabs for all users
      - Second row: 4 configuration tabs for admins only
      ADDITIONS:
      - show_edit_supplier() - Edit/delete supplier functionality
      - Supplier edit sub-tab with full CRUD operations
      - Active/inactive status toggle for suppliers
      - Delete protection for suppliers in use
      CHANGES:
      - Reorganized tab structure from single row to two rows
      - Updated supplier tab from 2 to 3 sub-tabs (View/Add/Edit)
      - Added descriptive section headers
      FEATURES:
      - Activity logging for supplier operations
      - Usage statistics for suppliers

2.1.7 - Added Categories Management Tab - 10/11/25
      ADDITIONS:
      - New "Categories" tab for admins (11th tab)
      - show_categories_tab() - Main categories management interface
      - show_view_categories() - View all categories with usage statistics
      - show_add_category() - Add new categories with description
      - show_edit_category() - Edit/delete existing categories
      FEATURES:
      - Category usage statistics showing items per category
      - Delete protection (prevents deletion of categories in use)
      - Activity logging for all category operations
      CHANGES:
      - Updated admin tabs from 10 to 11 tabs
      - Updated module documentation

2.1.6 - Improved category selection UI - 10/11/25
      ADDITIONS:
      - Dropdown category selector with existing categories
      - Option to add new categories inline
      CHANGES:
      - show_add_master_item - Replaced free-text category with dropdown + custom input
      - show_edit_master_item - Added dropdown category selector with current value
      FIXES:
      - Prevents foreign key constraint errors by using validated categories
      - Better UX with existing category suggestions

2.1.5 - Align master item schema - 10/11/25
      FIXES:
      - Use reorder_threshold column adopted in item_master schema
      - Backfill reorder_level display values from reorder_threshold
      - Store default supplier via default_supplier_id column when available
      CHANGES:
      - show_add_master_item
      - show_edit_master_item
      - show_all_master_items

2.1.4 - Align master item supplier field - 10/11/25
      FIXES:
      - Map supplier selections to supplier_id to match item_master schema
      - Prevent erroneous inserts when default supplier column is absent
      - Preserve inactive supplier assignments during edit
      CHANGES:
      - show_add_master_item
      - show_edit_master_item
      - VERSION HISTORY

2.1.3 - Normalize master item columns - 10/11/25
      FIXES:
      - Safely rename master list columns when optional fields are missing
      - Prevent pandas length mismatch errors in Item Master tab
      - Ensure unique keys on selectboxes to avoid duplicate Streamlit IDs
      CHANGES:
      - show_all_master_items
      - show_all_suppliers
      - show_add_stock_tab
      - show_adjustments_tab
      - show_all_purchase_orders
      - show_create_purchase_order
      - show_history_tab
      - show_add_master_item
      - show_edit_master_item
      - show_cost_analysis

2.1.2 - Resolved alerts column mismatch - 10/11/25
      FIXES:
      - Handle optional columns when renaming low stock alerts table
      - Prevent pandas length mismatch errors in Alerts tab
      CHANGES:
      - show_alerts_tab

2.1.1 - Fixed duplicate button IDs - 10/11/25
      FIXES:
      - Added unique key parameters to all refresh buttons
      - Added unique key parameters to all export buttons
      - Prevents StreamlitDuplicateElementId errors
      CHANGES:
      - refresh_current_stock, refresh_pos, refresh_alerts, refresh_history, refresh_master_items
      - export_current_stock, export_pos, export_history, export_consumption
      
2.1.0 - Complete rewrite for schema v2.0.0 compatibility - 10/11/25
      FIXES:
      - Compatible with item_master and inventory_batches tables
      - Uses correct db_inventory v2.0.0 method names
      - Proper role-based access (7 tabs for users, 10 for admins)
      - Cost data hidden from regular users
      - FIFO stock deduction with batch tracking
      FEATURES:
      - Dashboard with alerts and KPIs
      - Current stock view with batch details
      - Add stock with master item dropdown
      - Stock adjustments with reason tracking
      - Purchase order management
      - Low stock and expiry alerts
      - Complete transaction history
      - Item master list (admin only)
      - Category management (admin only)
      - Supplier management (admin only)
      - Analytics and reports (admin only)

ACCESS CONTROL:
- All Users: 7 operational tabs (Dashboard, Current Stock, Add Stock, Adjustments, POs, Alerts, History)
- Admin: Additional 4 configuration tabs (Item Master, Categories, Suppliers, Analytics)
- Two-row layout: User Operations (top) + Admin Configuration (bottom for admins only)
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
import time

# Import from your app structure
from auth.session import SessionManager
from config.database import ActivityLogger

# Import inventory database helper
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from db.db_inventory import InventoryDB
except ImportError:
    try:
        # Try alternate path
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from db.db_inventory import InventoryDB
    except ImportError:
        st.error("⚠️ Cannot import InventoryDB. Make sure db_inventory.py is in db/ folder")
        st.stop()


def show():
    """Main entry point for the Inventory Management module"""
    
    # Check module access
    SessionManager.require_module_access('inventory_management')
    
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


# =====================================================
# TAB 1: DASHBOARD
# =====================================================

def show_dashboard_tab(username: str, is_admin: bool):
    """Dashboard with KPIs, alerts, and quick stats"""
    
    st.markdown("### 📊 Inventory Dashboard")
    
    with st.spinner("Loading dashboard..."):
        # Get summary data
        summary = InventoryDB.get_inventory_summary()
        low_stock = InventoryDB.get_low_stock_items()
        expiring = InventoryDB.get_expiring_items(days_ahead=30)
    
    # KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Active Items",
            summary.get('total_active_items', 0),
            help="Number of active items in master list"
        )
    
    with col2:
        st.metric(
            "Total Batches",
            summary.get('total_batches', 0),
            help="Number of stock batches in inventory"
        )
    
    with col3:
        st.metric(
            "🔴 Low Stock Items",
            len(low_stock),
            help="Items below reorder level"
        )
    
    with col4:
        st.metric(
            "⚠️ Expiring Soon",
            len([e for e in expiring if e.get('days_until_expiry', 999) <= 30]),
            help="Items expiring in next 30 days"
        )
    
    # Show inventory value only to admin
    if is_admin and 'total_inventory_value' in summary:
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "💰 Total Inventory Value",
                f"₹{summary.get('total_inventory_value', 0):,.2f}",
                help="Total value of all stock"
            )
        with col2:
            st.metric(
                "📊 Avg Item Value",
                f"₹{summary.get('avg_item_value', 0):,.2f}",
                help="Average value per item"
            )
    
    st.markdown("---")
    
    # Quick Alerts Section
    st.markdown("### 🚨 Quick Alerts")
    
    alert_col1, alert_col2 = st.columns(2)
    
    with alert_col1:
        st.markdown("#### 🔴 Low Stock Alerts")
        if low_stock:
            for item in low_stock[:5]:  # Show top 5
                st.warning(
                    f"**{item.get('item_name')}** - Current: {item.get('current_qty', 0)} {item.get('unit', '')}, "
                    f"Reorder: {item.get('reorder_level', 0)}"
                )
            if len(low_stock) > 5:
                st.caption(f"+ {len(low_stock) - 5} more items below reorder level")
        else:
            st.success("✅ All items above reorder level")
    
    with alert_col2:
        st.markdown("#### ⚠️ Expiry Alerts")
        if expiring:
            critical = [e for e in expiring if e.get('days_until_expiry', 999) <= 7]
            warning = [e for e in expiring if 7 < e.get('days_until_expiry', 999) <= 30]
            
            for item in critical[:3]:  # Show top 3 critical
                st.error(
                    f"**{item.get('item_name')}** (Batch: {item.get('batch_number')}) - "
                    f"Expires in {item.get('days_until_expiry')} days"
                )
            
            for item in warning[:2]:  # Show 2 warnings
                st.warning(
                    f"**{item.get('item_name')}** (Batch: {item.get('batch_number')}) - "
                    f"Expires in {item.get('days_until_expiry')} days"
                )
            
            if len(expiring) > 5:
                st.caption(f"+ {len(expiring) - 5} more items expiring soon")
        else:
            st.success("✅ No items expiring in next 30 days")
    
    st.markdown("---")
    
    # Recent Activity
    st.markdown("### 📜 Recent Activity")
    
    with st.spinner("Loading recent transactions..."):
        recent = InventoryDB.get_recent_transactions(limit=10)
    
    if recent:
        df = pd.DataFrame(recent)
        display_cols = ['transaction_date', 'item_name', 'transaction_type', 'quantity', 'reference', 'performed_by']
        
        if all(col in df.columns for col in display_cols):
            display_df = df[display_cols].copy()
            display_df.columns = ['Date', 'Item', 'Type', 'Quantity', 'Reference', 'User']
            display_df['Date'] = pd.to_datetime(display_df['Date']).dt.strftime('%Y-%m-%d %H:%M')
            
            st.dataframe(display_df, use_container_width=True, hide_index=True, height=300)
    else:
        st.info("No recent transactions")


# =====================================================
# TAB 2: CURRENT STOCK
# =====================================================

def show_current_stock_tab(username: str, is_admin: bool):
    """View current stock with batch details"""
    
    st.markdown("### 📦 Current Stock Inventory")
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        search_term = st.text_input("🔍 Search", placeholder="Search items...", key="stock_search")
    
    with col2:
        categories = InventoryDB.get_all_categories()
        category_filter = st.selectbox("Category", ["All"] + categories, key="stock_category")
    
    with col3:
        batch_filter = st.selectbox("Batch Status", ["All", "Active Only", "Depleted"], key="stock_batch")
    
    with col4:
        if st.button("🔄 Refresh", use_container_width=True, key="refresh_current_stock"):
            st.session_state.inv_refresh_trigger += 1
            st.rerun()
    
    # Load batches
    with st.spinner("Loading stock..."):
        batches = InventoryDB.get_all_batches()
    
    # Apply filters
    if search_term:
        batches = [b for b in batches if search_term.lower() in b.get('item_name', '').lower()]
    
    if category_filter != "All":
        batches = [b for b in batches if b.get('category') == category_filter]
    
    if batch_filter == "Active Only":
        batches = [b for b in batches if b.get('remaining_qty', 0) > 0]
    elif batch_filter == "Depleted":
        batches = [b for b in batches if b.get('remaining_qty', 0) == 0]
    
    if not batches:
        st.info("No stock found matching filters")
        return
    
    st.success(f"✅ Found {len(batches)} batches")
    
    # Convert to DataFrame
    df = pd.DataFrame(batches)
    
    # Select columns - removed unit_cost from display
    display_cols = [
        'item_name', 'batch_number', 'purchase_date', 'supplier_name',
        'quantity', 'remaining_qty', 'unit', 'expiry_date', 'status'
    ]

    # Ensure columns exist
    display_cols = [col for col in display_cols if col in df.columns]
    display_df = df[display_cols].copy()

    # Format columns
    if 'purchase_date' in display_df.columns:
        display_df['purchase_date'] = pd.to_datetime(display_df['purchase_date']).dt.strftime('%Y-%m-%d')

    if 'expiry_date' in display_df.columns:
        display_df['expiry_date'] = pd.to_datetime(display_df['expiry_date'], errors='coerce').dt.strftime('%Y-%m-%d')
        display_df['expiry_date'] = display_df['expiry_date'].fillna('N/A')

    # Rename columns for display
    column_mapping = {
        'item_name': 'Item Name',
        'batch_number': 'Batch #',
        'purchase_date': 'Purchase Date',
        'supplier_name': 'Supplier',
        'quantity': 'Original Qty',
        'remaining_qty': 'Remaining Qty',
        'unit': 'Unit',
        'expiry_date': 'Expiry Date',
        'status': 'Status'
    }
    
    display_df.rename(columns=column_mapping, inplace=True)
    
    # Display table
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=500
    )
    
    # Export option
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col2:
        if st.button("📥 Export to Excel", use_container_width=True, key="export_current_stock"):
            export_to_excel(display_df, "current_stock")
    
    # Summary stats
    st.markdown("---")
    st.markdown("### 📊 Stock Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_items = df['item_name'].nunique() if 'item_name' in df.columns else 0
        st.metric("Unique Items", total_items)
    
    with col2:
        active_batches = len([b for b in batches if b.get('remaining_qty', 0) > 0])
        st.metric("Active Batches", active_batches)
    
    with col3:
        depleted_batches = len([b for b in batches if b.get('remaining_qty', 0) == 0])
        st.metric("Depleted Batches", depleted_batches)
    
    with col4:
        if is_admin and 'unit_cost' in df.columns and 'remaining_qty' in df.columns:
            # Calculate total value
            df['batch_value'] = df['unit_cost'] * df['remaining_qty']
            total_value = df['batch_value'].sum()
            st.metric("Total Stock Value", f"₹{total_value:,.2f}")


# =====================================================
# TAB 3: ADD STOCK
# =====================================================

def show_add_stock_tab(username: str):
    """Add new stock entry with batch tracking"""
    
    st.markdown("### ➕ Add New Stock")
    
    # Get master items for dropdown
    master_items = InventoryDB.get_all_master_items(active_only=True)
    for item in master_items:
        if 'reorder_level' not in item and 'reorder_threshold' in item:
            item['reorder_level'] = item['reorder_threshold']
        if 'default_supplier_id' not in item and 'supplier_id' in item:
            item['default_supplier_id'] = item['supplier_id']
    
    if not master_items:
        st.warning("⚠️ No active items in master list. Ask admin to add items first.")
        return
    
    st.info("📝 Add stock received from suppliers. Each entry creates a new batch for FIFO tracking.")
    
    with st.form("add_stock_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            # Item selection with search
            item_options = {
                f"{item['item_name']} ({item.get('category', 'N/A')}) - Current: {item.get('current_qty', 0)} {item.get('unit', '')}": item
                for item in master_items
            }
            
            selected_item_key = st.selectbox(
                "Select Item *",
                options=list(item_options.keys()),
                help="Search and select item from master list",
                key="add_stock_item_select"
            )
            selected_item = item_options[selected_item_key]
            
            # Show item details
            with st.expander("ℹ️ Item Details"):
                st.markdown(f"**Category:** {selected_item.get('category', 'N/A')}")
                st.markdown(f"**SKU:** {selected_item.get('sku', 'N/A')}")
                st.markdown(f"**Brand:** {selected_item.get('brand', 'N/A')}")
                st.markdown(f"**Current Stock:** {selected_item.get('current_qty', 0)} {selected_item.get('unit', '')}")
                st.markdown(f"**Reorder Level:** {selected_item.get('reorder_level', 0)}")
            
            # Batch details
            batch_number = st.text_input(
                "Batch Number *",
                placeholder="e.g., BATCH-2024-001",
                help="Unique identifier for this batch"
            )
            
            quantity = st.number_input(
                "Quantity *",
                min_value=0.01,
                step=0.01,
                format="%.2f",
                help=f"Amount received in {selected_item.get('unit', '')}"
            )
            
            unit_cost = st.number_input(
                "Unit Cost (₹) *",
                min_value=0.01,
                step=0.01,
                format="%.2f",
                help="Cost per unit (for cost tracking)"
            )
        
        with col2:
            # Purchase details
            purchase_date = st.date_input(
                "Purchase Date *",
                value=date.today(),
                max_value=date.today()
            )
            
            # Get suppliers for dropdown
            suppliers = InventoryDB.get_all_suppliers(active_only=True)
            supplier_options = ["Select Supplier"] + [s['supplier_name'] for s in suppliers]
            
            supplier_name = st.selectbox(
                "Supplier",
                options=supplier_options,
                help="Select supplier (optional)",
                key="add_stock_supplier_select"
            )
            
            if supplier_name == "Select Supplier":
                supplier_name = None
            
            # Expiry tracking
            has_expiry = st.checkbox("Has Expiry Date", value=False)
            
            expiry_date = None
            if has_expiry:
                expiry_date = st.date_input(
                    "Expiry Date",
                    value=date.today() + timedelta(days=180),
                    min_value=date.today()
                )
            
            notes = st.text_area(
                "Notes",
                placeholder="Additional notes about this stock entry...",
                height=100
            )
        
        # Submit button
        st.markdown("---")
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col3:
            submitted = st.form_submit_button("✅ Add Stock", type="primary", use_container_width=True)
        
        if submitted:
            # Validate
            errors = []
            
            if not batch_number or len(batch_number.strip()) < 3:
                errors.append("Batch number is required (minimum 3 characters)")
            
            if quantity <= 0:
                errors.append("Quantity must be greater than 0")
            
            if unit_cost <= 0:
                errors.append("Unit cost must be greater than 0")
            
            if errors:
                for error in errors:
                    st.error(f"❌ {error}")
            else:
                # Add stock
                with st.spinner("Adding stock..."):
                    success = InventoryDB.add_stock_batch(
                        item_master_id=selected_item['id'],
                        batch_number=batch_number.strip(),
                        quantity=quantity,
                        unit_cost=unit_cost,
                        purchase_date=purchase_date,
                        supplier_name=supplier_name,
                        expiry_date=expiry_date,
                        notes=notes.strip() if notes else None,
                        username=username
                    )
                
                if success:
                    st.success(f"✅ Successfully added {quantity} {selected_item.get('unit', '')} of {selected_item['item_name']}")
                    
                    # Log activity
                    ActivityLogger.log(
                        user_id=st.session_state.user['id'],
                        action_type='add_stock',
                        module_key='inventory_management',
                        description=f"Added stock: {selected_item['item_name']} (Batch: {batch_number})",
                        metadata={
                            'item': selected_item['item_name'],
                            'batch': batch_number,
                            'quantity': quantity
                        }
                    )
                    
                    st.balloons()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Failed to add stock. Check if batch number already exists.")


# =====================================================
# TAB 4: ADJUSTMENTS
# =====================================================

def show_adjustments_tab(username: str):
    """Record stock adjustments (損耗, corrections, etc.)"""
    
    st.markdown("### 🔄 Stock Adjustments")
    
    st.info("📝 Record stock corrections, damage, wastage, or other adjustments")
    
    # Get items with stock for adjustment
    items_with_stock = InventoryDB.get_items_with_stock()
    
    if not items_with_stock:
        st.warning("⚠️ No items with stock available for adjustment")
        return
    
    with st.form("adjustment_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            # Item selection
            item_options = {
                f"{item['item_name']} - Available: {item.get('current_qty', 0)} {item.get('unit', '')}": item
                for item in items_with_stock
            }
            
            selected_item_key = st.selectbox(
                "Select Item *",
                options=list(item_options.keys()),
                key="adjustment_item_select"
            )
            selected_item = item_options[selected_item_key]
            
            # Adjustment type
            adjustment_type = st.selectbox(
                "Adjustment Type *",
                options=["damage", "wastage", "theft", "correction", "other"],
                format_func=lambda x: x.title(),
                key="adjustment_type_select"
            )
            
            # Quantity
            quantity = st.number_input(
                "Quantity to Deduct *",
                min_value=0.01,
                max_value=float(selected_item.get('current_qty', 0)),
                step=0.01,
                format="%.2f",
                help=f"Maximum: {selected_item.get('current_qty', 0)} {selected_item.get('unit', '')}"
            )
        
        with col2:
            # Reason
            reason = st.text_area(
                "Reason *",
                placeholder="Explain the reason for this adjustment...",
                height=100,
                help="Required: Provide detailed reason"
            )
            
            # Reference
            reference_id = st.text_input(
                "Reference ID",
                placeholder="e.g., INCIDENT-001 (optional)",
                help="Optional reference number"
            )
            
            # Date
            adjustment_date = st.date_input(
                "Adjustment Date",
                value=date.today(),
                max_value=date.today()
            )
        
        # Submit
        st.markdown("---")
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col3:
            submitted = st.form_submit_button("✅ Record Adjustment", type="primary", use_container_width=True)
        
        if submitted:
            # Validate
            errors = []
            
            if quantity <= 0:
                errors.append("Quantity must be greater than 0")
            
            if quantity > selected_item.get('current_qty', 0):
                errors.append(f"Quantity exceeds available stock ({selected_item.get('current_qty', 0)})")
            
            if not reason or len(reason.strip()) < 10:
                errors.append("Reason is required (minimum 10 characters)")
            
            if errors:
                for error in errors:
                    st.error(f"❌ {error}")
            else:
                # Record adjustment
                with st.spinner("Recording adjustment..."):
                    success = InventoryDB.log_adjustment(
                        item_master_id=selected_item['id'],
                        adjustment_type=adjustment_type,
                        quantity=quantity,
                        reason=reason.strip(),
                        reference_id=reference_id.strip() if reference_id else None,
                        adjustment_date=adjustment_date,
                        username=username
                    )
                
                if success:
                    st.success(f"✅ Adjustment recorded: -{quantity} {selected_item.get('unit', '')} of {selected_item['item_name']}")
                    
                    # Log activity
                    ActivityLogger.log(
                        user_id=st.session_state.user['id'],
                        action_type='adjustment',
                        module_key='inventory_management',
                        description=f"Stock adjustment: {selected_item['item_name']} ({adjustment_type})",
                        metadata={
                            'item': selected_item['item_name'],
                            'type': adjustment_type,
                            'quantity': quantity
                        }
                    )
                    
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Failed to record adjustment")
    
    # Show recent adjustments
    st.markdown("---")
    st.markdown("### 📋 Recent Adjustments")
    
    with st.spinner("Loading adjustments..."):
        adjustments = InventoryDB.get_recent_adjustments(limit=20)
    
    if adjustments:
        df = pd.DataFrame(adjustments)
        display_cols = ['adjustment_date', 'item_name', 'adjustment_type', 'quantity', 'reason', 'performed_by']
        
        if all(col in df.columns for col in display_cols):
            display_df = df[display_cols].copy()
            display_df.columns = ['Date', 'Item', 'Type', 'Quantity', 'Reason', 'User']
            display_df['Date'] = pd.to_datetime(display_df['Date']).dt.strftime('%Y-%m-%d')
            
            st.dataframe(display_df, use_container_width=True, hide_index=True, height=400)
    else:
        st.info("No adjustments recorded yet")


# =====================================================
# TAB 5: PURCHASE ORDERS
# =====================================================

def show_purchase_orders_tab(username: str, is_admin: bool):
    """Manage purchase orders"""
    
    st.markdown("### 🛒 Purchase Orders")
    
    subtabs = st.tabs(["📋 All POs", "➕ Create PO"])
    
    with subtabs[0]:
        show_all_purchase_orders(username, is_admin)
    
    with subtabs[1]:
        show_create_purchase_order(username)


def show_all_purchase_orders(username: str, is_admin: bool):
    """View all purchase orders"""
    
    st.markdown("#### 📋 All Purchase Orders")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.selectbox(
            "Status",
            ["All", "pending", "approved", "ordered", "received", "cancelled"],
            key="po_status_filter_select"
        )
    
    with col2:
        days_back = st.number_input("Days to show", min_value=7, max_value=365, value=30)
    
    with col3:
        if st.button("🔄 Refresh", use_container_width=True, key="refresh_pos"):
            st.rerun()
    
    # Load POs
    with st.spinner("Loading purchase orders..."):
        if status_filter == "All":
            pos = InventoryDB.get_all_purchase_orders(days_back=days_back)
        else:
            pos = InventoryDB.get_purchase_orders_by_status(status_filter, days_back=days_back)
    
    if not pos:
        st.info("No purchase orders found")
        return
    
    st.success(f"✅ Found {len(pos)} purchase orders")
    
    # Convert to DataFrame
    df = pd.DataFrame(pos)
    
    # Select columns based on role
    if is_admin:
        display_cols = ['po_number', 'item_name', 'supplier_name', 'quantity', 'unit_cost', 'total_cost', 'po_date', 'status', 'created_by']
    else:
        # Hide costs
        display_cols = ['po_number', 'item_name', 'supplier_name', 'quantity', 'po_date', 'status', 'created_by']
    
    display_cols = [col for col in display_cols if col in df.columns]
    display_df = df[display_cols].copy()
    
    # Format
    if 'po_date' in display_df.columns:
        display_df['po_date'] = pd.to_datetime(display_df['po_date']).dt.strftime('%Y-%m-%d')
    
    if 'unit_cost' in display_df.columns:
        display_df['unit_cost'] = display_df['unit_cost'].apply(lambda x: f"₹{x:.2f}" if pd.notna(x) else 'N/A')
    
    if 'total_cost' in display_df.columns:
        display_df['total_cost'] = display_df['total_cost'].apply(lambda x: f"₹{x:.2f}" if pd.notna(x) else 'N/A')
    
    # Rename
    column_mapping = {
        'po_number': 'PO #',
        'item_name': 'Item',
        'supplier_name': 'Supplier',
        'quantity': 'Quantity',
        'unit_cost': 'Unit Cost',
        'total_cost': 'Total Cost',
        'po_date': 'Date',
        'status': 'Status',
        'created_by': 'Created By'
    }
    
    display_df.rename(columns=column_mapping, inplace=True)
    
    st.dataframe(display_df, use_container_width=True, hide_index=True, height=500)
    
    # Export
    if st.button("📥 Export to Excel", use_container_width=True, key="export_pos"):
        export_to_excel(display_df, "purchase_orders")


def show_create_purchase_order(username: str):
    """Create new purchase order"""
    
    st.markdown("#### ➕ Create Purchase Order")
    
    master_items = InventoryDB.get_all_master_items(active_only=True)
    for item in master_items:
        if 'reorder_level' not in item and 'reorder_threshold' in item:
            item['reorder_level'] = item['reorder_threshold']
        if 'default_supplier_id' not in item and 'supplier_id' in item:
            item['default_supplier_id'] = item['supplier_id']
    suppliers = InventoryDB.get_all_suppliers(active_only=True)
    
    if not master_items:
        st.warning("⚠️ No active items in master list")
        return
    
    with st.form("create_po_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            # Item
            item_options = {item['item_name']: item for item in master_items}
            selected_item_name = st.selectbox(
                "Select Item *",
                options=list(item_options.keys()),
                key="create_po_item_select"
            )
            selected_item = item_options[selected_item_name]
            
            # Supplier
            supplier_options = ["Select Supplier"] + [s['supplier_name'] for s in suppliers]
            supplier_name = st.selectbox(
                "Supplier *",
                options=supplier_options,
                key="create_po_supplier_select"
            )
            
            # Quantity
            quantity = st.number_input(
                f"Quantity ({selected_item.get('unit', '')}) *",
                min_value=0.01,
                step=0.01,
                format="%.2f"
            )
            
            # Unit cost
            unit_cost = st.number_input(
                "Unit Cost (₹) *",
                min_value=0.01,
                step=0.01,
                format="%.2f"
            )
        
        with col2:
            # PO date
            po_date = st.date_input("PO Date", value=date.today())
            
            # Expected delivery
            expected_delivery = st.date_input(
                "Expected Delivery",
                value=date.today() + timedelta(days=7),
                min_value=date.today()
            )
            
            # Total cost (calculated)
            total_cost = quantity * unit_cost
            st.metric("Total Cost", f"₹{total_cost:,.2f}")
            
            # Notes
            notes = st.text_area("Notes", height=100)
        
        # Submit
        st.markdown("---")
        submitted = st.form_submit_button("✅ Create PO", type="primary", use_container_width=True)
        
        if submitted:
            if supplier_name == "Select Supplier":
                st.error("❌ Please select a supplier")
            elif quantity <= 0:
                st.error("❌ Quantity must be greater than 0")
            elif unit_cost <= 0:
                st.error("❌ Unit cost must be greater than 0")
            else:
                with st.spinner("Creating purchase order..."):
                    po_number = f"PO-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

                    success = InventoryDB.create_purchase_order(
                        po_number=po_number,
                        item_master_id=selected_item['id'],
                        supplier_name=supplier_name,
                        quantity=quantity,
                        unit_cost=unit_cost,
                        po_date=po_date,
                        expected_delivery=expected_delivery,
                        notes=notes.strip() if notes else None,
                        username=st.session_state.user['id']  # Pass user_id (UUID) not display name
                    )
                
                if success:
                    st.success(f"✅ Purchase Order {po_number} created successfully!")
                    
                    ActivityLogger.log(
                        user_id=st.session_state.user['id'],
                        action_type='create_po',
                        module_key='inventory_management',
                        description=f"Created PO: {po_number}",
                        metadata={'po_number': po_number, 'item': selected_item_name},
                        user_email=st.session_state.user.get('email')
                    )
                    
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Failed to create purchase order")


# =====================================================
# TAB 6: ALERTS
# =====================================================

def show_alerts_tab(username: str):
    """Show low stock and expiry alerts"""
    
    st.markdown("### 🔔 Stock Alerts")
    
    # Low Stock Alerts
    st.markdown("#### 🔴 Low Stock Items")
    
    with st.spinner("Loading low stock items..."):
        low_stock = InventoryDB.get_low_stock_items()
    
    if low_stock:
        st.error(f"⚠️ {len(low_stock)} items below reorder level")
        
        df = pd.DataFrame(low_stock)
        display_cols = [
            'item_name',
            'category',
            'current_qty',
            'reorder_level',
            'unit',
            'avg_daily_usage',
            'days_until_stockout'
        ]
        display_cols = [col for col in display_cols if col in df.columns]
        
        if not display_cols:
            st.info("No displayable columns returned for low stock items.")
        else:
            display_df = df[display_cols].copy()
            column_mapping = {
                'item_name': 'Item',
                'category': 'Category',
                'current_qty': 'Current Stock',
                'reorder_level': 'Reorder Level',
                'unit': 'Unit',
                'avg_daily_usage': 'Avg Daily Usage',
                'days_until_stockout': 'Days to Stockout'
            }
            display_df.rename(
                columns={col: column_mapping.get(col, col) for col in display_df.columns},
                inplace=True
            )
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.success("✅ All items above reorder level")
    
    st.markdown("---")
    
    # Expiry Alerts
    st.markdown("#### ⚠️ Expiring Items")
    
    col1, col2 = st.columns(2)
    
    with col1:
        days_ahead = st.number_input("Days Ahead", min_value=7, max_value=365, value=30)
    
    with col2:
        if st.button("🔄 Refresh Alerts", use_container_width=True, key="refresh_alerts"):
            st.rerun()
    
    with st.spinner("Loading expiring items..."):
        expiring = InventoryDB.get_expiring_items(days_ahead=days_ahead)
    
    if expiring:
        # Categorize
        critical = [e for e in expiring if e.get('days_until_expiry', 999) <= 7]
        warning = [e for e in expiring if 7 < e.get('days_until_expiry', 999) <= 30]
        normal = [e for e in expiring if e.get('days_until_expiry', 999) > 30]
        
        # Show critical first
        if critical:
            st.error(f"🔴 CRITICAL: {len(critical)} items expiring in 7 days or less")
            df_critical = pd.DataFrame(critical)
            display_critical(df_critical)
        
        if warning:
            st.warning(f"🟡 WARNING: {len(warning)} items expiring in 8-30 days")
            df_warning = pd.DataFrame(warning)
            display_expiring(df_warning)
        
        if normal:
            st.info(f"🟢 {len(normal)} items expiring beyond 30 days")
            with st.expander("View items"):
                df_normal = pd.DataFrame(normal)
                display_expiring(df_normal)
    else:
        st.success(f"✅ No items expiring in next {days_ahead} days")


def display_critical(df: pd.DataFrame):
    """Display critical expiring items"""
    display_cols = ['item_name', 'batch_number', 'quantity', 'expiry_date', 'days_until_expiry']
    display_cols = [col for col in display_cols if col in df.columns]
    display_df = df[display_cols].copy()
    
    display_df['expiry_date'] = pd.to_datetime(display_df['expiry_date']).dt.strftime('%Y-%m-%d')
    display_df.columns = ['Item', 'Batch', 'Quantity', 'Expiry Date', 'Days Left']
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)


def display_expiring(df: pd.DataFrame):
    """Display expiring items"""
    display_cols = ['item_name', 'batch_number', 'quantity', 'expiry_date', 'days_until_expiry']
    display_cols = [col for col in display_cols if col in df.columns]
    display_df = df[display_cols].copy()
    
    display_df['expiry_date'] = pd.to_datetime(display_df['expiry_date']).dt.strftime('%Y-%m-%d')
    display_df.columns = ['Item', 'Batch', 'Quantity', 'Expiry Date', 'Days Left']
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)


# =====================================================
# TAB 7: HISTORY
# =====================================================

def show_history_tab(username: str, is_admin: bool):
    """View transaction history"""
    
    st.markdown("### 📜 Transaction History")
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        days_back = st.number_input("Days", min_value=7, max_value=365, value=30)
    
    with col2:
        transaction_types = ["All", "stock_in", "stock_out", "adjustment"]
        trans_filter = st.selectbox(
            "Type",
            options=transaction_types,
            key="history_type_filter_select"
        )
    
    with col3:
        master_items = InventoryDB.get_all_master_items()
        for item in master_items:
            if 'reorder_level' not in item and 'reorder_threshold' in item:
                item['reorder_level'] = item['reorder_threshold']
            if 'default_supplier_id' not in item and 'supplier_id' in item:
                item['default_supplier_id'] = item['supplier_id']
        item_names = ["All"] + [item['item_name'] for item in master_items]
        item_filter = st.selectbox(
            "Item",
            options=item_names,
            key="history_item_filter_select"
        )
    
    with col4:
        if st.button("🔄 Refresh", use_container_width=True, key="refresh_history"):
            st.rerun()
    
    # Load transactions
    with st.spinner("Loading transactions..."):
        transactions = InventoryDB.get_transaction_history(
            days_back=days_back,
            transaction_type=None if trans_filter == "All" else trans_filter,
            item_name=None if item_filter == "All" else item_filter
        )
    
    if not transactions:
        st.info("No transactions found matching filters")
        return
    
    st.success(f"✅ Found {len(transactions)} transactions")
    
    # Convert to DataFrame
    df = pd.DataFrame(transactions)
    
    # Select columns based on role
    if is_admin:
        display_cols = ['transaction_date', 'item_name', 'transaction_type', 'quantity', 'unit', 'batch_number', 'reference', 'unit_cost', 'total_cost', 'performed_by']
    else:
        display_cols = ['transaction_date', 'item_name', 'transaction_type', 'quantity', 'unit', 'batch_number', 'reference', 'performed_by']

    display_cols = [col for col in display_cols if col in df.columns]
    display_df = df[display_cols].copy()

    # Calculate total_cost if not present
    if 'total_cost' not in display_df.columns and 'unit_cost' in df.columns and 'quantity' in df.columns:
        display_df['total_cost'] = df['unit_cost'] * df['quantity']

    # Format
    if 'transaction_date' in display_df.columns:
        display_df['transaction_date'] = pd.to_datetime(display_df['transaction_date']).dt.strftime('%Y-%m-%d %H:%M')

    if 'unit_cost' in display_df.columns:
        display_df['unit_cost'] = display_df['unit_cost'].apply(lambda x: f"₹{x:.2f}" if pd.notna(x) else 'N/A')

    if 'total_cost' in display_df.columns:
        display_df['total_cost'] = display_df['total_cost'].apply(lambda x: f"₹{x:.2f}" if pd.notna(x) else 'N/A')

    # Rename
    column_mapping = {
        'transaction_date': 'Date & Time',
        'item_name': 'Item',
        'transaction_type': 'Type',
        'quantity': 'Quantity',
        'unit': 'Unit',
        'batch_number': 'Batch',
        'reference': 'Reference',
        'unit_cost': 'Unit Cost',
        'total_cost': 'Total Cost',
        'performed_by': 'User'
    }
    
    display_df.rename(columns=column_mapping, inplace=True)
    
    st.dataframe(display_df, use_container_width=True, hide_index=True, height=500)
    
    # Export
    if st.button("📥 Export to Excel", use_container_width=True, key="export_history"):
        export_to_excel(display_df, "transaction_history")


# =====================================================
# TAB 8: ITEM MASTER LIST (ADMIN ONLY)
# =====================================================

def show_item_master_tab(username: str):
    """Manage item master list (Admin only)"""
    
    st.markdown("### 📋 Item Master List")
    st.caption("Manage item templates - stock is tracked in batches")
    
    subtabs = st.tabs(["📋 All Items", "➕ Add Item", "✏️ Edit Item"])
    
    with subtabs[0]:
        show_all_master_items()
    
    with subtabs[1]:
        show_add_master_item(username)
    
    with subtabs[2]:
        show_edit_master_item(username)


def show_all_master_items():
    """View all master items"""
    
    st.markdown("#### 📋 All Master Items")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.selectbox(
            "Status",
            ["All", "Active", "Inactive"],
            key="master_status_filter_select"
        )
    
    with col2:
        categories = InventoryDB.get_all_categories()
        category_filter = st.selectbox(
            "Category",
            ["All"] + categories,
            key="master_category_filter_select"
        )
    
    with col3:
        if st.button("🔄 Refresh", use_container_width=True, key="refresh_master_items"):
            st.rerun()
    
    # Load items
    with st.spinner("Loading items..."):
        if status_filter == "Active":
            items = InventoryDB.get_all_master_items(active_only=True)
        elif status_filter == "Inactive":
            all_items = InventoryDB.get_all_master_items(active_only=False)
            items = [i for i in all_items if not i.get('is_active', True)]
        else:
            items = InventoryDB.get_all_master_items(active_only=False)
    
    # Apply category filter
    if category_filter != "All":
        items = [i for i in items if i.get('category') == category_filter]
    
    if not items:
        st.info("No items found")
        return
    
    st.success(f"✅ Found {len(items)} items")
    
    # Display
    df = pd.DataFrame(items)
    
    if 'reorder_level' not in df.columns and 'reorder_threshold' in df.columns:
        df['reorder_level'] = df['reorder_threshold']
    display_cols = ['item_name', 'sku', 'category', 'brand', 'unit', 'current_qty', 'reorder_level', 'is_active']
    display_cols = [col for col in display_cols if col in df.columns]
    
    if not display_cols:
        st.info("No displayable columns returned for master items.")
        return
    
    display_df = df[display_cols].copy()
    
    if 'is_active' in display_df.columns:
        display_df['is_active'] = display_df['is_active'].map({True: '✅ Active', False: '❌ Inactive'})
    
    column_mapping = {
        'item_name': 'Item Name',
        'sku': 'SKU',
        'category': 'Category',
        'brand': 'Brand',
        'unit': 'Unit',
        'current_qty': 'Current Stock',
        'reorder_level': 'Reorder Level',
        'is_active': 'Status'
    }
    
    display_df.rename(
        columns={col: column_mapping.get(col, col) for col in display_df.columns},
        inplace=True
    )
    
    st.dataframe(display_df, use_container_width=True, hide_index=True, height=500)


def show_add_master_item(username: str):
    """Add new master item"""
    
    st.markdown("#### ➕ Add New Master Item")
    
    user_id = st.session_state.user.get('id') if 'user' in st.session_state and st.session_state.user else None
    
    with st.form("add_master_item_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            item_name = st.text_input("Item Name *", placeholder="e.g., Fish Feed 3mm 28% Protein")
            sku = st.text_input("SKU *", placeholder="e.g., FF-3MM-28P")

            # Category selection with dropdown + custom option
            existing_categories = InventoryDB.get_all_categories()
            category_options = ["-- Add New Category --"] + existing_categories

            selected_category_option = st.selectbox(
                "Category *",
                options=category_options,
                key="add_master_category_select"
            )

            # If "Add New Category" selected, show text input
            if selected_category_option == "-- Add New Category --":
                category = st.text_input(
                    "Enter New Category Name *",
                    placeholder="e.g., Fish Feed, Chemicals, Equipment",
                    key="add_master_new_category_input"
                )
            else:
                category = selected_category_option

            brand = st.text_input("Brand/Manufacturer", placeholder="e.g., Growel")
            unit = st.selectbox(
                "Unit *",
                options=["kg", "g", "liter", "ml", "pieces", "bags", "boxes"],
                key="add_master_unit_select"
            )
        
        with col2:
            reorder_threshold = st.number_input("Reorder Level *", min_value=0.0, step=0.01, format="%.2f")
            
            suppliers = InventoryDB.get_all_suppliers(active_only=True)
            supplier_options = [None] + [s['id'] for s in suppliers if s.get('id') is not None]
            supplier_label_map = {
                None: "None",
                **{s['id']: s.get('supplier_name', f"Supplier #{s['id']}") for s in suppliers if s.get('id') is not None}
            }
            
            selected_supplier_id = st.selectbox(
                "Default Supplier",
                options=supplier_options,
                format_func=lambda value: supplier_label_map.get(value, "Unknown"),
                key="add_master_default_supplier_select"
            )
            selected_supplier_name = supplier_label_map.get(selected_supplier_id, "None")
            
            specifications = st.text_area("Specifications", height=80)
            notes = st.text_area("Notes", height=80)
        
        st.markdown("---")
        submitted = st.form_submit_button("✅ Add Item", type="primary", use_container_width=True)
        
        if submitted:
            errors = []
            
            if not item_name or len(item_name.strip()) < 3:
                errors.append("Item name is required (minimum 3 characters)")
            
            if not sku or len(sku.strip()) < 2:
                errors.append("SKU is required (minimum 2 characters)")
            
            if not category or len(category.strip()) < 2:
                errors.append("Category is required")
            
            if reorder_threshold < 0:
                errors.append("Reorder level cannot be negative")
            
            if errors:
                for error in errors:
                    st.error(f"❌ {error}")
            else:
                with st.spinner("Adding item..."):
                    supplier_kwargs = {}
                    if selected_supplier_id is not None:
                        supplier_kwargs["default_supplier_id"] = selected_supplier_id
                    
                    success = InventoryDB.add_master_item(
                        item_name=item_name.strip(),
                        sku=sku.strip(),
                        category=category.strip(),
                        brand=brand.strip() if brand else None,
                        unit=unit,
                        reorder_threshold=reorder_threshold,
                        specifications=specifications.strip() if specifications else None,
                        notes=notes.strip() if notes else None,
                        username=username,
                        user_id=user_id,
                        **supplier_kwargs
                    )
            
            if success:
                st.success(f"✅ Item '{item_name}' added successfully!")
                
                ActivityLogger.log(
                    user_id=st.session_state.user['id'],
                    action_type='add_master_item',
                    module_key='inventory_management',
                    description=f"Added master item: {item_name}",
                    metadata={
                        'item_name': item_name,
                        'sku': sku,
                        'supplier': selected_supplier_name if selected_supplier_id else None,
                        'default_supplier_id': selected_supplier_id,
                        'reorder_threshold': reorder_threshold
                    }
                )
                
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Failed to add item. SKU may already exist.")


def show_edit_master_item(username: str):
    """Edit master item"""
    
    st.markdown("#### ✏️ Edit Master Item")
    
    items = InventoryDB.get_all_master_items(active_only=False)
    
    if not items:
        st.warning("No items found")
        return
    
    # Item selection
    item_options = {f"{item['item_name']} ({item.get('sku', 'N/A')})": item for item in items}
    selected_key = st.selectbox(
        "Select Item",
        options=list(item_options.keys()),
        key="edit_master_item_select"
    )
    selected_item = item_options[selected_key]
    
    st.markdown("---")
    
    with st.form("edit_master_item_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            item_name = st.text_input("Item Name *", value=selected_item.get('item_name', ''))
            sku = st.text_input("SKU *", value=selected_item.get('sku', ''))

            # Category selection with dropdown + custom option
            current_category = selected_item.get('category', '')
            existing_categories = InventoryDB.get_all_categories()

            # Build category options with current category first if it exists
            if current_category and current_category not in existing_categories:
                category_options = [current_category, "-- Add New Category --"] + existing_categories
            else:
                category_options = ["-- Add New Category --"] + existing_categories

            # Set initial selection to current category or first option
            default_index = 0
            if current_category in category_options:
                default_index = category_options.index(current_category)

            selected_category_option = st.selectbox(
                "Category *",
                options=category_options,
                index=default_index,
                key="edit_master_category_select"
            )

            # If "Add New Category" selected, show text input
            if selected_category_option == "-- Add New Category --":
                category = st.text_input(
                    "Enter New Category Name *",
                    value=current_category,
                    placeholder="e.g., Fish Feed, Chemicals, Equipment",
                    key="edit_master_new_category_input"
                )
            else:
                category = selected_category_option

            brand = st.text_input("Brand", value=selected_item.get('brand', '') or '')

            units = ["kg", "g", "liter", "ml", "pieces", "bags", "boxes"]
            current_unit = selected_item.get('unit', 'kg')
            unit_index = units.index(current_unit) if current_unit in units else 0
            unit = st.selectbox(
                "Unit *",
                options=units,
                index=unit_index,
                key="edit_master_unit_select"
            )
        
        with col2:
            reorder_threshold_value = selected_item.get('reorder_threshold')
            if reorder_threshold_value is None:
                reorder_threshold_value = selected_item.get('reorder_level', 0)
            try:
                reorder_threshold_value = float(reorder_threshold_value or 0)
            except (TypeError, ValueError):
                reorder_threshold_value = 0.0
            
            reorder_threshold = st.number_input(
                "Reorder Level *",
                value=reorder_threshold_value,
                key="edit_master_reorder_threshold"
            )
            
            suppliers = InventoryDB.get_all_suppliers(active_only=True)
            supplier_options = [None] + [s['id'] for s in suppliers if s.get('id') is not None]
            supplier_label_map = {
                None: "None",
                **{s['id']: s.get('supplier_name', f"Supplier #{s['id']}") for s in suppliers if s.get('id') is not None}
            }
            
            current_supplier_id = selected_item.get('default_supplier_id')
            if current_supplier_id is None:
                current_supplier_id = selected_item.get('supplier_id')
            if current_supplier_id is not None and current_supplier_id not in supplier_label_map:
                supplier_options.append(current_supplier_id)
                supplier_label_map[current_supplier_id] = selected_item.get('supplier_name', f"Supplier #{current_supplier_id}")
            
            supplier_index = supplier_options.index(current_supplier_id) if current_supplier_id in supplier_options else 0
            
            selected_supplier_id = st.selectbox(
                "Default Supplier",
                options=supplier_options,
                index=supplier_index,
                format_func=lambda value: supplier_label_map.get(value, "Unknown"),
                key="edit_master_default_supplier_select"
            )
            selected_supplier_name = supplier_label_map.get(selected_supplier_id, "None")
            
            is_active = st.checkbox("Active", value=selected_item.get('is_active', True))
            
            specifications = st.text_area("Specifications", value=selected_item.get('specifications', '') or '', height=80)
            notes = st.text_area("Notes", value=selected_item.get('notes', '') or '', height=80)
        
        st.markdown("---")
        
        col1, col2 = st.columns([3, 1])
        with col2:
            submitted = st.form_submit_button("💾 Update Item", type="primary", use_container_width=True)
        
        if submitted:
            with st.spinner("Updating item..."):
                success = InventoryDB.update_master_item(
                    item_master_id=selected_item['id'],
                    item_name=item_name.strip(),
                    sku=sku.strip(),
                    category=category.strip(),
                    brand=brand.strip() if brand else None,
                    unit=unit,
                    reorder_threshold=reorder_threshold,
                    default_supplier_id=selected_supplier_id,
                    specifications=specifications.strip() if specifications else None,
                    notes=notes.strip() if notes else None,
                    is_active=is_active,
                    username=username
                )
            
            if success:
                st.success(f"✅ Item '{item_name}' updated successfully!")
                
                ActivityLogger.log(
                    user_id=st.session_state.user['id'],
                    action_type='update_master_item',
                    module_key='inventory_management',
                    description=f"Updated master item: {item_name}",
                    metadata={
                        'item_name': item_name,
                        'supplier': selected_supplier_name if selected_supplier_id else None,
                        'default_supplier_id': selected_supplier_id,
                        'reorder_threshold': reorder_threshold
                    }
                )
                
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Failed to update item")


# =====================================================
# TAB 9: SUPPLIERS (ADMIN ONLY)
# =====================================================

def show_suppliers_tab(username: str):
    """Manage suppliers (Admin only)"""

    st.markdown("### 👥 Suppliers")
    st.caption("Manage suppliers for inventory items")
    st.markdown("---")

    subtabs = st.tabs(["📋 View Suppliers", "➕ Add Supplier", "✏️ Edit Supplier"])

    with subtabs[0]:
        show_all_suppliers()

    with subtabs[1]:
        show_add_supplier(username)

    with subtabs[2]:
        show_edit_supplier(username)


def show_all_suppliers():
    """View all suppliers"""
    
    st.markdown("#### 📋 All Suppliers")
    
    status_filter = st.selectbox(
        "Status",
        ["All", "Active", "Inactive"],
        key="supplier_status_filter_select"
    )
    
    with st.spinner("Loading suppliers..."):
        if status_filter == "Active":
            suppliers = InventoryDB.get_all_suppliers(active_only=True)
        elif status_filter == "Inactive":
            all_suppliers = InventoryDB.get_all_suppliers(active_only=False)
            suppliers = [s for s in all_suppliers if not s.get('is_active', True)]
        else:
            suppliers = InventoryDB.get_all_suppliers(active_only=False)
    
    if not suppliers:
        st.info("No suppliers found")
        return
    
    st.success(f"✅ Found {len(suppliers)} suppliers")
    
    df = pd.DataFrame(suppliers)
    display_cols = ['supplier_name', 'contact_person', 'phone', 'email', 'address', 'is_active']
    display_cols = [col for col in display_cols if col in df.columns]
    display_df = df[display_cols].copy()
    
    display_df['is_active'] = display_df['is_active'].map({True: '✅ Active', False: '❌ Inactive'})
    display_df.columns = ['Supplier Name', 'Contact Person', 'Phone', 'Email', 'Address', 'Status']
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)


def show_add_supplier(username: str):
    """Add new supplier"""
    
    st.markdown("#### ➕ Add New Supplier")
    
    with st.form("add_supplier_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            supplier_name = st.text_input("Supplier Name *", placeholder="e.g., ABC Suppliers")
            contact_person = st.text_input("Contact Person", placeholder="e.g., John Doe")
            phone = st.text_input("Phone", placeholder="e.g., +91-9876543210")
        
        with col2:
            email = st.text_input("Email", placeholder="e.g., contact@supplier.com")
            address = st.text_area("Address", height=100)
            notes = st.text_area("Notes", height=100)
        
        st.markdown("---")
        submitted = st.form_submit_button("✅ Add Supplier", type="primary", use_container_width=True)
        
        if submitted:
            if not supplier_name or len(supplier_name.strip()) < 3:
                st.error("❌ Supplier name is required (minimum 3 characters)")
            else:
                with st.spinner("Adding supplier..."):
                    success = InventoryDB.add_supplier(
                        supplier_name=supplier_name.strip(),
                        contact_person=contact_person.strip() if contact_person else None,
                        phone=phone.strip() if phone else None,
                        email=email.strip() if email else None,
                        address=address.strip() if address else None,
                        notes=notes.strip() if notes else None,
                        username=username
                    )
                
                if success:
                    st.success(f"✅ Supplier '{supplier_name}' added successfully!")
                    
                    ActivityLogger.log(
                        user_id=st.session_state.user['id'],
                        action_type='add_supplier',
                        module_key='inventory_management',
                        description=f"Added supplier: {supplier_name}"
                    )
                    
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Failed to add supplier")


def show_edit_supplier(username: str):
    """Edit or delete existing supplier"""

    st.markdown("#### ✏️ Edit Supplier")

    suppliers = InventoryDB.get_all_suppliers(active_only=False)

    if not suppliers:
        st.warning("No suppliers found. Add a supplier first.")
        return

    # Supplier selection
    supplier_options = {f"{s['supplier_name']} ({s.get('phone', 'N/A')})": s for s in suppliers}
    selected_key = st.selectbox(
        "Select Supplier",
        options=list(supplier_options.keys()),
        key="edit_supplier_select"
    )
    selected_supplier = supplier_options[selected_key]

    st.markdown("---")

    # Get item count for this supplier
    all_items = InventoryDB.get_all_master_items(active_only=False)
    item_count = 0
    if all_items:
        items_df = pd.DataFrame(all_items)
        if 'default_supplier_id' in items_df.columns:
            item_count = len(items_df[items_df['default_supplier_id'] == selected_supplier['id']])

    if item_count > 0:
        st.info(f"ℹ️ This supplier is set as default for {item_count} item(s)")

    with st.form("edit_supplier_form"):
        col1, col2 = st.columns(2)

        with col1:
            supplier_name = st.text_input(
                "Supplier Name *",
                value=selected_supplier.get('supplier_name', ''),
                placeholder="e.g., ABC Suppliers"
            )
            contact_person = st.text_input(
                "Contact Person",
                value=selected_supplier.get('contact_person', '') or '',
                placeholder="e.g., John Doe"
            )
            phone = st.text_input(
                "Phone",
                value=selected_supplier.get('phone', '') or '',
                placeholder="e.g., +91-9876543210"
            )

        with col2:
            email = st.text_input(
                "Email",
                value=selected_supplier.get('email', '') or '',
                placeholder="e.g., contact@supplier.com"
            )
            address = st.text_area(
                "Address",
                value=selected_supplier.get('address', '') or '',
                height=80
            )
            notes = st.text_area(
                "Notes",
                value=selected_supplier.get('notes', '') or '',
                height=80
            )

        # Status toggle
        is_active = st.checkbox(
            "Active Supplier",
            value=selected_supplier.get('is_active', True),
            key="edit_supplier_is_active"
        )

        st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:
            update_submitted = st.form_submit_button("💾 Update Supplier", type="primary", use_container_width=True)

        with col2:
            delete_submitted = st.form_submit_button("🗑️ Delete Supplier", type="secondary", use_container_width=True)

        if update_submitted:
            # Validation
            if not supplier_name or len(supplier_name.strip()) < 3:
                st.error("❌ Supplier name is required (minimum 3 characters)")
                return

            # Update supplier
            updates = {
                'supplier_name': supplier_name.strip(),
                'contact_person': contact_person.strip() if contact_person else None,
                'phone': phone.strip() if phone else None,
                'email': email.strip() if email else None,
                'address': address.strip() if address else None,
                'notes': notes.strip() if notes else None,
                'is_active': is_active
            }

            success = InventoryDB.update_supplier(
                supplier_id=selected_supplier['id'],
                updates=updates
            )

            if success:
                st.success(f"✅ Supplier '{supplier_name}' updated successfully!")

                # Log activity
                if 'user' in st.session_state and st.session_state.user:
                    ActivityLogger.log(
                        user_id=st.session_state.user['id'],
                        action_type='update_supplier',
                        module_key='inventory_management',
                        description=f"Updated supplier: {selected_supplier['supplier_name']} → {supplier_name}",
                        metadata={
                            'supplier_id': selected_supplier['id'],
                            'old_name': selected_supplier['supplier_name'],
                            'new_name': supplier_name
                        }
                    )

                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Failed to update supplier")

        if delete_submitted:
            # Attempt to delete
            success = InventoryDB.delete_supplier(selected_supplier['id'])

            if success:
                st.success(f"✅ Supplier '{selected_supplier['supplier_name']}' deleted successfully!")

                # Log activity
                if 'user' in st.session_state and st.session_state.user:
                    ActivityLogger.log(
                        user_id=st.session_state.user['id'],
                        action_type='delete_supplier',
                        module_key='inventory_management',
                        description=f"Deleted supplier: {selected_supplier['supplier_name']}",
                        metadata={'supplier_name': selected_supplier['supplier_name']}
                    )

                time.sleep(1)
                st.rerun()
            # Error message is already shown by delete_supplier method


# =====================================================
# TAB 10: ANALYTICS (ADMIN ONLY)
# =====================================================

def show_analytics_tab(username: str):
    """Analytics and reports (Admin only)"""
    
    st.markdown("### 📈 Analytics & Reports")
    
    subtabs = st.tabs(["📊 Consumption", "💰 Cost Analysis", "📉 Trends"])
    
    with subtabs[0]:
        show_consumption_analytics()
    
    with subtabs[1]:
        show_cost_analysis()
    
    with subtabs[2]:
        show_trends_analytics()


def show_consumption_analytics():
    """Show consumption by module"""
    
    st.markdown("#### 📊 Module-wise Consumption")
    
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input("Start Date", value=date.today() - timedelta(days=30))
    
    with col2:
        end_date = st.date_input("End Date", value=date.today())
    
    if start_date > end_date:
        st.error("Start date must be before end date")
        return
    
    # Get modules from activity logs
    modules = ["biofloc", "ras", "hydroponics", "microgreens", "crops"]
    
    module_filter = st.multiselect("Modules", options=modules, default=modules)
    
    if not module_filter:
        st.warning("Please select at least one module")
        return
    
    with st.spinner("Generating consumption report..."):
        consumption_data = []
        
        for module in module_filter:
            module_consumption = InventoryDB.get_module_consumption(
                module_name=module,
                start_date=start_date,
                end_date=end_date
            )
            consumption_data.extend(module_consumption)
    
    if consumption_data:
        df = pd.DataFrame(consumption_data)
        
        # Summary by module
        st.markdown("##### Summary by Module")
        module_summary = df.groupby('module_name').agg({
            'total_quantity': 'sum',
            'total_cost': 'sum'
        }).reset_index()
        
        module_summary.columns = ['Module', 'Total Quantity', 'Total Cost']
        module_summary['Total Cost'] = module_summary['Total Cost'].apply(lambda x: f"₹{x:,.2f}")
        
        st.dataframe(module_summary, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # Detailed view
        st.markdown("##### Detailed Consumption")
        
        display_cols = ['module_name', 'item_name', 'total_quantity', 'unit', 'total_cost']
        display_cols = [col for col in display_cols if col in df.columns]
        display_df = df[display_cols].copy()
        
        display_df['total_cost'] = display_df['total_cost'].apply(lambda x: f"₹{x:,.2f}" if pd.notna(x) else 'N/A')
        display_df.columns = ['Module', 'Item', 'Quantity', 'Unit', 'Total Cost']
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # Export
        if st.button("📥 Export Report", use_container_width=True, key="export_consumption"):
            export_to_excel(display_df, "consumption_report")
    else:
        st.info("No consumption data found for selected period")


def show_cost_analysis():
    """Show cost analysis"""
    
    st.markdown("#### 💰 Cost Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        analysis_period = st.selectbox(
            "Period",
            ["Last 7 Days", "Last 30 Days", "Last 90 Days", "Custom"],
            key="cost_analysis_period_select"
        )
    
    with col2:
        if analysis_period == "Custom":
            custom_days = st.number_input("Days", min_value=1, max_value=365, value=30)
        else:
            period_map = {"Last 7 Days": 7, "Last 30 Days": 30, "Last 90 Days": 90}
            custom_days = period_map.get(analysis_period, 30)
    
    with st.spinner("Analyzing costs..."):
        # Get transaction history with costs
        transactions = InventoryDB.get_transaction_history(days_back=custom_days)
    
    if transactions:
        df = pd.DataFrame(transactions)
        
        # Total costs
        if 'unit_cost' in df.columns and 'quantity' in df.columns:
            df['total_cost'] = df['unit_cost'] * df['quantity']
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                total_cost = df['total_cost'].sum()
                st.metric("Total Cost", f"₹{total_cost:,.2f}")
            
            with col2:
                stock_in = df[df['transaction_type'] == 'stock_in']['total_cost'].sum()
                st.metric("Stock In Cost", f"₹{stock_in:,.2f}")
            
            with col3:
                stock_out = df[df['transaction_type'] == 'stock_out']['total_cost'].sum()
                st.metric("Stock Out Cost", f"₹{stock_out:,.2f}")
            
            st.markdown("---")
            
            # Cost by item
            st.markdown("##### Cost by Item")
            item_costs = df.groupby('item_name')['total_cost'].sum().reset_index()
            item_costs.columns = ['Item', 'Total Cost']
            item_costs = item_costs.sort_values('Total Cost', ascending=False)
            item_costs['Total Cost'] = item_costs['Total Cost'].apply(lambda x: f"₹{x:,.2f}")
            
            st.dataframe(item_costs, use_container_width=True, hide_index=True)
    else:
        st.info("No cost data available for selected period")


def show_trends_analytics():
    """Show inventory trends"""

    st.markdown("#### 📉 Inventory Trends")

    st.info("📊 Trend analysis coming soon - will show stock level changes over time")


# =====================================================
# CATEGORIES TAB
# =====================================================

def show_categories_tab(username: str):
    """Main categories management tab with view/add/edit sub-tabs"""

    st.markdown("### 🏷️ Category Management")
    st.caption("Manage inventory categories for master items")
    st.markdown("---")

    # Create sub-tabs for View, Add, Edit
    sub_tabs = st.tabs(["📋 View Categories", "➕ Add Category", "✏️ Edit Category"])

    with sub_tabs[0]:
        show_view_categories()

    with sub_tabs[1]:
        show_add_category(username)

    with sub_tabs[2]:
        show_edit_category(username)


def show_view_categories():
    """View all categories"""

    st.markdown("#### 📋 All Categories")

    categories = InventoryDB.get_categories()

    if not categories:
        st.info("No categories found. Add your first category using the 'Add Category' tab.")
        return

    # Display total count
    st.metric("Total Categories", len(categories))
    st.markdown("---")

    # Create dataframe for display
    df = pd.DataFrame(categories)

    # Format columns
    display_columns = ['category_name', 'description', 'created_at']
    if 'created_at' in df.columns:
        df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')

    # Rename columns for display
    column_mapping = {
        'category_name': 'Category Name',
        'description': 'Description',
        'created_at': 'Created At'
    }

    # Select and rename columns
    available_columns = [col for col in display_columns if col in df.columns]
    df_display = df[available_columns].copy()
    df_display.columns = [column_mapping.get(col, col) for col in available_columns]

    # Display table
    st.dataframe(df_display, use_container_width=True, hide_index=True)

    # Show category usage statistics
    st.markdown("---")
    st.markdown("#### 📊 Category Usage")

    # Get items per category
    all_items = InventoryDB.get_all_master_items(active_only=False)
    if all_items:
        items_df = pd.DataFrame(all_items)
        if 'category' in items_df.columns:
            category_counts = items_df['category'].value_counts().reset_index()
            category_counts.columns = ['Category', 'Number of Items']
            st.dataframe(category_counts, use_container_width=True, hide_index=True)
        else:
            st.info("No items assigned to categories yet")
    else:
        st.info("No items found in inventory")


def show_add_category(username: str):
    """Add new category"""

    st.markdown("#### ➕ Add New Category")

    user_id = st.session_state.user.get('id') if 'user' in st.session_state and st.session_state.user else None

    with st.form("add_category_form", clear_on_submit=True):
        category_name = st.text_input(
            "Category Name *",
            placeholder="e.g., Fish Feed, Chemicals, Equipment",
            max_chars=100
        )

        description = st.text_area(
            "Description",
            placeholder="Brief description of this category",
            height=100,
            max_chars=500
        )

        st.markdown("---")
        submitted = st.form_submit_button("✅ Add Category", type="primary", use_container_width=True)

        if submitted:
            # Validation
            if not category_name or len(category_name.strip()) < 2:
                st.error("❌ Category name is required (minimum 2 characters)")
                return

            # Check if category already exists
            existing_categories = InventoryDB.get_categories()
            existing_names = [cat['category_name'].lower() for cat in existing_categories]

            if category_name.strip().lower() in existing_names:
                st.error(f"❌ Category '{category_name}' already exists")
                return

            # Add category
            success = InventoryDB.add_category(
                category_name=category_name,
                description=description if description else None,
                user_id=user_id
            )

            if success:
                st.success(f"✅ Category '{category_name}' added successfully!")

                # Log activity
                if 'user' in st.session_state and st.session_state.user:
                    ActivityLogger.log(
                        user_id=st.session_state.user['id'],
                        action_type='add_category',
                        module_key='inventory_management',
                        description=f"Added category: {category_name}",
                        metadata={'category_name': category_name}
                    )

                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Failed to add category. Please try again.")


def show_edit_category(username: str):
    """Edit existing category"""

    st.markdown("#### ✏️ Edit Category")

    categories = InventoryDB.get_categories()

    if not categories:
        st.warning("No categories found. Add a category first.")
        return

    # Category selection
    category_options = {cat['category_name']: cat for cat in categories}
    selected_name = st.selectbox(
        "Select Category",
        options=list(category_options.keys()),
        key="edit_category_select"
    )
    selected_category = category_options[selected_name]

    st.markdown("---")

    # Get item count for this category
    all_items = InventoryDB.get_all_master_items(active_only=False)
    item_count = 0
    if all_items:
        items_df = pd.DataFrame(all_items)
        if 'category' in items_df.columns:
            item_count = len(items_df[items_df['category'] == selected_category['category_name']])

    if item_count > 0:
        st.info(f"ℹ️ This category is currently used by {item_count} item(s)")

    with st.form("edit_category_form"):
        new_category_name = st.text_input(
            "Category Name *",
            value=selected_category.get('category_name', ''),
            max_chars=100
        )

        new_description = st.text_area(
            "Description",
            value=selected_category.get('description', '') or '',
            height=100,
            max_chars=500
        )

        st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:
            update_submitted = st.form_submit_button("💾 Update Category", type="primary", use_container_width=True)

        with col2:
            delete_submitted = st.form_submit_button("🗑️ Delete Category", type="secondary", use_container_width=True)

        if update_submitted:
            # Validation
            if not new_category_name or len(new_category_name.strip()) < 2:
                st.error("❌ Category name is required (minimum 2 characters)")
                return

            # Check if new name conflicts with existing (except current)
            existing_categories = InventoryDB.get_categories()
            for cat in existing_categories:
                if cat['id'] != selected_category['id'] and cat['category_name'].lower() == new_category_name.strip().lower():
                    st.error(f"❌ Category name '{new_category_name}' already exists")
                    return

            # Update category
            success = InventoryDB.update_category(
                category_id=selected_category['id'],
                category_name=new_category_name,
                description=new_description if new_description else None
            )

            if success:
                st.success(f"✅ Category updated successfully!")

                # Log activity
                if 'user' in st.session_state and st.session_state.user:
                    ActivityLogger.log(
                        user_id=st.session_state.user['id'],
                        action_type='update_category',
                        module_key='inventory_management',
                        description=f"Updated category: {selected_category['category_name']} → {new_category_name}",
                        metadata={
                            'old_name': selected_category['category_name'],
                            'new_name': new_category_name
                        }
                    )

                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Failed to update category")

        if delete_submitted:
            # Attempt to delete
            success = InventoryDB.delete_category(selected_category['id'])

            if success:
                st.success(f"✅ Category '{selected_category['category_name']}' deleted successfully!")

                # Log activity
                if 'user' in st.session_state and st.session_state.user:
                    ActivityLogger.log(
                        user_id=st.session_state.user['id'],
                        action_type='delete_category',
                        module_key='inventory_management',
                        description=f"Deleted category: {selected_category['category_name']}",
                        metadata={'category_name': selected_category['category_name']}
                    )

                time.sleep(1)
                st.rerun()
            # Error message is already shown by delete_category method


# =====================================================
# HELPER FUNCTIONS
# =====================================================

def export_to_excel(df: pd.DataFrame, filename_prefix: str):
    """Export dataframe to Excel"""
    from io import BytesIO
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Data')
    
    output.seek(0)
    
    st.download_button(
        label="📥 Download Excel",
        data=output,
        file_name=f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
