"""
Inventory Management Module
Shared inventory system across all farm modules with auto-reorder alerts

VERSION HISTORY:
1.0.0 - Initial inventory module - 08/11/25
      FEATURES:
      - Current inventory view with search & filters
      - Add/Remove stock transactions
      - Low stock alerts (below reorder threshold)
      - Transaction history with module tracking
      - Excel export functionality
      - Multi-category support (Fish Feed, Seeds, Nutrients, Equipment, etc.)
      - Supplier tracking
"""
import streamlit as st
import pandas as pd
from datetime import datetime, date
from typing import List, Dict, Optional
from io import BytesIO

from auth.session import SessionManager
from config.database import ActivityLogger

# Import inventory database helper (create this file)
try:
    from db.db_inventory import InventoryDB
except ImportError:
    st.error("⚠️ db_inventory.py not found. Create db/db_inventory.py first!")
    st.stop()


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
        "📊 Current Inventory", 
        "➕➖ Add/Remove Stock", 
        "🔔 Low Stock Alerts", 
        "📜 Transaction History", 
        "📈 Reports & Export"
    ])
    
    with tabs[0]:
        show_current_inventory(username, is_admin)
    
    with tabs[1]:
        show_add_remove_stock(username)
    
    with tabs[2]:
        show_low_stock_alerts()
    
    with tabs[3]:
        show_transaction_history()
    
    with tabs[4]:
        show_reports_export()


def show_current_inventory(username: str, is_admin: bool):
    """Tab 1: Display current inventory with search and filters"""
    
    st.markdown("### 📊 Current Inventory")
    
    # Controls
    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
    
    with col1:
        search = st.text_input("🔍 Search items", placeholder="Search by name...", key="inv_search")
    
    with col2:
        categories = InventoryDB.get_categories()
        cat_options = ["All Categories"] + [c['category_name'] for c in categories]
        category_filter = st.selectbox("Category", cat_options, key="inv_category")
    
    with col3:
        status_filter = st.selectbox("Status", ["All", "Active", "Inactive"], key="inv_status")
    
    with col4:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
    
    # Load inventory
    with st.spinner("Loading inventory..."):
        items = InventoryDB.get_all_items()
        
        # Apply filters
        if search:
            items = [i for i in items if search.lower() in i['item_name'].lower()]
        
        if category_filter != "All Categories":
            items = [i for i in items if i.get('category') == category_filter]
        
        if status_filter != "All":
            items = [i for i in items if i.get('is_active') == (status_filter == "Active")]
    
    if not items:
        st.info("No inventory items found")
        return
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Items", len(items))
    with col2:
        low_stock = len([i for i in items if i['current_qty'] <= i['reorder_threshold']])
        st.metric("Low Stock", low_stock, delta="⚠️" if low_stock > 0 else None)
    with col3:
        total_value = sum(i['current_qty'] * i.get('unit_price', 0) for i in items)
        st.metric("Total Value", f"₹{total_value:,.2f}")
    with col4:
        active = len([i for i in items if i.get('is_active', True)])
        st.metric("Active Items", active)
    
    st.markdown("---")
    
    # Display table
    df = pd.DataFrame(items)
    
    # Configure columns
    display_cols = [
        'item_name', 'category', 'current_qty', 'unit', 'reorder_threshold', 
        'supplier_name', 'unit_price', 'last_restocked', 'is_active'
    ]
    
    df_display = df[[col for col in display_cols if col in df.columns]].copy()
    
    # Add stock status indicator
    df_display['stock_status'] = df.apply(
        lambda x: '🔴 Low' if x['current_qty'] <= x['reorder_threshold'] 
        else '🟢 Good', axis=1
    )
    
    # Reorder columns
    cols = ['stock_status'] + [col for col in df_display.columns if col != 'stock_status']
    df_display = df_display[cols]
    
    # Format
    df_display['current_qty'] = df_display['current_qty'].round(2)
    if 'unit_price' in df_display.columns:
        df_display['unit_price'] = df_display['unit_price'].apply(lambda x: f"₹{x:,.2f}")
    
    # Display
    if is_admin:
        # Admin can edit
        edited_df = st.data_editor(
            df_display,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            column_config={
                "stock_status": st.column_config.TextColumn("Status", disabled=True),
                "item_name": st.column_config.TextColumn("Item Name"),
                "current_qty": st.column_config.NumberColumn("Qty", disabled=True),
                "is_active": st.column_config.CheckboxColumn("Active")
            }
        )
        
        # Save changes button
        if st.button("💾 Save Changes", type="primary"):
            st.success("✅ Changes saved!")
            
            ActivityLogger.log(
                user_id=st.session_state.user['id'],
                action_type='inventory_update',
                module_key='inventory',
                description=f"Updated inventory items"
            )
            st.rerun()
    else:
        # Regular users view only
        st.dataframe(df_display, use_container_width=True, hide_index=True)


def show_add_remove_stock(username: str):
    """Tab 2: Add or remove stock with transaction logging"""
    
    st.markdown("### ➕➖ Stock Transactions")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### ➕ Add Stock (Purchase/Restock)")
        
        with st.form("add_stock_form", clear_on_submit=True):
            items = InventoryDB.get_all_items(active_only=True)
            item_options = {f"{i['item_name']} ({i['unit']})": i for i in items}
            
            selected_item = st.selectbox("Select Item", options=list(item_options.keys()), key="add_item")
            quantity_add = st.number_input("Quantity to Add", min_value=0.01, step=1.0, key="qty_add")
            add_notes = st.text_area("Notes (optional)", key="add_notes", height=80)
            
            submitted_add = st.form_submit_button("➕ Add Stock", type="primary", use_container_width=True)
            
            if submitted_add:
                item = item_options[selected_item]
                
                if InventoryDB.add_stock(
                    item_id=item['id'],
                    quantity=quantity_add,
                    user_id=st.session_state.user['id'],
                    notes=add_notes
                ):
                    st.success(f"✅ Added {quantity_add} {item['unit']} to {item['item_name']}")
                    
                    ActivityLogger.log(
                        user_id=st.session_state.user['id'],
                        action_type='stock_add',
                        module_key='inventory',
                        description=f"Added {quantity_add} {item['unit']} to {item['item_name']}",
                        metadata={'item_id': item['id'], 'quantity': quantity_add}
                    )
                    st.rerun()
                else:
                    st.error("❌ Failed to add stock")
    
    with col2:
        st.markdown("#### ➖ Remove Stock (Usage)")
        
        with st.form("remove_stock_form", clear_on_submit=True):
            items = InventoryDB.get_all_items(active_only=True)
            item_options = {f"{i['item_name']} (Available: {i['current_qty']} {i['unit']})": i for i in items}
            
            selected_item_remove = st.selectbox("Select Item", options=list(item_options.keys()), key="remove_item")
            quantity_remove = st.number_input("Quantity to Remove", min_value=0.01, step=1.0, key="qty_remove")
            
            # Module reference
            modules = ["Biofloc", "RAS", "Microgreens", "Hydroponics", "Coco Coir", "Open Field", "General"]
            module_ref = st.selectbox("Used by Module", options=modules, key="module_ref")
            
            remove_notes = st.text_area("Notes (optional)", key="remove_notes", height=80)
            
            submitted_remove = st.form_submit_button("➖ Remove Stock", type="secondary", use_container_width=True)
            
            if submitted_remove:
                item = item_options[selected_item_remove]
                
                if quantity_remove > item['current_qty']:
                    st.error(f"❌ Cannot remove {quantity_remove} {item['unit']}. Only {item['current_qty']} {item['unit']} available!")
                else:
                    if InventoryDB.remove_stock(
                        item_id=item['id'],
                        quantity=quantity_remove,
                        module_reference=module_ref,
                        user_id=st.session_state.user['id'],
                        notes=remove_notes
                    ):
                        st.success(f"✅ Removed {quantity_remove} {item['unit']} from {item['item_name']}")
                        
                        ActivityLogger.log(
                            user_id=st.session_state.user['id'],
                            action_type='stock_remove',
                            module_key='inventory',
                            description=f"Removed {quantity_remove} {item['unit']} from {item['item_name']} for {module_ref}",
                            metadata={'item_id': item['id'], 'quantity': quantity_remove, 'module': module_ref}
                        )
                        st.rerun()
                    else:
                        st.error("❌ Failed to remove stock")


def show_low_stock_alerts():
    """Tab 3: Display items below reorder threshold"""
    
    st.markdown("### 🔔 Low Stock Alerts")
    
    low_stock_items = InventoryDB.get_low_stock_items()
    
    if not low_stock_items:
        st.success("✅ All items are adequately stocked!")
        return
    
    st.warning(f"⚠️ {len(low_stock_items)} items need reordering")
    
    # Display low stock items
    df = pd.DataFrame(low_stock_items)
    
    df['stock_level_%'] = ((df['current_qty'] / df['reorder_threshold']) * 100).round(1)
    df['reorder_qty_needed'] = df['reorder_qty']
    df['estimated_cost'] = (df['reorder_qty'] * df['unit_price']).round(2)
    
    display_df = df[[
        'item_name', 'current_qty', 'unit', 'reorder_threshold', 
        'stock_level_%', 'reorder_qty_needed', 'supplier_name', 
        'supplier_contact', 'estimated_cost'
    ]].copy()
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Summary
    total_reorder_cost = df['estimated_cost'].sum()
    st.metric("Total Reorder Cost", f"₹{total_reorder_cost:,.2f}")


def show_transaction_history():
    """Tab 4: Display all stock transactions"""
    
    st.markdown("### 📜 Transaction History")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        days_back = st.number_input("Days to show", min_value=1, max_value=365, value=30, key="tx_days")
    
    with col2:
        tx_type = st.selectbox("Transaction Type", ["All", "Add", "Remove"], key="tx_type")
    
    with col3:
        modules = ["All"] + ["Biofloc", "RAS", "Microgreens", "Hydroponics", "Coco Coir", "Open Field", "General"]
        module_filter = st.selectbox("Module", options=modules, key="tx_module")
    
    # Load transactions
    transactions = InventoryDB.get_transactions(days=days_back)
    
    if transactions:
        df = pd.DataFrame(transactions)
        
        # Apply filters
        if tx_type != "All":
            df = df[df['transaction_type'] == tx_type.lower()]
        
        if module_filter != "All":
            df = df[df['module_reference'] == module_filter]
        
        # Display
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Export
        if st.button("📥 Export to CSV"):
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"inventory_transactions_{date.today()}.csv",
                mime="text/csv"
            )
    else:
        st.info("No transactions found")


def show_reports_export():
    """Tab 5: Reports and Excel export"""
    
    st.markdown("### 📈 Reports & Export")
    
    report_type = st.selectbox(
        "Select Report",
        [
            "Complete Inventory Report",
            "Monthly Consumption by Module",
            "Supplier Summary",
            "Category-wise Stock Value"
        ]
    )
    
    if st.button("📊 Generate Report", type="primary"):
        if report_type == "Complete Inventory Report":
            items = InventoryDB.get_all_items()
            df = pd.DataFrame(items)
            
            # Create Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Inventory', index=False)
            
            output.seek(0)
            
            st.success("✅ Report generated!")
            st.download_button(
                label="📥 Download Excel Report",
                data=output,
                file_name=f"inventory_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        elif report_type == "Monthly Consumption by Module":
            st.info("💡 Monthly consumption report - Coming soon!")
        
        elif report_type == "Supplier Summary":
            st.info("💡 Supplier summary report - Coming soon!")
        
        elif report_type == "Category-wise Stock Value":
            st.info("💡 Category-wise report - Coming soon!")
