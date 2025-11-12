"""
Public API for Inventory Management Module
Functions for cross-module communication (e.g., biofloc → inventory)

VERSION HISTORY:
1.0.0 - 2025-01-12 - Initial modular version
      - use_stock_item(): FIFO stock deduction
      - get_stock_level(): Current stock query
      - get_item_by_name(): Item lookup
      - add_stock_item(): Stock addition
      - Query operations for items, alerts, history

IMPORTANT: This is a PYTHON MODULE API, not a web API
- ✅ Other Python modules can import and use these functions
- ❌ NOT accessible over the internet
- Example usage: from modules.inventory import use_stock_item
"""

from typing import Dict, List, Optional
from datetime import datetime

from db.db_inventory import InventoryDB
from config.database import ActivityLogger


# =====================================================
# PUBLIC API - STOCK OPERATIONS
# =====================================================

def use_stock_item(
    item_id: int,
    quantity: float,
    user_id: str,
    purpose: str,
    notes: Optional[str] = None,
    batch_id: Optional[int] = None
) -> Dict:
    """
    PUBLIC API: Deduct stock from inventory (FIFO by default)

    Used by other modules (e.g., biofloc) to consume inventory items

    Args:
        item_id: ID of the item master
        quantity: Quantity to deduct
        user_id: UUID of the user performing the action
        purpose: Reason for using stock (e.g., "Fish feeding", "Lab testing")
        notes: Optional additional notes
        batch_id: Optional specific batch to use (otherwise uses FIFO)

    Returns:
        {
            'success': bool,
            'message': str,
            'transaction_id': int (if successful),
            'batches_used': List[Dict] (details of batches consumed)
        }

    Example:
        from modules.inventory import use_stock_item

        result = use_stock_item(
            item_id=42,
            quantity=5.0,
            user_id=current_user_id,
            purpose="Fish feeding - Pond A",
            notes="Daily feeding schedule"
        )

        if result['success']:
            print(f"Stock used successfully: {result['message']}")
        else:
            print(f"Error: {result['message']}")
    """
    try:
        # Use FIFO batch selection
        result = InventoryDB.use_stock(
            item_master_id=item_id,
            quantity=quantity,
            user_id=user_id,
            notes=f"{purpose} | {notes}" if notes else purpose,
            batch_id=batch_id
        )

        if result:
            # Log activity
            ActivityLogger.log(
                user_email=user_id,
                action="use_stock",
                details=f"Used {quantity} units of item {item_id} - {purpose}",
                module="inventory_api"
            )

            return {
                'success': True,
                'message': f'Successfully used {quantity} units',
                'transaction_id': result.get('transaction_id'),
                'batches_used': result.get('batches_used', [])
            }
        else:
            return {
                'success': False,
                'message': 'Failed to use stock - insufficient quantity or item not found',
                'transaction_id': None,
                'batches_used': []
            }

    except Exception as e:
        return {
            'success': False,
            'message': f'Error using stock: {str(e)}',
            'transaction_id': None,
            'batches_used': []
        }


def get_stock_level(item_id: int) -> Dict:
    """
    PUBLIC API: Get current stock level for an item

    Args:
        item_id: ID of the item master

    Returns:
        {
            'item_id': int,
            'item_name': str,
            'total_qty': float,
            'unit': str,
            'batches': List[Dict],
            'low_stock': bool
        }

    Example:
        from modules.inventory import get_stock_level

        stock = get_stock_level(item_id=42)
        print(f"{stock['item_name']}: {stock['total_qty']} {stock['unit']}")

        if stock['low_stock']:
            print("⚠️ Low stock alert!")
    """
    try:
        batches = InventoryDB.get_batches_by_item(item_id)

        if not batches:
            return {
                'item_id': item_id,
                'item_name': 'Unknown',
                'total_qty': 0,
                'unit': '',
                'batches': [],
                'low_stock': True
            }

        # Calculate total
        total_qty = sum(b.get('remaining_qty', 0) for b in batches if b.get('is_active'))

        # Get item details from first batch
        first_batch = batches[0]
        item_name = first_batch.get('item_name', 'Unknown')
        unit = first_batch.get('unit', '')
        reorder_threshold = first_batch.get('reorder_threshold', 0)

        return {
            'item_id': item_id,
            'item_name': item_name,
            'total_qty': total_qty,
            'unit': unit,
            'batches': batches,
            'low_stock': total_qty <= reorder_threshold
        }

    except Exception as e:
        return {
            'item_id': item_id,
            'item_name': 'Error',
            'total_qty': 0,
            'unit': '',
            'batches': [],
            'low_stock': True,
            'error': str(e)
        }


def get_item_by_name(item_name: str) -> Optional[Dict]:
    """
    PUBLIC API: Get item master details by name

    Args:
        item_name: Name of the item to search for

    Returns:
        Item master dict or None if not found
        {
            'id': int,
            'item_name': str,
            'category': str,
            'unit': str,
            'reorder_threshold': float,
            ...
        }

    Example:
        from modules.inventory import get_item_by_name

        item = get_item_by_name("Fish Feed - Premium")
        if item:
            stock = get_stock_level(item['id'])
    """
    try:
        items = InventoryDB.get_all_master_items(active_only=True)

        for item in items:
            if item.get('item_name', '').lower() == item_name.lower():
                return item

        return None

    except Exception as e:
        return None


def add_stock_item(
    item_id: int,
    quantity: float,
    unit_cost: float,
    supplier_id: int,
    user_id: str,
    batch_number: Optional[str] = None,
    expiry_date: Optional[str] = None,
    notes: Optional[str] = None
) -> Dict:
    """
    PUBLIC API: Add stock to inventory

    Args:
        item_id: ID of the item master
        quantity: Quantity to add
        unit_cost: Cost per unit
        supplier_id: ID of the supplier
        user_id: UUID of the user performing the action
        batch_number: Optional batch number
        expiry_date: Optional expiry date (YYYY-MM-DD)
        notes: Optional notes

    Returns:
        {
            'success': bool,
            'message': str,
            'batch_id': int (if successful)
        }

    Example:
        from modules.inventory import add_stock_item

        result = add_stock_item(
            item_id=42,
            quantity=100.0,
            unit_cost=25.50,
            supplier_id=5,
            user_id=current_user_id,
            notes="Received from supplier"
        )
    """
    try:
        batch_id = InventoryDB.add_stock(
            item_master_id=item_id,
            quantity=quantity,
            unit_cost=unit_cost,
            supplier_id=supplier_id,
            batch_number=batch_number,
            expiry_date=expiry_date,
            notes=notes
        )

        if batch_id:
            # Log activity
            ActivityLogger.log(
                user_email=user_id,
                action="add_stock",
                details=f"Added {quantity} units of item {item_id}",
                module="inventory_api"
            )

            return {
                'success': True,
                'message': f'Successfully added {quantity} units',
                'batch_id': batch_id
            }
        else:
            return {
                'success': False,
                'message': 'Failed to add stock',
                'batch_id': None
            }

    except Exception as e:
        return {
            'success': False,
            'message': f'Error adding stock: {str(e)}',
            'batch_id': None
        }


# =====================================================
# PUBLIC API - QUERY OPERATIONS
# =====================================================

def get_all_active_items() -> List[Dict]:
    """
    PUBLIC API: Get list of all active items

    Returns:
        List of active item master records

    Example:
        from modules.inventory import get_all_active_items

        items = get_all_active_items()
        for item in items:
            print(f"{item['item_name']} - {item['category']}")
    """
    try:
        return InventoryDB.get_all_master_items(active_only=True)
    except Exception as e:
        return []


def get_low_stock_items() -> List[Dict]:
    """
    PUBLIC API: Get list of items with low stock

    Returns:
        List of items below reorder threshold

    Example:
        from modules.inventory import get_low_stock_items

        low_items = get_low_stock_items()
        if low_items:
            print(f"⚠️ {len(low_items)} items need reordering")
    """
    try:
        return InventoryDB.get_low_stock_alerts()
    except Exception as e:
        return []


def get_expiring_items(days: int = 30) -> List[Dict]:
    """
    PUBLIC API: Get list of items expiring soon

    Args:
        days: Number of days to look ahead (default 30)

    Returns:
        List of batches expiring within specified days

    Example:
        from modules.inventory import get_expiring_items

        expiring = get_expiring_items(days=7)
        if expiring:
            print(f"⚠️ {len(expiring)} items expiring this week")
    """
    try:
        return InventoryDB.get_expiry_alerts(days=days)
    except Exception as e:
        return []


# =====================================================
# PUBLIC API - TRANSACTION HISTORY
# =====================================================

def get_item_transaction_history(item_id: int, limit: int = 100) -> List[Dict]:
    """
    PUBLIC API: Get transaction history for an item

    Args:
        item_id: ID of the item master
        limit: Maximum number of transactions to return

    Returns:
        List of transaction records

    Example:
        from modules.inventory import get_item_transaction_history

        history = get_item_transaction_history(item_id=42, limit=50)
        for tx in history:
            print(f"{tx['transaction_date']}: {tx['transaction_type']} - {tx['quantity']}")
    """
    try:
        all_history = InventoryDB.get_all_transactions()

        # Filter by item_id
        item_history = [
            tx for tx in all_history
            if tx.get('item_master_id') == item_id
        ]

        # Sort by date descending and limit
        item_history.sort(key=lambda x: x.get('transaction_date', ''), reverse=True)

        return item_history[:limit]

    except Exception as e:
        return []
