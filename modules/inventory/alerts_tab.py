"""
Alerts Tab
Display low stock and expiry alerts for inventory monitoring
"""

import streamlit as st
import pandas as pd

from db.db_inventory import InventoryDB


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

            st.dataframe(display_df, width='stretch', hide_index=True)
    else:
        st.success("✅ All items above reorder level")

    st.markdown("---")

    # Expiry Alerts
    st.markdown("#### ⚠️ Expiring Items")

    col1, col2 = st.columns(2)

    with col1:
        days_ahead = st.number_input("Days Ahead", min_value=7, max_value=365, value=30)

    with col2:
        if st.button("🔄 Refresh Alerts", width='stretch', key="refresh_alerts"):
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

    st.dataframe(display_df, width='stretch', hide_index=True)


def display_expiring(df: pd.DataFrame):
    """Display expiring items"""
    display_cols = ['item_name', 'batch_number', 'quantity', 'expiry_date', 'days_until_expiry']
    display_cols = [col for col in display_cols if col in df.columns]
    display_df = df[display_cols].copy()

    display_df['expiry_date'] = pd.to_datetime(display_df['expiry_date']).dt.strftime('%Y-%m-%d')
    display_df.columns = ['Item', 'Batch', 'Quantity', 'Expiry Date', 'Days Left']

    st.dataframe(display_df, width='stretch', hide_index=True)
