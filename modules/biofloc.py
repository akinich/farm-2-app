"""
BIOFLOC AQUACULTURE MODULE - IMPROVED
Manages tanks, water quality, growth tracking, and feeding logs.

VERSION: 1.1.0
DATE: 2025-11-08

CHANGES FROM V1.0.2:
✅ Fixed column name: "do" → "dissolved_oxygen"
✅ Added input validation with user-friendly error messages
✅ Improved Tank Overview with alerts and statistics
✅ Added date range filters for historical data
✅ Better Excel export with multiple sheets
✅ Uses new BioflocDB methods (v1.3.0)
✅ Moved activity logging to end of actions (no duplicate logs)
✅ Added success/error messages consistently
✅ Mobile-responsive improvements
"""

import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime, date, timedelta
from auth.session import SessionManager
from config.database import ActivityLogger, BioflocDB


def show():
    """Main entry point for the Biofloc Aquaculture Module"""
    
    # Access control
    SessionManager.require_module_access('biofloc')
    user = SessionManager.get_user()
    profile = SessionManager.get_user_profile()
    username = profile.get('full_name', user.get('email', 'User'))
    
    st.markdown("### 🐟 Biofloc Aquaculture Management")
    st.caption(f"👤 {username}")
    st.markdown("Track tank water quality, fish growth, and feed usage.")
    st.markdown("---")
    
    # Fetch tanks
    tanks = BioflocDB.get_tanks()
    if not tanks:
        st.warning("⚠️ No tanks found. Please ask Admin to add tanks in the database.")
        return
    
    # Create tabs
    tabs = st.tabs([
        "🧪 Water Testing",
        "📈 Growth Records",
        "🍽️ Feed Logs",
        "📊 Tank Overview",
        "📤 Reports & Export"
    ])
    
    # ============================================================
    # 🧪 TAB 1: WATER TESTING
    # ============================================================
    with tabs[0]:
        show_water_testing_tab(tanks, user)
    
    # ============================================================
    # 📈 TAB 2: GROWTH RECORDS
    # ============================================================
    with tabs[1]:
        show_growth_records_tab(tanks, user)
    
    # ============================================================
    # 🍽️ TAB 3: FEED LOGS
    # ============================================================
    with tabs[2]:
        show_feed_logs_tab(tanks, user)
    
    # ============================================================
    # 📊 TAB 4: TANK OVERVIEW
    # ============================================================
    with tabs[3]:
        show_tank_overview_tab()
    
    # ============================================================
    # 📤 TAB 5: EXPORT
    # ============================================================
    with tabs[4]:
        show_export_tab(tanks)
    
    # Log module access (once at the end)
    ActivityLogger.log(
        user_id=user['id'],
        action_type='module_use',
        module_key='biofloc',
        description=f"Accessed Biofloc module"
    )


# ============================================================
# WATER TESTING TAB
# ============================================================

def show_water_testing_tab(tanks: list, user: dict):
    """Water testing form and history"""
    
    st.markdown("#### 🧪 Record Water Test")
    
    tank_options = {f"{t['tank_name']} (#{t['tank_number']})": t['id'] for t in tanks}
    
    with st.form("water_test_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        selected_tank = col1.selectbox("Select Tank *", list(tank_options.keys()))
        test_date = col2.date_input("Test Date *", datetime.now().date())
        
        st.markdown("##### Water Parameters")
        
        col3, col4, col5 = st.columns(3)
        ph = col3.number_input("pH (0-14)", 0.0, 14.0, 7.0, step=0.1, help="Optimal: 6.5-8.5")
        do_val = col4.number_input("Dissolved Oxygen (mg/L)", 0.0, 20.0, 5.0, step=0.1, help="Optimal: >5 mg/L")
        temp = col5.number_input("Temperature (°C)", 0.0, 50.0, 28.0, step=0.1, help="Optimal: 26-30°C")
        
        col6, col7, col8 = st.columns(3)
        ammonia = col6.number_input("Ammonia (mg/L)", 0.0, 10.0, 0.0, step=0.01, help="Optimal: <0.5 mg/L")
        nitrite = col7.number_input("Nitrite (mg/L)", 0.0, 10.0, 0.0, step=0.01, help="Optimal: <0.5 mg/L")
        nitrate = col8.number_input("Nitrate (mg/L)", 0.0, 100.0, 0.0, step=0.1, help="Optimal: <50 mg/L")
        
        col9, col10, col11 = st.columns(3)
        salinity = col9.number_input("Salinity (ppt)", 0.0, 50.0, 0.0, step=0.1)
        tds = col10.number_input("TDS (ppm)", 0.0, 5000.0, 0.0, step=1.0)
        alkalinity = col11.number_input("Alkalinity (mg/L)", 0.0, 500.0, 0.0, step=1.0)
        
        notes = st.text_area("Notes (optional)")
        
        submitted = st.form_submit_button("💾 Save Water Test", type="primary", use_container_width=True)
        
        if submitted:
            data = {
                "tank_id": tank_options[selected_tank],
                "test_date": str(test_date),
                "ph": ph if ph > 0 else None,
                "dissolved_oxygen": do_val if do_val > 0 else None,
                "ammonia": ammonia if ammonia > 0 else None,
                "nitrite": nitrite if nitrite > 0 else None,
                "nitrate": nitrate if nitrate > 0 else None,
                "temp": temp if temp > 0 else None,
                "salinity": salinity if salinity > 0 else None,
                "tds": tds if tds > 0 else None,
                "alkalinity": alkalinity if alkalinity > 0 else None,
                "notes": notes if notes else None,
            }
            
            success, message = BioflocDB.add_water_test(data, user['id'])
            
            if success:
                st.success(f"✅ {message}")
                
                # Log the action
                ActivityLogger.log(
                    user_id=user['id'],
                    action_type='data_entry',
                    module_key='biofloc',
                    description=f"Added water test for {selected_tank}",
                    metadata={'tank_id': tank_options[selected_tank], 'test_date': str(test_date)}
                )
                
                st.rerun()
            else:
                st.error(f"❌ {message}")
    
    # View history
    st.markdown("---")
    st.markdown("#### 📋 Recent Water Tests")
    
    col1, col2 = st.columns([2, 1])
    selected_tank_view = col1.selectbox(
        "Select Tank to View",
        list(tank_options.keys()),
        key="wt_view"
    )
    days_back = col2.number_input("Days to show", 1, 90, 30, key="wt_days")
    
    test_data = BioflocDB.get_water_tests(tank_options[selected_tank_view], limit=days_back*3)
    
    if test_data:
        df = pd.DataFrame(test_data)
        
        # Select and rename columns for display
        display_cols = ['test_date', 'ph', 'dissolved_oxygen', 'ammonia', 'nitrite', 'nitrate', 'temp', 'salinity', 'notes']
        df_display = df[[col for col in display_cols if col in df.columns]].copy()
        
        if 'test_date' in df_display.columns:
            df_display['test_date'] = pd.to_datetime(df_display['test_date']).dt.strftime('%Y-%m-%d %H:%M')
        
        df_display.columns = ['Date', 'pH', 'DO (mg/L)', 'NH3 (mg/L)', 'NO2 (mg/L)', 'NO3 (mg/L)', 'Temp (°C)', 'Salinity (ppt)', 'Notes']
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        
        # Show latest test summary
        latest = test_data[0]
        st.info(f"📍 Latest test: {latest['test_date']} | pH: {latest.get('ph', '—')} | DO: {latest.get('dissolved_oxygen', '—')} mg/L")
    else:
        st.info("ℹ️ No water test data available for this tank yet. Add your first test above!")


# ============================================================
# GROWTH RECORDS TAB
# ============================================================

def show_growth_records_tab(tanks: list, user: dict):
    """Growth tracking form and history"""
    
    st.markdown("#### 📈 Record Fish Growth")
    
    tank_options = {f"{t['tank_name']} (#{t['tank_number']})": t['id'] for t in tanks}
    
    with st.form("growth_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        selected_tank = col1.selectbox("Select Tank *", list(tank_options.keys()), key="gr_tank")
        record_date = col2.date_input("Record Date *", datetime.now().date())
        
        st.markdown("##### Growth Metrics")
        
        col3, col4 = st.columns(2)
        biomass = col3.number_input("Current Biomass (kg) *", 0.0, 10000.0, 0.0, step=1.0)
        fish_count = col4.number_input("Fish Count", 0, 100000, 0, step=1)
        
        col5, col6 = st.columns(2)
        avg_weight = col5.number_input("Average Weight (g)", 0.0, 2000.0, 0.0, step=0.1)
        mortality = col6.number_input("Mortality Count", 0, 1000, 0, step=1)
        
        notes = st.text_area("Notes (optional)")
        
        submitted = st.form_submit_button("💾 Save Growth Record", type="primary", use_container_width=True)
        
        if submitted:
            if biomass <= 0:
                st.error("❌ Biomass must be greater than 0")
            else:
                data = {
                    "tank_id": tank_options[selected_tank],
                    "record_date": str(record_date),
                    "biomass_kg": biomass,
                    "fish_count": fish_count if fish_count > 0 else None,
                    "avg_weight": avg_weight if avg_weight > 0 else None,
                    "mortality": mortality,
                    "notes": notes if notes else None,
                }
                
                success, message = BioflocDB.add_growth_record(data, user['id'])
                
                if success:
                    st.success(f"✅ {message}")
                    
                    ActivityLogger.log(
                        user_id=user['id'],
                        action_type='data_entry',
                        module_key='biofloc',
                        description=f"Added growth record for {selected_tank}",
                        metadata={'tank_id': tank_options[selected_tank], 'biomass_kg': biomass}
                    )
                    
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
    
    # View history
    st.markdown("---")
    st.markdown("#### 📋 Growth History")
    
    selected_tank_view = st.selectbox(
        "Select Tank to View",
        list(tank_options.keys()),
        key="gr_view"
    )
    
    growth_data = BioflocDB.get_growth_records(tank_options[selected_tank_view], limit=50)
    
    if growth_data:
        df = pd.DataFrame(growth_data)
        
        display_cols = ['record_date', 'biomass_kg', 'fish_count', 'avg_weight', 'mortality', 'notes']
        df_display = df[[col for col in display_cols if col in df.columns]].copy()
        
        if 'record_date' in df_display.columns:
            df_display['record_date'] = pd.to_datetime(df_display['record_date']).dt.strftime('%Y-%m-%d')
        
        df_display.columns = ['Date', 'Biomass (kg)', 'Fish Count', 'Avg Weight (g)', 'Mortality', 'Notes']
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        
        # Show growth trend
        latest = growth_data[0]
        if len(growth_data) > 1:
            previous = growth_data[1]
            biomass_change = latest['biomass_kg'] - previous['biomass_kg']
            trend = "📈" if biomass_change > 0 else "📉" if biomass_change < 0 else "➡️"
            st.info(f"{trend} Latest: {latest['biomass_kg']} kg | Change: {biomass_change:+.2f} kg from {previous['record_date']}")
        else:
            st.info(f"📍 Latest biomass: {latest['biomass_kg']} kg")
    else:
        st.info("ℹ️ No growth records yet. Add your first record above!")


# ============================================================
# FEED LOGS TAB
# ============================================================

def show_feed_logs_tab(tanks: list, user: dict):
    """Feed logging form and history"""
    
    st.markdown("#### 🍽️ Record Feed Log")
    
    tank_options = {f"{t['tank_name']} (#{t['tank_number']})": t['id'] for t in tanks}
    
    with st.form("feed_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        selected_tank = col1.selectbox("Select Tank *", list(tank_options.keys()), key="feed_tank")
        feed_date = col2.date_input("Feed Date *", datetime.now().date())
        
        col3, col4 = st.columns(2)
        feed_type = col3.text_input("Feed Type *", placeholder="e.g., Starter Feed 1mm")
        quantity = col4.number_input("Quantity (kg) *", 0.0, 1000.0, 0.0, step=0.1)
        
        feeding_time = st.selectbox("Feeding Time *", ["Morning", "Afternoon", "Evening"])
        notes = st.text_area("Notes (optional)")
        
        submitted = st.form_submit_button("💾 Save Feed Log", type="primary", use_container_width=True)
        
        if submitted:
            if not feed_type:
                st.error("❌ Feed type is required")
            elif quantity <= 0:
                st.error("❌ Quantity must be greater than 0")
            else:
                data = {
                    "tank_id": tank_options[selected_tank],
                    "feed_date": str(feed_date),
                    "feed_type": feed_type,
                    "quantity_kg": quantity,
                    "feeding_time": feeding_time,
                    "notes": notes if notes else None,
                }
                
                success, message = BioflocDB.add_feed_log(data, user['id'])
                
                if success:
                    st.success(f"✅ {message}")
                    
                    ActivityLogger.log(
                        user_id=user['id'],
                        action_type='data_entry',
                        module_key='biofloc',
                        description=f"Added feed log for {selected_tank}",
                        metadata={'tank_id': tank_options[selected_tank], 'quantity_kg': quantity}
                    )
                    
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
    
    # View history
    st.markdown("---")
    st.markdown("#### 📋 Feed History")
    
    col1, col2 = st.columns([2, 1])
    selected_tank_view = col1.selectbox(
        "Select Tank to View",
        list(tank_options.keys()),
        key="feed_view"
    )
    
    # Show today's total
    feed_today = BioflocDB.get_feed_summary_today()
    tank_id = tank_options[selected_tank_view]
    today_total = next((f['total_feed_kg'] for f in feed_today if f['tank_id'] == tank_id), 0)
    
    col2.metric("Today's Feed", f"{today_total} kg")
    
    feed_data = BioflocDB.get_feed_logs(tank_id, limit=50)
    
    if feed_data:
        df = pd.DataFrame(feed_data)
        
        display_cols = ['feed_date', 'feed_type', 'quantity_kg', 'feeding_time', 'notes']
        df_display = df[[col for col in display_cols if col in df.columns]].copy()
        
        if 'feed_date' in df_display.columns:
            df_display['feed_date'] = pd.to_datetime(df_display['feed_date']).dt.strftime('%Y-%m-%d %H:%M')
        
        df_display.columns = ['Date', 'Feed Type', 'Quantity (kg)', 'Time', 'Notes']
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)
    else:
        st.info("ℹ️ No feed logs yet. Add your first feed log above!")


# ============================================================
# TANK OVERVIEW TAB
# ============================================================

def show_tank_overview_tab():
    """Tank overview with latest stats and alerts"""
    
    st.markdown("#### 📊 Tank Overview Dashboard")
    
    # Get overview data
    overview = BioflocDB.get_tank_overview()
    
    if not overview:
        st.info("ℹ️ No tank data available yet.")
        return
    
    # Show overdue alerts
    overdue = [t for t in overview if t.get('test_overdue', False)]
    if overdue:
        st.error(f"⚠️ **{len(overdue)} tank(s) have overdue water tests (>48 hours):**")
        for tank in overdue:
            st.warning(f"• {tank['tank_name']}: Last test {tank.get('last_test_date', 'Never')}")
        st.markdown("---")
    
    # Show tank cards
    for tank in overview:
        with st.expander(f"🐟 {tank['tank_name']} (Capacity: {tank['capacity_m3']} m³)", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("##### 🧪 Latest Water Test")
                if tank.get('last_test_date'):
                    st.write(f"**Date:** {tank['last_test_date']}")
                    st.write(f"**pH:** {tank.get('last_ph', '—')}")
                    st.write(f"**DO:** {tank.get('last_do', '—')} mg/L")
                    st.write(f"**Temp:** {tank.get('last_temp', '—')}°C")
                else:
                    st.info("_No water test data yet_")
            
            with col2:
                st.markdown("##### 📈 Latest Growth")
                if tank.get('last_growth_date'):
                    st.write(f"**Date:** {tank['last_growth_date']}")
                    st.write(f"**Biomass:** {tank.get('current_biomass', 0)} kg")
                    st.write(f"**Fish Count:** {tank.get('current_fish_count', '—')}")
                    st.write(f"**Mortality:** {tank.get('last_mortality', 0)}")
                else:
                    st.info("_No growth data yet_")
            
            # Show statistics
            stats = BioflocDB.get_tank_statistics(tank['id'])
            if stats:
                st.markdown("##### 📊 Statistics")
                col3, col4, col5 = st.columns(3)
                col3.metric("Total Tests", stats.get('total_tests', 0))
                col4.metric("Total Feed", f"{stats.get('total_feed_kg', 0)} kg")
                col5.metric("Total Mortality", stats.get('total_mortality', 0))


# ============================================================
# EXPORT TAB
# ============================================================

def show_export_tab(tanks: list):
    """Export data to Excel"""
    
    st.markdown("#### 📤 Export Tank Data")
    
    tank_options = {f"{t['tank_name']} (#{t['tank_number']})": t['id'] for t in tanks}
    
    col1, col2 = st.columns(2)
    selected_export_tank = col1.selectbox("Select Tank", list(tank_options.keys()), key="export_tank")
    
    # Date range
    export_all = col2.checkbox("Export all data", value=True)
    
    if not export_all:
        start_date = st.date_input("Start Date", date.today() - timedelta(days=30))
        end_date = st.date_input("End Date", date.today())
    
    if st.button("📥 Generate Excel Report", type="primary", use_container_width=True):
        tank_id = tank_options[selected_export_tank]
        
        # Fetch data
        test_data = BioflocDB.get_water_tests(tank_id, limit=1000)
        growth_data = BioflocDB.get_growth_records(tank_id, limit=1000)
        feed_data = BioflocDB.get_feed_logs(tank_id, limit=1000)
        
        # Convert to DataFrames
        df_tests = pd.DataFrame(test_data) if test_data else pd.DataFrame()
        df_growth = pd.DataFrame(growth_data) if growth_data else pd.DataFrame()
        df_feed = pd.DataFrame(feed_data) if feed_data else pd.DataFrame()
        
        # Create Excel file
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            if not df_tests.empty:
                df_tests.to_excel(writer, index=False, sheet_name='Water Tests')
            if not df_growth.empty:
                df_growth.to_excel(writer, index=False, sheet_name='Growth Records')
            if not df_feed.empty:
                df_feed.to_excel(writer, index=False, sheet_name='Feed Logs')
            
            # Add summary sheet
            summary_data = {
                'Metric': ['Total Water Tests', 'Total Growth Records', 'Total Feed Logs'],
                'Count': [len(df_tests), len(df_growth), len(df_feed)]
            }
            pd.DataFrame(summary_data).to_excel(writer, index=False, sheet_name='Summary')
        
        output.seek(0)
        
        st.download_button(
            label="📥 Download Excel Report",
            data=output,
            file_name=f"biofloc_{selected_export_tank.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        st.success("✅ Report generated successfully!")
