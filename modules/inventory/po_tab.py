"""
Purchase Orders Tab
Manage purchase orders with multi-item support, status tracking, and FIFO optimization

VERSION HISTORY:
1.0.0 - 2025-01-12 - Initial modular version extracted from inventory.py
      - Multi-item PO support (invoice-style)
      - PO status management
      - N+1 query optimization with caching
      - Delete PO functionality
      - Single-sheet Excel export
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Dict
import time

from auth.session import SessionManager
from config.database import ActivityLogger
from db.db_inventory import InventoryDB

from .utils import (
    get_master_items_cached,
    get_suppliers_cached,
    get_purchase_orders_cached,
    get_po_details_cached,
    generate_pos_excel,
    generate_po_detail_excel,
    get_status_badge,
    init_po_session_state,
    clear_po_cart,
    refresh_data_cache
)
from .constants import PO_PAGE_SIZE


def show_purchase_orders_tab(username: str, is_admin: bool):
    """Manage purchase orders"""

    st.markdown("### 🛒 Purchase Orders")

    subtabs = st.tabs(["📋 All POs", "➕ Create PO"])

    with subtabs[0]:
        show_all_purchase_orders(username, is_admin)

    with subtabs[1]:
        show_create_purchase_order(username)


def show_all_purchase_orders(username: str, is_admin: bool):
    """View all purchase orders with enhanced details and status management"""

    st.markdown("#### 📋 All Purchase Orders")

    # Filters
    col1, col2, col3 = st.columns(3)

    with col1:
        status_filter = st.selectbox(
            "Status",
            ["All", "pending", "approved", "ordered", "received", "closed", "cancelled"],
            key="po_status_filter_select"
        )

    with col2:
        days_back = st.number_input("Days to show", min_value=7, max_value=365, value=30)

    with col3:
        if st.button("🔄 Refresh", width='stretch', key="refresh_pos"):
            st.rerun()

    # Load POs (using cache)
    with st.spinner("Loading purchase orders..."):
        pos = get_purchase_orders_cached(status_filter, days_back)

    if not pos:
        st.info("No purchase orders found")
        return

    total_pos = len(pos)
    st.success(f"✅ Found {total_pos} purchase orders")

    # Pagination settings
    page_size = PO_PAGE_SIZE
    total_pages = (total_pos + page_size - 1) // page_size  # Ceiling division

    # Initialize page number in session state
    if 'po_page_number' not in st.session_state:
        st.session_state.po_page_number = 1

    # Pagination controls
    col_pg1, col_pg2, col_pg3, col_pg4, col_pg5 = st.columns([2, 1, 2, 1, 2])

    with col_pg2:
        if st.button("⬅️ Previous", disabled=(st.session_state.po_page_number == 1), key="prev_page"):
            st.session_state.po_page_number -= 1
            st.rerun()

    with col_pg3:
        st.markdown(f"**Page {st.session_state.po_page_number} of {total_pages}** ({total_pos} total)")

    with col_pg4:
        if st.button("Next ➡️", disabled=(st.session_state.po_page_number == total_pages), key="next_page"):
            st.session_state.po_page_number += 1
            st.rerun()

    # Calculate slice for current page
    start_idx = (st.session_state.po_page_number - 1) * page_size
    end_idx = min(start_idx + page_size, total_pos)
    pos_page = pos[start_idx:end_idx]

    # Export all POs - use cached Excel generation
    excel_data = generate_pos_excel(pos, is_admin)

    st.download_button(
        label="📥 Download All POs (Excel)",
        data=excel_data,
        file_name=f"purchase_orders_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width='stretch',
        key="download_all_pos_excel"
    )

    st.markdown("---")
    st.caption(f"💡 Showing {start_idx + 1}-{end_idx} of {total_pos} purchase orders | Click on any PO to view details")

    # Display each PO as an expandable card (paginated)
    for idx, po in enumerate(pos_page, start=start_idx + 1):
        # Get status emoji and text for expander label (HTML won't render in expander)
        status = po.get('status', 'pending')
        status_emojis = {
            'pending': '⏳',
            'approved': '✅',
            'ordered': '📦',
            'received': '✔️',
            'closed': '🔒',
            'cancelled': '❌'
        }
        status_emoji = status_emojis.get(status, '❓')

        with st.expander(
            f"📄 **{po.get('po_number', 'N/A')}** | {status_emoji} {status.upper()} | "
            f"{po.get('supplier_name', 'N/A')} | {po.get('item_name', 'N/A')} | "
            f"₹{po.get('total_cost', 0):,.2f}",
            expanded=False
        ):
            show_po_details(po, is_admin, username)


def show_po_details(po: Dict, is_admin: bool, username: str):
    """Display detailed PO information with management options - OPTIMIZED"""

    # Get full PO details (cached)
    po_id = po.get('id')
    po_full = get_po_details_cached(po_id)

    if not po_full:
        st.error("Could not load PO details")
        return

    # PO Header Information
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### 📋 PO Information")
        st.markdown(f"**PO Number:** {po_full.get('po_number', 'N/A')}")
        st.markdown(f"**Status:** {get_status_badge(po_full.get('status', 'pending'))}", unsafe_allow_html=True)
        st.markdown(f"**PO Date:** {po_full.get('po_date', 'N/A')}")
        st.markdown(f"**Expected Delivery:** {po_full.get('expected_delivery', 'N/A')}")
        st.markdown(f"**Created By:** {po_full.get('created_by_name', 'Unknown')}")

    with col2:
        st.markdown("#### 🏪 Supplier Details")
        st.markdown(f"**Name:** {po_full.get('supplier_name', 'N/A')}")
        st.markdown(f"**Contact:** {po_full.get('supplier_contact', 'N/A')}")
        st.markdown(f"**Phone:** {po_full.get('supplier_phone', 'N/A')}")
        st.markdown(f"**Email:** {po_full.get('supplier_email', 'N/A')}")
        if po_full.get('supplier_address') and po_full.get('supplier_address') != 'N/A':
            st.markdown(f"**Address:** {po_full.get('supplier_address')}")

    with col3:
        st.markdown("#### 💰 Summary")
        st.markdown(f"**Total Items:** {len(po_full.get('items', []))}")
        st.markdown(f"**Total Quantity:** {po_full.get('total_quantity', 0):.2f}")
        st.markdown(f"**Total Cost:** ₹{po_full.get('total_cost', 0):,.2f}")

        if po_full.get('notes'):
            st.markdown(f"**Notes:** {po_full.get('notes')}")

    st.markdown("---")

    # Items Table
    st.markdown("#### 📦 Items")
    items = po_full.get('items', [])

    if items:
        items_data = []
        for item in items:
            item_row = {
                'Item Name': item.get('item_name', 'N/A'),
                'SKU': item.get('sku', 'N/A'),
                'Quantity': f"{item.get('ordered_qty', 0):.2f} {item.get('unit', '')}",
                'Unit Cost': f"₹{item.get('unit_cost', 0):.2f}",
                'Total': f"₹{item.get('ordered_qty', 0) * item.get('unit_cost', 0):,.2f}"
            }
            items_data.append(item_row)

        st.dataframe(pd.DataFrame(items_data), hide_index=True, width='stretch')
    else:
        st.info("No items in this PO")

    st.markdown("---")

    # Action Buttons
    action_col1, action_col2, action_col3, action_col4 = st.columns(4)

    # Admin Status Management
    if is_admin:
        with action_col1:
            st.markdown("**🔄 Change Status**")
            current_status = po_full.get('status', 'pending')
            new_status = st.selectbox(
                "New Status",
                ["pending", "approved", "ordered", "received", "closed", "cancelled"],
                index=["pending", "approved", "ordered", "received", "closed", "cancelled"].index(current_status),
                key=f"status_change_{po_id}",
                label_visibility="collapsed"
            )

            if new_status != current_status:
                if st.button("✅ Update Status", key=f"update_status_{po_id}", type="primary"):
                    with st.spinner("Updating status..."):
                        if InventoryDB.update_po_status(po_id, new_status):
                            st.success(f"✅ Status updated to {new_status.upper()}")

                            # Log activity
                            ActivityLogger.log(
                                user_id=st.session_state.user['id'],
                                action_type='update_po_status',
                                module_key='inventory',
                                description=f"Updated PO {po_full.get('po_number')} status: {current_status} → {new_status}",
                                metadata={'po_id': po_id, 'old_status': current_status, 'new_status': new_status},
                                user_email=st.session_state.user.get('email')
                            )

                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("❌ Failed to update status")

    # Receive Stock Button (for ordered/received status)
    with action_col2:
        current_status = po_full.get('status', 'pending')
        if current_status in ['ordered', 'received']:
            st.markdown("**📥 Receive Stock**")
            if st.button("➕ Add to Stock", key=f"receive_stock_{po_id}"):
                # Store PO info in session state for pre-filling add stock form
                st.session_state['prefill_from_po'] = {
                    'po_id': po_id,
                    'po_number': po_full.get('po_number'),
                    'items': items,
                    'supplier_name': po_full.get('supplier_name')
                }
                st.info("💡 Switch to 'Add Stock' tab to complete stock receipt")
                st.info(f"📋 PO details saved for: {po_full.get('po_number')}")

    # Export Single PO
    with action_col3:
        st.markdown("**📄 Export PO**")

        # Use utility function for Excel generation
        excel_output = generate_po_detail_excel(po_full)

        st.download_button(
            label="📥 Download",
            data=excel_output,
            file_name=f"PO_{po_full.get('po_number', 'export')}_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"download_po_{po_id}"
        )

    # Delete PO (Admin only, pending status only)
    if is_admin and po_full.get('status') == 'pending':
        with action_col4:
            st.markdown("**🗑️ Delete PO**")

            # Initialize confirmation state
            confirm_key = f"confirm_delete_{po_id}"
            if confirm_key not in st.session_state:
                st.session_state[confirm_key] = False

            # First click: Ask for confirmation
            if not st.session_state[confirm_key]:
                if st.button("❌ Delete", key=f"delete_po_{po_id}", type="secondary"):
                    st.session_state[confirm_key] = True
                    st.rerun()
            # Second click: Confirm and delete
            else:
                st.warning("⚠️ Are you sure?")
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("✅ Yes, Delete", key=f"confirm_yes_{po_id}", type="primary"):
                        with st.spinner("Deleting PO..."):
                            if InventoryDB.delete_po(po_id):
                                st.success(f"✅ PO {po_full.get('po_number')} deleted successfully!")

                                # Log activity
                                ActivityLogger.log(
                                    user_id=st.session_state.user['id'],
                                    action_type='delete_po',
                                    module_key='inventory',
                                    description=f"Deleted PO: {po_full.get('po_number')}",
                                    metadata={'po_id': po_id, 'po_number': po_full.get('po_number')},
                                    user_email=st.session_state.user.get('email')
                                )

                                # Clear cache to reflect deletion immediately
                                refresh_data_cache()

                                # Clear confirmation state
                                st.session_state[confirm_key] = False
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("❌ Failed to delete PO")
                                st.session_state[confirm_key] = False
                with col_b:
                    if st.button("❌ Cancel", key=f"confirm_no_{po_id}"):
                        st.session_state[confirm_key] = False
                        st.rerun()


def show_create_purchase_order(username: str):
    """Create new purchase order with multiple items (invoice-style) - OPTIMIZED"""

    st.markdown("#### ➕ Create Purchase Order")

    # Initialize session state
    init_po_session_state()

    master_items = get_master_items_cached(active_only=True)
    suppliers = get_suppliers_cached(active_only=True)

    if not master_items:
        st.warning("⚠️ No active items in master list")
        return

    if not suppliers:
        st.warning("⚠️ No active suppliers found")
        return

    # PO Header Section - Use form to prevent reruns on every keystroke
    st.markdown("##### 📋 PO Header")

    with st.form("po_header_form", border=False):
        col1, col2 = st.columns(2)

        with col1:
            po_number = st.text_input(
                "PO Number *",
                value=st.session_state.po_header_data['po_number'],
                help="Auto-generated, but you can edit it"
            )

            supplier_options = {s['supplier_name']: s for s in suppliers}
            supplier_list = list(supplier_options.keys())
            supplier_idx = 0
            if st.session_state.po_header_data['supplier_name'] in supplier_list:
                supplier_idx = supplier_list.index(st.session_state.po_header_data['supplier_name'])

            supplier_name = st.selectbox(
                "Supplier *",
                options=supplier_list,
                index=supplier_idx
            )

        with col2:
            po_date = st.date_input("PO Date *", value=st.session_state.po_header_data['po_date'])

            expected_delivery = st.date_input(
                "Expected Delivery *",
                value=st.session_state.po_header_data['expected_delivery'],
                min_value=date.today()
            )

        notes = st.text_area("Notes (optional)", value=st.session_state.po_header_data['notes'], height=80)

        # Update button
        if st.form_submit_button("✅ Update Header", type="secondary"):
            st.session_state.po_header_data = {
                'po_number': po_number,
                'supplier_name': supplier_name,
                'po_date': po_date,
                'expected_delivery': expected_delivery,
                'notes': notes
            }
            st.toast("✅ Header updated!")

    st.markdown("---")

    # Add Items Section - Use fragment for instant updates
    show_add_item_section(master_items)

    # Display Added Items
    if st.session_state.po_items:
        show_po_cart(suppliers, supplier_options, username)
    else:
        st.info("ℹ️ No items added yet. Add items above to create a purchase order.")


@st.fragment
def show_add_item_section(master_items):
    """Fragment for adding items - isolated from main page, instant updates"""
    st.markdown("##### ➕ Add Items")

    item_col1, item_col2, item_col3, item_col4 = st.columns([3, 2, 2, 1])

    with item_col1:
        item_options = {item['item_name']: item for item in master_items}
        selected_item_name = st.selectbox(
            "Select Item",
            options=list(item_options.keys()),
            key="add_item_select_frag"
        )
        selected_item = item_options[selected_item_name]

    with item_col2:
        item_unit = selected_item.get('unit', 'unit')
        quantity = st.number_input(
            f"Quantity ({item_unit})",
            min_value=0.01,
            value=1.0,
            step=0.01,
            format="%.2f",
            key="add_item_qty_frag"
        )

    with item_col3:
        unit_cost = st.number_input(
            f"Unit Cost (₹/{item_unit})",
            min_value=0.01,
            value=1.0,
            step=0.01,
            format="%.2f",
            key="add_item_cost_frag"
        )

    with item_col4:
        st.markdown("&nbsp;")
        if st.button("➕ Add", key="add_item_btn_frag", width='stretch'):
            # Add item to cart
            new_item = {
                'item_master_id': selected_item['id'],
                'item_name': selected_item_name,
                'sku': selected_item.get('sku', ''),
                'unit': item_unit,
                'ordered_qty': quantity,
                'unit_cost': unit_cost,
                'total': quantity * unit_cost
            }
            st.session_state.po_items.append(new_item)
            st.toast(f"✅ Added {selected_item_name}")
            st.rerun()  # Force main page to update and show cart


def show_po_cart(suppliers, supplier_options, username):
    """Display PO cart and submission"""
    st.markdown("---")
    st.markdown("##### 📦 Items in PO")

    # Calculate totals
    total_items = len(st.session_state.po_items)
    total_quantity = sum(item['ordered_qty'] for item in st.session_state.po_items)
    grand_total = sum(item['total'] for item in st.session_state.po_items)

    # Show summary metrics
    metric_col1, metric_col2, metric_col3 = st.columns(3)
    with metric_col1:
        st.metric("Total Items", total_items)
    with metric_col2:
        st.metric("Total Quantity", f"{total_quantity:.2f}")
    with metric_col3:
        st.metric("Grand Total", f"₹{grand_total:,.2f}")

    # Display items table
    items_display = []
    for idx, item in enumerate(st.session_state.po_items):
        items_display.append({
            '#': idx + 1,
            'Item Name': item['item_name'],
            'SKU': item['sku'],
            'Quantity': f"{item['ordered_qty']:.2f} {item['unit']}",
            'Unit Cost': f"₹{item['unit_cost']:,.2f}",
            'Total': f"₹{item['total']:,.2f}",
            'Action': idx
        })

    df_display = pd.DataFrame(items_display)

    # Display table without Action column (we'll add delete buttons separately)
    st.dataframe(
        df_display.drop('Action', axis=1),
        hide_index=True,
        width='stretch'
    )

    # Delete buttons
    st.markdown("**Remove Items:**")
    delete_cols = st.columns(min(5, len(st.session_state.po_items)))
    for idx, item in enumerate(st.session_state.po_items):
        with delete_cols[idx % 5]:
            if st.button(f"🗑️ #{idx+1}", key=f"delete_{idx}"):
                st.session_state.po_items.pop(idx)
                st.rerun()

    # Action buttons
    st.markdown("---")
    action_col1, action_col2, action_col3 = st.columns([1, 1, 2])

    with action_col1:
        if st.button("🗑️ Clear All", width='stretch'):
            clear_po_cart()
            st.rerun()

    with action_col2:
        if st.button("✅ Create PO", type="primary", width='stretch'):
            # Get header data
            po_data = st.session_state.po_header_data
            po_number = po_data['po_number']
            supplier_name = po_data['supplier_name']
            po_date = po_data['po_date']
            expected_delivery = po_data['expected_delivery']
            notes = po_data['notes']

            # Validate
            if not po_number or len(po_number.strip()) < 3:
                st.error("❌ PO number is required")
            elif not supplier_name:
                st.error("❌ Please select a supplier and click 'Update Header'")
            elif len(st.session_state.po_items) == 0:
                st.error("❌ Please add at least one item")
            else:
                # Create PO using the existing create_po function
                with st.spinner("Creating purchase order..."):
                    supplier_id = supplier_options[supplier_name]['id']

                    po_data = {
                        'po_number': po_number.strip(),
                        'supplier_id': supplier_id,
                        'po_date': po_date.isoformat() if isinstance(po_date, date) else po_date,
                        'expected_delivery': expected_delivery.isoformat() if isinstance(expected_delivery, date) else expected_delivery,
                        'status': 'pending',
                        'notes': notes.strip() if notes else None
                    }

                    # Prepare items for database
                    po_items_data = []
                    for item in st.session_state.po_items:
                        po_items_data.append({
                            'item_master_id': item['item_master_id'],
                            'ordered_qty': item['ordered_qty'],
                            'unit_cost': item['unit_cost']
                        })

                    po_id = InventoryDB.create_po(
                        po_data=po_data,
                        po_items=po_items_data,
                        user_id=st.session_state.user['id']
                    )

                    if po_id:
                        st.success(f"✅ Purchase Order {po_number} created successfully with {len(st.session_state.po_items)} items!")

                        # Get user profile for full name
                        user_profile = SessionManager.get_user_profile()
                        full_name = user_profile.get('full_name', st.session_state.user.get('email', 'Unknown'))

                        ActivityLogger.log(
                            user_id=st.session_state.user['id'],
                            action_type='create_po',
                            module_key='inventory',
                            description=f"Created PO: {po_number} with {len(st.session_state.po_items)} items by {full_name}",
                            metadata={'po_number': po_number, 'items_count': len(st.session_state.po_items)},
                            user_email=st.session_state.user.get('email')
                        )

                        # Clear cache to show new PO immediately
                        refresh_data_cache()

                        # Clear session state
                        clear_po_cart()

                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Failed to create purchase order")
