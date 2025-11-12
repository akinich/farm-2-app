"""
Inventory Management Module
Complete inventory system with batch tracking, FIFO, expiry management, and cost tracking

PUBLIC API for cross-module communication:
- use_stock_item(): Deduct stock from inventory
- add_stock_item(): Add stock to inventory
- get_stock_level(): Get current stock level
- get_item_by_name(): Find item by name
- get_all_active_items(): Get list of all active items
- get_low_stock_items(): Get items needing reorder
- get_expiring_items(): Get items expiring soon
- get_item_transaction_history(): Get transaction history

Example usage from another module (e.g., biofloc):
    from modules.inventory import use_stock_item, get_stock_level

    # Check stock level
    stock = get_stock_level(item_id=42)
    if stock['total_qty'] >= 5.0:
        # Use stock
        result = use_stock_item(
            item_id=42,
            quantity=5.0,
            user_id=current_user_id,
            purpose="Fish feeding - Pond A"
        )
        if result['success']:
            print("Stock used successfully")
"""

# Export public API functions
from .api import (
    use_stock_item,
    add_stock_item,
    get_stock_level,
    get_item_by_name,
    get_all_active_items,
    get_low_stock_items,
    get_expiring_items,
    get_item_transaction_history
)

# Version
__version__ = "3.0.0"

# Public API list (for documentation)
__all__ = [
    'use_stock_item',
    'add_stock_item',
    'get_stock_level',
    'get_item_by_name',
    'get_all_active_items',
    'get_low_stock_items',
    'get_expiring_items',
    'get_item_transaction_history',
]
