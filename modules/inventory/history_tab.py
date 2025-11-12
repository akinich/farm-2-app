"""
History Tab
View and filter transaction history for all inventory operations


VERSION HISTORY:
1.0.0 - 2025-01-12 - Initial modular version extracted from inventory.py
      - Transaction filtering (type, item, date)
      - Role-based column display
      - Excel export capability
"""
import streamlit as st
import pandas as pd

from db.db_inventory import InventoryDB
from .utils import export_to_excel


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
        if st.button("🔄 Refresh", width='stretch', key="refresh_history"):
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

    st.dataframe(display_df, width='stretch', hide_index=True, height=500)

    # Export
    if st.button("📥 Export to Excel", width='stretch', key="export_history"):
        export_to_excel(display_df, "transaction_history")
