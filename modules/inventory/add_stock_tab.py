"""
Add Stock Tab
Add new stock entries with batch tracking and FIFO support
"""

VERSION HISTORY:
1.0.0 - 2025-01-12 - Initial modular version extracted from inventory.py
      - Batch tracking with FIFO support
      - Supplier management
      - Expiry date tracking
      - Form validation and activity logging

import streamlit as st
from datetime import date, timedelta
import time

from config.database import ActivityLogger
from db.db_inventory import InventoryDB
from .utils import get_master_items_cached, get_suppliers_cached


def show_add_stock_tab(username: str):
    """Add new stock entry with batch tracking"""

    st.markdown("### ➕ Add New Stock")

    # Get master items for dropdown (cached)
    master_items = get_master_items_cached(active_only=True)
    for item in master_items:
        if 'reorder_level' not in item and 'reorder_threshold' in item:
            item['reorder_level'] = item['reorder_threshold']
        if 'default_supplier_id' not in item and 'supplier_id' in item:
            item['default_supplier_id'] = item['supplier_id']

    if not master_items:
        st.warning("⚠️ No active items in master list. Ask admin to add items first.")
        return

    st.info("📝 Add stock received from suppliers. Each entry creates a new batch for FIFO tracking.")

    # Item selection OUTSIDE form so it can update dynamically
    item_options = {
        f"{item['item_name']} ({item.get('category', 'N/A')}) - Current: {item.get('current_qty', 0)} {item.get('unit', '')}": item
        for item in master_items
    }

    selected_item_key = st.selectbox(
        "Select Item *",
        options=list(item_options.keys()),
        help="Search and select item from master list",
        key="add_stock_item_select_main"
    )
    selected_item = item_options[selected_item_key]

    # Show item details (updates when item changes)
    with st.expander("ℹ️ Item Details", expanded=True):
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.markdown(f"**Category:** {selected_item.get('category', 'N/A')}")
            st.markdown(f"**SKU:** {selected_item.get('sku', 'N/A')}")
        with col_b:
            st.markdown(f"**Brand:** {selected_item.get('brand', 'N/A')}")
            st.markdown(f"**Unit:** {selected_item.get('unit', 'N/A')}")
        with col_c:
            st.markdown(f"**Current Stock:** {selected_item.get('current_qty', 0)} {selected_item.get('unit', '')}")
            st.markdown(f"**Reorder Level:** {selected_item.get('reorder_level', 0)}")

    # Get suppliers for dropdown (cached)
    suppliers = get_suppliers_cached(active_only=True)
    supplier_list = ["Select Supplier"] + [s['supplier_name'] for s in suppliers]

    # Find default supplier name for the selected item
    default_supplier_name = "Select Supplier"
    if selected_item.get('default_supplier_id'):
        for supplier in suppliers:
            if supplier['id'] == selected_item['default_supplier_id']:
                default_supplier_name = supplier['supplier_name']
                break

    # Find index for the default supplier in the list
    default_index = 0
    if default_supplier_name in supplier_list:
        default_index = supplier_list.index(default_supplier_name)

    with st.form("add_stock_form", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            # Batch details
            batch_number = st.text_input(
                "Batch Number *",
                placeholder="e.g., BATCH-2024-001",
                help="Unique identifier for this batch"
            )

            # Get unit for display
            unit = selected_item.get('unit', 'units')

            quantity = st.number_input(
                f"Quantity ({unit}) *",
                min_value=0.01,
                value=1.0,
                step=1.0,
                format="%.2f",
                help=f"Amount received in {unit}"
            )

            unit_cost = st.number_input(
                f"Unit Cost (₹ per {unit}) *",
                min_value=0.01,
                value=1.0,
                step=1.0,
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

            supplier_name = st.selectbox(
                "Supplier",
                options=supplier_list,
                index=default_index,
                help="Select supplier (auto-filled from item's default supplier)",
                key=f"add_stock_supplier_{selected_item['id']}"
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
            submitted = st.form_submit_button("✅ Add Stock", type="primary", width='stretch')

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
                    st.success(f"✅ Successfully added {quantity} {unit} of {selected_item['item_name']}")

                    # Log activity
                    ActivityLogger.log(
                        user_id=st.session_state.user['id'],
                        action_type='add_stock',
                        module_key='inventory',
                        description=f"Added stock: {selected_item['item_name']} (Batch: {batch_number})",
                        metadata={
                            'item': selected_item['item_name'],
                            'batch': batch_number,
                            'quantity': quantity
                        }
                    )

                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("❌ Failed to add stock. Check if batch number already exists.")
