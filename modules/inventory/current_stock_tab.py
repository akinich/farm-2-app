"""
Current Stock Tab
View current stock inventory with batch details and filtering
"""

import streamlit as st
import pandas as pd

from db.db_inventory import InventoryDB
from .utils import export_to_excel


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
        if st.button("🔄 Refresh", width='stretch', key="refresh_current_stock"):
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
        width='stretch',
        hide_index=True,
        height=500
    )

    # Export option
    col1, col2, col3 = st.columns([2, 1, 1])

    with col2:
        if st.button("📥 Export to Excel", width='stretch', key="export_current_stock"):
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
