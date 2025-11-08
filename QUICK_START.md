# 🚀 QUICK START GUIDE
## Farm Management System V1.1.0

### 📦 What You Have
Complete Phase 1 project with:
- ✅ 12 Python files
- ✅ 5 Documentation files
- ✅ Working authentication system
- ✅ Fixed user management
- ✅ Farm-focused dashboard
- ✅ Admin panel with all features

---

## ⚡ 5-Minute Setup

### Step 1: Extract Files
```bash
# Extract the farm_management_app folder
cd farm_management_app
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Configure Supabase
```bash
# Copy template
cp .streamlit/secrets.toml.template .streamlit/secrets.toml

# Edit with your credentials
nano .streamlit/secrets.toml  # or use any editor
```

Add your Supabase credentials:
```toml
[supabase]
url = "https://YOUR-PROJECT.supabase.co"
service_role_key = "YOUR-SERVICE-ROLE-KEY"
```

### Step 4: Set Up Database (Important!)
Before running the app, create these tables in Supabase:

**Minimum Required Tables:**
```sql
-- 1. Roles table
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    role_name VARCHAR(50) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Insert roles
INSERT INTO roles (role_name) VALUES ('Admin'), ('User');

-- 2. User profiles table
CREATE TABLE user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name VARCHAR(255) NOT NULL,
    role_id INT REFERENCES roles(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 3. Modules table
CREATE TABLE modules (
    id SERIAL PRIMARY KEY,
    module_name VARCHAR(100) NOT NULL,
    module_key VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    icon VARCHAR(10) DEFAULT '⚙️',
    display_order INT DEFAULT 99,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 4. User permissions table
CREATE TABLE user_module_permissions (
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    module_id INT REFERENCES modules(id) ON DELETE CASCADE,
    can_access BOOLEAN DEFAULT TRUE,
    granted_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (user_id, module_id)
);

-- 5. Activity logs table
CREATE TABLE activity_logs (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    user_email VARCHAR(255),
    action_type VARCHAR(50),
    module_key VARCHAR(100),
    description TEXT,
    success BOOLEAN DEFAULT TRUE,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 6. Create user_details view
CREATE VIEW user_details AS
SELECT 
    up.id,
    up.full_name,
    up.role_id,
    up.is_active,
    r.role_name,
    up.created_at,
    up.updated_at
FROM user_profiles up
LEFT JOIN roles r ON up.role_id = r.id;

-- 7. Create user_accessible_modules view
CREATE VIEW user_accessible_modules AS
SELECT 
    u.id AS user_id,
    m.*
FROM auth.users u
CROSS JOIN modules m
LEFT JOIN user_profiles up ON u.id = up.id
LEFT JOIN roles r ON up.role_id = r.id
WHERE r.role_name = 'Admin'
   OR EXISTS (
       SELECT 1 
       FROM user_module_permissions ump
       WHERE ump.user_id = u.id 
         AND ump.module_id = m.id 
         AND ump.can_access = TRUE
   );
```

### Step 5: Create First Admin User
In Supabase Dashboard > Authentication:
1. Click "Add User"
2. Enter email and password
3. Confirm email (or auto-confirm)

Then in SQL Editor:
```sql
-- Add to user_profiles
INSERT INTO user_profiles (id, full_name, role_id, is_active)
VALUES (
    '[USER-UUID-FROM-AUTH]',
    'Admin User',
    (SELECT id FROM roles WHERE role_name = 'Admin'),
    TRUE
);
```

### Step 6: Run the App
```bash
streamlit run app.py
```

Visit: http://localhost:8501

---

## ✅ First Login Checklist

After app starts:

1. **Login** with admin credentials
2. **Test Dashboard** - Should show placeholder metrics
3. **Go to Admin Panel > User Management**
4. **Create a Test User**
   - Enter email, name, select "User" role
   - Copy temporary password shown
5. **Go to User Permissions**
   - Assign modules to test user
6. **Logout and test** user login
7. **Verify** user sees only assigned modules

---

## 🐛 Common Startup Issues

### "Failed to connect to database"
**Fix:** Check `.streamlit/secrets.toml` has correct URL and key

### "User profile not found"
**Fix:** Run the SQL to create tables and views

### "Module not found"
**Fix:** This is normal - modules will be built in Phase 2

### User management not working
**Fix:** Ensure using `service_role_key` NOT `anon_key`

---

## 📁 File Locations

**Core Files:**
- `app.py` - Start here
- `auth/session.py` - User session logic
- `config/database.py` - All database operations
- `components/dashboard.py` - Main dashboard
- `components/admin_panel.py` - User management

**Documentation:**
- `README.md` - Complete guide
- `PHASE_1_SUMMARY.md` - What was done
- `PROJECT_STRUCTURE.md` - Architecture
- This file - Quick start

---

## 🎯 What Works Now

✅ **Authentication**
- Login/logout
- Session management
- Role-based access

✅ **User Management** (Admin)
- Create users (with temp password)
- Edit users (name, role, status)
- Delete users (with confirmation)
- Export user list

✅ **Permissions** (Admin)
- Assign modules to users
- View/edit all permissions

✅ **Dashboard**
- Farm overview (placeholder data)
- Activity logs
- Quick stats

✅ **Admin Panel**
- User management
- Permission management
- Activity log viewing
- Module management

---

## 🔜 What's Next (Phase 2)

After testing Phase 1, we'll build:

1. **Biofloc Module** - 9 tank tracking
2. **RAS Module** - System monitoring
3. **Inventory Module** - Stock management
4. **Tasks Module** - Daily operations
5. **Crop Modules** - Microgreens, hydroponics, etc.
6. **Database Editor** - Direct table access

Each module will have:
- Data entry forms
- Real-time metrics
- Excel exports
- Photo uploads
- Mobile-friendly UI

---

## 💡 Pro Tips

1. **Always use Admin for first login**
2. **Create test users before assigning real work**
3. **Export user list as backup**
4. **Check activity logs regularly**
5. **Test on mobile device before field deployment**

---

## 📞 Need Help?

1. Check `README.md` for detailed setup
2. Review `PHASE_1_SUMMARY.md` for what changed
3. Check code comments in Python files
4. All functions have docstrings

---

**You're Ready to Start! 🚀**

Run: `streamlit run app.py`

---

*Farm Management System V1.1.0 - Phase 1 Complete*
