"""
Categories Tab (Admin Only)
Manage inventory categories with CRUD operations

VERSION HISTORY:
1.0.0 - 2025-01-12 - Initial modular version extracted from inventory.py
      - View all categories with usage statistics
      - Add new categories with validation
      - Edit/delete categories with safety checks
      - Activity logging for all operations
"""

import streamlit as st
import pandas as pd
import time

from config.database import ActivityLogger
from db.db_inventory import InventoryDB


def show_categories_tab(username: str):
    """Main categories management tab with view/add/edit sub-tabs"""

    st.markdown("### 🏷️ Category Management")
    st.caption("Manage inventory categories for master items")
    st.markdown("---")

    # Create sub-tabs for View, Add, Edit
    sub_tabs = st.tabs(["📋 View Categories", "➕ Add Category", "✏️ Edit Category"])

    with sub_tabs[0]:
        show_view_categories()

    with sub_tabs[1]:
        show_add_category(username)

    with sub_tabs[2]:
        show_edit_category(username)


def show_view_categories():
    """View all categories"""

    st.markdown("#### 📋 All Categories")

    categories = InventoryDB.get_categories()

    if not categories:
        st.info("No categories found. Add your first category using the 'Add Category' tab.")
        return

    # Display total count
    st.metric("Total Categories", len(categories))
    st.markdown("---")

    # Create dataframe for display
    df = pd.DataFrame(categories)

    # Format columns
    display_columns = ['category_name', 'description', 'created_at']
    if 'created_at' in df.columns:
        df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')

    # Rename columns for display
    column_mapping = {
        'category_name': 'Category Name',
        'description': 'Description',
        'created_at': 'Created At'
    }

    # Select and rename columns
    available_columns = [col for col in display_columns if col in df.columns]
    df_display = df[available_columns].copy()
    df_display.columns = [column_mapping.get(col, col) for col in available_columns]

    # Display table
    st.dataframe(df_display, width='stretch', hide_index=True)

    # Show category usage statistics
    st.markdown("---")
    st.markdown("#### 📊 Category Usage")

    # Get items per category
    all_items = InventoryDB.get_all_master_items(active_only=False)
    if all_items:
        items_df = pd.DataFrame(all_items)
        if 'category' in items_df.columns:
            category_counts = items_df['category'].value_counts().reset_index()
            category_counts.columns = ['Category', 'Number of Items']
            st.dataframe(category_counts, width='stretch', hide_index=True)
        else:
            st.info("No items assigned to categories yet")
    else:
        st.info("No items found in inventory")


def show_add_category(username: str):
    """Add new category"""

    st.markdown("#### ➕ Add New Category")

    user_id = st.session_state.user.get('id') if 'user' in st.session_state and st.session_state.user else None

    with st.form("add_category_form", clear_on_submit=True):
        category_name = st.text_input(
            "Category Name *",
            placeholder="e.g., Fish Feed, Chemicals, Equipment",
            max_chars=100
        )

        description = st.text_area(
            "Description",
            placeholder="Brief description of this category",
            height=100,
            max_chars=500
        )

        st.markdown("---")
        submitted = st.form_submit_button("✅ Add Category", type="primary", width='stretch')

        if submitted:
            # Validation
            if not category_name or len(category_name.strip()) < 2:
                st.error("❌ Category name is required (minimum 2 characters)")
                return

            # Check if category already exists
            existing_categories = InventoryDB.get_categories()
            existing_names = [cat['category_name'].lower() for cat in existing_categories]

            if category_name.strip().lower() in existing_names:
                st.error(f"❌ Category '{category_name}' already exists")
                return

            # Add category
            success = InventoryDB.add_category(
                category_name=category_name,
                description=description if description else None,
                user_id=user_id
            )

            if success:
                st.success(f"✅ Category '{category_name}' added successfully!")

                # Log activity
                if 'user' in st.session_state and st.session_state.user:
                    ActivityLogger.log(
                        user_id=st.session_state.user['id'],
                        action_type='add_category',
                        module_key='inventory',
                        description=f"Added category: {category_name}",
                        metadata={'category_name': category_name}
                    )

                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Failed to add category. Please try again.")


def show_edit_category(username: str):
    """Edit existing category"""

    st.markdown("#### ✏️ Edit Category")

    categories = InventoryDB.get_categories()

    if not categories:
        st.warning("No categories found. Add a category first.")
        return

    # Category selection
    category_options = {cat['category_name']: cat for cat in categories}
    selected_name = st.selectbox(
        "Select Category",
        options=list(category_options.keys()),
        key="edit_category_select"
    )
    selected_category = category_options[selected_name]

    st.markdown("---")

    # Get item count for this category
    all_items = InventoryDB.get_all_master_items(active_only=False)
    item_count = 0
    if all_items:
        items_df = pd.DataFrame(all_items)
        if 'category' in items_df.columns:
            item_count = len(items_df[items_df['category'] == selected_category['category_name']])

    if item_count > 0:
        st.info(f"ℹ️ This category is currently used by {item_count} item(s)")

    with st.form("edit_category_form"):
        new_category_name = st.text_input(
            "Category Name *",
            value=selected_category.get('category_name', ''),
            max_chars=100
        )

        new_description = st.text_area(
            "Description",
            value=selected_category.get('description', '') or '',
            height=100,
            max_chars=500
        )

        st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:
            update_submitted = st.form_submit_button("💾 Update Category", type="primary", width='stretch')

        with col2:
            delete_submitted = st.form_submit_button("🗑️ Delete Category", type="secondary", width='stretch')

        if update_submitted:
            # Validation
            if not new_category_name or len(new_category_name.strip()) < 2:
                st.error("❌ Category name is required (minimum 2 characters)")
                return

            # Check if new name conflicts with existing (except current)
            existing_categories = InventoryDB.get_categories()
            for cat in existing_categories:
                if cat['id'] != selected_category['id'] and cat['category_name'].lower() == new_category_name.strip().lower():
                    st.error(f"❌ Category name '{new_category_name}' already exists")
                    return

            # Update category
            success = InventoryDB.update_category(
                category_id=selected_category['id'],
                category_name=new_category_name,
                description=new_description if new_description else None
            )

            if success:
                st.success(f"✅ Category updated successfully!")

                # Log activity
                if 'user' in st.session_state and st.session_state.user:
                    ActivityLogger.log(
                        user_id=st.session_state.user['id'],
                        action_type='update_category',
                        module_key='inventory',
                        description=f"Updated category: {selected_category['category_name']} → {new_category_name}",
                        metadata={
                            'old_name': selected_category['category_name'],
                            'new_name': new_category_name
                        }
                    )

                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Failed to update category")

        if delete_submitted:
            # Attempt to delete
            success = InventoryDB.delete_category(selected_category['id'])

            if success:
                st.success(f"✅ Category '{selected_category['category_name']}' deleted successfully!")

                # Log activity
                if 'user' in st.session_state and st.session_state.user:
                    ActivityLogger.log(
                        user_id=st.session_state.user['id'],
                        action_type='delete_category',
                        module_key='inventory',
                        description=f"Deleted category: {selected_category['category_name']}",
                        metadata={'category_name': selected_category['category_name']}
                    )

                time.sleep(1)
                st.rerun()
            # Error message is already shown by delete_category method
