-- =====================================================
-- DATABASE INDEXES FOR PERFORMANCE OPTIMIZATION (CORRECTED)
-- =====================================================
-- This is the corrected version based on your actual schema
-- Run these SQL statements in your Supabase SQL Editor
--
-- Expected Impact: 2x-5x faster query performance
-- Execution Time: ~1-2 minutes total
-- =====================================================

-- =====================================================
-- PURCHASE ORDERS TABLE INDEXES
-- =====================================================

-- 1. Purchase Orders - PO Date Index
-- Speeds up date range queries (e.g., "show POs from last 30 days")
CREATE INDEX IF NOT EXISTS idx_purchase_orders_po_date
ON purchase_orders(po_date DESC);

-- 2. Purchase Orders - Status Index
-- Speeds up status filtering (e.g., "show pending POs")
-- Note: Only create if 'status' column exists
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'purchase_orders' AND column_name = 'status'
    ) THEN
        CREATE INDEX IF NOT EXISTS idx_purchase_orders_status
        ON purchase_orders(status);
    END IF;
END $$;

-- 3. Purchase Orders - Created By Index
-- Speeds up user lookups for "created by" information
CREATE INDEX IF NOT EXISTS idx_purchase_orders_created_by
ON purchase_orders(created_by);

-- 4. Purchase Orders - Composite Index (Status + Date)
-- Optimizes the most common query: filter by status AND date range
-- Note: Only create if 'status' column exists
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'purchase_orders' AND column_name = 'status'
    ) THEN
        CREATE INDEX IF NOT EXISTS idx_purchase_orders_status_date
        ON purchase_orders(status, po_date DESC);
    END IF;
END $$;

-- =====================================================
-- PURCHASE ORDER ITEMS TABLE INDEXES
-- =====================================================

-- 5. Purchase Order Items - PO ID Index
-- Speeds up fetching all items for a specific PO
CREATE INDEX IF NOT EXISTS idx_purchase_order_items_po_id
ON purchase_order_items(po_id);

-- 6. Purchase Order Items - Item Master ID Index
-- Speeds up item-based queries and joins
CREATE INDEX IF NOT EXISTS idx_purchase_order_items_item_master_id
ON purchase_order_items(item_master_id);

-- =====================================================
-- INVENTORY BATCHES TABLE INDEXES
-- =====================================================

-- 7. Inventory Batches - Item Master ID Index
-- Speeds up stock queries by item
CREATE INDEX IF NOT EXISTS idx_inventory_batches_item_master_id
ON inventory_batches(item_master_id);

-- 8. Inventory Batches - Expiry Date Index
-- Speeds up expiry alerts and FEFO queries
CREATE INDEX IF NOT EXISTS idx_inventory_batches_expiry_date
ON inventory_batches(expiry_date);

-- 9. Inventory Batches - Is Active Index
-- Speeds up filtering active vs inactive batches
-- (Using is_active boolean instead of status string)
CREATE INDEX IF NOT EXISTS idx_inventory_batches_is_active
ON inventory_batches(is_active);

-- 10. Inventory Batches - Purchase Date Index
-- Speeds up date-based queries
CREATE INDEX IF NOT EXISTS idx_inventory_batches_purchase_date
ON inventory_batches(purchase_date DESC);

-- 11. Inventory Batches - Supplier ID Index
-- Speeds up supplier-based queries
CREATE INDEX IF NOT EXISTS idx_inventory_batches_supplier_id
ON inventory_batches(supplier_id);

-- =====================================================
-- INVENTORY TRANSACTIONS TABLE INDEXES
-- =====================================================

-- 12. Inventory Transactions - Item Master ID Index
-- Speeds up transaction history queries
CREATE INDEX IF NOT EXISTS idx_inventory_transactions_item_master_id
ON inventory_transactions(item_master_id);

-- 13. Inventory Transactions - Transaction Date Index
-- Speeds up date range queries for transaction history
-- Note: Check if column is 'transaction_date' or 'created_at'
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'inventory_transactions' AND column_name = 'transaction_date'
    ) THEN
        CREATE INDEX IF NOT EXISTS idx_inventory_transactions_transaction_date
        ON inventory_transactions(transaction_date DESC);
    ELSIF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'inventory_transactions' AND column_name = 'created_at'
    ) THEN
        CREATE INDEX IF NOT EXISTS idx_inventory_transactions_created_at
        ON inventory_transactions(created_at DESC);
    END IF;
END $$;

-- 14. Inventory Transactions - Batch ID Index
-- Speeds up batch-related transaction queries
CREATE INDEX IF NOT EXISTS idx_inventory_transactions_batch_id
ON inventory_transactions(batch_id);

-- =====================================================
-- ITEM MASTER TABLE INDEXES
-- =====================================================

-- 15. Item Master - Category Index
-- Speeds up category-based filtering
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'item_master' AND column_name = 'category'
    ) THEN
        CREATE INDEX IF NOT EXISTS idx_item_master_category
        ON item_master(category);
    END IF;
END $$;

-- 16. Item Master - Active Status Index
-- Speeds up filtering active items
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'item_master' AND column_name = 'is_active'
    ) THEN
        CREATE INDEX IF NOT EXISTS idx_item_master_is_active
        ON item_master(is_active);
    ELSIF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'item_master' AND column_name = 'active'
    ) THEN
        CREATE INDEX IF NOT EXISTS idx_item_master_active
        ON item_master(active);
    END IF;
END $$;

-- =====================================================
-- SUPPLIERS TABLE INDEXES
-- =====================================================

-- 17. Suppliers - Active Status Index
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'suppliers' AND column_name = 'is_active'
    ) THEN
        CREATE INDEX IF NOT EXISTS idx_suppliers_is_active
        ON suppliers(is_active);
    ELSIF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'suppliers' AND column_name = 'active'
    ) THEN
        CREATE INDEX IF NOT EXISTS idx_suppliers_active
        ON suppliers(active);
    END IF;
END $$;

-- =====================================================
-- VERIFICATION QUERIES
-- =====================================================
-- Run these to verify indexes were created successfully:

-- Check all indexes on purchase_orders table
SELECT
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'purchase_orders'
  AND schemaname = 'public'
ORDER BY indexname;

-- Check all indexes on purchase_order_items table
SELECT
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'purchase_order_items'
  AND schemaname = 'public'
ORDER BY indexname;

-- Check all indexes on inventory_batches table
SELECT
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'inventory_batches'
  AND schemaname = 'public'
ORDER BY indexname;

-- Check all indexes on inventory_transactions table
SELECT
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'inventory_transactions'
  AND schemaname = 'public'
ORDER BY indexname;

-- Summary: Count of indexes per table
SELECT
    tablename,
    COUNT(*) as index_count
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename IN ('purchase_orders', 'purchase_order_items', 'inventory_batches', 'inventory_transactions', 'item_master', 'suppliers')
GROUP BY tablename
ORDER BY tablename;

-- =====================================================
-- NOTES
-- =====================================================
-- 1. This script uses conditional logic (DO blocks) to check if columns exist before creating indexes
-- 2. This prevents errors if your schema is different from expected
-- 3. Indexes that can't be created (due to missing columns) will be skipped silently
-- 4. Run the verification queries at the end to see which indexes were successfully created
-- 5. No code changes required - indexes work transparently once created
