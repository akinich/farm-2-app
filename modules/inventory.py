"""
Inventory Management Module V1.1.0
Professional inventory system with expiry tracking, batches, POs, and analytics

VERSION HISTORY:
1.1.0 - Professional features added - 09/11/25
      FEATURES:
      - Expiry date tracking with 30-day alerts (no blocking)
      - Batch/Lot number tracking
      - Stock adjustments (wastage, damage, expired, etc.)
      - Purchase Order management
      - Supplier management
      - Usage analytics by module
      - Cost tracking (unit_cost prominently displayed)
      - Delete entries option (admin only)
      - Integration hooks for other modules
      - Excel export for all reports
      TABS:
      1. Dashboard - Quick metrics and charts
      2. Current Inventory - Editable table with filters
      3. Add Stock - Purchase with batch tracking
      4. Remove Stock - Usage tracking by module
      5. Stock Adjustments - Wastage, damage, etc.
      6. Purchase Orders - PO creation and tracking
      7. Low Stock & Expiry Alerts - Combined alerts
      8. Transaction History - Full audit trail
      9. Suppliers - Supplier management
      10. Analytics & Reports - Consumption trends, exports
1.0.0 - Initial inventory module - 08/11/25
"""
import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
from io import BytesIO

from auth.session import SessionManager
from config.database import ActivityLogger
from db.db_inventory import InventoryDB


def show():
    """Main entry point for Inventory Management module"""
    
    # Check module access
    SessionManager.require_module_access('inventory')
    
    # Get user info
    user = SessionManager.get_user()
    profile = SessionManager.get_user_profile()
    is_admin = SessionManager.is_admin()
    username = profile.get('full_name', user.get('email', 'Unknown'))
    
    # Module header
    st.title("📦 Inventory Management")
    st.caption(f"👤 {username} | Shared resource across all farm modules")
    st.markdown("---")
    
    # Create tabs
    tabs = st.tabs([
        "📊 Dashboard",
        "📦 Current Inventory",
        "➕ Add Stock",
        "➖ Remove Stock",
        "🔄 Adjustments",
        "🛒 Purchase Orders",
        "🔔 Alerts",
        "📜 History",
        "👥 Suppliers",
        "📈 Analytics"
    ])
    
    with tabs[0]:
        show_dashboard()
    
    with tabs[1]:
        show_current_inventory(username, is_admin)
    
    with tabs[2]:
        show_add_stock(username, is_admin)
    
    with tabs[3]:
        show_remove_stock(username)
    
    with tabs[4]:
        show_adjustments(username, is_admin)
    
    with tabs[5]:
        show_purchase_orders(username, is_admin)
    
    with tabs[6]:
        show_alerts()
    
    with tabs[7]:
        show_transaction_history(is_admin)
    
    with tabs[8]:
        show_suppliers(username, is_admin)
    
    with tabs[9]:
        show_analytics()


# =====================================================
# TAB 1: DASHBOARD
# =====================================================

def show_dashboard():
    """Dashboard with quick metrics and charts"""
    
    st.markdown("### 📊 Inventory Dashboard")
    
    # Load data
    items = InventoryDB.get_all_items(active_only=True)
    low_stock = InventoryDB.get_low_stock_items()
    expiring = InventoryDB.get_expiring_items(days_ahead=30)
    valuation = InventoryDB.get_inventory_valuation()
    
    # Top metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_items = len(items)
        st.metric("Total Items", total_items)
    
    with col2:
        low_stock_count = len(low_stock)
        st.metric("Low Stock Items", low_stock_count, 
                 delta="⚠️" if low_stock_count > 0 else None)
    
    with col3:
        expiring_count = len(expiring)
        st.metric("Expiring Soon", expiring_count,
                 delta="⚠️" if expiring_count > 0 else None)
    
    with col4:
        total_value = sum(v['total_value'] for v in valuation) if valuation else 0
        st.metric("Total Inventory Value", f"₹{total_value:,.2f}")
    
    st.markdown("---")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📊 Stock Status Distribution")
        if items:
            status_counts = {
                'Good Stock': len([i for i in items if i.get('stock_status') == 'good']),
                'Low Stock': len([i for i in items if i.get('stock_status') == 'low']),
                'Critical': len([i for i in items if i.get('stock_status') == 'critical'])
            }
            st.bar_chart(status_counts)
        else:
            st.info("No data available")
    
    with col2:
        st.markdown("#### 💰 Value by Category")
        if valuation:
            val_df = pd.DataFrame(valuation)
            st.bar_chart(val_df.set_index('category')['total_value'])
        else:
            st.info("No data available")
    
    # Recent activity
    st.markdown("---")
    st.markdown("#### 📜 Recent Transactions (Last 7 Days)")
    
    recent_tx = InventoryDB.get_transactions(days=7)
    if recent_tx:
        df = pd.DataFrame(recent_tx)
        df = df[['transaction_date', 'transaction_type', 'quantity_change', 'module_reference']].head(10)
        df['transaction_date'] = pd.to_datetime(df['transaction_date']).dt.strftime('%Y-%m-%d %H:%M')
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No recent transactions")


# =====================================================
# TAB 2: CURRENT INVENTORY
# =====================================================

def show_current_inventory(username: str, is_admin: bool):
    """Display current inventory with search, filters, and editing"""
    
    st.markdown("### 📦 Current Inventory")
    
    # Controls
    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
    
    with col1:
        search = st.text_input("🔍 Search items", placeholder="Search by name...", key="inv_search")
    
    with col2:
        categories = InventoryDB.get_categories()
        cat_options = ["All Categories"] + [c['category_name'] for c in categories]
        category_filter = st.selectbox("Category", cat_options, key="inv_category")
    
    with col3:
        stock_filter = st.selectbox("Stock Status", 
                                   ["All", "Good", "Low", "Critical"], key="inv_stock")
    
    with col4:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
    
    # Load inventory
    items = InventoryDB.get_all_items(active_only=True)
    
    # Apply filters
    if search:
        items = [i for i in items if search.lower() in i['item_name'].lower()]
    
    if category_filter != "All Categories":
        items = [i for i in items if i.get('category') == category_filter]
    
    if stock_filter != "All":
        items = [i for i in items if i.get('stock_status') == stock_filter.lower()]
    
    if not items:
        st.info("No items found")
        return
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Items Shown", len(items))
    with col2:
        total_qty = sum(i['current_qty'] for i in items)
        st.metric("Total Quantity", f"{total_qty:,.2f}")
    with col3:
        total_value = sum(i['current_qty'] * i.get('unit_cost', 0) for i in items)
        st.metric("Total Value", f"₹{total_value:,.2f}")
    with col4:
        low_count = len([i for i in items if i.get('stock_status') in ['low', 'critical']])
        st.metric("Need Attention", low_count)
    
    st.markdown("---")
    
    # Display table
    df = pd.DataFrame(items)
    
    # Select and format columns
    display_cols = [
        'item_name', 'category', 'current_qty', 'unit', 'unit_cost',
        'min_stock_level', 'reorder_threshold', 'max_stock_level',
        'supplier_name', 'last_restocked', 'stock_status'
    ]
    
    df_display = df[[col for col in display_cols if col in df.columns]].copy()
    
    # Format columns
    df_display['current_qty'] = df_display['current_qty'].round(2)
    df_display['unit_cost'] = df_display['unit_cost'].apply(lambda x: f"₹{x:,.2f}")
    
    if 'last_restocked' in df_display.columns:
        df_display['last_restocked'] = pd.to_datetime(df_display['last_restocked'], errors='coerce').dt.strftime('%Y-%m-%d')
    
    # Add status indicator
    status_map = {'good': '🟢 Good', 'low': '🟡 Low', 'critical': '🔴 Critical'}
    df_display['stock_status'] = df_display['stock_status'].map(status_map)
    
    # Display
    st.dataframe(df_display, use_container_width=True, hide_index=True, height=400)
    
    # Actions
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.info("💡 Admin can edit items in Admin Panel → Module Management")
    
    with col2:
        if st.button("📥 Export to Excel", use_container_width=True):
            export_inventory_excel(df_display, "current_inventory")
    
    with col3:
        if is_admin:
            if st.button("➕ Add New Item", use_container_width=True, type="primary"):
                st.session_state['show_add_item_form'] = True
    
    # Add item form (admin only)
    if is_admin and st.session_state.get('show_add_item_form', False):
        show_add_item_form(username)


def show_add_item_form(username: str):
    """Form to add new inventory item"""
    
    st.markdown("---")
    st.markdown("#### ➕ Add New Item")
    
    with st.form("add_item_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            item_name = st.text_input("Item Name *")
            categories = InventoryDB.get_categories()
            category = st.selectbox("Category *", [c['category_name'] for c in categories])
            unit = st.text_input("Unit *", placeholder="kg, L, pcs, etc.")
            unit_cost = st.number_input("Unit Cost (₹) *", min_value=0.0, step=1.0)
        
        with col2:
            min_stock = st.number_input("Min Stock Level", min_value=0.0, step=1.0, value=0.0)
            reorder_threshold = st.number_input("Reorder Threshold *", min_value=0.0, step=1.0)
            max_stock = st.number_input("Max Stock Level", min_value=0.0, step=1.0)
            reorder_qty = st.number_input("Reorder Quantity *", min_value=0.0, step=1.0)
        
        suppliers = InventoryDB.get_suppliers()
        supplier_options = {s['supplier_name']: s['id'] for s in suppliers}
        supplier = st.selectbox("Default Supplier", options=list(supplier_options.keys()))
        
        notes = st.text_area("Notes")
        
        col1, col2 = st.columns([3, 1])
        with col2:
            submitted = st.form_submit_button("➕ Add Item", type="primary", use_container_width=True)
        
        if submitted:
            if not item_name or not unit:
                st.error("Item name and unit are required")
            else:
                item_data = {
                    'item_name': item_name,
                    'category': category,
                    'unit': unit,
                    'unit_cost': unit_cost,
                    'min_stock_level': min_stock,
                    'reorder_threshold': reorder_threshold,
                    'max_stock_level': max_stock if max_stock > 0 else None,
                    'reorder_qty': reorder_qty,
                    'supplier_id': supplier_options[supplier],
                    'notes': notes,
                    'is_active': True
                }
                
                if InventoryDB.add_item(item_data, st.session_state.user['id']):
                    st.success(f"✅ Added {item_name} to inventory!")
                    st.session_state['show_add_item_form'] = False
                    
                    ActivityLogger.log(
                        user_id=st.session_state.user['id'],
                        action_type='add_inventory_item',
                        module_key='inventory',
                        description=f"Added new item: {item_name}"
                    )
                    st.rerun()


# =====================================================
# TAB 3: ADD STOCK (PURCHASE)
# =====================================================

def show_add_stock(username: str, is_admin: bool):
    """Add stock with batch tracking"""
    
    st.markdown("### ➕ Add Stock (Purchase/Restock)")
    st.info("💡 Record new stock purchases with batch tracking and expiry dates")
    
    with st.form("add_stock_form", clear_on_submit=True):
        # Item selection
        items = InventoryDB.get_all_items(active_only=True)
        item_options = {f"{i['item_name']} (Current: {i['current_qty']} {i['unit']})": i for i in items}
        
        selected_item = st.selectbox("Select Item *", options=list(item_options.keys()))
        item = item_options[selected_item]
        
        st.markdown("---")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            quantity = st.number_input("Quantity to Add *", min_value=0.01, step=1.0)
            unit_cost = st.number_input("Unit Cost (₹) *", min_value=0.0, step=1.0, 
                                       value=float(item.get('unit_cost', 0)))
        
        with col2:
            batch_number = st.text_input("Batch/Lot Number *", 
                                        value=f"BATCH-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
            expiry_date = st.date_input("Expiry Date", 
                                       min_value=date.today(),
                                       value=date.today() + timedelta(days=180))
        
        with col3:
            suppliers = InventoryDB.get_suppliers()
            supplier_options = {s['supplier_name']: s['id'] for s in suppliers}
            supplier = st.selectbox("Supplier *", options=list(supplier_options.keys()))
            
            po_number = st.text_input("PO Number (optional)")
        
        notes = st.text_area("Notes")
        
        # Summary
        st.markdown("---")
        st.markdown("#### 📋 Purchase Summary")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Current Stock", f"{item['current_qty']} {item['unit']}")
        with col2:
            st.metric("After Purchase", f"{item['current_qty'] + quantity} {item['unit']}")
        with col3:
            total_cost = quantity * unit_cost
            st.metric("Total Cost", f"₹{total_cost:,.2f}")
        
        submitted = st.form_submit_button("➕ Add Stock", type="primary", use_container_width=True)
        
        if submitted:
            if quantity <= 0:
                st.error("Quantity must be greater than 0")
            elif not batch_number:
                st.error("Batch number is required")
            else:
                if InventoryDB.add_stock(
                    item_id=item['id'],
                    quantity=quantity,
                    unit_cost=unit_cost,
                    batch_number=batch_number,
                    expiry_date=expiry_date,
                    supplier_id=supplier_options[supplier],
                    user_id=st.session_state.user['id'],
                    notes=notes,
                    po_number=po_number if po_number else None
                ):
                    st.success(f"✅ Added {quantity} {item['unit']} to {item['item_name']}")
                    st.success(f"🏷️ Batch: {batch_number}")
                    
                    ActivityLogger.log(
                        user_id=st.session_state.user['id'],
                        action_type='stock_add',
                        module_key='inventory',
                        description=f"Added {quantity} {item['unit']} of {item['item_name']}",
                        metadata={'item_id': item['id'], 'quantity': quantity, 'batch': batch_number}
                    )
                    st.rerun()


# =====================================================
# TAB 4: REMOVE STOCK (USAGE)
# =====================================================

def show_remove_stock(username: str):
    """Remove stock for module usage"""
    
    st.markdown("### ➖ Remove Stock (Usage)")
    st.info("💡 Record stock usage by different farm modules")
    
    with st.form("remove_stock_form", clear_on_submit=True):
        # Item selection
        items = InventoryDB.get_all_items(active_only=True)
        item_options = {f"{i['item_name']} (Available: {i['current_qty']} {i['unit']})": i for i in items}
        
        selected_item = st.selectbox("Select Item *", options=list(item_options.keys()))
        item = item_options[selected_item]
        
        st.markdown("---")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            quantity = st.number_input("Quantity to Remove *", 
                                      min_value=0.01, 
                                      max_value=float(item['current_qty']),
                                      step=0.1)
        
        with col2:
            modules = ["Biofloc", "RAS", "Microgreens", "Hydroponics", "Coco Coir", "Open Field", "General"]
            module_ref = st.selectbox("Used by Module *", options=modules)
        
        with col3:
            # Show batches for this item
            batches = InventoryDB.get_batches(item_id=item['id'], active_only=True)
            if batches:
                batch_options = {f"{b['batch_number']} (Qty: {b['remaining_qty']})": b['id'] for b in batches}
                selected_batch = st.selectbox("Batch (optional)", options=["Auto (FIFO)"] + list(batch_options.keys()))
                batch_id = batch_options.get(selected_batch) if selected_batch != "Auto (FIFO)" else None
            else:
                st.info("No batches available")
                batch_id = None
        
        notes = st.text_area("Notes")
        
        # Summary
        st.markdown("---")
        st.markdown("#### 📋 Usage Summary")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Current Stock", f"{item['current_qty']} {item['unit']}")
        with col2:
            new_qty = item['current_qty'] - quantity
            st.metric("After Usage", f"{new_qty} {item['unit']}")
        with col3:
            usage_cost = quantity * item.get('unit_cost', 0)
            st.metric("Usage Cost", f"₹{usage_cost:,.2f}")
        
        # Warning if stock low
        if new_qty <= item['reorder_threshold']:
            st.warning(f"⚠️ Stock will be below reorder threshold ({item['reorder_threshold']} {item['unit']})")
        
        submitted = st.form_submit_button("➖ Remove Stock", type="secondary", use_container_width=True)
        
        if submitted:
            if quantity <= 0:
                st.error("Quantity must be greater than 0")
            elif quantity > item['current_qty']:
                st.error(f"Cannot remove {quantity} {item['unit']}. Only {item['current_qty']} {item['unit']} available!")
            else:
                if InventoryDB.remove_stock(
                    item_id=item['id'],
                    quantity=quantity,
                    module_reference=module_ref,
                    user_id=st.session_state.user['id'],
                    notes=notes,
                    batch_id=batch_id
                ):
                    st.success(f"✅ Removed {quantity} {item['unit']} from {item['item_name']}")
                    st.success(f"📍 Used by: {module_ref}")
                    
                    ActivityLogger.log(
                        user_id=st.session_state.user['id'],
                        action_type='stock_remove',
                        module_key='inventory',
                        description=f"Removed {quantity} {item['unit']} of {item['item_name']} for {module_ref}",
                        metadata={'item_id': item['id'], 'quantity': quantity, 'module': module_ref}
                    )
                    st.rerun()


# =====================================================
# TAB 5: STOCK ADJUSTMENTS
# =====================================================

def show_adjustments(username: str, is_admin: bool):
    """Log stock adjustments (wastage, damage, etc.)"""
    
    st.markdown("### 🔄 Stock Adjustments")
    st.info("💡 Record wastage, damage, expiry, or stock count corrections")
    
    # Form to log adjustment
    with st.form("adjustment_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            items = InventoryDB.get_all_items(active_only=True)
            item_options = {f"{i['item_name']} (Current: {i['current_qty']} {i['unit']})": i for i in items}
            
            selected_item = st.selectbox("Select Item *", options=list(item_options.keys()))
            item = item_options[selected_item]
            
            adjustment_types = ['wastage', 'damage', 'expired', 'theft', 'count_correction', 'other']
            adjustment_type = st.selectbox("Adjustment Type *", options=adjustment_types)
            
            quantity = st.number_input("Quantity to Adjust *", min_value=0.01, step=0.1)
        
        with col2:
            # Show batches
            batches = InventoryDB.get_batches(item_id=item['id'], active_only=True)
            if batches:
                batch_options = {f"{b['batch_number']} (Qty: {b['remaining_qty']})": b['id'] for b in batches}
                selected_batch = st.selectbox("Batch (optional)", options=["Not specified"] + list(batch_options.keys()))
                batch_id = batch_options.get(selected_batch) if selected_batch != "Not specified" else None
            else:
                st.info("No batches available")
                batch_id = None
            
            reason = st.text_input("Reason *", placeholder="e.g., Spilled during transfer")
        
        notes = st.text_area("Additional Notes")
        
        submitted = st.form_submit_button("🔄 Log Adjustment", type="primary", use_container_width=True)
        
        if submitted:
            if not reason:
                st.error("Reason is required")
            elif quantity <= 0:
                st.error("Quantity must be greater than 0")
            else:
                if InventoryDB.log_adjustment(
                    item_id=item['id'],
                    adjustment_type=adjustment_type,
                    quantity=quantity,
                    reason=reason,
                    user_id=st.session_state.user['id'],
                    batch_id=batch_id,
                    notes=notes
                ):
                    st.success(f"✅ Logged adjustment: {quantity} {item['unit']} ({adjustment_type})")
                    
                    ActivityLogger.log(
                        user_id=st.session_state.user['id'],
                        action_type='stock_adjustment',
                        module_key='inventory',
                        description=f"Adjusted {item['item_name']}: -{quantity} {item['unit']} ({adjustment_type})",
                        metadata={'item_id': item['id'], 'type': adjustment_type, 'quantity': quantity}
                    )
                    st.rerun()
    
    # Show recent adjustments
    st.markdown("---")
    st.markdown("#### 📜 Recent Adjustments (Last 30 Days)")
    
    adjustments = InventoryDB.get_adjustments(days=30)
    
    if adjustments:
        df = pd.DataFrame(adjustments)
        
        # Flatten nested data
        df['item_name'] = df['inventory_items'].apply(lambda x: x['item_name'] if x else '')
        df['unit'] = df['inventory_items'].apply(lambda x: x['unit'] if x else '')
        
        display_df = df[['adjustment_date', 'item_name', 'adjustment_type', 
                        'quantity_adjusted', 'unit', 'reason']].copy()
        
        display_df['adjustment_date'] = pd.to_datetime(display_df['adjustment_date']).dt.strftime('%Y-%m-%d')
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("No adjustments logged in the last 30 days")


# =====================================================
# TAB 6: PURCHASE ORDERS
# =====================================================

def show_purchase_orders(username: str, is_admin: bool):
    """Create and manage purchase orders"""
    
    st.markdown("### 🛒 Purchase Orders")
    
    tab1, tab2 = st.tabs(["📋 View POs", "➕ Create PO"])
    
    with tab1:
        show_po_list(is_admin)
    
    with tab2:
        if is_admin:
            show_create_po(username)
        else:
            st.info("ℹ️ Only admins can create purchase orders")


def show_po_list(is_admin: bool):
    """Display list of purchase orders"""
    
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        status_filter = st.selectbox("Filter by Status", 
                                    ["All", "draft", "sent", "partial", "received", "closed", "cancelled"])
    
    with col2:
        days = st.number_input("Days to show", min_value=30, max_value=365, value=90)
    
    with col3:
        if st.button("🔄 Refresh"):
            st.rerun()
    
    # Load POs
    pos = InventoryDB.get_pos(status=None if status_filter == "All" else status_filter, days=days)
    
    if not pos:
        st.info("No purchase orders found")
        return
    
    st.success(f"✅ Found {len(pos)} purchase orders")
    
    # Display
    df = pd.DataFrame(pos)
    
    # Flatten supplier
    df['supplier_name'] = df['suppliers'].apply(lambda x: x['supplier_name'] if x else '')
    
    display_df = df[['po_number', 'supplier_name', 'po_date', 'expected_delivery_date', 
                     'status', 'total_amount']].copy()
    
    display_df['po_date'] = pd.to_datetime(display_df['po_date']).dt.strftime('%Y-%m-%d')
    display_df['expected_delivery_date'] = pd.to_datetime(display_df['expected_delivery_date'], errors='coerce').dt.strftime('%Y-%m-%d')
    display_df['total_amount'] = display_df['total_amount'].apply(lambda x: f"₹{x:,.2f}")
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)


def show_create_po(username: str):
    """Form to create a new purchase order"""
    
    st.markdown("#### ➕ Create New Purchase Order")
    
    # Initialize session state for PO items
    if 'po_items' not in st.session_state:
        st.session_state.po_items = []
    
    col1, col2 = st.columns(2)
    
    with col1:
        po_number = st.text_input("PO Number *", value=f"PO-{datetime.now().strftime('%Y%m%d-%H%M')}")
        
        suppliers = InventoryDB.get_suppliers()
        supplier_options = {s['supplier_name']: s['id'] for s in suppliers}
        supplier = st.selectbox("Supplier *", options=list(supplier_options.keys()))
    
    with col2:
        po_date = st.date_input("PO Date *", value=date.today())
        expected_delivery = st.date_input("Expected Delivery", value=date.today() + timedelta(days=7))
    
    notes = st.text_area("Notes")
    
    st.markdown("---")
    st.markdown("#### 📦 Add Items to PO")
    
    # Item selection
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
    
    with col1:
        items = InventoryDB.get_all_items(active_only=True)
        item_options = {i['item_name']: i for i in items}
        selected_item_name = st.selectbox("Item", options=list(item_options.keys()), key="po_item_select")
    
    with col2:
        item_qty = st.number_input("Quantity", min_value=0.1, step=1.0, key="po_item_qty")
    
    with col3:
        item = item_options[selected_item_name]
        item_cost = st.number_input("Unit Cost", min_value=0.0, step=1.0, 
                                    value=float(item.get('unit_cost', 0)), key="po_item_cost")
    
    with col4:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Add", use_container_width=True):
            po_item = {
                'item_id': item['id'],
                'item_name': item['item_name'],
                'unit': item['unit'],
                'ordered_qty': item_qty,
                'unit_cost': item_cost,
                'total': item_qty * item_cost
            }
            st.session_state.po_items.append(po_item)
            st.rerun()
    
    # Display added items
    if st.session_state.po_items:
        st.markdown("#### 📋 PO Items")
        
        po_df = pd.DataFrame(st.session_state.po_items)
        po_df['total'] = po_df['total'].apply(lambda x: f"₹{x:,.2f}")
        po_df['unit_cost'] = po_df['unit_cost'].apply(lambda x: f"₹{x:,.2f}")
        
        st.dataframe(po_df[['item_name', 'ordered_qty', 'unit', 'unit_cost', 'total']], 
                    use_container_width=True, hide_index=True)
        
        # Total
        total_amount = sum(i['ordered_qty'] * i['unit_cost'] for i in st.session_state.po_items)
        st.metric("Total PO Amount", f"₹{total_amount:,.2f}")
        
        # Actions
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col2:
            if st.button("🗑️ Clear Items", use_container_width=True):
                st.session_state.po_items = []
                st.rerun()
        
        with col3:
            if st.button("✅ Create PO", type="primary", use_container_width=True):
                po_data = {
                    'po_number': po_number,
                    'supplier_id': supplier_options[supplier],
                    'po_date': po_date.isoformat(),
                    'expected_delivery_date': expected_delivery.isoformat(),
                    'status': 'draft',
                    'total_amount': total_amount,
                    'notes': notes
                }
                
                po_items_data = [
                    {
                        'item_id': i['item_id'],
                        'ordered_qty': i['ordered_qty'],
                        'unit_cost': i['unit_cost']
                    }
                    for i in st.session_state.po_items
                ]
                
                po_id = InventoryDB.create_po(po_data, po_items_data, st.session_state.user['id'])
                
                if po_id:
                    st.success(f"✅ Purchase Order {po_number} created!")
                    st.session_state.po_items = []
                    
                    ActivityLogger.log(
                        user_id=st.session_state.user['id'],
                        action_type='create_po',
                        module_key='inventory',
                        description=f"Created PO {po_number} for {supplier}",
                        metadata={'po_id': po_id, 'total': total_amount}
                    )
                    st.rerun()
    else:
        st.info("ℹ️ Add items to the purchase order above")


# =====================================================
# TAB 7: ALERTS
# =====================================================

def show_alerts():
    """Display low stock and expiry alerts"""
    
    st.markdown("### 🔔 Low Stock & Expiry Alerts")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📉 Low Stock Items")
        
        low_stock = InventoryDB.get_low_stock_items()
        
        if low_stock:
            st.warning(f"⚠️ {len(low_stock)} items need reordering")
            
            df = pd.DataFrame(low_stock)
            df['reorder_cost'] = (df['reorder_qty'] * df['unit_cost']).round(2)
            
            display_df = df[['item_name', 'current_qty', 'unit', 'reorder_threshold', 
                           'stock_level_pct', 'reorder_qty', 'supplier_name', 'reorder_cost']].copy()
            
            display_df['stock_level_pct'] = display_df['stock_level_pct'].apply(lambda x: f"{x}%")
            display_df['reorder_cost'] = display_df['reorder_cost'].apply(lambda x: f"₹{x:,.2f}")
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # Total reorder cost
            total_reorder = df['reorder_cost'].sum()
            st.metric("Total Reorder Cost", f"₹{total_reorder:,.2f}")
        else:
            st.success("✅ All items are adequately stocked!")
    
    with col2:
        st.markdown("#### ⏰ Expiring Items (30 Days)")
        
        expiring = InventoryDB.get_expiring_items(days_ahead=30)
        
        if expiring:
            st.warning(f"⚠️ {len(expiring)} items expiring soon")
            
            df = pd.DataFrame(expiring)
            
            display_df = df[['item_name', 'batch_number', 'remaining_qty', 'unit', 
                           'expiry_date', 'days_until_expiry', 'supplier_name']].copy()
            
            display_df['expiry_date'] = pd.to_datetime(display_df['expiry_date']).dt.strftime('%Y-%m-%d')
            
            # Color code by urgency
            def highlight_urgency(row):
                if row['days_until_expiry'] <= 7:
                    return ['background-color: #ffcccc'] * len(row)
                elif row['days_until_expiry'] <= 14:
                    return ['background-color: #fff4cc'] * len(row)
                else:
                    return [''] * len(row)
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            st.caption("🔴 Red: ≤7 days | 🟡 Yellow: ≤14 days")
        else:
            st.success("✅ No items expiring in the next 30 days!")


# =====================================================
# TAB 8: TRANSACTION HISTORY
# =====================================================

def show_transaction_history(is_admin: bool):
    """Display full transaction history with filters and delete option"""
    
    st.markdown("### 📜 Transaction History")
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        days = st.number_input("Days to show", min_value=7, max_value=365, value=30)
    
    with col2:
        tx_types = ["All", "add", "remove", "adjustment"]
        tx_type = st.selectbox("Type", tx_types)
    
    with col3:
        modules = ["All", "Biofloc", "RAS", "Microgreens", "Hydroponics", "Coco Coir", "Open Field", "General"]
        module = st.selectbox("Module", modules)
    
    with col4:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
    
    # Load transactions
    transactions = InventoryDB.get_transactions(
        days=days,
        transaction_type=None if tx_type == "All" else tx_type,
        module=None if module == "All" else module
    )
    
    if not transactions:
        st.info("No transactions found")
        return
    
    st.success(f"✅ Found {len(transactions)} transactions")
    
    # Display
    df = pd.DataFrame(transactions)
    
    # Flatten nested data
    df['item_name'] = df['inventory_items'].apply(lambda x: x['item_name'] if x else '')
    df['unit'] = df['inventory_items'].apply(lambda x: x['unit'] if x else '')
    
    display_df = df[['id', 'transaction_date', 'item_name', 'transaction_type', 
                     'quantity_change', 'unit', 'new_balance', 'unit_cost', 
                     'module_reference', 'notes']].copy()
    
    display_df['transaction_date'] = pd.to_datetime(display_df['transaction_date']).dt.strftime('%Y-%m-%d %H:%M')
    
    if 'unit_cost' in display_df.columns:
        display_df['unit_cost'] = display_df['unit_cost'].apply(
            lambda x: f"₹{x:,.2f}" if pd.notna(x) else ''
        )
    
    st.dataframe(display_df, use_container_width=True, hide_index=True, height=400)
    
    # Export and delete options
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col2:
        if st.button("📥 Export to CSV", use_container_width=True):
            csv = display_df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"inventory_transactions_{date.today()}.csv",
                mime="text/csv"
            )
    
    with col3:
        if is_admin:
            st.info("💡 Select transaction ID to delete (coming soon)")


# =====================================================
# TAB 9: SUPPLIERS
# =====================================================

def show_suppliers(username: str, is_admin: bool):
    """Manage suppliers"""
    
    st.markdown("### 👥 Supplier Management")
    
    if is_admin:
        tab1, tab2 = st.tabs(["📋 View Suppliers", "➕ Add Supplier"])
        
        with tab1:
            show_supplier_list()
        
        with tab2:
            show_add_supplier(username)
    else:
        show_supplier_list()


def show_supplier_list():
    """Display list of suppliers"""
    
    suppliers = InventoryDB.get_suppliers(active_only=False)
    
    if not suppliers:
        st.info("No suppliers found")
        return
    
    st.success(f"✅ {len(suppliers)} suppliers registered")
    
    df = pd.DataFrame(suppliers)
    
    display_cols = ['supplier_name', 'contact_person', 'phone', 'email', 
                   'payment_terms', 'is_active']
    
    df_display = df[[col for col in display_cols if col in df.columns]].copy()
    df_display['is_active'] = df_display['is_active'].map({True: '✅ Active', False: '❌ Inactive'})
    
    st.dataframe(df_display, use_container_width=True, hide_index=True)


def show_add_supplier(username: str):
    """Form to add new supplier"""
    
    st.markdown("#### ➕ Add New Supplier")
    
    with st.form("add_supplier_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            supplier_name = st.text_input("Supplier Name *")
            contact_person = st.text_input("Contact Person")
            phone = st.text_input("Phone *")
        
        with col2:
            email = st.text_input("Email")
            payment_terms = st.text_input("Payment Terms", placeholder="e.g., 30 days, Cash")
        
        address = st.text_area("Address")
        notes = st.text_area("Notes")
        
        submitted = st.form_submit_button("➕ Add Supplier", type="primary", use_container_width=True)
        
        if submitted:
            if not supplier_name or not phone:
                st.error("Supplier name and phone are required")
            else:
                supplier_data = {
                    'supplier_name': supplier_name,
                    'contact_person': contact_person,
                    'phone': phone,
                    'email': email,
                    'payment_terms': payment_terms,
                    'address': address,
                    'notes': notes,
                    'is_active': True
                }
                
                if InventoryDB.add_supplier(supplier_data):
                    st.success(f"✅ Added supplier: {supplier_name}")
                    
                    ActivityLogger.log(
                        user_id=st.session_state.user['id'],
                        action_type='add_supplier',
                        module_key='inventory',
                        description=f"Added supplier: {supplier_name}"
                    )
                    st.rerun()


# =====================================================
# TAB 10: ANALYTICS & REPORTS
# =====================================================

def show_analytics():
    """Analytics and reports"""
    
    st.markdown("### 📈 Analytics & Reports")
    
    # Inventory valuation
    st.markdown("#### 💰 Inventory Valuation by Category")
    
    valuation = InventoryDB.get_inventory_valuation()
    
    if valuation:
        df = pd.DataFrame(valuation)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.bar_chart(df.set_index('category')['total_value'])
        
        with col2:
            df['total_value'] = df['total_value'].apply(lambda x: f"₹{x:,.2f}")
            st.dataframe(df, use_container_width=True, hide_index=True)
        
        total_value = sum(v['total_value'] for v in valuation if isinstance(v['total_value'], (int, float)))
        st.metric("Total Inventory Value", f"₹{total_value:,.2f}")
    
    st.markdown("---")
    
    # Consumption by module
    st.markdown("#### 📊 Consumption by Module (Last 30 Days)")
    
    consumption = InventoryDB.get_consumption_by_module(days=30)
    
    if consumption:
        df = pd.DataFrame.from_dict(consumption, orient='index')
        df = df.reset_index()
        df.columns = ['Module', 'Quantity', 'Cost', 'Transactions']
        df['Cost'] = df['Cost'].apply(lambda x: f"₹{x:,.2f}")
        
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No consumption data available")
    
    st.markdown("---")
    
    # Export options
    st.markdown("#### 📥 Export Reports")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Complete Inventory", use_container_width=True):
            items = InventoryDB.get_all_items()
            export_inventory_excel(pd.DataFrame(items), "complete_inventory")
    
    with col2:
        if st.button("📉 Low Stock Report", use_container_width=True):
            low_stock = InventoryDB.get_low_stock_items()
            export_inventory_excel(pd.DataFrame(low_stock), "low_stock_report")
    
    with col3:
        if st.button("⏰ Expiry Report", use_container_width=True):
            expiring = InventoryDB.get_expiring_items(days_ahead=60)
            export_inventory_excel(pd.DataFrame(expiring), "expiry_report")


# =====================================================
# HELPER FUNCTIONS
# =====================================================

def export_inventory_excel(df: pd.DataFrame, filename: str):
    """Export dataframe to Excel"""
    
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Inventory', index=False)
        
        # Auto-adjust column widths
        worksheet = writer.sheets['Inventory']
        for i, col in enumerate(df.columns):
            max_len = max(df[col].astype(str).apply(len).max(), len(col)) + 2
            worksheet.set_column(i, i, max_len)
    
    output.seek(0)
    
    st.download_button(
        label="📥 Download Excel",
        data=output,
        file_name=f"{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
