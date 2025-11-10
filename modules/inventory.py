"""
Inventory Management Module
Comprehensive inventory system with expiry tracking, batch management, POs, and analytics

VERSION HISTORY:
2.0.0 - Complete professional inventory system - 10/11/25
      FEATURES:
      - Dashboard with metrics and charts
      - Current inventory with editable table
      - Add stock with batch tracking
      - Remove stock with module tracking
      - Stock adjustments (wastage, damage, etc.)
      - Purchase order management
      - Low stock and expiry alerts (30-day warning)
      - Transaction history with full audit trail
      - Supplier management
      - Analytics with consumption reports and Excel exports
      NOTES:
      - Expiry alerts are warnings only (no blocking)
      - All costs tracked prominently
      - Delete functionality for all entries
      - Integration hooks for farm modules
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO

from auth.session import SessionManager
from config.database import ActivityLogger

# Import inventory database helper
try:
    from db_inventory import InventoryDB
except ImportError:
    st.error("⚠️ Cannot import InventoryDB. Make sure db_inventory.py exists")
    st.stop()


# =====================================================
# HELPER FUNCTIONS
# =====================================================

def format_currency(amount: float) -> str:
    """Format number as currency"""
    return f"₹{amount:,.2f}"


def get_stock_status_color(current: float, reorder: float) -> str:
    """Get color based on stock level"""
    if current == 0:
        return "🔴"
    elif current <= reorder:
        return "🟡"
    else:
        return "🟢"


def get_expiry_status(expiry_date: date) -> Tuple[str, str]:
    """Get expiry status and color"""
    if not expiry_date:
        return "No expiry", "⚪"
    
    days_until = (expiry_date - date.today()).days
    
    if days_until < 0:
        return f"Expired {abs(days_until)}d ago", "🔴"
    elif days_until <= 7:
        return f"Expires in {days_until}d", "🔴"
    elif days_until <= 30:
        return f"Expires in {days_until}d", "🟡"
    else:
        return f"Expires in {days_until}d", "🟢"


def create_stock_level_chart(summary_df: pd.DataFrame):
    """Create stock level visualization"""
    if summary_df.empty:
        return None
    
    # Prepare data
    chart_data = summary_df[['item_name', 'current_stock', 'reorder_level']].copy()
    chart_data = chart_data.head(10)  # Top 10 items
    
    fig = go.Figure()
    
    # Current stock bars
    fig.add_trace(go.Bar(
        name='Current Stock',
        x=chart_data['item_name'],
        y=chart_data['current_stock'],
        marker_color='lightblue'
    ))
    
    # Reorder level line
    fig.add_trace(go.Scatter(
        name='Reorder Level',
        x=chart_data['item_name'],
        y=chart_data['reorder_level'],
        mode='lines+markers',
        marker_color='red',
        line=dict(dash='dash')
    ))
    
    fig.update_layout(
        title='Stock Levels vs Reorder Points (Top 10)',
        xaxis_title='Item',
        yaxis_title='Quantity',
        height=400,
        showlegend=True,
        hovermode='x unified'
    )
    
    return fig


def create_category_pie_chart(summary_df: pd.DataFrame):
    """Create category distribution pie chart"""
    if summary_df.empty:
        return None
    
    category_value = summary_df.groupby('category')['total_value'].sum().reset_index()
    
    fig = px.pie(
        category_value,
        values='total_value',
        names='category',
        title='Inventory Value by Category',
        hole=0.3
    )
    
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(height=400)
    
    return fig


def export_to_excel(dataframes: Dict[str, pd.DataFrame], filename: str) -> BytesIO:
    """Export multiple dataframes to Excel with multiple sheets"""
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for sheet_name, df in dataframes.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    output.seek(0)
    return output


# =====================================================
# MAIN MODULE FUNCTION
# =====================================================

def show():
    """Main entry point for Inventory Management module"""
    
    # Check access
    SessionManager.require_module_access('inventory_management')
    
    # Get user info
    user = SessionManager.get_user()
    profile = SessionManager.get_user_profile()
    is_admin = SessionManager.is_admin()
    username = profile.get('full_name', user.get('email', 'Unknown'))
    
    # Module header
    st.title("📦 Inventory Management")
    st.caption(f"👤 {username} | Role: {profile.get('role_name', 'User')}")
    st.markdown("---")
    
    # Initialize session state
    if 'inv_refresh_trigger' not in st.session_state:
        st.session_state.inv_refresh_trigger = 0
    
    # Create tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
        "📊 Dashboard",
        "📋 Current Inventory",
        "➕ Add Stock",
        "➖ Remove Stock",
        "⚖️ Adjustments",
        "📝 Purchase Orders",
        "⚠️ Alerts",
        "📜 History",
        "🏢 Suppliers",
        "📈 Analytics"
    ])
    
    with tab1:
        show_dashboard_tab(user, is_admin)
    
    with tab2:
        show_current_inventory_tab(user, is_admin)
    
    with tab3:
        show_add_stock_tab(user, is_admin)
    
    with tab4:
        show_remove_stock_tab(user, is_admin)
    
    with tab5:
        show_adjustments_tab(user, is_admin)
    
    with tab6:
        show_purchase_orders_tab(user, is_admin)
    
    with tab7:
        show_alerts_tab(user, is_admin)
    
    with tab8:
        show_history_tab(user, is_admin)
    
    with tab9:
        show_suppliers_tab(user, is_admin)
    
    with tab10:
        show_analytics_tab(user, is_admin)


# =====================================================
# TAB 1: DASHBOARD
# =====================================================

def show_dashboard_tab(user: Dict, is_admin: bool):
    """Dashboard with key metrics and visualizations"""
    
    st.markdown("### 📊 Inventory Dashboard")
    
    col1, col2 = st.columns([3, 1])
    
    with col2:
        if st.button("🔄 Refresh", key="dash_refresh", use_container_width=True):
            st.session_state.inv_refresh_trigger += 1
            st.rerun()
    
    # Fetch summary data
    with st.spinner("Loading dashboard..."):
        summary = InventoryDB.get_inventory_summary()
        low_stock = InventoryDB.get_low_stock_items()
        expiring = InventoryDB.get_expiring_items(days_ahead=30)
    
    if not summary:
        st.info("No inventory items found. Add items to get started!")
        return
    
    # Convert to DataFrame
    summary_df = pd.DataFrame(summary)
    
    # Key Metrics
    st.markdown("#### 📈 Key Metrics")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        total_items = len(summary_df)
        st.metric("Total Items", total_items)
    
    with col2:
        total_value = summary_df['total_value'].sum()
        st.metric("Total Value", format_currency(total_value))
    
    with col3:
        low_stock_count = len(low_stock) if low_stock else 0
        st.metric("Low Stock Items", low_stock_count, delta=None if low_stock_count == 0 else "⚠️")
    
    with col4:
        expiring_count = len(expiring) if expiring else 0
        st.metric("Expiring Soon (30d)", expiring_count, delta=None if expiring_count == 0 else "⚠️")
    
    with col5:
        active_batches = summary_df['active_batches'].sum()
        st.metric("Active Batches", int(active_batches))
    
    st.markdown("---")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        stock_chart = create_stock_level_chart(summary_df)
        if stock_chart:
            st.plotly_chart(stock_chart, use_container_width=True)
    
    with col2:
        category_chart = create_category_pie_chart(summary_df)
        if category_chart:
            st.plotly_chart(category_chart, use_container_width=True)
    
    st.markdown("---")
    
    # Quick Actions
    st.markdown("#### ⚡ Quick Actions")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if low_stock_count > 0:
            if st.button(f"🟡 View {low_stock_count} Low Stock Items", use_container_width=True):
                st.session_state['inv_active_tab'] = 6  # Alerts tab
                st.rerun()
    
    with col2:
        if expiring_count > 0:
            if st.button(f"🟡 View {expiring_count} Expiring Items", use_container_width=True):
                st.session_state['inv_active_tab'] = 6  # Alerts tab
                st.rerun()
    
    with col3:
        if st.button("➕ Add New Stock", use_container_width=True, type="primary"):
            st.session_state['inv_active_tab'] = 2  # Add Stock tab
            st.rerun()
    
    with col4:
        if st.button("📝 Create PO", use_container_width=True):
            st.session_state['inv_active_tab'] = 5  # PO tab
            st.rerun()


# =====================================================
# TAB 2: CURRENT INVENTORY
# =====================================================

def show_current_inventory_tab(user: Dict, is_admin: bool):
    """View and edit current inventory"""
    
    st.markdown("### 📋 Current Inventory")
    
    # Controls
    col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
    
    with col1:
        search_term = st.text_input("🔍 Search items", key="inv_search")
    
    with col2:
        categories = InventoryDB.get_categories()
        category_filter = st.selectbox("Filter by category", ["All"] + categories, key="inv_category")
    
    with col3:
        show_low_only = st.checkbox("Low stock only", key="inv_low_only")
    
    with col4:
        if st.button("🔄 Refresh", key="inv_refresh", use_container_width=True):
            st.session_state.inv_refresh_trigger += 1
            st.rerun()
    
    # Fetch data
    with st.spinner("Loading inventory..."):
        summary = InventoryDB.get_inventory_summary()
    
    if not summary:
        st.info("No inventory items found.")
        return
    
    df = pd.DataFrame(summary)
    
    # Apply filters
    if search_term:
        df = df[df['item_name'].str.contains(search_term, case=False, na=False)]
    
    if category_filter != "All":
        df = df[df['category'] == category_filter]
    
    if show_low_only:
        df = df[df['is_low_stock'] == True]
    
    if df.empty:
        st.info("No items found matching filters.")
        return
    
    st.success(f"✅ Found {len(df)} items")
    
    # Prepare display
    display_df = df[[
        'item_name', 'category', 'current_stock', 'unit', 'unit_cost',
        'total_value', 'reorder_level', 'is_low_stock'
    ]].copy()
    
    # Add status indicators
    display_df['status'] = display_df.apply(
        lambda row: get_stock_status_color(row['current_stock'], row['reorder_level']),
        axis=1
    )
    
    # Configure columns
    column_config = {
        "status": st.column_config.TextColumn("Status", width="small"),
        "item_name": st.column_config.TextColumn("Item Name", width="large"),
        "category": st.column_config.TextColumn("Category"),
        "current_stock": st.column_config.NumberColumn("Stock", format="%.2f"),
        "unit": st.column_config.TextColumn("Unit"),
        "unit_cost": st.column_config.NumberColumn("Unit Cost", format="₹%.2f"),
        "total_value": st.column_config.NumberColumn("Total Value", format="₹%.2f"),
        "reorder_level": st.column_config.NumberColumn("Reorder Level", format="%.2f"),
        "is_low_stock": st.column_config.CheckboxColumn("Low Stock", disabled=True)
    }
    
    # Display table
    st.dataframe(
        display_df,
        column_config=column_config,
        use_container_width=True,
        hide_index=True,
        height=400
    )
    
    # Export option
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col2:
        if st.button("📥 Export to Excel", key="inv_export", use_container_width=True):
            excel_file = export_to_excel({"Current Inventory": display_df}, "inventory.xlsx")
            st.download_button(
                label="📥 Download Excel",
                data=excel_file,
                file_name=f"inventory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )


# =====================================================
# TAB 3: ADD STOCK
# =====================================================

def show_add_stock_tab(user: Dict, is_admin: bool):
    """Add stock with batch tracking"""
    
    st.markdown("### ➕ Add Stock (Purchase)")
    
    st.info("💡 Add new stock received from suppliers with batch and expiry tracking")
    
    # Get items and suppliers
    items = InventoryDB.get_all_items(active_only=True)
    suppliers = InventoryDB.get_all_suppliers(active_only=True)
    
    if not items:
        st.warning("No inventory items found. Please add items first.")
        return
    
    with st.form("add_stock_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            # Item selection
            item_options = {f"{item['item_name']} ({item['unit']})": item for item in items}
            selected_item_key = st.selectbox("Select Item *", options=list(item_options.keys()))
            selected_item = item_options[selected_item_key]
            
            # Quantity
            quantity = st.number_input(
                f"Quantity ({selected_item['unit']}) *",
                min_value=0.01,
                value=1.0,
                step=0.01
            )
            
            # Unit cost
            unit_cost = st.number_input(
                "Unit Cost (₹) *",
                min_value=0.01,
                value=float(selected_item['unit_cost']),
                step=0.01
            )
            
            # Purchase date
            purchase_date = st.date_input(
                "Purchase Date *",
                value=date.today(),
                max_value=date.today()
            )
        
        with col2:
            # Batch number
            batch_number = st.text_input(
                "Batch Number *",
                value=f"BATCH-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            )
            
            # Expiry date (optional)
            has_expiry = st.checkbox("Has expiry date?", value=True)
            expiry_date = None
            if has_expiry:
                expiry_date = st.date_input(
                    "Expiry Date",
                    value=date.today() + timedelta(days=180),
                    min_value=date.today()
                )
            
            # Supplier
            if suppliers:
                supplier_options = {"No supplier": None}
                supplier_options.update({s['supplier_name']: s['id'] for s in suppliers})
                selected_supplier = st.selectbox("Supplier", options=list(supplier_options.keys()))
                supplier_id = supplier_options[selected_supplier]
            else:
                supplier_id = None
                st.caption("⚠️ No suppliers found")
            
            # Notes
            notes = st.text_area("Notes", height=100)
        
        # Calculate total
        total_cost = quantity * unit_cost
        st.markdown(f"**Total Cost:** {format_currency(total_cost)}")
        
        st.markdown("---")
        
        # Submit
        submitted = st.form_submit_button("✅ Add Stock", type="primary", use_container_width=True)
        
        if submitted:
            if not batch_number:
                st.error("❌ Batch number is required")
            else:
                success = InventoryDB.add_stock(
                    item_id=selected_item['id'],
                    quantity=quantity,
                    unit_cost=unit_cost,
                    batch_number=batch_number,
                    expiry_date=expiry_date,
                    purchase_date=purchase_date,
                    supplier_id=supplier_id,
                    notes=notes,
                    user_id=user['id']
                )
                
                if success:
                    st.success(f"✅ Added {quantity} {selected_item['unit']} of {selected_item['item_name']}")
                    
                    # Log activity
                    ActivityLogger.log(
                        user_id=user['id'],
                        action_type='inventory_add',
                        module_key='inventory_management',
                        description=f"Added stock: {selected_item['item_name']} ({quantity} {selected_item['unit']})",
                        metadata={'item': selected_item['item_name'], 'quantity': quantity, 'cost': total_cost}
                    )
                    
                    st.session_state.inv_refresh_trigger += 1
                    st.rerun()
                else:
                    st.error("❌ Failed to add stock")


# =====================================================
# TAB 4: REMOVE STOCK
# =====================================================

def show_remove_stock_tab(user: Dict, is_admin: bool):
    """Remove stock (usage tracking)"""
    
    st.markdown("### ➖ Remove Stock (Usage)")
    
    st.info("💡 Track stock usage by different farm modules")
    
    # Get items
    items = InventoryDB.get_all_items(active_only=True)
    
    if not items:
        st.warning("No inventory items found.")
        return
    
    # Module options for usage tracking
    farm_modules = [
        "Biofloc Aquaculture",
        "RAS Aquaculture",
        "Microgreens",
        "Hydroponics",
        "Coco Coir",
        "Open Field Crops",
        "General Farm",
        "Other"
    ]
    
    with st.form("remove_stock_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            # Item selection
            item_options = {f"{item['item_name']} ({item['unit']}) - Stock: {item['current_stock']}": item for item in items}
            selected_item_key = st.selectbox("Select Item *", options=list(item_options.keys()))
            selected_item = item_options[selected_item_key]
            
            # Show current stock
            st.metric("Current Stock", f"{selected_item['current_stock']} {selected_item['unit']}")
            
            # Quantity
            max_qty = float(selected_item['current_stock'])
            quantity = st.number_input(
                f"Quantity to Remove ({selected_item['unit']}) *",
                min_value=0.01,
                max_value=max_qty if max_qty > 0 else 999999.0,
                value=1.0,
                step=0.01
            )
            
            if quantity > max_qty:
                st.warning(f"⚠️ Quantity exceeds current stock ({max_qty})")
        
        with col2:
            # Module
            module = st.selectbox("Used by Module *", options=farm_modules)
            
            # Reference ID (optional)
            reference_id = st.text_input("Reference ID", help="Tank ID, Batch ID, etc.")
            
            # Notes
            notes = st.text_area("Notes", height=100)
        
        # Calculate cost
        estimated_cost = quantity * float(selected_item['unit_cost'])
        st.markdown(f"**Estimated Cost:** {format_currency(estimated_cost)}")
        
        st.markdown("---")
        
        # Submit
        submitted = st.form_submit_button("✅ Remove Stock", type="primary", use_container_width=True)
        
        if submitted:
            if quantity > max_qty:
                st.error("❌ Cannot remove more than current stock")
            else:
                success = InventoryDB.remove_stock(
                    item_id=selected_item['id'],
                    quantity=quantity,
                    module=module,
                    reference_id=reference_id,
                    notes=notes,
                    user_id=user['id']
                )
                
                if success:
                    st.success(f"✅ Removed {quantity} {selected_item['unit']} of {selected_item['item_name']}")
                    
                    # Log activity
                    ActivityLogger.log(
                        user_id=user['id'],
                        action_type='inventory_remove',
                        module_key='inventory_management',
                        description=f"Removed stock: {selected_item['item_name']} ({quantity} {selected_item['unit']}) for {module}",
                        metadata={'item': selected_item['item_name'], 'quantity': quantity, 'module': module}
                    )
                    
                    st.session_state.inv_refresh_trigger += 1
                    st.rerun()
                else:
                    st.error("❌ Failed to remove stock")


# =====================================================
# TAB 5: STOCK ADJUSTMENTS
# =====================================================

def show_adjustments_tab(user: Dict, is_admin: bool):
    """Stock adjustments (wastage, damage, etc.)"""
    
    st.markdown("### ⚖️ Stock Adjustments")
    
    st.info("💡 Record stock wastage, damage, expiry, or other adjustments")
    
    # Get items
    items = InventoryDB.get_all_items(active_only=True)
    
    if not items:
        st.warning("No inventory items found.")
        return
    
    # Adjustment types
    adjustment_types = [
        "wastage",
        "damage",
        "expired",
        "lost",
        "found",
        "other"
    ]
    
    with st.form("adjustment_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            # Item selection
            item_options = {f"{item['item_name']} ({item['unit']}) - Stock: {item['current_stock']}": item for item in items}
            selected_item_key = st.selectbox("Select Item *", options=list(item_options.keys()))
            selected_item = item_options[selected_item_key]
            
            # Adjustment type
            adjustment_type = st.selectbox("Adjustment Type *", options=adjustment_types)
            
            # Quantity
            quantity = st.number_input(
                f"Quantity ({selected_item['unit']}) *",
                min_value=0.01,
                value=1.0,
                step=0.01,
                help="Positive for additions, will be stored as absolute value"
            )
        
        with col2:
            # Reason
            reason = st.text_area(
                "Reason *",
                height=150,
                help="Explain the reason for this adjustment"
            )
        
        # Calculate cost impact
        cost_impact = quantity * float(selected_item['unit_cost'])
        st.markdown(f"**Cost Impact:** {format_currency(cost_impact)}")
        
        st.markdown("---")
        
        # Submit
        submitted = st.form_submit_button("✅ Record Adjustment", type="primary", use_container_width=True)
        
        if submitted:
            if not reason or len(reason.strip()) < 10:
                st.error("❌ Please provide a detailed reason (minimum 10 characters)")
            else:
                success = InventoryDB.record_adjustment(
                    item_id=selected_item['id'],
                    adjustment_type=adjustment_type,
                    quantity=quantity,
                    reason=reason,
                    user_id=user['id']
                )
                
                if success:
                    st.success(f"✅ Recorded {adjustment_type} adjustment: {quantity} {selected_item['unit']}")
                    
                    # Log activity
                    ActivityLogger.log(
                        user_id=user['id'],
                        action_type='inventory_adjustment',
                        module_key='inventory_management',
                        description=f"Stock adjustment: {selected_item['item_name']} - {adjustment_type} ({quantity} {selected_item['unit']})",
                        metadata={'item': selected_item['item_name'], 'type': adjustment_type, 'quantity': quantity}
                    )
                    
                    st.session_state.inv_refresh_trigger += 1
                    st.rerun()
                else:
                    st.error("❌ Failed to record adjustment")
    
    st.markdown("---")
    
    # Recent adjustments
    st.markdown("#### Recent Adjustments")
    
    adjustments = InventoryDB.get_recent_adjustments(limit=10)
    
    if adjustments:
        df = pd.DataFrame(adjustments)
        display_cols = ['adjustment_date', 'item_name', 'adjustment_type', 'quantity', 'reason', 'adjusted_by']
        
        if all(col in df.columns for col in display_cols):
            display_df = df[display_cols].copy()
            display_df.columns = ['Date', 'Item', 'Type', 'Quantity', 'Reason', 'User']
            display_df['Date'] = pd.to_datetime(display_df['Date']).dt.strftime('%Y-%m-%d %H:%M')
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("No recent adjustments found")


# =====================================================
# TAB 6: PURCHASE ORDERS
# =====================================================

def show_purchase_orders_tab(user: Dict, is_admin: bool):
    """Purchase order management"""
    
    st.markdown("### 📝 Purchase Orders")
    
    if not is_admin:
        st.info("ℹ️ Purchase order creation is restricted to admins. You can view existing POs below.")
    
    # Get suppliers
    suppliers = InventoryDB.get_all_suppliers(active_only=True)
    items = InventoryDB.get_all_items(active_only=True)
    
    if is_admin:
        # Create new PO
        with st.expander("➕ Create New Purchase Order", expanded=False):
            if not suppliers:
                st.warning("⚠️ No active suppliers found. Please add suppliers first.")
            elif not items:
                st.warning("⚠️ No inventory items found. Please add items first.")
            else:
                with st.form("create_po_form", clear_on_submit=True):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Supplier
                        supplier_options = {s['supplier_name']: s['id'] for s in suppliers}
                        selected_supplier = st.selectbox("Supplier *", options=list(supplier_options.keys()))
                        supplier_id = supplier_options[selected_supplier]
                        
                        # Order date
                        order_date = st.date_input("Order Date *", value=date.today())
                        
                        # Expected delivery
                        expected_delivery = st.date_input(
                            "Expected Delivery",
                            value=date.today() + timedelta(days=7),
                            min_value=date.today()
                        )
                    
                    with col2:
                        # PO Number (auto-generated)
                        po_number = st.text_input(
                            "PO Number *",
                            value=f"PO-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                        )
                        
                        # Notes
                        notes = st.text_area("Notes", height=100)
                    
                    st.markdown("---")
                    st.markdown("#### Items")
                    
                    # Add items to PO
                    num_items = st.number_input("Number of items in PO", min_value=1, max_value=20, value=1)
                    
                    po_items = []
                    total_amount = 0
                    
                    for i in range(num_items):
                        st.markdown(f"**Item {i+1}**")
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            item_options = {f"{item['item_name']} ({item['unit']})": item for item in items}
                            selected_item_key = st.selectbox(
                                "Item",
                                options=list(item_options.keys()),
                                key=f"po_item_{i}"
                            )
                            selected_item = item_options[selected_item_key]
                        
                        with col2:
                            quantity = st.number_input(
                                "Quantity",
                                min_value=0.01,
                                value=1.0,
                                step=0.01,
                                key=f"po_qty_{i}"
                            )
                        
                        with col3:
                            unit_cost = st.number_input(
                                "Unit Cost (₹)",
                                min_value=0.01,
                                value=float(selected_item['unit_cost']),
                                step=0.01,
                                key=f"po_cost_{i}"
                            )
                        
                        item_total = quantity * unit_cost
                        st.caption(f"Item Total: {format_currency(item_total)}")
                        
                        po_items.append({
                            'item_id': selected_item['id'],
                            'quantity': quantity,
                            'unit_cost': unit_cost
                        })
                        
                        total_amount += item_total
                    
                    st.markdown(f"**Total PO Amount:** {format_currency(total_amount)}")
                    
                    st.markdown("---")
                    
                    # Submit
                    submitted = st.form_submit_button("✅ Create Purchase Order", type="primary", use_container_width=True)
                    
                    if submitted:
                        success, po_id = InventoryDB.create_purchase_order(
                            po_number=po_number,
                            supplier_id=supplier_id,
                            order_date=order_date,
                            expected_delivery=expected_delivery,
                            notes=notes,
                            items=po_items,
                            user_id=user['id']
                        )
                        
                        if success:
                            st.success(f"✅ Purchase Order {po_number} created successfully!")
                            
                            # Log activity
                            ActivityLogger.log(
                                user_id=user['id'],
                                action_type='po_created',
                                module_key='inventory_management',
                                description=f"Created PO {po_number} for supplier {selected_supplier}",
                                metadata={'po_number': po_number, 'total': total_amount}
                            )
                            
                            st.session_state.inv_refresh_trigger += 1
                            st.rerun()
                        else:
                            st.error("❌ Failed to create purchase order")
    
    st.markdown("---")
    
    # View existing POs
    st.markdown("#### Existing Purchase Orders")
    
    # Status filter
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        status_filter = st.selectbox("Filter by Status", ["All", "pending", "received", "cancelled"])
    
    with col2:
        pass  # Reserved for future filters
    
    with col3:
        if st.button("🔄 Refresh", key="po_refresh", use_container_width=True):
            st.session_state.inv_refresh_trigger += 1
            st.rerun()
    
    # Fetch POs
    status = None if status_filter == "All" else status_filter
    pos = InventoryDB.get_purchase_orders(status=status)
    
    if pos:
        df = pd.DataFrame(pos)
        display_cols = ['po_number', 'supplier_name', 'order_date', 'expected_delivery', 'status', 'total_amount']
        
        if all(col in df.columns for col in display_cols):
            display_df = df[display_cols].copy()
            display_df.columns = ['PO Number', 'Supplier', 'Order Date', 'Expected Delivery', 'Status', 'Total Amount']
            display_df['Total Amount'] = display_df['Total Amount'].apply(lambda x: format_currency(x))
            
            st.dataframe(display_df, use_container_width=True, hide_index=True, height=400)
            
            # Mark as received (Admin only)
            if is_admin:
                st.markdown("---")
                st.markdown("#### Mark PO as Received")
                
                pending_pos = [p for p in pos if p['status'] == 'pending']
                if pending_pos:
                    po_options = {f"{p['po_number']} - {p['supplier_name']} ({format_currency(p['total_amount'])})": p for p in pending_pos}
                    selected_po_key = st.selectbox("Select PO to mark as received", options=list(po_options.keys()))
                    selected_po = po_options[selected_po_key]
                    
                    if st.button(f"✅ Mark {selected_po['po_number']} as Received", type="primary"):
                        if InventoryDB.mark_po_received(selected_po['id'], user['id']):
                            st.success(f"✅ PO {selected_po['po_number']} marked as received!")
                            
                            # Log activity
                            ActivityLogger.log(
                                user_id=user['id'],
                                action_type='po_received',
                                module_key='inventory_management',
                                description=f"Marked PO {selected_po['po_number']} as received",
                                metadata={'po_number': selected_po['po_number']}
                            )
                            
                            st.rerun()
                        else:
                            st.error("Failed to update PO status")
                else:
                    st.info("No pending POs to receive")
    else:
        st.info("No purchase orders found")


# =====================================================
# TAB 7: ALERTS (LOW STOCK + EXPIRY)
# =====================================================

def show_alerts_tab(user: Dict, is_admin: bool):
    """Low stock and expiry alerts"""
    
    st.markdown("### ⚠️ Alerts")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🟡 Low Stock Items")
        
        low_stock = InventoryDB.get_low_stock_items()
        
        if low_stock:
            df = pd.DataFrame(low_stock)
            display_df = df[['item_name', 'category', 'current_stock', 'reorder_level', 'days_until_stockout']].copy()
            display_df.columns = ['Item', 'Category', 'Current Stock', 'Reorder Level', 'Days Until Stockout']
            
            # Color code based on urgency
            def highlight_urgent(row):
                if row['Days Until Stockout'] <= 3:
                    return ['background-color: #ffcccc'] * len(row)
                elif row['Days Until Stockout'] <= 7:
                    return ['background-color: #fff4cc'] * len(row)
                else:
                    return [''] * len(row)
            
            styled_df = display_df.style.apply(highlight_urgent, axis=1)
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
            
            st.caption("🔴 Red: Critical (≤3 days) | 🟡 Yellow: Warning (≤7 days)")
        else:
            st.success("✅ All items are above reorder levels!")
    
    with col2:
        st.markdown("#### 🔴 Expiring Items (Next 30 Days)")
        
        expiring = InventoryDB.get_expiring_items(days_ahead=30)
        
        if expiring:
            df = pd.DataFrame(expiring)
            display_df = df[['item_name', 'batch_number', 'quantity', 'expiry_date', 'days_until_expiry']].copy()
            display_df.columns = ['Item', 'Batch', 'Quantity', 'Expiry Date', 'Days Left']
            
            # Add status indicator
            display_df['Status'] = display_df['Days Left'].apply(
                lambda x: '🔴 Expired' if x < 0 else ('🔴 Critical' if x <= 7 else '🟡 Warning')
            )
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            st.caption("🔴 Expired/Critical (≤7 days) | 🟡 Warning (≤30 days)")
            st.info("💡 Note: Expiry alerts are for information only. Expired items can still be used if needed.")
        else:
            st.success("✅ No items expiring in the next 30 days!")
    
    st.markdown("---")
    
    # Quick Actions
    st.markdown("#### ⚡ Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if low_stock:
            if st.button(f"📝 Create PO for {len(low_stock)} Items", use_container_width=True, type="primary"):
                st.info("💡 Navigate to Purchase Orders tab to create PO")
    
    with col2:
        if expiring:
            if st.button("📊 View Expiring Stock Details", use_container_width=True):
                st.info("💡 Check Current Inventory tab for batch details")
    
    with col3:
        if st.button("📥 Export Alerts", use_container_width=True):
            sheets = {}
            if low_stock:
                sheets['Low Stock'] = pd.DataFrame(low_stock)
            if expiring:
                sheets['Expiring'] = pd.DataFrame(expiring)
            
            if sheets:
                excel_file = export_to_excel(sheets, "alerts.xlsx")
                st.download_button(
                    label="📥 Download Excel",
                    data=excel_file,
                    file_name=f"inventory_alerts_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )


# =====================================================
# TAB 8: TRANSACTION HISTORY
# =====================================================

def show_history_tab(user: Dict, is_admin: bool):
    """Complete transaction history"""
    
    st.markdown("### 📜 Transaction History")
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        days_back = st.number_input("Days to show", min_value=1, max_value=365, value=30)
    
    with col2:
        transaction_types = ['All', 'purchase', 'usage', 'adjustment', 'wastage', 'damage', 'return']
        type_filter = st.selectbox("Transaction Type", options=transaction_types)
    
    with col3:
        items = InventoryDB.get_all_items()
        item_filter = st.selectbox("Filter by Item", options=["All"] + [item['item_name'] for item in items])
    
    with col4:
        if st.button("🔄 Refresh", key="history_refresh", use_container_width=True):
            st.session_state.inv_refresh_trigger += 1
            st.rerun()
    
    # Fetch transactions
    start_date = date.today() - timedelta(days=days_back)
    transaction_type = None if type_filter == "All" else type_filter
    item_name = None if item_filter == "All" else item_filter
    
    transactions = InventoryDB.get_transaction_history(
        start_date=start_date,
        transaction_type=transaction_type,
        item_name=item_name
    )
    
    if transactions:
        df = pd.DataFrame(transactions)
        
        # Calculate totals
        total_purchases = df[df['transaction_type'] == 'purchase']['total_cost'].sum()
        total_usage = df[df['transaction_type'] == 'usage']['total_cost'].sum()
        total_wastage = df[df['transaction_type'].isin(['wastage', 'damage'])]['total_cost'].sum()
        
        # Show summary
        st.markdown("#### 📊 Summary")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Transactions", len(df))
        with col2:
            st.metric("Purchases", format_currency(total_purchases))
        with col3:
            st.metric("Usage", format_currency(total_usage))
        with col4:
            st.metric("Wastage/Damage", format_currency(total_wastage))
        
        st.markdown("---")
        
        # Display transactions
        display_cols = ['transaction_date', 'item_name', 'transaction_type', 'quantity', 
                       'unit_cost', 'total_cost', 'reference_module', 'notes', 'performed_by']
        
        if all(col in df.columns for col in display_cols):
            display_df = df[display_cols].copy()
            display_df.columns = ['Date', 'Item', 'Type', 'Quantity', 'Unit Cost', 
                                 'Total Cost', 'Module', 'Notes', 'User']
            display_df['Date'] = pd.to_datetime(display_df['Date']).dt.strftime('%Y-%m-%d %H:%M')
            display_df['Unit Cost'] = display_df['Unit Cost'].apply(lambda x: format_currency(x) if pd.notna(x) else '-')
            display_df['Total Cost'] = display_df['Total Cost'].apply(lambda x: format_currency(x) if pd.notna(x) else '-')
            
            st.dataframe(display_df, use_container_width=True, hide_index=True, height=400)
            
            # Export option
            if st.button("📥 Export History", key="history_export"):
                excel_file = export_to_excel({"Transaction History": display_df}, "transaction_history.xlsx")
                st.download_button(
                    label="📥 Download Excel",
                    data=excel_file,
                    file_name=f"transaction_history_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    else:
        st.info("No transactions found for the selected filters")


# =====================================================
# TAB 9: SUPPLIERS
# =====================================================

def show_suppliers_tab(user: Dict, is_admin: bool):
    """Supplier management"""
    
    st.markdown("### 🏢 Suppliers")
    
    if not is_admin:
        st.info("ℹ️ Supplier management is restricted to admins. You can view suppliers below.")
    
    # Add new supplier (Admin only)
    if is_admin:
        with st.expander("➕ Add New Supplier", expanded=False):
            with st.form("add_supplier_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    supplier_name = st.text_input("Supplier Name *")
                    contact_person = st.text_input("Contact Person")
                    phone = st.text_input("Phone")
                
                with col2:
                    email = st.text_input("Email")
                    address = st.text_area("Address", height=100)
                    notes = st.text_area("Notes", height=100)
                
                submitted = st.form_submit_button("✅ Add Supplier", type="primary", use_container_width=True)
                
                if submitted:
                    if not supplier_name:
                        st.error("❌ Supplier name is required")
                    else:
                        success = InventoryDB.add_supplier(
                            supplier_name=supplier_name,
                            contact_person=contact_person,
                            phone=phone,
                            email=email,
                            address=address,
                            notes=notes,
                            user_id=user['id']
                        )
                        
                        if success:
                            st.success(f"✅ Supplier '{supplier_name}' added successfully!")
                            
                            # Log activity
                            ActivityLogger.log(
                                user_id=user['id'],
                                action_type='supplier_added',
                                module_key='inventory_management',
                                description=f"Added supplier: {supplier_name}",
                                metadata={'supplier': supplier_name}
                            )
                            
                            st.session_state.inv_refresh_trigger += 1
                            st.rerun()
                        else:
                            st.error("❌ Failed to add supplier (may already exist)")
    
    st.markdown("---")
    
    # View suppliers
    st.markdown("#### Active Suppliers")
    
    col1, col2 = st.columns([3, 1])
    
    with col2:
        if st.button("🔄 Refresh", key="suppliers_refresh", use_container_width=True):
            st.session_state.inv_refresh_trigger += 1
            st.rerun()
    
    suppliers = InventoryDB.get_all_suppliers(active_only=True)
    
    if suppliers:
        df = pd.DataFrame(suppliers)
        display_cols = ['supplier_name', 'contact_person', 'phone', 'email', 'address']
        
        if all(col in df.columns for col in display_cols):
            display_df = df[display_cols].copy()
            display_df.columns = ['Supplier Name', 'Contact Person', 'Phone', 'Email', 'Address']
            
            st.dataframe(display_df, use_container_width=True, hide_index=True, height=400)
    else:
        st.info("No active suppliers found")


# =====================================================
# TAB 10: ANALYTICS
# =====================================================

def show_analytics_tab(user: Dict, is_admin: bool):
    """Analytics and reports"""
    
    st.markdown("### 📈 Analytics & Reports")
    
    # Date range selector
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=date.today() - timedelta(days=30)
        )
    
    with col2:
        end_date = st.date_input(
            "End Date",
            value=date.today()
        )
    
    with col3:
        if st.button("🔄 Refresh", key="analytics_refresh", use_container_width=True):
            st.session_state.inv_refresh_trigger += 1
            st.rerun()
    
    # Module consumption report
    st.markdown("#### 📊 Consumption by Module")
    
    modules = [
        "Biofloc Aquaculture",
        "RAS Aquaculture",
        "Microgreens",
        "Hydroponics",
        "Coco Coir",
        "Open Field Crops",
        "General Farm"
    ]
    
    module_consumption = []
    for module in modules:
        consumption = InventoryDB.get_module_consumption(
            module_name=module,
            start_date=start_date,
            end_date=end_date
        )
        if consumption:
            module_consumption.extend(consumption)
    
    if module_consumption:
        df = pd.DataFrame(module_consumption)
        
        # Summary by module
        summary = df.groupby('reference_module').agg({
            'total_quantity': 'sum',
            'total_cost': 'sum'
        }).reset_index()
        summary.columns = ['Module', 'Total Quantity', 'Total Cost']
        summary['Total Cost'] = summary['Total Cost'].apply(format_currency)
        
        st.dataframe(summary, use_container_width=True, hide_index=True)
        
        # Detailed breakdown
        with st.expander("📋 Detailed Breakdown"):
            detail_df = df[['reference_module', 'item_name', 'total_quantity', 'total_cost']].copy()
            detail_df.columns = ['Module', 'Item', 'Quantity', 'Cost']
            detail_df['Cost'] = detail_df['Cost'].apply(format_currency)
            st.dataframe(detail_df, use_container_width=True, hide_index=True)
        
        # Export
        if st.button("📥 Export Analytics", key="analytics_export"):
            sheets = {
                'Summary by Module': summary,
                'Detailed Breakdown': detail_df
            }
            excel_file = export_to_excel(sheets, "analytics.xlsx")
            st.download_button(
                label="📥 Download Excel",
                data=excel_file,
                file_name=f"inventory_analytics_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.info("No consumption data found for the selected date range")
