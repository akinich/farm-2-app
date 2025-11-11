-- =====================================================
-- DATABASE SCHEMA DIAGNOSTIC SCRIPT
-- =====================================================
-- Run this first to see what columns exist in each table
-- This will help us create the correct indexes
-- =====================================================

-- Check purchase_orders table structure
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'purchase_orders'
ORDER BY ordinal_position;

-- Check purchase_order_items table structure
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'purchase_order_items'
ORDER BY ordinal_position;

-- Check inventory_batches table structure
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'inventory_batches'
ORDER BY ordinal_position;

-- Check inventory_transactions table structure
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'inventory_transactions'
ORDER BY ordinal_position;

-- Check item_master table structure
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'item_master'
ORDER BY ordinal_position;
