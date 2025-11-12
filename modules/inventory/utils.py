"""
Shared Utilities for Inventory Management Module
Cached data loaders, formatters, and common functions
"""

import streamlit as st
import pandas as pd
from typing import List, Dict, Optional
from io import BytesIO

from db.db_inventory import InventoryDB
from .constants import (
    CACHE_TTL_MASTER_DATA,
    CACHE_TTL_PO_DATA,
    PO_EXPORT_COLS_ADMIN,
    PO_EXPORT_COLS_USER,
    STATUS_EMOJIS,
    STATUS_COLORS
)


# =====================================================
# CACHED DATA LOADERS (Performance Optimization)
# =====================================================

@st.cache_data(ttl=CACHE_TTL_MASTER_DATA, show_spinner=False)
def get_master_items_cached(active_only: bool = True):
    """Cached wrapper for getting master items"""
    return InventoryDB.get_all_master_items(active_only=active_only)


@st.cache_data(ttl=CACHE_TTL_MASTER_DATA, show_spinner=False)
def get_suppliers_cached(active_only: bool = True):
    """Cached wrapper for getting suppliers"""
    return InventoryDB.get_all_suppliers(active_only=active_only)


@st.cache_data(ttl=CACHE_TTL_PO_DATA, show_spinner=False)
def get_purchase_orders_cached(status: str, days_back: int):
    """Cached wrapper for getting purchase orders"""
    if status == "All":
        return InventoryDB.get_all_purchase_orders(days_back=days_back)
    else:
        return InventoryDB.get_purchase_orders_by_status(status, days_back=days_back)


@st.cache_data(ttl=CACHE_TTL_PO_DATA, show_spinner=False)
def get_po_details_cached(po_id: int):
    """Cached wrapper for getting PO details by ID"""
    return InventoryDB.get_po_by_id(po_id)


@st.cache_data(ttl=CACHE_TTL_MASTER_DATA, show_spinner=False)
def get_categories_cached():
    """Cached wrapper for getting categories"""
    return InventoryDB.get_all_categories()


@st.cache_data(ttl=CACHE_TTL_PO_DATA, show_spinner=False)
def get_stock_batches_cached(item_id: int):
    """Cached wrapper for getting stock batches by item"""
    return InventoryDB.get_batches_by_item(item_id)


# =====================================================
# EXCEL GENERATION
# =====================================================

@st.cache_data(ttl=CACHE_TTL_PO_DATA, show_spinner=False)
def generate_pos_excel(pos: List[Dict], is_admin: bool) -> bytes:
    """Generate Excel file for purchase orders (cached)"""
    df_export = pd.DataFrame(pos)

    if is_admin:
        export_cols = PO_EXPORT_COLS_ADMIN
    else:
        export_cols = PO_EXPORT_COLS_USER

    export_cols = [col for col in export_cols if col in df_export.columns]
    df_export = df_export[export_cols].copy()

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_export.to_excel(writer, index=False, sheet_name='Purchase Orders')
    output.seek(0)

    return output.getvalue()


def generate_po_detail_excel(po: Dict) -> bytes:
    """Generate single PO Excel file with items"""
    po_number = po.get('po_number', 'Unknown')
    po_date = po.get('po_date', 'Unknown')
    supplier = po.get('supplier_name', 'Unknown')
    total_cost = po.get('total_cost', 0)
    notes = po.get('notes', '')
    created_by = po.get('created_by_name', 'Unknown')

    items = po.get('items', [])

    # Build single sheet with sections
    export_rows = []

    # PO Header Section
    export_rows.append({
        'Section': 'PO HEADER',
        'Field': 'PO Number',
        'Value': po_number,
        'Item': '',
        'Qty': '',
        'Unit': '',
        'Unit Cost': '',
        'Total': ''
    })
    export_rows.append({
        'Section': 'PO HEADER',
        'Field': 'Date',
        'Value': po_date,
        'Item': '',
        'Qty': '',
        'Unit': '',
        'Unit Cost': '',
        'Total': ''
    })
    export_rows.append({
        'Section': 'PO HEADER',
        'Field': 'Supplier',
        'Value': supplier,
        'Item': '',
        'Qty': '',
        'Unit': '',
        'Unit Cost': '',
        'Total': ''
    })
    export_rows.append({
        'Section': 'PO HEADER',
        'Field': 'Notes',
        'Value': notes,
        'Item': '',
        'Qty': '',
        'Unit': '',
        'Unit Cost': '',
        'Total': ''
    })
    export_rows.append({
        'Section': 'PO HEADER',
        'Field': 'Created By',
        'Value': created_by,
        'Item': '',
        'Qty': '',
        'Unit': '',
        'Unit Cost': '',
        'Total': ''
    })

    # Empty row
    export_rows.append({
        'Section': '',
        'Field': '',
        'Value': '',
        'Item': '',
        'Qty': '',
        'Unit': '',
        'Unit Cost': '',
        'Total': ''
    })

    # Items Header
    export_rows.append({
        'Section': 'ITEMS',
        'Field': '',
        'Value': '',
        'Item': 'Item Name',
        'Qty': 'Quantity',
        'Unit': 'Unit',
        'Unit Cost': 'Unit Cost (₹)',
        'Total': 'Total (₹)'
    })

    # Items Data
    for idx, item in enumerate(items, 1):
        item_name = item.get('item_name', 'Unknown')
        qty = item.get('ordered_qty', 0)
        unit = item.get('unit', '')
        unit_cost = item.get('unit_cost', 0)
        item_total = qty * unit_cost

        export_rows.append({
            'Section': 'ITEMS',
            'Field': f'Item {idx}',
            'Value': '',
            'Item': item_name,
            'Qty': qty,
            'Unit': unit,
            'Unit Cost': unit_cost,
            'Total': item_total
        })

    # Empty row
    export_rows.append({
        'Section': '',
        'Field': '',
        'Value': '',
        'Item': '',
        'Qty': '',
        'Unit': '',
        'Unit Cost': '',
        'Total': ''
    })

    # Totals Section
    total_qty = sum(item.get('ordered_qty', 0) for item in items)
    export_rows.append({
        'Section': 'TOTALS',
        'Field': 'Total Quantity',
        'Value': total_qty,
        'Item': '',
        'Qty': '',
        'Unit': '',
        'Unit Cost': '',
        'Total': ''
    })
    export_rows.append({
        'Section': 'TOTALS',
        'Field': 'Total Items',
        'Value': len(items),
        'Item': '',
        'Qty': '',
        'Unit': '',
        'Unit Cost': '',
        'Total': ''
    })
    export_rows.append({
        'Section': 'TOTALS',
        'Field': 'Grand Total',
        'Value': f'₹{total_cost:,.2f}',
        'Item': '',
        'Qty': '',
        'Unit': '',
        'Unit Cost': '',
        'Total': ''
    })

    # Create DataFrame
    df = pd.DataFrame(export_rows)

    # Export to Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Purchase Order', index=False)
    output.seek(0)

    return output.getvalue()


# =====================================================
# UI FORMATTERS
# =====================================================

def get_status_badge(status: str) -> str:
    """Generate colored badge for status display"""
    emoji = STATUS_EMOJIS.get(status, "❓")
    color = STATUS_COLORS.get(status, "#999999")

    return f'<span style="background-color: {color}; color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: bold;">{emoji} {status.upper()}</span>'


def format_currency(amount: float) -> str:
    """Format currency value with rupee symbol"""
    return f"₹{amount:,.2f}"


def format_date(date_value) -> str:
    """Format date value for display"""
    if date_value:
        return str(date_value)
    return "N/A"


# =====================================================
# SESSION STATE HELPERS
# =====================================================

def init_po_session_state():
    """Initialize session state for PO management"""
    if 'po_items' not in st.session_state:
        st.session_state.po_items = []

    if 'po_number_draft' not in st.session_state:
        from datetime import datetime
        st.session_state.po_number_draft = f"PO-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    if 'po_header_data' not in st.session_state:
        from datetime import date, timedelta
        st.session_state.po_header_data = {
            'po_number': st.session_state.po_number_draft,
            'supplier_name': None,
            'po_date': date.today(),
            'expected_delivery': date.today() + timedelta(days=7),
            'notes': ''
        }

    # Initialize delete confirmation states for POs
    if 'confirm_delete_states' not in st.session_state:
        st.session_state.confirm_delete_states = {}


def clear_po_cart():
    """Clear PO cart and reset"""
    st.session_state.po_items = []
    from datetime import datetime
    st.session_state.po_number_draft = f"PO-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    st.session_state.po_header_data = None


def refresh_data_cache():
    """Clear all cached data to force refresh"""
    get_master_items_cached.clear()
    get_suppliers_cached.clear()
    get_purchase_orders_cached.clear()
    get_po_details_cached.clear()
    get_categories_cached.clear()
    get_stock_batches_cached.clear()
