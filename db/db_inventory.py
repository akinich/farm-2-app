"""
Inventory Database Operations V2.1.1
Fixed foreign key constraint issues with category management

VERSION HISTORY:
2.1.1 - Fixed category foreign key constraint violations - 10/11/25
      ADDITIONS:
      - ensure_category_exists() - Auto-create categories in inventory_categories table
      CHANGES:
      - add_master_item() - Now ensures category exists before insert
      - update_master_item() - Now validates category exists before update
      FIXES:
      - Resolved "item_master_category_fkey" foreign key constraint errors

2.1.0 - Added missing helper methods for UI compatibility - 10/11/25
      ADDITIONS:
      - get_inventory_summary() - Dashboard summary statistics
      - get_recent_transactions() - Recent transaction wrapper
      - get_all_categories() - Category list helper
      - get_recent_adjustments() - Recent adjustments wrapper
      - get_all_purchase_orders() - PO list wrapper
      - get_purchase_orders_by_status() - Filtered PO wrapper
      - create_purchase_order() - Simplified PO creation
      - get_transaction_history() - History wrapper with filters
      - get_module_consumption() - Module consumption wrapper
      - get_all_suppliers() - Supplier list wrapper (alias)
      FIXES:
      - All methods now compatible with inventory.py v2.1.0
      - Preserved all v2.0.0 functionality
      
2.0.0 - Complete architectural rebuild - 10/11/25
      NEW ARCHITECTURE:
      - Item Master List (templates, no stock qty)
      - Inventory Batches (actual stock with FIFO)
      - Auto-update current_qty via triggers
      - FIFO cost tracking for production costing
      - Batch traceability reports
      - Module integration functions
      - Physical verification reports
      
      KEY METHODS:
      - get_items_with_stock() - Items that have available stock
      - add_stock_batch() - Add new batch with cost tracking
      - deduct_stock_fifo() - Auto FIFO deduction with cost return
      - get_batch_lifecycle() - Complete batch traceability
      - generate_verification_report() - Physical stock audit
"""
import streamlit as st
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta, date
from config.database import Database


class InventoryDB:
    """Complete inventory database operations"""
    
    # =====================================================
    # ITEM MASTER LIST (Templates)
    # =====================================================
    
    @staticmethod
    def get_all_master_items(active_only: bool = True) -> List[Dict]:
        """Get all items from master list"""
        try:
            db = Database.get_client()
            
            query = db.table('item_master') \
                .select('*, suppliers(supplier_name)') \
                .order('item_name')
            
            if active_only:
                query = query.eq('is_active', True)
            
            response = query.execute()
            
            # Flatten supplier
            items = response.data if response.data else []
            for item in items:
                if item.get('suppliers'):
                    item['supplier_name'] = item['suppliers']['supplier_name']
                else:
                    item['supplier_name'] = ''
                
                # Add stock status
                if item['current_qty'] <= item.get('min_stock_level', 0):
                    item['stock_status'] = 'critical'
                elif item['current_qty'] <= item['reorder_threshold']:
                    item['stock_status'] = 'low'
                else:
                    item['stock_status'] = 'good'
            
            return items
        
        except Exception as e:
            st.error(f"Error fetching master items: {str(e)}")
            return []
    
    @staticmethod
    def get_items_with_stock() -> List[Dict]:
        """
        Get only items that have available stock
        Used for: Biofloc dropdown, Remove Stock dropdown
        """
        try:
            db = Database.get_client()
            
            response = db.table('item_master') \
                .select('id, item_name, sku, category, unit, current_qty') \
                .eq('is_active', True) \
                .gt('current_qty', 0) \
                .order('item_name') \
                .execute()
            
            return response.data if response.data else []
        
        except Exception as e:
            st.error(f"Error fetching items with stock: {str(e)}")
            return []
    
    @staticmethod
    def ensure_category_exists(category_name: str) -> bool:
        """
        Ensure a category exists in inventory_categories table.
        Creates it if it doesn't exist.

        Args:
            category_name: Name of the category to ensure exists

        Returns:
            bool: True if category exists or was created successfully
        """
        try:
            db = Database.get_client()

            # Check if category already exists
            existing = db.table('inventory_categories') \
                .select('category_name') \
                .eq('category_name', category_name) \
                .execute()

            if existing.data:
                return True

            # Create new category
            db.table('inventory_categories').insert({
                'category_name': category_name
            }).execute()

            return True

        except Exception as e:
            # If it's a duplicate key error, category exists - that's fine
            if '23505' in str(e) or 'duplicate key' in str(e).lower():
                return True
            st.error(f"Error ensuring category exists: {str(e)}")
            return False

    @staticmethod
    def add_master_item(item_data: Dict = None, user_id: str = None, **kwargs) -> bool:
        """
        Add new item to master list (admin only)
        Supports both dict and keyword arguments for compatibility
        """
        try:
            db = Database.get_client()

            # Handle both calling styles
            if item_data is None:
                item_data = kwargs

            item_data['created_by'] = user_id or kwargs.get('username')
            item_data['current_qty'] = 0  # Always starts at 0

            # Remove username if present (not a database column)
            item_data.pop('username', None)

            # Ensure category exists before inserting
            if 'category' in item_data and item_data['category']:
                if not InventoryDB.ensure_category_exists(item_data['category']):
                    st.error("Failed to create category. Please try again.")
                    return False

            db.table('item_master').insert(item_data).execute()
            return True

        except Exception as e:
            st.error(f"Error adding master item: {str(e)}")
            return False
    
    @staticmethod
    def update_master_item(item_id: int = None, updates: Dict = None, item_master_id: int = None, **kwargs) -> bool:
        """
        Update master item details
        Supports both v2.0.0 and v2.1.0 calling styles
        """
        try:
            db = Database.get_client()

            # Handle different parameter names
            item_id = item_id or item_master_id
            if updates is None:
                updates = kwargs

            updates['updated_at'] = datetime.now().isoformat()

            # Remove non-database fields
            updates.pop('username', None)
            updates.pop('item_master_id', None)

            # Ensure category exists if being updated
            if 'category' in updates and updates['category']:
                if not InventoryDB.ensure_category_exists(updates['category']):
                    st.error("Failed to create category. Please try again.")
                    return False

            db.table('item_master') \
                .update(updates) \
                .eq('id', item_id) \
                .execute()

            return True

        except Exception as e:
            st.error(f"Error updating master item: {str(e)}")
            return False
    
    @staticmethod
    def delete_master_item(item_id: int) -> bool:
        """Delete master item (admin only)"""
        try:
            db = Database.get_client()
            
            db.table('item_master').delete().eq('id', item_id).execute()
            return True
        
        except Exception as e:
            st.error(f"Error deleting master item: {str(e)}")
            return False
    
    # =====================================================
    # INVENTORY BATCHES (Actual Stock)
    # =====================================================
    
    @staticmethod
    def get_all_batches(item_master_id: int = None, active_only: bool = True) -> List[Dict]:
        """Get all inventory batches"""
        try:
            db = Database.get_client()
            
            query = db.table('inventory_batches') \
                .select('*, item_master(item_name, sku, unit, category), suppliers(supplier_name)') \
                .order('purchase_date', desc=True)
            
            if item_master_id:
                query = query.eq('item_master_id', item_master_id)
            
            if active_only:
                query = query.eq('is_active', True).gt('remaining_qty', 0)
            
            response = query.execute()
            
            # Flatten nested data
            batches = response.data if response.data else []
            for batch in batches:
                if batch.get('item_master'):
                    batch['item_name'] = batch['item_master']['item_name']
                    batch['sku'] = batch['item_master'].get('sku', '')
                    batch['unit'] = batch['item_master']['unit']
                    batch['category'] = batch['item_master'].get('category', '')
                
                if batch.get('suppliers'):
                    batch['supplier_name'] = batch['suppliers']['supplier_name']
                else:
                    batch['supplier_name'] = ''
                
                # Calculate value
                batch['batch_value'] = batch['remaining_qty'] * batch['unit_cost']
                
                # Add quantity alias for compatibility
                batch['quantity'] = batch.get('quantity_purchased', batch['remaining_qty'])
                
                # Add status
                if batch['remaining_qty'] <= 0:
                    batch['status'] = 'depleted'
                elif batch.get('expiry_date'):
                    expiry = datetime.fromisoformat(str(batch['expiry_date'])).date() if isinstance(batch['expiry_date'], str) else batch['expiry_date']
                    if expiry < date.today():
                        batch['status'] = 'expired'
                    elif expiry <= date.today() + timedelta(days=7):
                        batch['status'] = 'expiring_soon'
                    else:
                        batch['status'] = 'active'
                else:
                    batch['status'] = 'active'
            
            return batches
        
        except Exception as e:
            st.error(f"Error fetching batches: {str(e)}")
            return []
    
    @staticmethod
    def add_stock_batch(
        item_master_id: int,
        batch_number: str,
        quantity: float,
        unit_cost: float,
        purchase_date: date,
        expiry_date: date = None,
        supplier_id: int = None,
        supplier_name: str = None,
        user_id: str = None,
        username: str = None,
        po_number: str = None,
        notes: str = None
    ) -> bool:
        """
        Add new stock batch
        Trigger auto-updates item_master.current_qty
        """
        try:
            db = Database.get_client()
            
            # Get supplier_id from name if provided
            if supplier_name and not supplier_id:
                supplier_response = db.table('suppliers') \
                    .select('id') \
                    .eq('supplier_name', supplier_name) \
                    .execute()
                
                if supplier_response.data:
                    supplier_id = supplier_response.data[0]['id']
            
            # Insert batch
            batch_data = {
                'item_master_id': item_master_id,
                'batch_number': batch_number,
                'quantity_purchased': quantity,
                'remaining_qty': quantity,
                'unit_cost': unit_cost,
                'purchase_date': purchase_date.isoformat() if isinstance(purchase_date, date) else purchase_date,
                'expiry_date': expiry_date.isoformat() if expiry_date and isinstance(expiry_date, date) else expiry_date,
                'supplier_id': supplier_id,
                'po_number': po_number,
                'notes': notes,
                'added_by': user_id,
                'is_active': True
            }
            
            batch_response = db.table('inventory_batches').insert(batch_data).execute()
            
            if not batch_response.data:
                return False
            
            batch_id = batch_response.data[0]['id']
            
            # Get new balance (trigger will update item_master.current_qty)
            item_response = db.table('item_master') \
                .select('current_qty') \
                .eq('id', item_master_id) \
                .single() \
                .execute()
            
            new_balance = item_response.data['current_qty'] if item_response.data else quantity
            
            # Log transaction
            db.table('inventory_transactions').insert({
                'item_master_id': item_master_id,
                'batch_id': batch_id,
                'transaction_type': 'add',
                'quantity_change': quantity,
                'new_balance': new_balance,
                'unit_cost': unit_cost,
                'total_cost': quantity * unit_cost,
                'po_number': po_number,
                'user_id': user_id,
                'username': username,
                'notes': notes
            }).execute()
            
            return True
        
        except Exception as e:
            st.error(f"Error adding stock batch: {str(e)}")
            return False
    
    @staticmethod
    def deduct_stock_fifo(
        item_master_id: int,
        quantity: float,
        module_reference: str,
        user_id: str,
        username: str,
        tank_id: int = None,
        cycle_id: int = None,
        notes: str = None
    ) -> Dict:
        """
        Deduct stock using FIFO logic
        Returns cost information for module costing
        
        Returns:
            {
                'success': bool,
                'quantity_deducted': float,
                'batches_used': [{'batch_id', 'batch_number', 'qty_from_batch', 'unit_cost'}],
                'total_cost': float,
                'weighted_avg_cost': float,
                'remaining_stock': float,
                'transaction_ids': [int]
            }
        """
        try:
            db = Database.get_client()
            
            # Get available batches (FIFO - oldest first)
            batches_response = db.table('inventory_batches') \
                .select('id, batch_number, remaining_qty, unit_cost') \
                .eq('item_master_id', item_master_id) \
                .eq('is_active', True) \
                .gt('remaining_qty', 0) \
                .order('purchase_date') \
                .execute()
            
            if not batches_response.data:
                st.error("No stock available")
                return {'success': False, 'error': 'No stock available'}
            
            batches = batches_response.data
            total_available = sum(b['remaining_qty'] for b in batches)
            
            if quantity > total_available:
                st.error(f"Insufficient stock. Available: {total_available}")
                return {'success': False, 'error': 'Insufficient stock'}
            
            # Deduct from batches (FIFO)
            remaining_to_deduct = quantity
            batches_used = []
            transaction_ids = []
            total_cost = 0
            
            for batch in batches:
                if remaining_to_deduct <= 0:
                    break
                
                qty_from_batch = min(remaining_to_deduct, batch['remaining_qty'])
                cost_from_batch = qty_from_batch * batch['unit_cost']
                
                # Update batch
                new_batch_qty = batch['remaining_qty'] - qty_from_batch
                db.table('inventory_batches') \
                    .update({'remaining_qty': new_batch_qty}) \
                    .eq('id', batch['id']) \
                    .execute()
                
                # Get new item balance
                item_response = db.table('item_master') \
                    .select('current_qty') \
                    .eq('id', item_master_id) \
                    .single() \
                    .execute()
                
                new_balance = item_response.data['current_qty'] if item_response.data else 0
                
                # Log transaction
                tx_response = db.table('inventory_transactions').insert({
                    'item_master_id': item_master_id,
                    'batch_id': batch['id'],
                    'transaction_type': 'remove',
                    'quantity_change': -qty_from_batch,
                    'new_balance': new_balance,
                    'unit_cost': batch['unit_cost'],
                    'total_cost': cost_from_batch,
                    'module_reference': module_reference,
                    'tank_id': tank_id,
                    'cycle_id': cycle_id,
                    'user_id': user_id,
                    'username': username,
                    'notes': notes
                }).execute()
                
                transaction_ids.append(tx_response.data[0]['id'])
                
                batches_used.append({
                    'batch_id': batch['id'],
                    'batch_number': batch['batch_number'],
                    'qty_from_batch': qty_from_batch,
                    'unit_cost': batch['unit_cost'],
                    'cost': cost_from_batch
                })
                
                total_cost += cost_from_batch
                remaining_to_deduct -= qty_from_batch
            
            # Calculate weighted average cost
            weighted_avg_cost = total_cost / quantity if quantity > 0 else 0
            
            # Get final remaining stock
            final_response = db.table('item_master') \
                .select('current_qty') \
                .eq('id', item_master_id) \
                .single() \
                .execute()
            
            remaining_stock = final_response.data['current_qty'] if final_response.data else 0
            
            return {
                'success': True,
                'quantity_deducted': quantity,
                'batches_used': batches_used,
                'total_cost': total_cost,
                'weighted_avg_cost': weighted_avg_cost,
                'remaining_stock': remaining_stock,
                'transaction_ids': transaction_ids
            }
        
        except Exception as e:
            st.error(f"Error deducting stock: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def log_adjustment(
        item_master_id: int,
        adjustment_type: str,
        quantity: float,
        reason: str,
        user_id: str = None,
        username: str = None,
        batch_id: int = None,
        reference_id: str = None,
        adjustment_date: date = None,
        notes: str = None
    ) -> bool:
        """Log stock adjustment (wastage, damage, etc.)"""
        try:
            db = Database.get_client()
            
            # Get batch info if specified
            if batch_id:
                batch_response = db.table('inventory_batches') \
                    .select('remaining_qty, unit_cost') \
                    .eq('id', batch_id) \
                    .single() \
                    .execute()
                
                if batch_response.data:
                    old_batch_qty = batch_response.data['remaining_qty']
                    unit_cost = batch_response.data['unit_cost']
                    new_batch_qty = old_batch_qty - abs(quantity)
                    
                    # Update batch
                    db.table('inventory_batches') \
                        .update({'remaining_qty': new_batch_qty}) \
                        .eq('id', batch_id) \
                        .execute()
            else:
                unit_cost = 0
            
            # Get item quantities
            item_response = db.table('item_master') \
                .select('current_qty') \
                .eq('id', item_master_id) \
                .single() \
                .execute()
            
            old_qty = item_response.data['current_qty'] if item_response.data else 0
            new_qty = old_qty - abs(quantity)
            
            # Log adjustment
            adjustment_data = {
                'item_master_id': item_master_id,
                'batch_id': batch_id,
                'adjustment_type': adjustment_type,
                'quantity_adjusted': -abs(quantity),
                'old_qty': old_qty,
                'new_qty': new_qty,
                'reason': reason,
                'adjusted_by': user_id,
                'username': username,
                'notes': notes or reason
            }
            
            if adjustment_date:
                adjustment_data['adjustment_date'] = adjustment_date.isoformat() if isinstance(adjustment_date, date) else adjustment_date
            
            db.table('stock_adjustments').insert(adjustment_data).execute()
            
            # Log transaction
            db.table('inventory_transactions').insert({
                'item_master_id': item_master_id,
                'batch_id': batch_id,
                'transaction_type': 'adjustment',
                'quantity_change': -abs(quantity),
                'new_balance': new_qty,
                'unit_cost': unit_cost,
                'total_cost': abs(quantity) * unit_cost if unit_cost else 0,
                'adjustment_reason': adjustment_type,
                'user_id': user_id,
                'username': username,
                'notes': f"{adjustment_type}: {reason}"
            }).execute()
            
            return True
        
        except Exception as e:
            st.error(f"Error logging adjustment: {str(e)}")
            return False
    
    # =====================================================
    # CATEGORIES & SUPPLIERS
    # =====================================================
    
    @staticmethod
    def get_categories() -> List[Dict]:
        """Get all categories"""
        try:
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
    def get_all_categories() -> List[str]:
        """
        Get list of category names (for UI dropdowns)
        NEW in v2.1.0
        """
        try:
            db = Database.get_client()
            
            # Get unique categories from item_master
            response = db.table('item_master') \
                .select('category') \
                .execute()
            
            if response.data:
                categories = list(set([item['category'] for item in response.data if item.get('category')]))
                return sorted(categories)
            
            return []
        
        except Exception as e:
            st.error(f"Error fetching categories: {str(e)}")
            return []
    
    @staticmethod
    def get_suppliers(active_only: bool = True) -> List[Dict]:
        """Get all suppliers"""
        try:
            db = Database.get_client()
            
            query = db.table('suppliers').select('*').order('supplier_name')
            
            if active_only:
                query = query.eq('is_active', True)
            
            response = query.execute()
            return response.data if response.data else []
        
        except Exception as e:
            st.error(f"Error fetching suppliers: {str(e)}")
            return []
    
    @staticmethod
    def get_all_suppliers(active_only: bool = True) -> List[Dict]:
        """
        Alias for get_suppliers (for UI compatibility)
        NEW in v2.1.0
        """
        return InventoryDB.get_suppliers(active_only=active_only)
    
    @staticmethod
    def add_supplier(supplier_data: Dict = None, **kwargs) -> bool:
        """Add new supplier"""
        try:
            db = Database.get_client()
            
            # Handle both calling styles
            if supplier_data is None:
                supplier_data = kwargs
            
            # Remove non-database fields
            supplier_data.pop('username', None)
            
            db.table('suppliers').insert(supplier_data).execute()
            return True
        
        except Exception as e:
            st.error(f"Error adding supplier: {str(e)}")
            return False
    
    @staticmethod
    def update_supplier(supplier_id: int, updates: Dict) -> bool:
        """Update supplier info"""
        try:
            db = Database.get_client()
            
            db.table('suppliers') \
                .update(updates) \
                .eq('id', supplier_id) \
                .execute()
            
            return True
        
        except Exception as e:
            st.error(f"Error updating supplier: {str(e)}")
            return False
    
    # =====================================================
    # ALERTS
    # =====================================================
    
    @staticmethod
    def get_low_stock_items() -> List[Dict]:
        """Get items below reorder threshold"""
        try:
            db = Database.get_client()
            
            response = db.rpc('get_low_stock_items').execute()
            return response.data if response.data else []
        
        except Exception as e:
            st.error(f"Error fetching low stock items: {str(e)}")
            return []
    
    @staticmethod
    def get_expiring_items(days_ahead: int = 30) -> List[Dict]:
        """Get items expiring in next X days"""
        try:
            db = Database.get_client()
            
            response = db.rpc('get_expiring_items', {'days_ahead': days_ahead}).execute()
            return response.data if response.data else []
        
        except Exception as e:
            st.error(f"Error fetching expiring items: {str(e)}")
            return []
    
    # =====================================================
    # TRANSACTIONS & HISTORY
    # =====================================================
    
    @staticmethod
    def get_transactions(
        days: int = 30,
        item_master_id: int = None,
        transaction_type: str = None,
        module: str = None
    ) -> List[Dict]:
        """Get transaction history"""
        try:
            db = Database.get_client()
            
            since_date = datetime.now() - timedelta(days=days)
            
            query = db.table('inventory_transactions') \
                .select('*, item_master(item_name, sku, unit), inventory_batches(batch_number)') \
                .gte('transaction_date', since_date.isoformat()) \
                .order('transaction_date', desc=True)
            
            if item_master_id:
                query = query.eq('item_master_id', item_master_id)
            
            if transaction_type:
                query = query.eq('transaction_type', transaction_type)
            
            if module:
                query = query.eq('module_reference', module)
            
            response = query.execute()
            
            # Flatten nested data
            txs = response.data if response.data else []
            for tx in txs:
                if tx.get('item_master'):
                    tx['item_name'] = tx['item_master']['item_name']
                    tx['sku'] = tx['item_master'].get('sku', '')
                    tx['unit'] = tx['item_master']['unit']
                
                if tx.get('inventory_batches'):
                    tx['batch_number'] = tx['inventory_batches']['batch_number']
                else:
                    tx['batch_number'] = ''
                
                # Add aliases for compatibility
                tx['quantity'] = abs(tx.get('quantity_change', 0))
                tx['reference'] = tx.get('module_reference') or tx.get('po_number') or ''
                tx['performed_by'] = tx.get('username', 'Unknown')
            
            return txs
        
        except Exception as e:
            st.error(f"Error fetching transactions: {str(e)}")
            return []
    
    @staticmethod
    def get_recent_transactions(limit: int = 10) -> List[Dict]:
        """
        Get recent transactions (wrapper for UI)
        NEW in v2.1.0
        """
        transactions = InventoryDB.get_transactions(days=7)
        return transactions[:limit] if transactions else []
    
    @staticmethod
    def get_transaction_history(
        days_back: int = 30,
        transaction_type: str = None,
        item_name: str = None
    ) -> List[Dict]:
        """
        Get filtered transaction history (wrapper for UI)
        NEW in v2.1.0
        """
        try:
            transactions = InventoryDB.get_transactions(days=days_back, transaction_type=transaction_type)
            
            # Filter by item name if provided
            if item_name:
                transactions = [t for t in transactions if t.get('item_name') == item_name]
            
            return transactions
        
        except Exception as e:
            st.error(f"Error fetching transaction history: {str(e)}")
            return []
    
    @staticmethod
    def get_adjustments(days: int = 30) -> List[Dict]:
        """Get adjustment history"""
        try:
            db = Database.get_client()
            
            since_date = datetime.now() - timedelta(days=days)
            
            response = db.table('stock_adjustments') \
                .select('*, item_master(item_name, unit)') \
                .gte('adjustment_date', since_date.date().isoformat()) \
                .order('adjustment_date', desc=True) \
                .execute()
            
            # Flatten
            adjustments = response.data if response.data else []
            for adj in adjustments:
                if adj.get('item_master'):
                    adj['item_name'] = adj['item_master']['item_name']
                    adj['unit'] = adj['item_master']['unit']
                
                # Add aliases
                adj['quantity'] = abs(adj.get('quantity_adjusted', 0))
                adj['performed_by'] = adj.get('username', 'Unknown')
            
            return adjustments
        
        except Exception as e:
            st.error(f"Error fetching adjustments: {str(e)}")
            return []
    
    @staticmethod
    def get_recent_adjustments(limit: int = 20) -> List[Dict]:
        """
        Get recent adjustments (wrapper for UI)
        NEW in v2.1.0
        """
        adjustments = InventoryDB.get_adjustments(days=30)
        return adjustments[:limit] if adjustments else []
    
    # =====================================================
    # BATCH TRACEABILITY
    # =====================================================
    
    @staticmethod
    def get_batch_lifecycle(batch_id: int) -> Dict:
        """
        Get complete lifecycle of a batch
        Returns: purchase details + all transactions
        """
        try:
            db = Database.get_client()
            
            # Get batch details
            batch_response = db.table('inventory_batches') \
                .select('*, item_master(item_name, sku, unit), suppliers(supplier_name)') \
                .eq('id', batch_id) \
                .single() \
                .execute()
            
            if not batch_response.data:
                return {}
            
            batch = batch_response.data
            
            # Flatten
            if batch.get('item_master'):
                batch['item_name'] = batch['item_master']['item_name']
                batch['sku'] = batch['item_master'].get('sku', '')
                batch['unit'] = batch['item_master']['unit']
            
            if batch.get('suppliers'):
                batch['supplier_name'] = batch['suppliers']['supplier_name']
            
            # Get all transactions for this batch
            tx_response = db.rpc('get_batch_lifecycle', {'p_batch_id': batch_id}).execute()
            batch['transactions'] = tx_response.data if tx_response.data else []
            
            return batch
        
        except Exception as e:
            st.error(f"Error fetching batch lifecycle: {str(e)}")
            return {}
    
    # =====================================================
    # PURCHASE ORDERS
    # =====================================================
    
    @staticmethod
    def create_po(po_data: Dict, po_items: List[Dict], user_id: str) -> Optional[int]:
        """Create purchase order (v2.0.0 signature)"""
        try:
            db = Database.get_client()
            
            po_data['created_by'] = user_id
            
            # Insert PO
            po_response = db.table('purchase_orders').insert(po_data).execute()
            
            if not po_response.data:
                return None
            
            po_id = po_response.data[0]['id']
            
            # Insert items
            for item in po_items:
                item['po_id'] = po_id
            
            db.table('purchase_order_items').insert(po_items).execute()
            
            return po_id
        
        except Exception as e:
            st.error(f"Error creating PO: {str(e)}")
            return None
    
    @staticmethod
    def create_purchase_order(
        po_number: str,
        item_master_id: int,
        supplier_name: str,
        quantity: float,
        unit_cost: float,
        po_date: date,
        expected_delivery: date = None,
        notes: str = None,
        username: str = None
    ) -> bool:
        """
        Create purchase order (simplified UI wrapper)
        NEW in v2.1.0
        """
        try:
            db = Database.get_client()
            
            # Get supplier_id from name
            supplier_id = None
            if supplier_name:
                supplier_response = db.table('suppliers') \
                    .select('id') \
                    .eq('supplier_name', supplier_name) \
                    .execute()
                
                if supplier_response.data:
                    supplier_id = supplier_response.data[0]['id']
            
            # Create PO
            po_data = {
                'po_number': po_number,
                'supplier_id': supplier_id,
                'po_date': po_date.isoformat() if isinstance(po_date, date) else po_date,
                'expected_delivery': expected_delivery.isoformat() if expected_delivery and isinstance(expected_delivery, date) else expected_delivery,
                'status': 'pending',
                'notes': notes,
                'created_by': username
            }
            
            po_response = db.table('purchase_orders').insert(po_data).execute()
            
            if not po_response.data:
                return False
            
            po_id = po_response.data[0]['id']
            
            # Create PO item
            po_item = {
                'po_id': po_id,
                'item_master_id': item_master_id,
                'quantity_ordered': quantity,
                'unit_cost': unit_cost,
                'total_cost': quantity * unit_cost
            }
            
            db.table('purchase_order_items').insert(po_item).execute()
            
            return True
        
        except Exception as e:
            st.error(f"Error creating purchase order: {str(e)}")
            return False
    
    @staticmethod
    def get_pos(status: str = None, days: int = 90) -> List[Dict]:
        """Get purchase orders (v2.0.0 signature)"""
        try:
            db = Database.get_client()
            
            since_date = datetime.now() - timedelta(days=days)
            
            query = db.table('purchase_orders') \
                .select('*, suppliers(supplier_name)') \
                .gte('po_date', since_date.date().isoformat()) \
                .order('po_date', desc=True)
            
            if status:
                query = query.eq('status', status)
            
            response = query.execute()
            
            # Flatten
            pos = response.data if response.data else []
            for po in pos:
                if po.get('suppliers'):
                    po['supplier_name'] = po['suppliers']['supplier_name']
            
            return pos
        
        except Exception as e:
            st.error(f"Error fetching POs: {str(e)}")
            return []
    
    @staticmethod
    def get_all_purchase_orders(days_back: int = 30) -> List[Dict]:
        """
        Get all purchase orders (UI wrapper)
        NEW in v2.1.0
        """
        return InventoryDB.get_pos(status=None, days=days_back)
    
    @staticmethod
    def get_purchase_orders_by_status(status: str, days_back: int = 30) -> List[Dict]:
        """
        Get filtered purchase orders (UI wrapper)
        NEW in v2.1.0
        """
        return InventoryDB.get_pos(status=status, days=days_back)
    
    @staticmethod
    def get_po_items(po_id: int) -> List[Dict]:
        """Get items for a PO"""
        try:
            db = Database.get_client()
            
            response = db.table('purchase_order_items') \
                .select('*, item_master(item_name, sku, unit)') \
                .eq('po_id', po_id) \
                .execute()
            
            # Flatten
            items = response.data if response.data else []
            for item in items:
                if item.get('item_master'):
                    item['item_name'] = item['item_master']['item_name']
                    item['sku'] = item['item_master'].get('sku', '')
                    item['unit'] = item['item_master']['unit']
            
            return items
        
        except Exception as e:
            st.error(f"Error fetching PO items: {str(e)}")
            return []
    
    @staticmethod
    def update_po_status(po_id: int, new_status: str) -> bool:
        """Update PO status"""
        try:
            db = Database.get_client()
            
            db.table('purchase_orders') \
                .update({'status': new_status, 'updated_at': datetime.now().isoformat()}) \
                .eq('id', po_id) \
                .execute()
            
            return True
        
        except Exception as e:
            st.error(f"Error updating PO: {str(e)}")
            return False
    
    # =====================================================
    # ANALYTICS & REPORTS
    # =====================================================
    
    @staticmethod
    def get_inventory_summary() -> Dict:
        """
        Get inventory summary statistics (for dashboard)
        NEW in v2.1.0
        """
        try:
            db = Database.get_client()
            
            # Get active items count
            items_response = db.table('item_master') \
                .select('id', count='exact') \
                .eq('is_active', True) \
                .execute()
            
            total_active_items = items_response.count if items_response else 0
            
            # Get total batches
            batches_response = db.table('inventory_batches') \
                .select('id', count='exact') \
                .gt('remaining_qty', 0) \
                .execute()
            
            total_batches = batches_response.count if batches_response else 0
            
            # Get inventory value (admin only)
            try:
                valuation_response = db.rpc('get_inventory_valuation').execute()
                if valuation_response.data:
                    total_value = sum([v.get('total_value', 0) for v in valuation_response.data])
                    avg_value = total_value / total_active_items if total_active_items > 0 else 0
                else:
                    total_value = 0
                    avg_value = 0
            except:
                # If RPC doesn't exist, calculate manually
                batches = InventoryDB.get_all_batches(active_only=True)
                total_value = sum([b.get('batch_value', 0) for b in batches])
                avg_value = total_value / total_active_items if total_active_items > 0 else 0
            
            return {
                'total_active_items': total_active_items,
                'total_batches': total_batches,
                'total_inventory_value': total_value,
                'avg_item_value': avg_value
            }
        
        except Exception as e:
            st.error(f"Error fetching inventory summary: {str(e)}")
            return {
                'total_active_items': 0,
                'total_batches': 0,
                'total_inventory_value': 0,
                'avg_item_value': 0
            }
    
    @staticmethod
    def get_inventory_valuation() -> List[Dict]:
        """Get inventory value by category (admin only)"""
        try:
            db = Database.get_client()
            
            response = db.rpc('get_inventory_valuation').execute()
            return response.data if response.data else []
        
        except Exception as e:
            st.error(f"Error fetching valuation: {str(e)}")
            return []
    
    @staticmethod
    def get_consumption_by_module(days: int = 30) -> Dict:
        """Get consumption breakdown by module"""
        try:
            db = Database.get_client()
            
            since_date = datetime.now() - timedelta(days=days)
            
            response = db.table('inventory_transactions') \
                .select('module_reference, quantity_change, total_cost') \
                .eq('transaction_type', 'remove') \
                .gte('transaction_date', since_date.isoformat()) \
                .execute()
            
            if not response.data:
                return {}
            
            # Group by module
            consumption = {}
            for tx in response.data:
                module = tx.get('module_reference', 'Unknown')
                if not module:
                    module = 'Unknown'
                
                qty = abs(tx['quantity_change'])
                cost = tx.get('total_cost', 0) or 0
                
                if module not in consumption:
                    consumption[module] = {'quantity': 0, 'cost': 0, 'count': 0}
                
                consumption[module]['quantity'] += qty
                consumption[module]['cost'] += cost
                consumption[module]['count'] += 1
            
            return consumption
        
        except Exception as e:
            st.error(f"Error fetching consumption: {str(e)}")
            return {}
    
    @staticmethod
    def get_module_consumption(
        module_name: str,
        start_date: date,
        end_date: date
    ) -> List[Dict]:
        """
        Get consumption for specific module (UI wrapper)
        NEW in v2.1.0
        """
        try:
            db = Database.get_client()
            
            response = db.table('inventory_transactions') \
                .select('item_master(item_name, unit), quantity_change, total_cost, module_reference') \
                .eq('transaction_type', 'remove') \
                .eq('module_reference', module_name) \
                .gte('transaction_date', start_date.isoformat()) \
                .lte('transaction_date', end_date.isoformat()) \
                .execute()
            
            if not response.data:
                return []
            
            # Flatten and aggregate
            consumption = {}
            for tx in response.data:
                item_name = tx['item_master']['item_name'] if tx.get('item_master') else 'Unknown'
                unit = tx['item_master']['unit'] if tx.get('item_master') else ''
                
                qty = abs(tx.get('quantity_change', 0))
                cost = tx.get('total_cost', 0) or 0
                
                if item_name not in consumption:
                    consumption[item_name] = {
                        'module_name': module_name,
                        'item_name': item_name,
                        'unit': unit,
                        'total_quantity': 0,
                        'total_cost': 0
                    }
                
                consumption[item_name]['total_quantity'] += qty
                consumption[item_name]['total_cost'] += cost
            
            return list(consumption.values())
        
        except Exception as e:
            st.error(f"Error fetching module consumption: {str(e)}")
            return []
    
    @staticmethod
    def generate_verification_report() -> List[Dict]:
        """Generate physical stock verification report"""
        try:
            batches = InventoryDB.get_all_batches(active_only=True)
            
            # Format for verification
            report = []
            for batch in batches:
                report.append({
                    'item_name': batch.get('item_name', ''),
                    'sku': batch.get('sku', ''),
                    'batch_number': batch['batch_number'],
                    'system_qty': batch['remaining_qty'],
                    'unit': batch.get('unit', ''),
                    'expiry_date': batch.get('expiry_date', ''),
                    'physical_qty': '',  # To be filled manually
                    'variance': ''  # To be calculated
                })
            
            return report
        
        except Exception as e:
            st.error(f"Error generating verification report: {str(e)}")
            return []
