# Farm Management System - FastAPI Migration Specification

**Version:** 2.0.0
**Date:** November 17, 2025
**Migration From:** Streamlit v1.1.0
**Migration To:** FastAPI + Modern Frontend

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Database Schema](#database-schema)
3. [Authentication & Authorization](#authentication--authorization)
4. [API Endpoints Specification](#api-endpoints-specification)
5. [Module Specifications](#module-specifications)
6. [Tech Stack Recommendations](#tech-stack-recommendations)
7. [Performance Requirements](#performance-requirements)
8. [Migration Strategy](#migration-strategy)

---

## Executive Summary

### Purpose
Migrate from Streamlit-based UI to FastAPI backend with modern frontend to solve:
- **Performance bottlenecks** (PO tab loads in 2-3 seconds, needs <0.5s)
- **Scalability issues** (current ~100 users max, need 1000+)
- **Multi-client support** (web, mobile, third-party integrations)
- **Growing complexity** (10+ modules planned, biofloc 50% complete)

### Current State
- **9,651 lines** of Python code across 29 files
- **2 active modules**: Inventory (full), Biofloc (50% complete)
- **Database**: Supabase PostgreSQL
- **~70-80% UI coupling** to Streamlit

### Migration Scope
**Phase 1 (Core Backend):**
- FastAPI REST API
- JWT authentication
- Inventory module (complete)
- Biofloc module (complete implementation)
- Admin panel APIs
- Dashboard APIs

**Phase 2 (Frontend):**
- React/Vue.js SPA
- Mobile-responsive design
- Real-time updates via WebSockets

---

## Database Schema

### Supabase PostgreSQL Setup

**Connection:**
- Use Supabase PostgreSQL (existing instance OR new instance)
- Connection via `asyncpg` for FastAPI async operations
- Supabase client for Auth, RLS policies, and convenience methods

### Core Tables

#### 1. Authentication & Users

```sql
-- Managed by Supabase Auth
-- auth.users table (built-in)

-- User Profiles
CREATE TABLE user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name VARCHAR(255) NOT NULL,
    role_id INTEGER NOT NULL REFERENCES roles(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Roles
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    role_name VARCHAR(50) UNIQUE NOT NULL,  -- 'Admin', 'User'
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Initial data
INSERT INTO roles (role_name, description) VALUES
('Admin', 'Full system access'),
('User', 'Standard farm worker access');
```

#### 2. Modules & Permissions

```sql
-- Modules (installable features)
CREATE TABLE modules (
    id SERIAL PRIMARY KEY,
    module_key VARCHAR(50) UNIQUE NOT NULL,  -- 'inventory', 'biofloc', etc.
    module_name VARCHAR(100) NOT NULL,
    description TEXT,
    icon VARCHAR(50) DEFAULT '⚙️',
    display_order INTEGER DEFAULT 99,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User Module Permissions (granular access control)
CREATE TABLE user_module_permissions (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    module_id INTEGER NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    can_access BOOLEAN DEFAULT TRUE,
    granted_by UUID REFERENCES user_profiles(id),
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, module_id)
);

-- Initial modules
INSERT INTO modules (module_key, module_name, description, icon, display_order) VALUES
('inventory', 'Inventory Management', 'Track stock, POs, and suppliers', '📦', 1),
('biofloc', 'Biofloc Aquaculture', 'Manage fish tanks, water quality, growth', '🐟', 2);
```

#### 3. Activity Logging

```sql
CREATE TABLE activity_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES user_profiles(id),
    user_email VARCHAR(255),
    user_role VARCHAR(50),  -- 'admin' or 'user'
    action_type VARCHAR(100) NOT NULL,  -- 'login', 'create_po', 'add_water_test', etc.
    module_key VARCHAR(50),
    description TEXT,
    metadata JSONB,  -- Additional structured data
    success BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_activity_logs_user ON activity_logs(user_id, created_at DESC);
CREATE INDEX idx_activity_logs_module ON activity_logs(module_key, created_at DESC);
CREATE INDEX idx_activity_logs_action ON activity_logs(action_type, created_at DESC);
```

#### 4. Inventory Module Tables

```sql
-- Inventory Categories
CREATE TABLE inventory_categories (
    id SERIAL PRIMARY KEY,
    category_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Suppliers
CREATE TABLE suppliers (
    id SERIAL PRIMARY KEY,
    supplier_name VARCHAR(255) NOT NULL,
    contact_person VARCHAR(255),
    phone VARCHAR(50),
    email VARCHAR(255),
    address TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Item Master List (templates, NO stock quantities here)
CREATE TABLE item_master (
    id SERIAL PRIMARY KEY,
    item_name VARCHAR(255) NOT NULL,
    sku VARCHAR(100) UNIQUE,
    category VARCHAR(100) REFERENCES inventory_categories(category_name),
    unit VARCHAR(50) NOT NULL,  -- 'kg', 'liters', 'pcs', etc.
    default_supplier_id INTEGER REFERENCES suppliers(id),
    reorder_threshold NUMERIC(10,2) DEFAULT 0,
    min_stock_level NUMERIC(10,2) DEFAULT 0,
    current_qty NUMERIC(10,2) DEFAULT 0,  -- Auto-updated by triggers
    is_active BOOLEAN DEFAULT TRUE,
    created_by UUID REFERENCES user_profiles(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Inventory Batches (actual stock with FIFO tracking)
CREATE TABLE inventory_batches (
    id SERIAL PRIMARY KEY,
    item_master_id INTEGER NOT NULL REFERENCES item_master(id) ON DELETE CASCADE,
    batch_number VARCHAR(100),
    quantity_purchased NUMERIC(10,2) NOT NULL,
    remaining_qty NUMERIC(10,2) NOT NULL,
    unit_cost NUMERIC(10,2) NOT NULL,
    purchase_date DATE NOT NULL,
    expiry_date DATE,
    supplier_id INTEGER REFERENCES suppliers(id),
    po_number VARCHAR(100),
    notes TEXT,
    added_by UUID REFERENCES user_profiles(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Inventory Transactions (complete audit trail)
CREATE TABLE inventory_transactions (
    id BIGSERIAL PRIMARY KEY,
    item_master_id INTEGER NOT NULL REFERENCES item_master(id),
    batch_id INTEGER REFERENCES inventory_batches(id),
    transaction_type VARCHAR(50) NOT NULL,  -- 'add', 'use', 'adjust', 'expire'
    quantity_change NUMERIC(10,2) NOT NULL,  -- Positive for add, negative for use
    new_balance NUMERIC(10,2) NOT NULL,
    unit_cost NUMERIC(10,2),
    total_cost NUMERIC(10,2),
    po_number VARCHAR(100),
    module_reference VARCHAR(100),  -- 'biofloc', 'hydroponics', etc.
    tank_id INTEGER,  -- If related to specific tank
    user_id UUID REFERENCES user_profiles(id),
    username VARCHAR(255),
    notes TEXT,
    transaction_date TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Purchase Orders
CREATE TABLE purchase_orders (
    id SERIAL PRIMARY KEY,
    po_number VARCHAR(100) UNIQUE NOT NULL,
    supplier_id INTEGER NOT NULL REFERENCES suppliers(id),
    po_date DATE NOT NULL,
    expected_delivery DATE,
    status VARCHAR(50) DEFAULT 'pending',  -- 'pending','approved','ordered','received','closed','cancelled'
    total_cost NUMERIC(12,2) GENERATED ALWAYS AS (
        (SELECT COALESCE(SUM(ordered_qty * unit_cost), 0)
         FROM purchase_order_items
         WHERE purchase_order_id = id)
    ) STORED,
    notes TEXT,
    created_by UUID REFERENCES user_profiles(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Purchase Order Items (multi-item PO support)
CREATE TABLE purchase_order_items (
    id SERIAL PRIMARY KEY,
    purchase_order_id INTEGER NOT NULL REFERENCES purchase_orders(id) ON DELETE CASCADE,
    item_master_id INTEGER NOT NULL REFERENCES item_master(id),
    ordered_qty NUMERIC(10,2) NOT NULL,
    unit_cost NUMERIC(10,2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for inventory
CREATE INDEX idx_inventory_batches_item ON inventory_batches(item_master_id, remaining_qty DESC);
CREATE INDEX idx_inventory_batches_expiry ON inventory_batches(expiry_date) WHERE expiry_date IS NOT NULL;
CREATE INDEX idx_inventory_transactions_item ON inventory_transactions(item_master_id, transaction_date DESC);
CREATE INDEX idx_po_items_po ON purchase_order_items(purchase_order_id);
CREATE INDEX idx_po_status ON purchase_orders(status, po_date DESC);
```

#### 5. Biofloc Aquaculture Tables

```sql
-- Biofloc Tanks
CREATE TABLE biofloc_tanks (
    id SERIAL PRIMARY KEY,
    tank_number INTEGER UNIQUE NOT NULL,
    tank_name VARCHAR(100) NOT NULL,
    capacity_m3 NUMERIC(10,2),
    location VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Water Quality Tests
CREATE TABLE biofloc_water_tests (
    id SERIAL PRIMARY KEY,
    tank_id INTEGER NOT NULL REFERENCES biofloc_tanks(id),
    test_date DATE NOT NULL,
    ph NUMERIC(4,2),  -- 0-14
    dissolved_oxygen NUMERIC(5,2),  -- mg/L
    ammonia NUMERIC(5,2),  -- mg/L
    nitrite NUMERIC(5,2),  -- mg/L
    nitrate NUMERIC(6,2),  -- mg/L
    temp NUMERIC(4,1),  -- Celsius
    salinity NUMERIC(5,2),  -- ppt
    tds NUMERIC(8,2),  -- ppm
    alkalinity NUMERIC(6,2),  -- mg/L
    notes TEXT,
    tested_by UUID REFERENCES user_profiles(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Growth Records
CREATE TABLE biofloc_growth_records (
    id SERIAL PRIMARY KEY,
    tank_id INTEGER NOT NULL REFERENCES biofloc_tanks(id),
    record_date DATE NOT NULL,
    biomass_kg NUMERIC(10,2) NOT NULL,
    fish_count INTEGER,
    avg_weight NUMERIC(8,2),  -- grams
    mortality INTEGER DEFAULT 0,
    notes TEXT,
    recorded_by UUID REFERENCES user_profiles(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Feed Logs
CREATE TABLE biofloc_feed_logs (
    id SERIAL PRIMARY KEY,
    tank_id INTEGER NOT NULL REFERENCES biofloc_tanks(id),
    feed_date DATE NOT NULL,
    feed_type VARCHAR(255) NOT NULL,
    quantity_kg NUMERIC(8,2) NOT NULL,
    feeding_time VARCHAR(50),  -- 'Morning', 'Afternoon', 'Evening'
    notes TEXT,
    logged_by UUID REFERENCES user_profiles(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for biofloc
CREATE INDEX idx_water_tests_tank ON biofloc_water_tests(tank_id, test_date DESC);
CREATE INDEX idx_growth_records_tank ON biofloc_growth_records(tank_id, record_date DESC);
CREATE INDEX idx_feed_logs_tank ON biofloc_feed_logs(tank_id, feed_date DESC);
```

#### 6. Database Views (for efficient queries)

```sql
-- User Details View (combines auth + profile + role)
CREATE OR REPLACE VIEW user_details AS
SELECT
    up.id,
    au.email,
    up.full_name,
    up.role_id,
    r.role_name,
    up.is_active,
    up.created_at,
    up.updated_at
FROM user_profiles up
JOIN auth.users au ON au.id = up.id
LEFT JOIN roles r ON r.id = up.role_id;

-- User Accessible Modules (RBAC + user permissions)
CREATE OR REPLACE VIEW user_accessible_modules AS
SELECT DISTINCT
    up.id AS user_id,
    m.id AS module_id,
    m.module_key,
    m.module_name,
    m.icon,
    m.display_order
FROM user_profiles up
JOIN roles r ON r.id = up.role_id
CROSS JOIN modules m
LEFT JOIN user_module_permissions ump ON ump.user_id = up.id AND ump.module_id = m.id
WHERE m.is_active = TRUE
  AND up.is_active = TRUE
  AND (
      r.role_name = 'Admin'  -- Admins get all modules
      OR (ump.can_access = TRUE)  -- Users get explicitly granted modules
  )
ORDER BY m.display_order;

-- Tank Overview (Biofloc dashboard summary)
CREATE OR REPLACE VIEW biofloc_tank_overview AS
SELECT
    t.id,
    t.tank_number,
    t.tank_name,
    t.capacity_m3,
    wt.test_date AS last_test_date,
    wt.ph AS last_ph,
    wt.dissolved_oxygen AS last_do,
    wt.temp AS last_temp,
    (NOW()::date - wt.test_date) > 2 AS test_overdue,
    gr.record_date AS last_growth_date,
    gr.biomass_kg AS current_biomass,
    gr.fish_count AS current_fish_count,
    gr.mortality AS last_mortality
FROM biofloc_tanks t
LEFT JOIN LATERAL (
    SELECT * FROM biofloc_water_tests
    WHERE tank_id = t.id
    ORDER BY test_date DESC
    LIMIT 1
) wt ON TRUE
LEFT JOIN LATERAL (
    SELECT * FROM biofloc_growth_records
    WHERE tank_id = t.id
    ORDER BY record_date DESC
    LIMIT 1
) gr ON TRUE
WHERE t.is_active = TRUE;
```

#### 7. Database Triggers (Auto-update current_qty)

```sql
-- Trigger to auto-update item_master.current_qty when batches change
CREATE OR REPLACE FUNCTION update_item_master_qty()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE item_master
    SET current_qty = (
        SELECT COALESCE(SUM(remaining_qty), 0)
        FROM inventory_batches
        WHERE item_master_id = NEW.item_master_id
          AND is_active = TRUE
    ),
    updated_at = NOW()
    WHERE id = NEW.item_master_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_item_qty_on_batch_change
AFTER INSERT OR UPDATE OF remaining_qty ON inventory_batches
FOR EACH ROW
EXECUTE FUNCTION update_item_master_qty();
```

---

## Authentication & Authorization

### Supabase Auth Integration

**Authentication Flow:**
1. User submits email + password to FastAPI `/auth/login`
2. FastAPI calls Supabase Auth API (`supabase.auth.sign_in_with_password()`)
3. On success:
   - Fetch user profile from `user_profiles` table
   - Generate JWT access token (FastAPI)
   - Generate JWT refresh token (FastAPI)
   - Return tokens + user profile
4. Client stores tokens (HTTP-only cookies OR localStorage)

**JWT Token Structure:**
```python
# Access Token Payload
{
    "sub": "user_uuid",  # Supabase user ID
    "email": "user@example.com",
    "role": "admin",  # or "user"
    "full_name": "John Doe",
    "exp": 1234567890,  # 15 minutes from issue
    "type": "access"
}

# Refresh Token Payload
{
    "sub": "user_uuid",
    "exp": 1234567890,  # 7 days from issue
    "type": "refresh"
}
```

### Authorization Levels

**1. Admin Role:**
- Full access to all modules automatically
- Can manage users, roles, permissions
- Can access admin panel endpoints

**2. User Role:**
- Access only to explicitly granted modules
- Cannot access admin panel
- Cannot manage other users

### Permission Checking

```python
# FastAPI dependency for auth
async def get_current_user(token: str = Depends(oauth2_scheme)):
    # Decode JWT
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    user_id = payload.get("sub")
    # Fetch user from DB (with caching)
    user = await get_user_from_db(user_id)
    if not user or not user.is_active:
        raise HTTPException(401, "Invalid or inactive user")
    return user

# Check admin access
async def require_admin(user: User = Depends(get_current_user)):
    if user.role_name != "admin":
        raise HTTPException(403, "Admin access required")
    return user

# Check module access
def require_module_access(module_key: str):
    async def check_access(user: User = Depends(get_current_user)):
        if user.role_name == "admin":
            return user  # Admins have all access

        # Check user_module_permissions
        has_access = await db.check_module_permission(user.id, module_key)
        if not has_access:
            raise HTTPException(403, f"Access denied to module: {module_key}")
        return user
    return check_access
```

### Password Reset Flow

**Current Streamlit Flow (keep similar):**
1. User clicks "Forgot Password"
2. Enters email → FastAPI `/auth/forgot-password`
3. FastAPI calls Supabase `auth.reset_password_email(email)`
4. Supabase sends email with reset link
5. User clicks link → Redirected to frontend with `access_token` in URL
6. Frontend calls `/auth/reset-password` with token + new password
7. FastAPI calls Supabase `auth.update_user({"password": new_password})`

---

## API Endpoints Specification

### Base URL Structure
```
https://api.farmmanagement.com/v1
```

### Authentication Endpoints

#### POST /auth/login
**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepass123"
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "Bearer",
  "expires_in": 900,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "John Doe",
    "role": "admin",
    "is_active": true
  }
}
```

**Errors:**
- 401: Invalid credentials
- 403: Account inactive

#### POST /auth/refresh
**Request:**
```json
{
  "refresh_token": "eyJhbGc..."
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "Bearer",
  "expires_in": 900
}
```

#### POST /auth/logout
**Headers:** `Authorization: Bearer <access_token>`

**Response (200):**
```json
{
  "message": "Logged out successfully"
}
```

#### POST /auth/forgot-password
**Request:**
```json
{
  "email": "user@example.com"
}
```

**Response (200):**
```json
{
  "message": "Password reset email sent if account exists"
}
```

#### POST /auth/reset-password
**Request:**
```json
{
  "recovery_token": "supabase_recovery_token",
  "new_password": "newpass123"
}
```

**Response (200):**
```json
{
  "message": "Password reset successful"
}
```

### User Management Endpoints (Admin Only)

#### GET /admin/users
**Headers:** `Authorization: Bearer <admin_token>`

**Query Params:**
- `is_active`: boolean (optional)
- `role`: string (optional)
- `page`: int (default 1)
- `limit`: int (default 50)

**Response (200):**
```json
{
  "users": [
    {
      "id": "uuid",
      "email": "user@example.com",
      "full_name": "John Doe",
      "role_id": 2,
      "role_name": "User",
      "is_active": true,
      "created_at": "2025-01-01T00:00:00Z"
    }
  ],
  "total": 25,
  "page": 1,
  "limit": 50
}
```

#### POST /admin/users
**Create new user**

**Request:**
```json
{
  "email": "newuser@example.com",
  "full_name": "Jane Smith",
  "role_id": 2
}
```

**Response (201):**
```json
{
  "user": {
    "id": "uuid",
    "email": "newuser@example.com",
    "full_name": "Jane Smith",
    "role_name": "User"
  },
  "temporary_password": "auto_generated_secure_password"
}
```

#### PUT /admin/users/{user_id}
**Update user**

**Request:**
```json
{
  "full_name": "Jane Doe",
  "role_id": 1,
  "is_active": true
}
```

**Response (200):**
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "Jane Doe",
    "role_name": "Admin",
    "is_active": true
  }
}
```

#### DELETE /admin/users/{user_id}
**Delete user**

**Response (200):**
```json
{
  "message": "User deleted successfully"
}
```

### Module Permission Endpoints

#### GET /admin/permissions/{user_id}
**Get user's module permissions**

**Response (200):**
```json
{
  "user_id": "uuid",
  "permissions": [
    {
      "module_id": 1,
      "module_key": "inventory",
      "module_name": "Inventory Management",
      "can_access": true
    },
    {
      "module_id": 2,
      "module_key": "biofloc",
      "module_name": "Biofloc Aquaculture",
      "can_access": false
    }
  ]
}
```

#### PUT /admin/permissions/{user_id}
**Update user permissions (bulk)**

**Request:**
```json
{
  "module_ids": [1, 2, 3]
}
```

**Response (200):**
```json
{
  "message": "Permissions updated successfully",
  "granted_modules": ["inventory", "biofloc", "dashboard"]
}
```

### Activity Log Endpoints

#### GET /admin/activity-logs
**Query Params:**
- `days`: int (default 7)
- `user_id`: uuid (optional)
- `module_key`: string (optional)
- `action_type`: string (optional)
- `page`: int (default 1)
- `limit`: int (default 100)

**Response (200):**
```json
{
  "logs": [
    {
      "id": 123,
      "user_email": "user@example.com",
      "action_type": "create_po",
      "module_key": "inventory",
      "description": "Created PO PO-2025-001",
      "metadata": {"po_id": 42},
      "created_at": "2025-11-17T10:30:00Z"
    }
  ],
  "total": 150,
  "page": 1,
  "limit": 100
}
```

---

## Module Specifications

### Inventory Module

#### Endpoints Overview

| Endpoint | Method | Description | Auth |
|----------|--------|-------------|------|
| `/inventory/items` | GET | List all master items | User |
| `/inventory/items` | POST | Create master item | Admin |
| `/inventory/items/{id}` | GET | Get item details | User |
| `/inventory/items/{id}` | PUT | Update item | Admin |
| `/inventory/items/{id}` | DELETE | Delete item | Admin |
| `/inventory/stock` | GET | Get current stock levels | User |
| `/inventory/stock/add` | POST | Add stock batch | User |
| `/inventory/stock/use` | POST | Use/deduct stock (FIFO) | User |
| `/inventory/batches` | GET | List batches | User |
| `/inventory/batches/{id}` | GET | Get batch details | User |
| `/inventory/transactions` | GET | Transaction history | User |
| `/inventory/alerts/low-stock` | GET | Low stock alerts | User |
| `/inventory/alerts/expiry` | GET | Expiring items | User |
| `/inventory/purchase-orders` | GET | List POs | User |
| `/inventory/purchase-orders` | POST | Create PO | User |
| `/inventory/purchase-orders/{id}` | GET | Get PO details | User |
| `/inventory/purchase-orders/{id}` | PUT | Update PO status | Admin |
| `/inventory/purchase-orders/{id}` | DELETE | Delete PO | Admin |
| `/inventory/suppliers` | GET | List suppliers | User |
| `/inventory/suppliers` | POST | Create supplier | Admin |
| `/inventory/suppliers/{id}` | PUT | Update supplier | Admin |
| `/inventory/suppliers/{id}` | DELETE | Delete supplier | Admin |
| `/inventory/categories` | GET | List categories | User |
| `/inventory/export/items` | GET | Export items (Excel) | User |
| `/inventory/export/transactions` | GET | Export transactions | User |

#### Key Endpoint Details

##### GET /inventory/purchase-orders
**CRITICAL: This is the slow endpoint in Streamlit!**

**Performance Requirement:** <200ms response time

**Query Params:**
- `status`: string (All, pending, approved, ordered, received, closed, cancelled)
- `days_back`: int (default 30)
- `page`: int (default 1)
- `page_size`: int (default 20)

**Response (200):**
```json
{
  "pos": [
    {
      "id": 1,
      "po_number": "PO-2025-001",
      "supplier_id": 5,
      "supplier_name": "Acme Supplies",
      "po_date": "2025-11-15",
      "expected_delivery": "2025-11-20",
      "status": "ordered",
      "total_cost": 15250.50,
      "items_count": 3,
      "created_by_name": "John Doe",
      "created_at": "2025-11-15T09:00:00Z"
    }
  ],
  "total": 45,
  "page": 1,
  "page_size": 20,
  "total_pages": 3
}
```

**Backend Optimization:**
```python
# Use async queries with eager loading
async def get_purchase_orders(
    status: str,
    days_back: int,
    page: int,
    page_size: int
):
    # Single query with joins (not N+1)
    query = """
    SELECT
        po.id, po.po_number, po.supplier_id, po.po_date,
        po.expected_delivery, po.status, po.total_cost,
        s.supplier_name,
        u.full_name AS created_by_name,
        COUNT(poi.id) AS items_count
    FROM purchase_orders po
    JOIN suppliers s ON s.id = po.supplier_id
    LEFT JOIN user_profiles u ON u.id = po.created_by
    LEFT JOIN purchase_order_items poi ON poi.purchase_order_id = po.id
    WHERE po.po_date >= CURRENT_DATE - $1::interval
      AND ($2 = 'All' OR po.status = $2)
    GROUP BY po.id, s.supplier_name, u.full_name
    ORDER BY po.po_date DESC
    LIMIT $3 OFFSET $4
    """

    offset = (page - 1) * page_size
    results = await db.fetch_all(
        query,
        f"{days_back} days",
        status,
        page_size,
        offset
    )

    return results
```

##### POST /inventory/purchase-orders
**Create multi-item PO**

**Request:**
```json
{
  "po_number": "PO-2025-002",
  "supplier_id": 5,
  "po_date": "2025-11-17",
  "expected_delivery": "2025-11-25",
  "notes": "Urgent order",
  "items": [
    {
      "item_master_id": 42,
      "ordered_qty": 100.0,
      "unit_cost": 25.50
    },
    {
      "item_master_id": 43,
      "ordered_qty": 50.0,
      "unit_cost": 15.00
    }
  ]
}
```

**Response (201):**
```json
{
  "po": {
    "id": 123,
    "po_number": "PO-2025-002",
    "total_cost": 3300.00,
    "items_count": 2
  },
  "message": "PO created successfully"
}
```

**Business Logic:**
1. Validate PO number is unique
2. Validate supplier exists
3. Validate all items exist in master list
4. Create PO record
5. Create PO items records (transaction)
6. Log activity
7. Return created PO

##### POST /inventory/stock/use
**FIFO stock deduction (used by other modules)**

**Request:**
```json
{
  "item_master_id": 42,
  "quantity": 5.0,
  "purpose": "Fish feeding - Tank 3",
  "module_reference": "biofloc",
  "tank_id": 3,
  "notes": "Morning feeding"
}
```

**Response (200):**
```json
{
  "success": true,
  "quantity_used": 5.0,
  "batches_used": [
    {
      "batch_id": 15,
      "batch_number": "B-2025-001",
      "qty_from_batch": 3.0,
      "unit_cost": 25.50
    },
    {
      "batch_id": 16,
      "batch_number": "B-2025-002",
      "qty_from_batch": 2.0,
      "unit_cost": 26.00
    }
  ],
  "total_cost": 128.50,
  "new_balance": 95.0
}
```

**FIFO Logic:**
```python
async def use_stock_fifo(
    item_master_id: int,
    quantity: float,
    user_id: str,
    purpose: str,
    module_reference: str = None,
    tank_id: int = None
):
    # Get available batches (FIFO order: oldest first)
    batches = await db.fetch_all("""
        SELECT id, batch_number, remaining_qty, unit_cost
        FROM inventory_batches
        WHERE item_master_id = $1
          AND is_active = TRUE
          AND remaining_qty > 0
        ORDER BY purchase_date ASC, id ASC
    """, item_master_id)

    if sum(b.remaining_qty for b in batches) < quantity:
        raise HTTPException(400, "Insufficient stock")

    remaining_to_deduct = quantity
    batches_used = []
    total_cost = 0

    async with db.transaction():
        for batch in batches:
            if remaining_to_deduct <= 0:
                break

            qty_from_batch = min(batch.remaining_qty, remaining_to_deduct)
            new_remaining = batch.remaining_qty - qty_from_batch

            # Update batch
            await db.execute("""
                UPDATE inventory_batches
                SET remaining_qty = $1
                WHERE id = $2
            """, new_remaining, batch.id)

            batches_used.append({
                "batch_id": batch.id,
                "batch_number": batch.batch_number,
                "qty_from_batch": qty_from_batch,
                "unit_cost": batch.unit_cost
            })

            total_cost += qty_from_batch * batch.unit_cost
            remaining_to_deduct -= qty_from_batch

            # Log transaction
            await log_transaction(
                item_master_id,
                batch.id,
                "use",
                -qty_from_batch,
                user_id,
                purpose,
                module_reference,
                tank_id
            )

    return {
        "success": True,
        "quantity_used": quantity,
        "batches_used": batches_used,
        "total_cost": total_cost
    }
```

---

### Biofloc Module

#### Endpoints Overview

| Endpoint | Method | Description | Auth |
|----------|--------|-------------|------|
| `/biofloc/tanks` | GET | List all tanks | User |
| `/biofloc/tanks/{id}` | GET | Get tank details | User |
| `/biofloc/water-tests` | GET | List water tests | User |
| `/biofloc/water-tests` | POST | Add water test | User |
| `/biofloc/water-tests/{id}` | GET | Get test details | User |
| `/biofloc/water-tests/{id}` | PUT | Update test | Owner |
| `/biofloc/water-tests/{id}` | DELETE | Delete test | Owner |
| `/biofloc/growth-records` | GET | List growth records | User |
| `/biofloc/growth-records` | POST | Add growth record | User |
| `/biofloc/growth-records/{id}` | GET | Get record details | User |
| `/biofloc/feed-logs` | GET | List feed logs | User |
| `/biofloc/feed-logs` | POST | Add feed log | User |
| `/biofloc/tank-overview` | GET | Dashboard summary | User |
| `/biofloc/statistics/{tank_id}` | GET | Tank statistics | User |
| `/biofloc/export/{tank_id}` | GET | Export tank data (Excel) | User |

#### Key Endpoint Details

##### POST /biofloc/water-tests
**Add water quality test**

**Request:**
```json
{
  "tank_id": 3,
  "test_date": "2025-11-17",
  "ph": 7.2,
  "dissolved_oxygen": 6.5,
  "ammonia": 0.3,
  "nitrite": 0.1,
  "nitrate": 25.0,
  "temp": 28.5,
  "salinity": 0.0,
  "tds": 450.0,
  "alkalinity": 120.0,
  "notes": "All parameters within range"
}
```

**Validation Rules:**
- pH: 0-14
- Temperature: 0-50°C
- Salinity: 0-50 ppt
- All nutrients: >= 0

**Response (201):**
```json
{
  "test": {
    "id": 456,
    "tank_id": 3,
    "test_date": "2025-11-17",
    "ph": 7.2,
    "dissolved_oxygen": 6.5,
    "tested_by": "uuid",
    "created_at": "2025-11-17T10:30:00Z"
  },
  "message": "Water test recorded successfully"
}
```

##### GET /biofloc/tank-overview
**Dashboard summary for all tanks**

**Response (200):**
```json
{
  "tanks": [
    {
      "id": 3,
      "tank_number": 3,
      "tank_name": "Tank 3 - Fingerlings",
      "capacity_m3": 50.0,
      "last_test_date": "2025-11-17",
      "last_ph": 7.2,
      "last_do": 6.5,
      "last_temp": 28.5,
      "test_overdue": false,
      "last_growth_date": "2025-11-16",
      "current_biomass": 125.5,
      "current_fish_count": 5000,
      "last_mortality": 10
    }
  ],
  "overdue_tanks": 2,
  "total_tanks": 9
}
```

**Performance:** Use database view `biofloc_tank_overview` for single query

---

### Admin Panel

All admin endpoints require `role = "admin"` in JWT.

#### Modules Management

##### GET /admin/modules
**List all modules**

**Response (200):**
```json
{
  "modules": [
    {
      "id": 1,
      "module_key": "inventory",
      "module_name": "Inventory Management",
      "icon": "📦",
      "display_order": 1,
      "is_active": true
    }
  ]
}
```

##### PUT /admin/modules/{id}
**Update module (enable/disable, reorder)**

**Request:**
```json
{
  "is_active": true,
  "display_order": 2
}
```

---

### Dashboard

#### GET /dashboard/summary
**Farm-wide KPIs**

**Response (200):**
```json
{
  "active_tanks": 12,
  "low_stock_items": 7,
  "tasks_due_today": 5,
  "alerts_count": 3,
  "aquaculture": {
    "biofloc_tanks": 9,
    "total_biomass_kg": 1850,
    "feed_used_today_kg": 45
  },
  "inventory": {
    "total_items": 150,
    "total_value": 125000.50,
    "pending_pos": 3
  }
}
```

---

## Tech Stack Recommendations

### Backend (FastAPI)

**Core:**
- **FastAPI** 0.104+
- **Python** 3.11+
- **Pydantic** v2 (data validation)
- **uvicorn** (ASGI server)

**Database:**
- **asyncpg** (async PostgreSQL driver)
- **databases** library (async query builder)
- **supabase-py** (for Auth + convenience)
- **SQLAlchemy** 2.0 (optional, for ORM if needed)

**Authentication:**
- **python-jose** (JWT encoding/decoding)
- **passlib** + **bcrypt** (password hashing - fallback)
- **python-multipart** (form data)

**Additional:**
- **xlsxwriter** (Excel exports)
- **pandas** (data manipulation for exports)
- **python-dotenv** (environment variables)

**Development:**
- **pytest** + **pytest-asyncio** (testing)
- **httpx** (async HTTP client for tests)
- **black** (code formatting)
- **ruff** (linting)

### Frontend (Recommended)

**Option 1: React + Material UI**
- **React** 18+
- **Material-UI** (MUI) v5
- **React Router** v6
- **Axios** (API calls)
- **React Query** (caching, real-time sync)
- **Zustand** or **Redux Toolkit** (state management)

**Option 2: Vue 3 + Vuetify**
- **Vue 3** (Composition API)
- **Vuetify 3**
- **Vue Router** 4
- **Pinia** (state management)
- **Axios**

### Deployment

**Backend:**
- **Docker** container
- **Railway** / **Render** / **DigitalOcean App Platform**
- OR **AWS ECS** / **Google Cloud Run**

**Frontend:**
- **Vercel** (optimal for React/Next.js)
- **Netlify**
- **Cloudflare Pages**

**Database:**
- **Supabase** (managed PostgreSQL + Auth)

---

## Performance Requirements

### Response Time Targets

| Endpoint Type | Target | Max Acceptable |
|---------------|--------|----------------|
| Auth endpoints | <100ms | 200ms |
| List endpoints (paginated) | <200ms | 500ms |
| Detail endpoints | <100ms | 300ms |
| Create/Update | <300ms | 1000ms |
| Complex queries (analytics) | <500ms | 2000ms |
| Excel exports | <2000ms | 5000ms |

### Specific Endpoints (Critical)

- **GET /inventory/purchase-orders**: <200ms (currently 2-3s in Streamlit)
- **GET /biofloc/tank-overview**: <300ms
- **POST /inventory/stock/use**: <200ms (used by other modules)
- **GET /dashboard/summary**: <500ms

### Concurrency

- **Target**: 1000+ concurrent users
- **Database connections**: Pool of 20-50 connections
- **Async operations**: All database queries async
- **Caching**: Redis for frequently accessed data (optional Phase 2)

### Database Optimization

1. **Indexes** on:
   - All foreign keys
   - Frequently queried date fields
   - Status fields
   - User IDs in logs

2. **Pagination**:
   - All list endpoints MUST paginate
   - Default page size: 20-50 items
   - Max page size: 100 items

3. **Query Optimization**:
   - Use database views for complex joins
   - Single query for list endpoints (no N+1)
   - Eager loading for related data
   - Limit SELECT columns to needed fields only

4. **Connection Pooling**:
   ```python
   # asyncpg pool
   DATABASE_POOL_MIN = 10
   DATABASE_POOL_MAX = 50
   ```

---

## Migration Strategy

### Phase 1: Backend Foundation (Week 1-2)

**Goals:**
- FastAPI project structure
- Database setup (Supabase)
- Authentication working
- Admin user management APIs
- Activity logging

**Deliverables:**
1. FastAPI app with JWT auth
2. All database tables created
3. User CRUD endpoints
4. Permission management endpoints
5. Activity log endpoints
6. Pytest test suite (>80% coverage)

### Phase 2: Inventory Module (Week 3-4)

**Goals:**
- Complete inventory backend
- All CRUD operations
- FIFO stock logic
- PO management
- Excel exports

**Deliverables:**
1. All inventory endpoints functional
2. FIFO stock deduction tested
3. PO creation/status updates working
4. Supplier/category management
5. Low stock & expiry alerts

### Phase 3: Biofloc Module (Week 5-6)

**Goals:**
- Complete biofloc backend
- Water testing
- Growth tracking
- Feed logging
- Tank overview

**Deliverables:**
1. All biofloc endpoints functional
2. Tank overview dashboard API
3. Statistics calculations
4. Excel exports
5. Integration with inventory (feed usage)

### Phase 4: Frontend (Week 7-10)

**Goals:**
- React/Vue SPA
- Authentication UI
- All module UIs
- Admin panel UI
- Dashboard

**Deliverables:**
1. Login/logout flow
2. User management UI
3. Inventory UI (all tabs)
4. Biofloc UI (all tabs)
5. Dashboard UI
6. Mobile-responsive design

### Phase 5: Testing & Deployment (Week 11-12)

**Goals:**
- End-to-end testing
- Performance optimization
- Deployment to production
- Data migration (if needed)

**Deliverables:**
1. Load testing results
2. Security audit passed
3. Production deployment
4. User training materials
5. API documentation (auto-generated)

---

## Current Streamlit Code Patterns to Preserve

### Business Logic (KEEP)

**1. FIFO Stock Deduction:**
- Implemented in `db_inventory.py:deduct_stock_fifo()`
- Critical for accurate costing
- Reuse logic in FastAPI service layer

**2. Input Validation:**
- pH range: 0-14
- Temperature: 0-50°C
- Non-negative quantities
- Implement as Pydantic validators

**3. Activity Logging:**
- Every significant action logged
- Includes user, module, metadata
- Keep this pattern in FastAPI middleware

**4. Role-Based Access:**
- Admins: all access
- Users: granular module permissions
- Preserve this hybrid system

### API Patterns (ALREADY GOOD)

**inventory/api.py** (95% reusable):
```python
# Current pattern - perfect for FastAPI!
def use_stock_item(...) -> Dict:
    return {
        'success': bool,
        'message': str,
        'transaction_id': int,
        'batches_used': List[Dict]
    }
```

**Convert to FastAPI:**
```python
@router.post("/stock/use")
async def use_stock_item(...) -> UseStockResponse:
    result = await InventoryService.use_stock(...)
    return result
```

### Error Handling (IMPROVE)

**Current (Streamlit):**
```python
if not result:
    st.error("❌ Failed to create PO")
    return
```

**FastAPI (Better):**
```python
if not result:
    raise HTTPException(
        status_code=400,
        detail="Failed to create PO: invalid supplier"
    )
```

---

## API Documentation (Auto-Generated)

FastAPI automatically generates:

**Swagger UI:** `https://api.farmmanagement.com/docs`
**ReDoc:** `https://api.farmmanagement.com/redoc`
**OpenAPI JSON:** `https://api.farmmanagement.com/openapi.json`

No manual documentation needed!

---

## Security Considerations

### 1. Input Validation
- All inputs validated via Pydantic schemas
- SQL injection prevented by parameterized queries
- XSS prevention via proper escaping

### 2. Authentication
- JWT tokens with short expiry (15 min access, 7 day refresh)
- HTTP-only cookies (recommended) OR secure localStorage
- Password hashing via bcrypt (min 12 rounds)

### 3. Authorization
- Every protected endpoint checks JWT
- Module access verified via database
- Admin-only endpoints strictly enforced

### 4. Rate Limiting
- Implement rate limiting on auth endpoints
- 5 login attempts per minute per IP
- 10 requests/second per user for API

### 5. CORS
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://farm.yourdomain.com"],  # Whitelist only
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

### 6. HTTPS Only
- All production traffic over HTTPS
- HSTS headers enabled
- Secure cookie flags

---

## Environment Variables

```bash
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key
SUPABASE_ANON_KEY=your_anon_key

# Database (Direct connection for async)
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# JWT
JWT_SECRET_KEY=generate_random_256_bit_key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# App
APP_ENV=production
API_BASE_URL=https://api.farmmanagement.com
FRONTEND_URL=https://farm.farmmanagement.com

# CORS
ALLOWED_ORIGINS=https://farm.farmmanagement.com,https://admin.farmmanagement.com
```

---

## Testing Strategy

### 1. Unit Tests
- All service layer functions
- Pydantic validators
- Utility functions
- Target: >80% coverage

### 2. Integration Tests
- API endpoints (all)
- Database operations
- Auth flow end-to-end

### 3. Performance Tests
- Load testing with Locust
- Target: 1000 concurrent users
- Critical endpoints <200ms

### 4. Security Tests
- OWASP top 10 checks
- JWT validation
- Permission boundary tests

---

## Migration Checklist

**Pre-Migration:**
- [ ] New Supabase project created
- [ ] Database schema deployed
- [ ] Test data populated
- [ ] Environment variables configured

**Development:**
- [ ] FastAPI project initialized
- [ ] Auth endpoints working
- [ ] User management working
- [ ] Inventory module complete
- [ ] Biofloc module complete
- [ ] All tests passing

**Pre-Launch:**
- [ ] Performance tests passed
- [ ] Security audit complete
- [ ] API documentation reviewed
- [ ] Frontend integrated
- [ ] Staging environment tested

**Launch:**
- [ ] Production deployment
- [ ] DNS configured
- [ ] Monitoring enabled
- [ ] Users migrated (if needed)
- [ ] Old system deprecated

---

## Support & Maintenance

**Monitoring:**
- Application performance monitoring (APM)
- Error tracking (Sentry recommended)
- Database query performance
- API response times

**Logging:**
- Structured logging (JSON format)
- Log levels: DEBUG, INFO, WARNING, ERROR
- Centralized log aggregation

**Backup:**
- Daily database backups (Supabase automatic)
- Weekly full exports
- Point-in-time recovery enabled

---

## Contact & Questions

For questions about this specification:
- Review current codebase: `/home/user/farm-2-app`
- Check Streamlit version: 1.1.0
- Reference database: Supabase PostgreSQL

---

**End of Specification**

*This document contains all information needed to build a production-ready FastAPI backend for the Farm Management System, migrating from the current Streamlit implementation while preserving all business logic and improving performance 10-100x.*
