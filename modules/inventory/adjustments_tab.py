"""
Adjustments Tab
Record stock adjustments for damage, wastage, corrections, etc.

VERSION HISTORY:
1.0.0 - 2025-01-12 - Initial modular version extracted from inventory.py
      - Stock adjustments (damage, wastage, corrections)
      - Reason tracking
      - Recent adjustments history
      - Activity logging
"""

import streamlit as st
import pandas as pd
from datetime import date
import time

from config.database import ActivityLogger
from db.db_inventory import InventoryDB


def show_adjustments_tab(username: str):
    """Record stock adjustments (damage, corrections, etc.)"""

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
            submitted = st.form_submit_button("✅ Record Adjustment", type="primary", width='stretch')

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
                        module_key='inventory',
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

            st.dataframe(display_df, width='stretch', hide_index=True, height=400)
    else:
        st.info("No adjustments recorded yet")
