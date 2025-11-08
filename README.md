# Farm Management System (Farm2)
**Version:** 1.1.0  
**Phase:** 1 - Clean Project Setup  
**Date:** November 8, 2025

## 📋 Overview
Multi-module farm management system built with Streamlit and Supabase PostgreSQL.

### Farm Modules (Phase 2)
- 🐟 **Biofloc Aquaculture** - Individual tank water testing & growth tracking (9 tanks)
- 🔬 **RAS Aquaculture** - System-wide water testing across shared tanks
- 🌱 **Microgreens** - Fast-cycle crop production
- 💧 **Hydroponics** - Water-based crop cultivation
- 🥥 **Coco Coir Production** - Alternative growing medium
- 🌾 **Open Field Crops** - Traditional farming operations
- 📦 **Inventory Management** - Shared inventory with auto-reorder alerts
- ✅ **Task Management** - Multi-user assignment with priority tracking
- 🗄️ **Database Editor** - Admin-only direct table access (view/edit/export)

### Core Features
- **Authentication:** Role-based access (Admin + User)
- **Mobile-friendly:** Responsive design for field use
- **Excel Exports:** All data exportable
- **Activity Logging:** Comprehensive audit trails
- **Multi-user:** 1-3 concurrent users supported

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Supabase account
- Git

### Installation

1. **Clone/Download** this project:
```bash
cd farm_management_app
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure Supabase:**
   - Copy `.streamlit/secrets.toml.template` to `.streamlit/secrets.toml`
   - Fill in your Supabase credentials:
     - URL from Supabase Project Settings
     - Service Role Key (NOT anon key!)

4. **Set up Database:**
   - Run the SQL schema (Phase 2)
   - Create tables for modules, users, permissions, activity logs
   - Set up RLS policies

5. **Run the app:**
```bash
streamlit run app.py
```

---

## 📁 Project Structure

```
farm_management_app/
├── app.py                    # Main entry point
├── requirements.txt          # Python dependencies
├── .streamlit/
│   └── secrets.toml         # Supabase credentials (create manually)
├── auth/
│   ├── session.py           # Session management
│   └── login.py             # Login UI
├── config/
│   └── database.py          # Database operations
├── components/
│   ├── sidebar.py           # Navigation sidebar
│   ├── dashboard.py         # Farm dashboard
│   └── admin_panel.py       # Admin controls
└── modules/
    ├── module_template.py   # Template for new modules
    └── [farm modules]       # Phase 2 implementation
```

---

## 🔧 Configuration

### Supabase Setup

1. **Create Project** at supabase.com
2. **Get Credentials:**
   - Go to Project Settings > API
   - Copy Project URL
   - Copy `service_role` key (NOT anon key!)

3. **Database Tables Required:**
   - `roles` - User roles (Admin, User)
   - `user_profiles` - User information
   - `modules` - Farm modules registry
   - `user_module_permissions` - User access control
   - `activity_logs` - Audit trail
   - Module-specific tables (Phase 2)

4. **RLS Policies:**
   - Enable Row Level Security on all tables
   - Configure admin-only access for sensitive tables
   - Allow users to read their own data

### Environment Variables

Create `.streamlit/secrets.toml`:
```toml
[supabase]
url = "https://your-project.supabase.co"
service_role_key = "your-service-role-key-here"
```

⚠️ **Security:** Never commit `secrets.toml` to version control!

---

## 👥 User Roles

### Admin
- Full system access
- User management (create, edit, delete)
- Permission management
- All modules
- Activity log access
- Database editor

### User
- Access to assigned modules only
- View own activity logs
- Standard farm operations

---

## 🐛 Troubleshooting

### Common Issues

**"Failed to connect to database"**
- Check `secrets.toml` exists in `.streamlit/` folder
- Verify URL and service_role_key are correct
- Ensure no extra spaces in credentials

**"User profile not found"**
- Run database migrations
- Check `user_profiles` table exists
- Verify user was created properly

**"Module not found"**
- Check module is registered in `modules` table
- Verify `module_key` matches filename
- Ensure module has `show()` function

**User management not working**
- Verify using `service_role_key` (NOT anon key)
- Check RLS policies allow admin operations
- Ensure Supabase Auth is enabled

---

## 📝 Development

### Adding New Modules

1. Copy `modules/module_template.py`
2. Rename to `modules/your_module.py`
3. Update `module_key` in `require_module_access()`
4. Implement your module logic
5. Register in database:
```sql
INSERT INTO modules (module_name, module_key, description, icon, display_order)
VALUES ('Your Module', 'your_module', 'Description', '🎯', 10);
```

### Code Standards
- Follow existing code structure
- Add docstrings to functions
- Log user actions with ActivityLogger
- Handle errors gracefully
- Test with both Admin and User roles

---

## 🔐 Security Best Practices

1. **Never expose service_role_key** in client-side code
2. **Use RLS policies** for all sensitive tables
3. **Validate user input** before database operations
4. **Log admin actions** for audit trails
5. **Regular backups** of Supabase database
6. **Keep dependencies updated** (`pip install --upgrade`)

---

## 📊 Phase 2 Roadmap

### Module Implementation Priority
1. ✅ **Biofloc & RAS** - Core aquaculture tracking
2. 📦 **Inventory** - Shared stock management
3. ✅ **Tasks** - Daily operations tracking
4. 🌱 **Crop Systems** - Microgreens, hydroponics, etc.
5. 🗄️ **Database Editor** - Admin data management

### Features to Add
- Photo uploads for tasks/inspections
- Automated alerts (low stock, water quality)
- Mobile camera integration
- Export reports (daily/weekly/monthly)
- Data visualization charts
- Batch operations for efficiency

---

## 🆘 Support

### Getting Help
- Check `PROJECT_STRUCTURE.md` for file organization
- Review `module_template.py` for module examples
- Test admin features in sandbox environment first

### Version History
- **V1.1.0** (Nov 8, 2025) - Phase 1 complete, fixed user management
- **V1.0.0** - Original B2C application (deprecated)

---

## 📄 License
Internal farm management tool - All rights reserved

---

**Built with ❤️ for modern farm operations**
