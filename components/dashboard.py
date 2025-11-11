"""
Farm Management Dashboard
Displays farm-wide KPIs and module statistics

VERSION: 1.1.0
DATE: November 8, 2025
CHANGES FROM V1.0.0:
- Complete rebuild from B2C order dashboard
- Farm-focused metrics and visualizations
- Placeholder metrics for Phase 2 implementation
"""
import streamlit as st
from datetime import datetime, date, timedelta
import pandas as pd
from auth.session import SessionManager
from config.database import ActivityLogger


def show_dashboard():
    """Display farm management dashboard with key metrics"""
    
    profile = SessionManager.get_user_profile()
    user = SessionManager.get_user()
    
    # Welcome message
    st.markdown(f"### Welcome back, {profile.get('full_name', user.get('email'))}! 👋")
    st.markdown("---")
    
    # Dashboard Title
    st.markdown("## 🌾 Farm Management Dashboard")
    st.caption(f"📅 {date.today().strftime('%B %d, %Y')}")
    
    st.markdown("---")
    
    # Quick Stats Row
    st.markdown("### 📊 Today's Overview")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="🐟 Active Tanks",
            value="12",
            delta="2 new",
            help="Biofloc + RAS tanks currently in operation"
        )
    
    with col2:
        st.metric(
            label="📦 Low Stock Items",
            value="7",
            delta="-3",
            delta_color="inverse",
            help="Items below reorder threshold"
        )
    
    with col3:
        st.metric(
            label="✅ Tasks Due Today",
            value="5",
            delta="2 completed",
            help="Tasks scheduled for today"
        )
    
    with col4:
        st.metric(
            label="⚠️ Alerts",
            value="3",
            delta="1 new",
            delta_color="inverse",
            help="Critical notifications requiring attention"
        )
    
    st.markdown("---")
    
    # Module Sections
    tab1, tab2, tab3, tab4 = st.tabs([
        "🐟 Aquaculture", 
        "🌱 Crop Systems", 
        "📋 Operations",
        "🔔 Recent Activity"
    ])
    
    with tab1:
        show_aquaculture_summary()
    
    with tab2:
        show_crop_systems_summary()
    
    with tab3:
        show_operations_summary()
    
    with tab4:
        show_recent_activity()
    
    # Footer
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🔄 Refresh Dashboard", width='stretch'):
            st.rerun()


def show_aquaculture_summary():
    """Display aquaculture systems summary"""
    st.markdown("### 🐟 Aquaculture Systems")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Biofloc Tanks")
        st.info("📌 9 tanks tracked individually")
        
        # Placeholder metrics
        metrics = {
            "Active Tanks": "9/9",
            "Avg Water Quality": "Good ✅",
            "Total Biomass": "1,850 kg",
            "Feed Used Today": "45 kg"
        }
        
        for label, value in metrics.items():
            st.markdown(f"**{label}:** {value}")
        
        st.caption("💡 Phase 2: Real-time tank monitoring")
    
    with col2:
        st.markdown("#### RAS System")
        st.info("📌 System-wide water testing")
        
        # Placeholder metrics
        metrics = {
            "Active Tanks": "3/3",
            "System Health": "Excellent ✅",
            "Total Biomass": "650 kg",
            "Last Water Test": "2 hours ago"
        }
        
        for label, value in metrics.items():
            st.markdown(f"**{label}:** {value}")
        
        st.caption("💡 Phase 2: Automated water parameter tracking")
    
    st.markdown("---")
    
    # Quick action buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        st.button("📊 View Biofloc Data", width='stretch', disabled=True)
    with col2:
        st.button("🔬 View RAS Data", width='stretch', disabled=True)
    with col3:
        st.button("📝 Log Water Test", width='stretch', disabled=True)


def show_crop_systems_summary():
    """Display crop production systems summary"""
    st.markdown("### 🌱 Crop Production Systems")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Microgreens")
        st.info("📌 Fast-cycle crop production")
        metrics = {
            "Active Trays": "48",
            "Ready to Harvest": "12 trays",
            "Next Harvest": "Tomorrow",
            "Weekly Yield": "~25 kg"
        }
        for label, value in metrics.items():
            st.markdown(f"**{label}:** {value}")
        st.caption("💡 Phase 2: Batch tracking and yield optimization")
        
        st.markdown("---")
        
        st.markdown("#### Coco Coir Production")
        st.info("📌 Alternative growing medium")
        metrics = {
            "Active Beds": "6",
            "Substrate Quality": "Good ✅",
            "Monthly Output": "~180 kg",
            "Next Refresh": "In 5 days"
        }
        for label, value in metrics.items():
            st.markdown(f"**{label}:** {value}")
        st.caption("💡 Phase 2: Bed rotation and quality tracking")
    
    with col2:
        st.markdown("#### Hydroponics")
        st.info("📌 Water-based crop cultivation")
        metrics = {
            "Active Systems": "4",
            "System Health": "Good ✅",
            "Current Crops": "Lettuce, Herbs",
            "Nutrient Levels": "Optimal"
        }
        for label, value in metrics.items():
            st.markdown(f"**{label}:** {value}")
        st.caption("💡 Phase 2: Nutrient management and growth tracking")
        
        st.markdown("---")
        
        st.markdown("#### Open Field Crops")
        st.info("📌 Traditional farming operations")
        metrics = {
            "Active Fields": "3",
            "Total Area": "2.5 hectares",
            "Current Season": "Winter Crops",
            "Next Planting": "15 days"
        }
        for label, value in metrics.items():
            st.markdown(f"**{label}:** {value}")
        st.caption("💡 Phase 2: Field management and crop rotation")
    
    st.markdown("---")
    
    # Quick action buttons
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.button("🌱 Microgreens", width='stretch', disabled=True)
    with col2:
        st.button("💧 Hydroponics", width='stretch', disabled=True)
    with col3:
        st.button("🥥 Coco Coir", width='stretch', disabled=True)
    with col4:
        st.button("🌾 Open Field", width='stretch', disabled=True)


def show_operations_summary():
    """Display operational metrics"""
    st.markdown("### 📋 Farm Operations")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📦 Inventory Status")
        st.info("Shared across all farm modules")
        
        # Placeholder low stock items
        st.markdown("**⚠️ Low Stock Items:**")
        low_stock = [
            {"Item": "Fish Feed (Premium)", "Current": "45 kg", "Reorder": "100 kg"},
            {"Item": "Microgreen Seeds (Radish)", "Current": "0.5 kg", "Reorder": "2 kg"},
            {"Item": "pH Down Solution", "Current": "2 L", "Reorder": "5 L"},
            {"Item": "Hydroponic Nutrients", "Current": "8 L", "Reorder": "20 L"},
        ]
        
        df = pd.DataFrame(low_stock)
        st.dataframe(df, width='stretch', hide_index=True)
        
        st.button("📦 View Full Inventory", width='stretch', disabled=True)
        st.caption("💡 Phase 2: Auto-reorder alerts and supplier integration")
    
    with col2:
        st.markdown("#### ✅ Task Management")
        st.info("Multi-user task tracking")
        
        # Placeholder tasks
        st.markdown("**📋 Today's Tasks:**")
        tasks = [
            {"Task": "Water quality test - Biofloc Tank 3", "Assigned": "User 1", "Status": "⏳ Pending"},
            {"Task": "Harvest microgreen trays 12-18", "Assigned": "User 2", "Status": "⏳ Pending"},
            {"Task": "Feed RAS system", "Assigned": "User 1", "Status": "✅ Done"},
            {"Task": "Check hydroponic pH levels", "Assigned": "User 2", "Status": "⏳ Pending"},
        ]
        
        df_tasks = pd.DataFrame(tasks)
        st.dataframe(df_tasks, width='stretch', hide_index=True)
        
        st.button("✅ View All Tasks", width='stretch', disabled=True)
        st.caption("💡 Phase 2: Priority system and photo completion tracking")
    
    st.markdown("---")
    
    # Database Editor (Admin only)
    if SessionManager.is_admin():
        st.markdown("#### 🗄️ Database Management")
        st.info("Admin-only module for direct database access")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.button("🗄️ Database Editor", width='stretch', disabled=True)
        with col2:
            st.button("📥 Export Tables", width='stretch', disabled=True)
        with col3:
            st.button("🔧 System Settings", width='stretch', disabled=True)
        
        st.caption("💡 Phase 2: View/edit/download any table as Excel")


def show_recent_activity():
    """Display recent farm activity"""
    st.markdown("### 🔔 Recent Activity")
    
    # Get recent logs
    logs = ActivityLogger.get_all_activity(limit=20)
    
    if logs:
        df = pd.DataFrame(logs)
        
        # Select display columns
        if all(col in df.columns for col in ['created_at', 'user_email', 'action_type', 'description']):
            display_df = df[['created_at', 'user_email', 'action_type', 'description']].copy()
            display_df.columns = ['Time', 'User', 'Action', 'Description']
            
            # Format timestamp
            display_df['Time'] = pd.to_datetime(display_df['Time'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M')
            
            st.dataframe(display_df, width='stretch', hide_index=True, height=400)
        else:
            st.info("Activity log format differs from expected. Check database schema.")
    else:
        st.info("No recent activity to display.")
        st.markdown("**Getting Started:**")
        st.markdown("1. Add users in Admin Panel")
        st.markdown("2. Configure module permissions")
        st.markdown("3. Set up farm modules (Phase 2)")
        st.markdown("4. Start logging farm operations")
    
    st.markdown("---")
    
    # Export activity log
    if SessionManager.is_admin():
        if st.button("📥 Export Activity Log", width='stretch'):
            if logs:
                df_export = pd.DataFrame(logs)
                csv = df_export.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"activity_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            else:
                st.info("No activity to export")
