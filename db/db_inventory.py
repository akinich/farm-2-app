"""
Inventory Database Operations
Handles all database operations for inventory management

VERSION HISTORY:
1.0.0 - Initial inventory database helper - 08/11/25
      METHODS:
      - get_all_items() - Get all inventory items with optional filters
      - get_categories() - Get all inventory categories
      - get_low_stock_items() - Get items below reorder threshold
      - add_stock() - Add stock to an item
      - remove_stock() - Remove stock from an item
      - get_transactions() - Get transaction history
"""
import streamlit as st
from typing import List, Dict, Optional
from datetime import datetime, timedelta


class InventoryDB:
    """Inventory-related database operations"""
    
    @staticmethod
    def get_all_items(active_only: bool = False) -> List[Dict]:
        """
        Get all inventory items
        
        Args:
            active_only: If True, only return active items
            
        Returns:
            List of inventory item dictionaries
        """
        try:
            from config.database import Database
            db = Database.get_client()
            
            query = db.table('inventory_items').select('*').order('item_name')
            
            if active_only:
                query = query.eq('is_active', True)
            
            response = query.execute()
            return response.data if response.data else []
        
        except Exception as e:
            st.error(f"Error fetching inventory items: {str(e)}")
            return []
    
    @staticmethod
    def get_categories() -> List[Dict]:
        """Get all inventory categories"""
        try:
            from config.database import Database
            db = Database.get_client()
            
            response = db.table('inventory_categories') \
                .select('*') \
                .order('category_name') \
                .execute()
            
            return response.data if response.data else []
        
        except Exception as e:
            st.error(f"Error fetching categories: {str(e)}")
            return []
    
    @staticmethod
    def get_low_stock_items() -> List[Dict]:
        """Get items where current_qty <= reorder_threshold"""
        try:
            from config.database import Database
            db = Database.get_client()
            
            # Use RPC function for complex query
            response = db.rpc('get_low_stock_items').execute()
            
            # Fallback: Manual filtering
            if not response.data:
                all_items = InventoryDB.get_all_items(active_only=True)
                return [
                    item for item in all_items 
                    if item['current_qty'] <= item['reorder_threshold']
                ]
            
            return response.data
        
        except Exception as e:
            st.error(f"Error fetching low stock items: {str(e)}")
            return []
    
    @staticmethod
    def add_stock(item_id: int, quantity: float, user_id: str, 
                  notes: str = None) -> bool:
        """
        Add stock to an item and log transaction
        
        Args:
            item_id: Inventory item ID
            quantity: Quantity to add
            user_id: User performing the action
            notes: Optional notes
            
        Returns:
            True if successful
        """
        try:
            from config.database import Database
            db = Database.get_client()
            
            # Get current item
            item_response = db.table('inventory_items') \
                .select('current_qty') \
                .eq('id', item_id) \
                .single() \
                .execute()
            
            if not item_response.data:
                st.error("Item not found")
                return False
            
            current_qty = item_response.data['current_qty']
            new_qty = current_qty + quantity
            
            # Update item quantity
            db.table('inventory_items') \
                .update({
                    'current_qty': new_qty,
                    'last_restocked': datetime.now().isoformat()
                }) \
                .eq('id', item_id) \
                .execute()
            
            # Log transaction
            db.table('inventory_transactions').insert({
                'item_id': item_id,
                'transaction_type': 'add',
                'quantity_change': quantity,
                'new_balance': new_qty,
                'user_id': user_id,
                'notes': notes
            }).execute()
            
            return True
        
        except Exception as e:
            st.error(f"Error adding stock: {str(e)}")
            return False
    
    @staticmethod
    def remove_stock(item_id: int, quantity: float, module_reference: str,
                     user_id: str, notes: str = None) -> bool:
        """
        Remove stock from an item and log transaction
        
        Args:
            item_id: Inventory item ID
            quantity: Quantity to remove
            module_reference: Which module is using this item
            user_id: User performing the action
            notes: Optional notes
            
        Returns:
            True if successful
        """
        try:
            from config.database import Database
            db = Database.get_client()
            
            # Get current item
            item_response = db.table('inventory_items') \
                .select('current_qty') \
                .eq('id', item_id) \
                .single() \
                .execute()
            
            if not item_response.data:
                st.error("Item not found")
                return False
            
            current_qty = item_response.data['current_qty']
            
            if quantity > current_qty:
                st.error(f"Insufficient stock. Available: {current_qty}")
                return False
            
            new_qty = current_qty - quantity
            
            # Update item quantity
            db.table('inventory_items') \
                .update({'current_qty': new_qty}) \
                .eq('id', item_id) \
                .execute()
            
            # Log transaction
            db.table('inventory_transactions').insert({
                'item_id': item_id,
                'transaction_type': 'remove',
                'quantity_change': -quantity,
                'new_balance': new_qty,
                'module_reference': module_reference,
                'user_id': user_id,
                'notes': notes
            }).execute()
            
            return True
        
        except Exception as e:
            st.error(f"Error removing stock: {str(e)}")
            return False
    
    @staticmethod
    def get_transactions(days: int = 30, item_id: int = None) -> List[Dict]:
        """
        Get transaction history
        
        Args:
            days: Number of days to look back
            item_id: Optional filter by item ID
            
        Returns:
            List of transaction dictionaries
        """
        try:
            from config.database import Database
            db = Database.get_client()
            
            since_date = datetime.now() - timedelta(days=days)
            
            query = db.table('inventory_transactions') \
                .select('*, inventory_items(item_name, unit)') \
                .gte('transaction_date', since_date.isoformat()) \
                .order('transaction_date', desc=True)
            
            if item_id:
                query = query.eq('item_id', item_id)
            
            response = query.execute()
            return response.data if response.data else []
        
        except Exception as e:
            st.error(f"Error fetching transactions: {str(e)}")
            return []
    
    @staticmethod
    def add_item(item_data: Dict, user_id: str) -> bool:
        """
        Add a new inventory item (admin only)
        
        Args:
            item_data: Dictionary with item details
            user_id: User creating the item
            
        Returns:
            True if successful
        """
        try:
            from config.database import Database
            db = Database.get_client()
            
            item_data['created_by'] = user_id
            
            db.table('inventory_items').insert(item_data).execute()
            return True
        
        except Exception as e:
            st.error(f"Error adding item: {str(e)}")
            return False
    
    @staticmethod
    def update_item(item_id: int, updates: Dict) -> bool:
        """
        Update an inventory item
        
        Args:
            item_id: Item ID to update
            updates: Dictionary of fields to update
            
        Returns:
            True if successful
        """
        try:
            from config.database import Database
            db = Database.get_client()
            
            db.table('inventory_items') \
                .update(updates) \
                .eq('id', item_id) \
                .execute()
            
            return True
        
        except Exception as e:
            st.error(f"Error updating item: {str(e)}")
            return False
