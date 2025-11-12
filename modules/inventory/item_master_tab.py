"""
Item Master Tab (Admin Only)
Manage master item templates with CRUD operations

VERSION HISTORY:
1.0.0 - 2025-01-12 - Initial modular version extracted from inventory.py
      - View all master items with filtering (status, category)
      - Add new master items with validation
      - Edit existing items with status management
      - Activity logging for all operations
"""

import streamlit as st
import pandas as pd
import time

from config.database import ActivityLogger
from db.db_inventory import InventoryDB


def show_item_master_tab(username: str):
    """Manage item master list (Admin only)"""

    st.markdown("### 📋 Item Master List")
    st.caption("Manage item templates - stock is tracked in batches")

    subtabs = st.tabs(["📋 All Items", "➕ Add Item", "✏️ Edit Item"])

    with subtabs[0]:
        show_all_master_items()

    with subtabs[1]:
        show_add_master_item(username)

    with subtabs[2]:
        show_edit_master_item(username)


def show_all_master_items():
    """View all master items"""

    st.markdown("#### 📋 All Master Items")

    # Filters
    col1, col2, col3 = st.columns(3)

    with col1:
        status_filter = st.selectbox(
            "Status",
            ["All", "Active", "Inactive"],
            key="master_status_filter_select"
        )

    with col2:
        categories = InventoryDB.get_all_categories()
        category_filter = st.selectbox(
            "Category",
            ["All"] + categories,
            key="master_category_filter_select"
        )

    with col3:
        if st.button("🔄 Refresh", width='stretch', key="refresh_master_items"):
            st.rerun()

    # Load items
    with st.spinner("Loading items..."):
        if status_filter == "Active":
            items = InventoryDB.get_all_master_items(active_only=True)
        elif status_filter == "Inactive":
            all_items = InventoryDB.get_all_master_items(active_only=False)
            items = [i for i in all_items if not i.get('is_active', True)]
        else:
            items = InventoryDB.get_all_master_items(active_only=False)

    # Apply category filter
    if category_filter != "All":
        items = [i for i in items if i.get('category') == category_filter]

    if not items:
        st.info("No items found")
        return

    st.success(f"✅ Found {len(items)} items")

    # Display
    df = pd.DataFrame(items)

    if 'reorder_level' not in df.columns and 'reorder_threshold' in df.columns:
        df['reorder_level'] = df['reorder_threshold']
    display_cols = ['item_name', 'sku', 'category', 'brand', 'unit', 'current_qty', 'reorder_level', 'is_active']
    display_cols = [col for col in display_cols if col in df.columns]

    if not display_cols:
        st.info("No displayable columns returned for master items.")
        return

    display_df = df[display_cols].copy()

    if 'is_active' in display_df.columns:
        display_df['is_active'] = display_df['is_active'].map({True: '✅ Active', False: '❌ Inactive'})

    column_mapping = {
        'item_name': 'Item Name',
        'sku': 'SKU',
        'category': 'Category',
        'brand': 'Brand',
        'unit': 'Unit',
        'current_qty': 'Current Stock',
        'reorder_level': 'Reorder Level',
        'is_active': 'Status'
    }

    display_df.rename(
        columns={col: column_mapping.get(col, col) for col in display_df.columns},
        inplace=True
    )

    st.dataframe(display_df, width='stretch', hide_index=True, height=500)


def show_add_master_item(username: str):
    """Add new master item"""

    st.markdown("#### ➕ Add New Master Item")

    user_id = st.session_state.user.get('id') if 'user' in st.session_state and st.session_state.user else None

    with st.form("add_master_item_form", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            item_name = st.text_input("Item Name *", placeholder="e.g., Fish Feed 3mm 28% Protein")
            sku = st.text_input("SKU *", placeholder="e.g., FF-3MM-28P")

            # Category selection with dropdown + custom option
            existing_categories = InventoryDB.get_all_categories()
            category_options = ["-- Add New Category --"] + existing_categories

            selected_category_option = st.selectbox(
                "Category *",
                options=category_options,
                key="add_master_category_select"
            )

            # If "Add New Category" selected, show text input
            if selected_category_option == "-- Add New Category --":
                category = st.text_input(
                    "Enter New Category Name *",
                    placeholder="e.g., Fish Feed, Chemicals, Equipment",
                    key="add_master_new_category_input"
                )
            else:
                category = selected_category_option

            brand = st.text_input("Brand/Manufacturer", placeholder="e.g., Growel")
            unit = st.selectbox(
                "Unit *",
                options=["kg", "g", "liter", "ml", "pieces", "bags", "boxes"],
                key="add_master_unit_select"
            )

        with col2:
            reorder_threshold = st.number_input("Reorder Level *", min_value=0.0, step=0.01, format="%.2f")

            suppliers = InventoryDB.get_all_suppliers(active_only=True)
            supplier_options = [None] + [s['id'] for s in suppliers if s.get('id') is not None]
            supplier_label_map = {
                None: "None",
                **{s['id']: s.get('supplier_name', f"Supplier #{s['id']}") for s in suppliers if s.get('id') is not None}
            }

            selected_supplier_id = st.selectbox(
                "Default Supplier",
                options=supplier_options,
                format_func=lambda value: supplier_label_map.get(value, "Unknown"),
                key="add_master_default_supplier_select"
            )
            selected_supplier_name = supplier_label_map.get(selected_supplier_id, "None")

            specifications = st.text_area("Specifications", height=80)
            notes = st.text_area("Notes", height=80)

        st.markdown("---")
        submitted = st.form_submit_button("✅ Add Item", type="primary", width='stretch')

        if submitted:
            errors = []

            if not item_name or len(item_name.strip()) < 3:
                errors.append("Item name is required (minimum 3 characters)")

            if not sku or len(sku.strip()) < 2:
                errors.append("SKU is required (minimum 2 characters)")

            if not category or len(category.strip()) < 2:
                errors.append("Category is required")

            if reorder_threshold < 0:
                errors.append("Reorder level cannot be negative")

            if errors:
                for error in errors:
                    st.error(f"❌ {error}")
            else:
                with st.spinner("Adding item..."):
                    supplier_kwargs = {}
                    if selected_supplier_id is not None:
                        supplier_kwargs["default_supplier_id"] = selected_supplier_id

                    success = InventoryDB.add_master_item(
                        item_name=item_name.strip(),
                        sku=sku.strip(),
                        category=category.strip(),
                        brand=brand.strip() if brand else None,
                        unit=unit,
                        reorder_threshold=reorder_threshold,
                        specifications=specifications.strip() if specifications else None,
                        notes=notes.strip() if notes else None,
                        username=username,
                        user_id=user_id,
                        **supplier_kwargs
                    )

            if success:
                st.success(f"✅ Item '{item_name}' added successfully!")

                ActivityLogger.log(
                    user_id=st.session_state.user['id'],
                    action_type='add_master_item',
                    module_key='inventory',
                    description=f"Added master item: {item_name}",
                    metadata={
                        'item_name': item_name,
                        'sku': sku,
                        'supplier': selected_supplier_name if selected_supplier_id else None,
                        'default_supplier_id': selected_supplier_id,
                        'reorder_threshold': reorder_threshold
                    }
                )

                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Failed to add item. SKU may already exist.")


def show_edit_master_item(username: str):
    """Edit master item"""

    st.markdown("#### ✏️ Edit Master Item")

    items = InventoryDB.get_all_master_items(active_only=False)

    if not items:
        st.warning("No items found")
        return

    # Item selection
    item_options = {f"{item['item_name']} ({item.get('sku', 'N/A')})": item for item in items}
    selected_key = st.selectbox(
        "Select Item",
        options=list(item_options.keys()),
        key="edit_master_item_select"
    )
    selected_item = item_options[selected_key]

    st.markdown("---")

    with st.form("edit_master_item_form"):
        col1, col2 = st.columns(2)

        with col1:
            item_name = st.text_input("Item Name *", value=selected_item.get('item_name', ''))
            sku = st.text_input("SKU *", value=selected_item.get('sku', ''))

            # Category selection with dropdown + custom option
            current_category = selected_item.get('category', '')
            existing_categories = InventoryDB.get_all_categories()

            # Build category options with current category first if it exists
            if current_category and current_category not in existing_categories:
                category_options = [current_category, "-- Add New Category --"] + existing_categories
            else:
                category_options = ["-- Add New Category --"] + existing_categories

            # Set initial selection to current category or first option
            default_index = 0
            if current_category in category_options:
                default_index = category_options.index(current_category)

            selected_category_option = st.selectbox(
                "Category *",
                options=category_options,
                index=default_index,
                key="edit_master_category_select"
            )

            # If "Add New Category" selected, show text input
            if selected_category_option == "-- Add New Category --":
                category = st.text_input(
                    "Enter New Category Name *",
                    value=current_category,
                    placeholder="e.g., Fish Feed, Chemicals, Equipment",
                    key="edit_master_new_category_input"
                )
            else:
                category = selected_category_option

            brand = st.text_input("Brand", value=selected_item.get('brand', '') or '')

            units = ["kg", "g", "liter", "ml", "pieces", "bags", "boxes"]
            current_unit = selected_item.get('unit', 'kg')
            unit_index = units.index(current_unit) if current_unit in units else 0
            unit = st.selectbox(
                "Unit *",
                options=units,
                index=unit_index,
                key="edit_master_unit_select"
            )

        with col2:
            reorder_threshold_value = selected_item.get('reorder_threshold')
            if reorder_threshold_value is None:
                reorder_threshold_value = selected_item.get('reorder_level', 0)
            try:
                reorder_threshold_value = float(reorder_threshold_value or 0)
            except (TypeError, ValueError):
                reorder_threshold_value = 0.0

            reorder_threshold = st.number_input(
                "Reorder Level *",
                value=reorder_threshold_value,
                key="edit_master_reorder_threshold"
            )

            suppliers = InventoryDB.get_all_suppliers(active_only=True)
            supplier_options = [None] + [s['id'] for s in suppliers if s.get('id') is not None]
            supplier_label_map = {
                None: "None",
                **{s['id']: s.get('supplier_name', f"Supplier #{s['id']}") for s in suppliers if s.get('id') is not None}
            }

            current_supplier_id = selected_item.get('default_supplier_id')
            if current_supplier_id is None:
                current_supplier_id = selected_item.get('supplier_id')
            if current_supplier_id is not None and current_supplier_id not in supplier_label_map:
                supplier_options.append(current_supplier_id)
                supplier_label_map[current_supplier_id] = selected_item.get('supplier_name', f"Supplier #{current_supplier_id}")

            supplier_index = supplier_options.index(current_supplier_id) if current_supplier_id in supplier_options else 0

            selected_supplier_id = st.selectbox(
                "Default Supplier",
                options=supplier_options,
                index=supplier_index,
                format_func=lambda value: supplier_label_map.get(value, "Unknown"),
                key="edit_master_default_supplier_select"
            )
            selected_supplier_name = supplier_label_map.get(selected_supplier_id, "None")

            is_active = st.checkbox("Active", value=selected_item.get('is_active', True))

            specifications = st.text_area("Specifications", value=selected_item.get('specifications', '') or '', height=80)
            notes = st.text_area("Notes", value=selected_item.get('notes', '') or '', height=80)

        st.markdown("---")

        col1, col2 = st.columns([3, 1])
        with col2:
            submitted = st.form_submit_button("💾 Update Item", type="primary", width='stretch')

        if submitted:
            with st.spinner("Updating item..."):
                success = InventoryDB.update_master_item(
                    item_master_id=selected_item['id'],
                    item_name=item_name.strip(),
                    sku=sku.strip(),
                    category=category.strip(),
                    brand=brand.strip() if brand else None,
                    unit=unit,
                    reorder_threshold=reorder_threshold,
                    default_supplier_id=selected_supplier_id,
                    specifications=specifications.strip() if specifications else None,
                    notes=notes.strip() if notes else None,
                    is_active=is_active,
                    username=username
                )

            if success:
                st.success(f"✅ Item '{item_name}' updated successfully!")

                ActivityLogger.log(
                    user_id=st.session_state.user['id'],
                    action_type='update_master_item',
                    module_key='inventory',
                    description=f"Updated master item: {item_name}",
                    metadata={
                        'item_name': item_name,
                        'supplier': selected_supplier_name if selected_supplier_id else None,
                        'default_supplier_id': selected_supplier_id,
                        'reorder_threshold': reorder_threshold
                    }
                )

                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Failed to update item")
