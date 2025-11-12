"""
Constants for Inventory Management Module
Centralized configuration and shared constants
"""

# =====================================================
# CACHE TTL (Time To Live) Settings
# =====================================================

CACHE_TTL_MASTER_DATA = 300  # 5 minutes for master items, suppliers, categories
CACHE_TTL_PO_DATA = 60       # 1 minute for purchase orders
CACHE_TTL_STOCK_DATA = 60    # 1 minute for stock/batches


# =====================================================
# STATUS VALUES
# =====================================================

# Purchase Order Statuses
PO_STATUS_PENDING = "pending"
PO_STATUS_APPROVED = "approved"
PO_STATUS_RECEIVED = "received"
PO_STATUS_CANCELLED = "cancelled"
PO_STATUSES = ["All", PO_STATUS_PENDING, PO_STATUS_APPROVED, PO_STATUS_RECEIVED, PO_STATUS_CANCELLED]

# Batch/Stock Statuses
BATCH_ACTIVE = True
BATCH_INACTIVE = False

# Transaction Types
TX_TYPE_ADD = "add"
TX_TYPE_USE = "use"
TX_TYPE_ADJUST = "adjust"
TX_TYPE_RECEIVE = "receive"


# =====================================================
# PAGINATION SETTINGS
# =====================================================

PO_PAGE_SIZE = 20  # Number of POs per page


# =====================================================
# DATE RANGES
# =====================================================

DEFAULT_PO_DAYS_BACK = 90
DEFAULT_DELIVERY_DAYS = 7


# =====================================================
# COLUMN MAPPINGS
# =====================================================

# Purchase Order Export Columns
PO_EXPORT_COLS_ADMIN = [
    'po_number', 'item_name', 'supplier_name', 'quantity',
    'unit_cost', 'total_cost', 'po_date', 'status', 'created_by'
]

PO_EXPORT_COLS_USER = [
    'po_number', 'item_name', 'supplier_name', 'quantity',
    'po_date', 'status', 'created_by'
]


# =====================================================
# UI LABELS
# =====================================================

MODULE_TITLE = "📦 Inventory Management"

# Tab Names - User Operations
TAB_DASHBOARD = "📊 Dashboard"
TAB_CURRENT_STOCK = "📦 Current Stock"
TAB_ADD_STOCK = "➕ Add Stock"
TAB_ADJUSTMENTS = "🔄 Adjustments"
TAB_PURCHASE_ORDERS = "🛒 Purchase Orders"
TAB_ALERTS = "🔔 Alerts"
TAB_HISTORY = "📜 History"

# Tab Names - Admin Configuration
TAB_ITEM_MASTER = "📋 Item Master"
TAB_CATEGORIES = "🏷️ Categories"
TAB_SUPPLIERS = "🏭 Suppliers"
TAB_ANALYTICS = "📊 Analytics"


# =====================================================
# STATUS BADGE EMOJIS
# =====================================================

STATUS_EMOJIS = {
    PO_STATUS_PENDING: "⏳",
    PO_STATUS_APPROVED: "✅",
    PO_STATUS_RECEIVED: "📦",
    PO_STATUS_CANCELLED: "❌"
}

STATUS_COLORS = {
    PO_STATUS_PENDING: "#FFA500",    # Orange
    PO_STATUS_APPROVED: "#4CAF50",   # Green
    PO_STATUS_RECEIVED: "#2196F3",   # Blue
    PO_STATUS_CANCELLED: "#F44336"   # Red
}
