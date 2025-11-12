"""
Suppliers Tab (Admin Only)
Manage supplier information with CRUD operations

VERSION HISTORY:
1.0.0 - 2025-01-12 - Initial modular version extracted from inventory.py
      - View all suppliers with status filtering
      - Add new suppliers with contact details
      - Edit/delete suppliers with usage statistics
      - Activity logging for all operations
"""

import streamlit as st
import pandas as pd
import time

from config.database import ActivityLogger
from db.db_inventory import InventoryDB


def show_suppliers_tab(username: str):
    """Manage suppliers (Admin only)"""

    st.markdown("### 👥 Suppliers")
    st.caption("Manage suppliers for inventory items")
    st.markdown("---")

    subtabs = st.tabs(["📋 View Suppliers", "➕ Add Supplier", "✏️ Edit Supplier"])

    with subtabs[0]:
        show_all_suppliers()

    with subtabs[1]:
        show_add_supplier(username)

    with subtabs[2]:
        show_edit_supplier(username)


def show_all_suppliers():
    """View all suppliers"""

    st.markdown("#### 📋 All Suppliers")

    status_filter = st.selectbox(
        "Status",
        ["All", "Active", "Inactive"],
        key="supplier_status_filter_select"
    )

    with st.spinner("Loading suppliers..."):
        if status_filter == "Active":
            suppliers = InventoryDB.get_all_suppliers(active_only=True)
        elif status_filter == "Inactive":
            all_suppliers = InventoryDB.get_all_suppliers(active_only=False)
            suppliers = [s for s in all_suppliers if not s.get('is_active', True)]
        else:
            suppliers = InventoryDB.get_all_suppliers(active_only=False)

    if not suppliers:
        st.info("No suppliers found")
        return

    st.success(f"✅ Found {len(suppliers)} suppliers")

    df = pd.DataFrame(suppliers)
    display_cols = ['supplier_name', 'contact_person', 'phone', 'email', 'address', 'is_active']
    display_cols = [col for col in display_cols if col in df.columns]
    display_df = df[display_cols].copy()

    display_df['is_active'] = display_df['is_active'].map({True: '✅ Active', False: '❌ Inactive'})
    display_df.columns = ['Supplier Name', 'Contact Person', 'Phone', 'Email', 'Address', 'Status']

    st.dataframe(display_df, width='stretch', hide_index=True)


def show_add_supplier(username: str):
    """Add new supplier"""

    st.markdown("#### ➕ Add New Supplier")

    with st.form("add_supplier_form", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            supplier_name = st.text_input("Supplier Name *", placeholder="e.g., ABC Suppliers")
            contact_person = st.text_input("Contact Person", placeholder="e.g., John Doe")
            phone = st.text_input("Phone", placeholder="e.g., +91-9876543210")

        with col2:
            email = st.text_input("Email", placeholder="e.g., contact@supplier.com")
            address = st.text_area("Address", height=100)
            notes = st.text_area("Notes", height=100)

        st.markdown("---")
        submitted = st.form_submit_button("✅ Add Supplier", type="primary", width='stretch')

        if submitted:
            if not supplier_name or len(supplier_name.strip()) < 3:
                st.error("❌ Supplier name is required (minimum 3 characters)")
            else:
                with st.spinner("Adding supplier..."):
                    success = InventoryDB.add_supplier(
                        supplier_name=supplier_name.strip(),
                        contact_person=contact_person.strip() if contact_person else None,
                        phone=phone.strip() if phone else None,
                        email=email.strip() if email else None,
                        address=address.strip() if address else None,
                        notes=notes.strip() if notes else None,
                        username=username
                    )

                if success:
                    st.success(f"✅ Supplier '{supplier_name}' added successfully!")

                    ActivityLogger.log(
                        user_id=st.session_state.user['id'],
                        action_type='add_supplier',
                        module_key='inventory',
                        description=f"Added supplier: {supplier_name}"
                    )

                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Failed to add supplier")


def show_edit_supplier(username: str):
    """Edit or delete existing supplier"""

    st.markdown("#### ✏️ Edit Supplier")

    suppliers = InventoryDB.get_all_suppliers(active_only=False)

    if not suppliers:
        st.warning("No suppliers found. Add a supplier first.")
        return

    # Supplier selection
    supplier_options = {f"{s['supplier_name']} ({s.get('phone', 'N/A')})": s for s in suppliers}
    selected_key = st.selectbox(
        "Select Supplier",
        options=list(supplier_options.keys()),
        key="edit_supplier_select"
    )
    selected_supplier = supplier_options[selected_key]

    st.markdown("---")

    # Get item count for this supplier
    all_items = InventoryDB.get_all_master_items(active_only=False)
    item_count = 0
    if all_items:
        items_df = pd.DataFrame(all_items)
        if 'default_supplier_id' in items_df.columns:
            item_count = len(items_df[items_df['default_supplier_id'] == selected_supplier['id']])

    if item_count > 0:
        st.info(f"ℹ️ This supplier is set as default for {item_count} item(s)")

    with st.form("edit_supplier_form"):
        col1, col2 = st.columns(2)

        with col1:
            supplier_name = st.text_input(
                "Supplier Name *",
                value=selected_supplier.get('supplier_name', ''),
                placeholder="e.g., ABC Suppliers"
            )
            contact_person = st.text_input(
                "Contact Person",
                value=selected_supplier.get('contact_person', '') or '',
                placeholder="e.g., John Doe"
            )
            phone = st.text_input(
                "Phone",
                value=selected_supplier.get('phone', '') or '',
                placeholder="e.g., +91-9876543210"
            )

        with col2:
            email = st.text_input(
                "Email",
                value=selected_supplier.get('email', '') or '',
                placeholder="e.g., contact@supplier.com"
            )
            address = st.text_area(
                "Address",
                value=selected_supplier.get('address', '') or '',
                height=80
            )
            notes = st.text_area(
                "Notes",
                value=selected_supplier.get('notes', '') or '',
                height=80
            )

        # Status toggle
        is_active = st.checkbox(
            "Active Supplier",
            value=selected_supplier.get('is_active', True),
            key="edit_supplier_is_active"
        )

        st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:
            update_submitted = st.form_submit_button("💾 Update Supplier", type="primary", width='stretch')

        with col2:
            delete_submitted = st.form_submit_button("🗑️ Delete Supplier", type="secondary", width='stretch')

        if update_submitted:
            # Validation
            if not supplier_name or len(supplier_name.strip()) < 3:
                st.error("❌ Supplier name is required (minimum 3 characters)")
                return

            # Update supplier
            updates = {
                'supplier_name': supplier_name.strip(),
                'contact_person': contact_person.strip() if contact_person else None,
                'phone': phone.strip() if phone else None,
                'email': email.strip() if email else None,
                'address': address.strip() if address else None,
                'notes': notes.strip() if notes else None,
                'is_active': is_active
            }

            success = InventoryDB.update_supplier(
                supplier_id=selected_supplier['id'],
                updates=updates
            )

            if success:
                st.success(f"✅ Supplier '{supplier_name}' updated successfully!")

                # Log activity
                if 'user' in st.session_state and st.session_state.user:
                    ActivityLogger.log(
                        user_id=st.session_state.user['id'],
                        action_type='update_supplier',
                        module_key='inventory',
                        description=f"Updated supplier: {selected_supplier['supplier_name']} → {supplier_name}",
                        metadata={
                            'supplier_id': selected_supplier['id'],
                            'old_name': selected_supplier['supplier_name'],
                            'new_name': supplier_name
                        }
                    )

                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Failed to update supplier")

        if delete_submitted:
            # Attempt to delete
            success = InventoryDB.delete_supplier(selected_supplier['id'])

            if success:
                st.success(f"✅ Supplier '{selected_supplier['supplier_name']}' deleted successfully!")

                # Log activity
                if 'user' in st.session_state and st.session_state.user:
                    ActivityLogger.log(
                        user_id=st.session_state.user['id'],
                        action_type='delete_supplier',
                        module_key='inventory',
                        description=f"Deleted supplier: {selected_supplier['supplier_name']}",
                        metadata={'supplier_name': selected_supplier['supplier_name']}
                    )

                time.sleep(1)
                st.rerun()
            # Error message is already shown by delete_supplier method
