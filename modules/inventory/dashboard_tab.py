"""
Dashboard Tab
KPIs, alerts, and quick stats for inventory overview

VERSION HISTORY:
1.0.0 - 2025-01-12 - Initial modular version extracted from inventory.py
      - KPI metrics display
      - Quick alerts (low stock and expiry)
      - Recent activity feed
"""

import streamlit as st
import pandas as pd

from db.db_inventory import InventoryDB


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

            st.dataframe(display_df, width='stretch', hide_index=True, height=300)
    else:
        st.info("No recent transactions")
