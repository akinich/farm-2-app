-- =====================================================
-- DATABASE INDEXES FOR PERFORMANCE OPTIMIZATION
-- =====================================================
-- Run these SQL statements in your Supabase SQL Editor
-- to create indexes on frequently queried columns
--
-- Expected Impact: 2x-5x faster query performance
-- Execution Time: ~1-2 minutes total
-- =====================================================

-- 1. Purchase Orders - PO Date Index
-- Speeds up date range queries (e.g., "show POs from last 30 days")
CREATE INDEX IF NOT EXISTS idx_purchase_orders_po_date
ON purchase_orders(po_date DESC);

-- 2. Purchase Orders - Status Index
-- Speeds up status filtering (e.g., "show pending POs")
CREATE INDEX IF NOT EXISTS idx_purchase_orders_status
ON purchase_orders(status);

-- 3. Purchase Orders - Created By Index
-- Speeds up user lookups for "created by" information
CREATE INDEX IF NOT EXISTS idx_purchase_orders_created_by
ON purchase_orders(created_by);

-- 4. Purchase Orders - Composite Index (Status + Date)
-- Optimizes the most common query: filter by status AND date range
CREATE INDEX IF NOT EXISTS idx_purchase_orders_status_date
ON purchase_orders(status, po_date DESC);

-- 5. Purchase Order Items - PO ID Index
-- Speeds up fetching all items for a specific PO
CREATE INDEX IF NOT EXISTS idx_purchase_order_items_po_id
ON purchase_order_items(po_id);

-- 6. Purchase Order Items - Item Master ID Index
-- Speeds up item-based queries and joins
CREATE INDEX IF NOT EXISTS idx_purchase_order_items_item_master_id
ON purchase_order_items(item_master_id);

-- 7. Inventory Batches - Item Master ID Index
-- Speeds up stock queries by item
CREATE INDEX IF NOT EXISTS idx_inventory_batches_item_master_id
ON inventory_batches(item_master_id);

-- 8. Inventory Batches - Expiry Date Index
-- Speeds up expiry alerts and FEFO queries
CREATE INDEX IF NOT EXISTS idx_inventory_batches_expiry_date
ON inventory_batches(expiry_date);

-- 9. Inventory Batches - Status Index
-- Speeds up filtering active vs consumed batches
CREATE INDEX IF NOT EXISTS idx_inventory_batches_status
ON inventory_batches(status);

-- 10. Inventory Transactions - Item Master ID Index
-- Speeds up transaction history queries
CREATE INDEX IF NOT EXISTS idx_inventory_transactions_item_master_id
ON inventory_transactions(item_master_id);

-- 11. Inventory Transactions - Transaction Date Index
-- Speeds up date range queries for transaction history
CREATE INDEX IF NOT EXISTS idx_inventory_transactions_transaction_date
ON inventory_transactions(transaction_date DESC);

-- 12. User Profiles - ID Index (if not already primary key)
-- Speeds up user profile lookups
-- Note: This may already exist if 'id' is the primary key
-- CREATE INDEX IF NOT EXISTS idx_user_profiles_id
-- ON user_profiles(id);

-- =====================================================
-- VERIFICATION QUERIES
-- =====================================================
-- Run these to verify indexes were created successfully:

-- Check all indexes on purchase_orders table
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'purchase_orders'
ORDER BY indexname;

-- Check all indexes on purchase_order_items table
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'purchase_order_items'
ORDER BY indexname;

-- Check all indexes on inventory_batches table
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'inventory_batches'
ORDER BY indexname;

-- =====================================================
-- PERFORMANCE MONITORING
-- =====================================================
-- After creating indexes, you can monitor their usage:

SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;

-- =====================================================
-- NOTES
-- =====================================================
-- 1. These indexes will be created automatically and maintained by PostgreSQL
-- 2. They will slightly slow down INSERT/UPDATE operations but dramatically speed up SELECT queries
-- 3. The trade-off is worth it for read-heavy applications like yours
-- 4. Indexes are automatically used by the query planner when appropriate
-- 5. No code changes required - indexes work transparently
