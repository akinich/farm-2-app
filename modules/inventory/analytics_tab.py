"""
Analytics Tab (Admin Only)
Analytics and reports for inventory management

VERSION HISTORY:
1.0.0 - 2025-01-12 - Initial modular version extracted from inventory.py
      - Inventory value analytics with batch breakdown
      - Module-wise consumption tracking
      - Cost analysis with period filtering
      - Trends analytics (placeholder for future)
      - Excel export capabilities
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta

from db.db_inventory import InventoryDB
from .utils import export_to_excel


def show_analytics_tab(username: str):
    """Analytics and reports (Admin only)"""

    st.markdown("### 📈 Analytics & Reports")

    subtabs = st.tabs(["💰 Inventory Value", "📊 Consumption", "📈 Cost Analysis", "📉 Trends"])

    with subtabs[0]:
        show_inventory_value_analytics()

    with subtabs[1]:
        show_consumption_analytics()

    with subtabs[2]:
        show_cost_analysis()

    with subtabs[3]:
        show_trends_analytics()


def show_inventory_value_analytics():
    """Show total inventory value and statistics"""

    st.markdown("#### 💰 Inventory Valuation")

    with st.spinner("Calculating inventory value..."):
        # Get all stock batches with costs (only active batches with remaining qty)
        batches = InventoryDB.get_all_batches(active_only=True)

        if not batches:
            st.info("No stock data available")
            return

        df = pd.DataFrame(batches)

        # batch_value is already calculated in get_all_batches() using remaining_qty
        # If not present, calculate it
        if 'batch_value' not in df.columns:
            df['batch_value'] = df['remaining_qty'] * df['unit_cost']

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            total_value = df['batch_value'].sum()
            st.metric(
                label="💵 Total Inventory Value",
                value=f"₹{total_value:,.2f}",
                help="Total value of all stock on hand"
            )

        with col2:
            avg_value = df['batch_value'].mean()
            st.metric(
                label="📊 Avg Batch Value",
                value=f"₹{avg_value:,.2f}",
                help="Average value per batch"
            )

        with col3:
            total_items = df['item_name'].nunique()
            st.metric(
                label="📦 Unique Items",
                value=total_items,
                help="Number of different items in stock"
            )

        with col4:
            total_batches = len(df)
            st.metric(
                label="🏷️ Total Batches",
                value=total_batches,
                help="Number of stock batches"
            )

        st.markdown("---")

        # Value breakdown by item
        st.markdown("##### 💰 Value by Item")

        # Use remaining_qty for current stock value
        qty_col = 'remaining_qty' if 'remaining_qty' in df.columns else 'quantity'
        item_values = df.groupby('item_name').agg({
            'batch_value': 'sum',
            qty_col: 'sum',
            'unit_cost': 'mean'
        }).reset_index()

        # Rename the quantity column
        item_values.columns = ['item_name', 'batch_value', 'quantity', 'unit_cost']

        item_values = item_values.sort_values('batch_value', ascending=False)
        item_values['batch_value'] = item_values['batch_value'].apply(lambda x: f"₹{x:,.2f}")
        item_values['unit_cost'] = item_values['unit_cost'].apply(lambda x: f"₹{x:,.2f}")
        item_values['quantity'] = item_values['quantity'].apply(lambda x: f"{x:,.2f}")

        item_values.columns = ['Item Name', 'Total Value', 'Total Quantity', 'Avg Unit Cost']

        st.dataframe(item_values, width='stretch', hide_index=True, height=400)

        # Export option
        st.markdown("---")
        col1, col2, col3 = st.columns([2, 1, 1])
        with col2:
            if st.button("📥 Export to Excel", width='stretch', key="export_inventory_value"):
                from io import BytesIO

                # Create Excel file
                output = BytesIO()

                # Convert formatted strings back to numbers for Excel
                df_export = df.copy()
                df_export = df_export[['item_name', 'batch_number', 'quantity', 'unit_cost', 'batch_value', 'purchase_date']]
                df_export.columns = ['Item Name', 'Batch Number', 'Quantity', 'Unit Cost', 'Total Value', 'Purchase Date']

                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_export.to_excel(writer, sheet_name='Inventory Value', index=False)
                    item_values_export = df.groupby('item_name').agg({
                        'batch_value': 'sum',
                        'quantity': 'sum',
                        'unit_cost': 'mean'
                    }).reset_index()
                    item_values_export.columns = ['Item Name', 'Total Value', 'Total Quantity', 'Avg Unit Cost']
                    item_values_export.to_excel(writer, sheet_name='Value Summary', index=False)

                output.seek(0)

                st.download_button(
                    label="📥 Download Excel",
                    data=output,
                    file_name=f"inventory_value_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    width='stretch',
                    key="download_inventory_value_excel"
                )


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

        st.dataframe(module_summary, width='stretch', hide_index=True)

        st.markdown("---")

        # Detailed view
        st.markdown("##### Detailed Consumption")

        display_cols = ['module_name', 'item_name', 'total_quantity', 'unit', 'total_cost']
        display_cols = [col for col in display_cols if col in df.columns]
        display_df = df[display_cols].copy()

        display_df['total_cost'] = display_df['total_cost'].apply(lambda x: f"₹{x:,.2f}" if pd.notna(x) else 'N/A')
        display_df.columns = ['Module', 'Item', 'Quantity', 'Unit', 'Total Cost']

        st.dataframe(display_df, width='stretch', hide_index=True)

        # Export
        if st.button("📥 Export Report", width='stretch', key="export_consumption"):
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

            st.dataframe(item_costs, width='stretch', hide_index=True)
    else:
        st.info("No cost data available for selected period")


def show_trends_analytics():
    """Show inventory trends"""

    st.markdown("#### 📉 Inventory Trends")

    st.info("📊 Trend analysis coming soon - will show stock level changes over time")
