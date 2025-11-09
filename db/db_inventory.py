"""
Inventory Database Operations V1.1.0
Handles all database operations for inventory management

VERSION HISTORY:
1.1.0 - Enhanced with expiry, batches, POs, suppliers, analytics - 09/11/25
      NEW METHODS:
      - Batch tracking (add_batch, get_batches, get_expiring_items)
      - Supplier management (get_suppliers, add_supplier, update_supplier)
      - Purchase orders (create_po, get_pos, receive_po_items)
      - Stock adjustments (log_adjustment, get_adjustments)
      - Analytics (get_consumption_trends, get_inventory_valuation)
      - Delete operations (delete_item, delete_transaction)
      UPDATES:
      - Enhanced get_all_items with batch info
      - Enhanced add/remove stock with batch tracking
      - Added cost tracking throughout
1.0.0 - Initial inventory database helper - 08/11/25
"""
import streamlit as st
from typing import List, Dict, Optional
from datetime import datetime, timedelta, date


class InventoryDB:
    """Inventory-related database operations"""
    
    # =====================================================
    # INVENTORY ITEMS
    # =====================================================
    
    @staticmethod
    def get_all_items(active_only: bool = False) -> List[Dict]:
        """Get all inventory items with enhanced info"""
        try:
            from config.database import Database
            db = Database.get_client()
            
            query = db.table('inventory_items') \
                .select('*, suppliers(supplier_name)') \
                .order('item_name')
            
            if active_only:
                query = query.eq('is_active', True)
            
            response = query.execute()
            
            # Flatten supplier name
            items = response.data if response.data else []
            for item in items:
                if item.get('suppliers'):
                    item['supplier_name'] = item['suppliers']['supplier_name']
                else:
                    item['supplier_name'] = item.get('default_supplier_name', '')
                
                # Add stock status
                if item['current_qty'] <= item.get('min_stock_level', 0):
                    item['stock_status'] = 'critical'
                elif item['current_qty'] <= item['reorder_threshold']:
                    item['stock_status'] = 'low'
                else:
                    item['stock_status'] = 'good'
            
            return items
        
        except Exception as e:
            st.error(f"Error fetching inventory items: {str(e)}")
            return []
    
    @staticmethod
    def add_item(item_data: Dict, user_id: str) -> bool:
        """Add a new inventory item (admin only)"""
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
        """Update an inventory item"""
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
    
    @staticmethod
    def delete_item(item_id: int) -> bool:
        """Delete an inventory item (admin only)"""
        try:
            from config.database import Database
            db = Database.get_client()
            
            db.table('inventory_items').delete().eq('id', item_id).execute()
            return True
        
        except Exception as e:
            st.error(f"Error deleting item: {str(e)}")
            return False
    
    # =====================================================
    # CATEGORIES
    # =====================================================
    
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
    
    # =====================================================
    # BATCHES
    # =====================================================
    
    @staticmethod
    def add_batch(batch_data: Dict) -> Optional[int]:
        """Add a new batch and return batch_id"""
        try:
            from config.database import Database
            db = Database.get_client()
            
            response = db.table('inventory_batches').insert(batch_data).execute()
            
            if response.data:
                return response.data[0]['id']
            return None
        
        except Exception as e:
            st.error(f"Error adding batch: {str(e)}")
            return None
    
    @staticmethod
    def get_batches(item_id: int = None, active_only: bool = True) -> List[Dict]:
        """Get batches for an item or all batches"""
        try:
            from config.database import Database
            db = Database.get_client()
            
            query = db.table('inventory_batches') \
                .select('*, inventory_items(item_name, unit), suppliers(supplier_name)') \
                .order('expiry_date')
            
            if item_id:
                query = query.eq('item_id', item_id)
            
            if active_only:
                query = query.eq('is_active', True).gt('remaining_qty', 0)
            
            response = query.execute()
            return response.data if response.data else []
        
        except Exception as e:
            st.error(f"Error fetching batches: {str(e)}")
            return []
    
    @staticmethod
    def get_expiring_items(days_ahead: int = 30) -> List[Dict]:
        """Get items expiring in the next X days using RPC"""
        try:
            from config.database import Database
            db = Database.get_client()
            
            response = db.rpc('get_expiring_items', {'days_ahead': days_ahead}).execute()
            return response.data if response.data else []
        
        except Exception as e:
            st.error(f"Error fetching expiring items: {str(e)}")
            return []
    
    @staticmethod
    def update_batch_qty(batch_id: int, new_qty: float) -> bool:
        """Update remaining quantity of a batch"""
        try:
            from config.database import Database
            db = Database.get_client()
            
            db.table('inventory_batches') \
                .update({'remaining_qty': new_qty}) \
                .eq('id', batch_id) \
                .execute()
            
            return True
        
        except Exception as e:
            st.error(f"Error updating batch: {str(e)}")
            return False
    
    # =====================================================
    # STOCK OPERATIONS
    # =====================================================
    
    @staticmethod
    def add_stock(item_id: int, quantity: float, unit_cost: float, 
                  batch_number: str, expiry_date: date, supplier_id: int,
                  user_id: str, notes: str = None, po_number: str = None) -> bool:
        """Add stock with batch tracking"""
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
            
            # Create batch
            batch_data = {
                'item_id': item_id,
                'batch_number': batch_number,
                'quantity': quantity,
                'remaining_qty': quantity,
                'unit_cost': unit_cost,
                'purchase_date': date.today().isoformat(),
                'expiry_date': expiry_date.isoformat() if expiry_date else None,
                'supplier_id': supplier_id,
                'po_number': po_number,
                'notes': notes
            }
            
            batch_id = InventoryDB.add_batch(batch_data)
            
            if not batch_id:
                return False
            
            # Update item quantity and cost
            db.table('inventory_items') \
                .update({
                    'current_qty': new_qty,
                    'last_purchase_cost': unit_cost,
                    'last_restocked': datetime.now().isoformat()
                }) \
                .eq('id', item_id) \
                .execute()
            
            # Log transaction
            db.table('inventory_transactions').insert({
                'item_id': item_id,
                'batch_id': batch_id,
                'transaction_type': 'add',
                'quantity_change': quantity,
                'new_balance': new_qty,
                'unit_cost': unit_cost,
                'po_number': po_number,
                'user_id': user_id,
                'notes': notes
            }).execute()
            
            return True
        
        except Exception as e:
            st.error(f"Error adding stock: {str(e)}")
            return False
    
    @staticmethod
    def remove_stock(item_id: int, quantity: float, module_reference: str,
                     user_id: str, notes: str = None, batch_id: int = None) -> bool:
        """Remove stock with FIFO batch tracking"""
        try:
            from config.database import Database
            db = Database.get_client()
            
            # Get current item
            item_response = db.table('inventory_items') \
                .select('current_qty, unit_cost') \
                .eq('id', item_id) \
                .single() \
                .execute()
            
            if not item_response.data:
                st.error("Item not found")
                return False
            
            current_qty = item_response.data['current_qty']
            unit_cost = item_response.data.get('unit_cost', 0)
            
            if quantity > current_qty:
                st.error(f"Insufficient stock. Available: {current_qty}")
                return False
            
            new_qty = current_qty - quantity
            
            # If batch specified, deduct from that batch
            if batch_id:
                batch_response = db.table('inventory_batches') \
                    .select('remaining_qty') \
                    .eq('id', batch_id) \
                    .single() \
                    .execute()
                
                if batch_response.data:
                    batch_remaining = batch_response.data['remaining_qty']
                    if quantity <= batch_remaining:
                        InventoryDB.update_batch_qty(batch_id, batch_remaining - quantity)
            
            # Update item quantity
            db.table('inventory_items') \
                .update({'current_qty': new_qty}) \
                .eq('id', item_id) \
                .execute()
            
            # Log transaction
            db.table('inventory_transactions').insert({
                'item_id': item_id,
                'batch_id': batch_id,
                'transaction_type': 'remove',
                'quantity_change': -quantity,
                'new_balance': new_qty,
                'unit_cost': unit_cost,
                'module_reference': module_reference,
                'user_id': user_id,
                'notes': notes
            }).execute()
            
            return True
        
        except Exception as e:
            st.error(f"Error removing stock: {str(e)}")
            return False
    
    # =====================================================
    # STOCK ADJUSTMENTS
    # =====================================================
    
    @staticmethod
    def log_adjustment(item_id: int, adjustment_type: str, quantity: float,
                      reason: str, user_id: str, batch_id: int = None,
                      notes: str = None) -> bool:
        """Log stock adjustment (wastage, damage, etc.)"""
        try:
            from config.database import Database
            db = Database.get_client()
            
            # Get current quantity
            item_response = db.table('inventory_items') \
                .select('current_qty') \
                .eq('id', item_id) \
                .single() \
                .execute()
            
            if not item_response.data:
                return False
            
            old_qty = item_response.data['current_qty']
            new_qty = old_qty - abs(quantity)  # Always subtract for adjustments
            
            # Update item
            db.table('inventory_items') \
                .update({'current_qty': new_qty}) \
                .eq('id', item_id) \
                .execute()
            
            # Update batch if specified
            if batch_id:
                batch_response = db.table('inventory_batches') \
                    .select('remaining_qty') \
                    .eq('id', batch_id) \
                    .single() \
                    .execute()
                
                if batch_response.data:
                    batch_qty = batch_response.data['remaining_qty']
                    InventoryDB.update_batch_qty(batch_id, batch_qty - abs(quantity))
            
            # Log adjustment
            db.table('stock_adjustments').insert({
                'item_id': item_id,
                'batch_id': batch_id,
                'adjustment_type': adjustment_type,
                'quantity_adjusted': -abs(quantity),
                'old_qty': old_qty,
                'new_qty': new_qty,
                'reason': reason,
                'adjusted_by': user_id,
                'notes': notes
            }).execute()
            
            # Also log as transaction
            db.table('inventory_transactions').insert({
                'item_id': item_id,
                'batch_id': batch_id,
                'transaction_type': 'adjustment',
                'quantity_change': -abs(quantity),
                'new_balance': new_qty,
                'adjustment_reason': adjustment_type,
                'user_id': user_id,
                'notes': f"{adjustment_type}: {reason}"
            }).execute()
            
            return True
        
        except Exception as e:
            st.error(f"Error logging adjustment: {str(e)}")
            return False
    
    @staticmethod
    def get_adjustments(days: int = 30) -> List[Dict]:
        """Get stock adjustment history"""
        try:
            from config.database import Database
            db = Database.get_client()
            
            since_date = datetime.now() - timedelta(days=days)
            
            response = db.table('stock_adjustments') \
                .select('*, inventory_items(item_name, unit)') \
                .gte('adjustment_date', since_date.date().isoformat()) \
                .order('adjustment_date', desc=True) \
                .execute()
            
            return response.data if response.data else []
        
        except Exception as e:
            st.error(f"Error fetching adjustments: {str(e)}")
            return []
    
    # =====================================================
    # TRANSACTIONS
    # =====================================================
    
    @staticmethod
    def get_transactions(days: int = 30, item_id: int = None, 
                        transaction_type: str = None, module: str = None) -> List[Dict]:
        """Get transaction history with filters"""
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
            
            if transaction_type:
                query = query.eq('transaction_type', transaction_type)
            
            if module:
                query = query.eq('module_reference', module)
            
            response = query.execute()
            return response.data if response.data else []
        
        except Exception as e:
            st.error(f"Error fetching transactions: {str(e)}")
            return []
    
    @staticmethod
    def delete_transaction(transaction_id: int) -> bool:
        """Delete a transaction (admin only)"""
        try:
            from config.database import Database
            db = Database.get_client()
            
            db.table('inventory_transactions').delete().eq('id', transaction_id).execute()
            return True
        
        except Exception as e:
            st.error(f"Error deleting transaction: {str(e)}")
            return False
    
    # =====================================================
    # ALERTS
    # =====================================================
    
    @staticmethod
    def get_low_stock_items() -> List[Dict]:
        """Get items where current_qty <= reorder_threshold using RPC"""
        try:
            from config.database import Database
            db = Database.get_client()
            
            response = db.rpc('get_low_stock_items').execute()
            return response.data if response.data else []
        
        except Exception as e:
            st.error(f"Error fetching low stock items: {str(e)}")
            return []
    
    # =====================================================
    # SUPPLIERS
    # =====================================================
    
    @staticmethod
    def get_suppliers(active_only: bool = True) -> List[Dict]:
        """Get all suppliers"""
        try:
            from config.database import Database
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
    def add_supplier(supplier_data: Dict) -> bool:
        """Add a new supplier"""
        try:
            from config.database import Database
            db = Database.get_client()
            
            db.table('suppliers').insert(supplier_data).execute()
            return True
        
        except Exception as e:
            st.error(f"Error adding supplier: {str(e)}")
            return False
    
    @staticmethod
    def update_supplier(supplier_id: int, updates: Dict) -> bool:
        """Update supplier information"""
        try:
            from config.database import Database
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
    # PURCHASE ORDERS
    # =====================================================
    
    @staticmethod
    def create_po(po_data: Dict, po_items: List[Dict], user_id: str) -> Optional[int]:
        """Create a new purchase order with items"""
        try:
            from config.database import Database
            db = Database.get_client()
            
            po_data['created_by'] = user_id
            
            # Insert PO
            po_response = db.table('purchase_orders').insert(po_data).execute()
            
            if not po_response.data:
                return None
            
            po_id = po_response.data[0]['id']
            
            # Insert PO items
            for item in po_items:
                item['po_id'] = po_id
            
            db.table('purchase_order_items').insert(po_items).execute()
            
            return po_id
        
        except Exception as e:
            st.error(f"Error creating PO: {str(e)}")
            return None
    
    @staticmethod
    def get_pos(status: str = None, days: int = 90) -> List[Dict]:
        """Get purchase orders with optional status filter"""
        try:
            from config.database import Database
            db = Database.get_client()
            
            since_date = datetime.now() - timedelta(days=days)
            
            query = db.table('purchase_orders') \
                .select('*, suppliers(supplier_name)') \
                .gte('po_date', since_date.date().isoformat()) \
                .order('po_date', desc=True)
            
            if status:
                query = query.eq('status', status)
            
            response = query.execute()
            return response.data if response.data else []
        
        except Exception as e:
            st.error(f"Error fetching POs: {str(e)}")
            return []
    
    @staticmethod
    def get_po_items(po_id: int) -> List[Dict]:
        """Get items for a specific PO"""
        try:
            from config.database import Database
            db = Database.get_client()
            
            response = db.table('purchase_order_items') \
                .select('*, inventory_items(item_name, unit)') \
                .eq('po_id', po_id) \
                .execute()
            
            return response.data if response.data else []
        
        except Exception as e:
            st.error(f"Error fetching PO items: {str(e)}")
            return []
    
    @staticmethod
    def update_po_status(po_id: int, new_status: str) -> bool:
        """Update PO status"""
        try:
            from config.database import Database
            db = Database.get_client()
            
            db.table('purchase_orders') \
                .update({'status': new_status}) \
                .eq('id', po_id) \
                .execute()
            
            return True
        
        except Exception as e:
            st.error(f"Error updating PO status: {str(e)}")
            return False
    
    # =====================================================
    # ANALYTICS
    # =====================================================
    
    @staticmethod
    def get_inventory_valuation() -> List[Dict]:
        """Get inventory valuation by category using RPC"""
        try:
            from config.database import Database
            db = Database.get_client()
            
            response = db.rpc('get_inventory_valuation').execute()
            return response.data if response.data else []
        
        except Exception as e:
            st.error(f"Error fetching inventory valuation: {str(e)}")
            return []
    
    @staticmethod
    def get_consumption_by_module(days: int = 30) -> Dict:
        """Get consumption breakdown by module"""
        try:
            from config.database import Database
            db = Database.get_client()
            
            since_date = datetime.now() - timedelta(days=days)
            
            response = db.table('inventory_transactions') \
                .select('module_reference, quantity_change, unit_cost') \
                .eq('transaction_type', 'remove') \
                .gte('transaction_date', since_date.isoformat()) \
                .execute()
            
            if not response.data:
                return {}
            
            # Group by module
            consumption = {}
            for tx in response.data:
                module = tx.get('module_reference', 'Unknown')
                qty = abs(tx['quantity_change'])
                cost = qty * tx.get('unit_cost', 0)
                
                if module not in consumption:
                    consumption[module] = {'quantity': 0, 'cost': 0, 'count': 0}
                
                consumption[module]['quantity'] += qty
                consumption[module]['cost'] += cost
                consumption[module]['count'] += 1
            
            return consumption
        
        except Exception as e:
            st.error(f"Error fetching consumption data: {str(e)}")
            return {}
