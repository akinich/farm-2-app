"""
BIOFLOC AQUACULTURE MODULE
Manages tanks, water quality, growth tracking, and feeding logs.

VERSION: 1.0.2 (Aligned with module template)
DATE: 2025-11-08
"""

import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
from auth.session import SessionManager
from config.database import ActivityLogger, BioflocDB


def show():
    """
    Main entry point for the Biofloc Aquaculture Module
    This function will be called by app.py when the module is accessed
    """

    # ----------------------------------------------------------
    # ✅ Access control
    # ----------------------------------------------------------
    SessionManager.require_module_access('biofloc')
    user = SessionManager.get_user()
    profile = SessionManager.get_user_profile()

    st.markdown("### 🐟 Biofloc Aquaculture Management")
    st.markdown("Track tank water quality, fish growth, and feed usage.")
    st.markdown("---")

    # ----------------------------------------------------------
    # 🧭 Tabs for each feature
    # ----------------------------------------------------------
    tabs = st.tabs([
        "🧪 Water Testing",
        "📈 Growth Records",
        "🍽️ Feed Logs",
        "📊 Tank Overview",
        "📤 Reports & Export"
    ])

    tanks = BioflocDB.get_tanks()
    if not tanks:
        st.warning("No tanks found. Please ask Admin to add tanks in the database.")
        return

    tank_options = {f"{t['tank_name']} (#{t['tank_number']})": t['id'] for t in tanks}

    # ============================================================
    # 🧪 TAB 1: WATER TESTING
    # ============================================================
    with tabs[0]:
        st.markdown("#### Record Water Test")
        with st.form("water_test_form"):
            col1, col2 = st.columns(2)
            selected_tank = col1.selectbox("Select Tank", list(tank_options.keys()))
            test_date = col2.date_input("Test Date", datetime.now().date())

            col3, col4, col5 = st.columns(3)
            ph = col3.number_input("pH", 0.0, 14.0, step=0.1)
            do_val = col4.number_input("Dissolved Oxygen (mg/L)", 0.0, 20.0, step=0.1)
            ammonia = col5.number_input("Ammonia (mg/L)", 0.0, 10.0, step=0.01)

            col6, col7, col8 = st.columns(3)
            nitrite = col6.number_input("Nitrite (mg/L)", 0.0, 10.0, step=0.01)
            nitrate = col7.number_input("Nitrate (mg/L)", 0.0, 100.0, step=0.1)
            temp = col8.number_input("Temperature (°C)", 0.0, 40.0, step=0.1)

            col9, col10, col11 = st.columns(3)
            salinity = col9.number_input("Salinity (ppt)", 0.0, 50.0, step=0.1)
            tds = col10.number_input("TDS (ppm)", 0.0, 5000.0, step=1.0)
            alkalinity = col11.number_input("Alkalinity (mg/L)", 0.0, 500.0, step=1.0)

            notes = st.text_area("Notes")
            submitted = st.form_submit_button("💾 Save Water Test", type="primary")

            if submitted:
                try:
                    data = {
                        "tank_id": tank_options[selected_tank],
                        "test_date": str(test_date),
                        "ph": ph,
                        '"do"': do_val,
                        "ammonia": ammonia,
                        "nitrite": nitrite,
                        "nitrate": nitrate,
                        "temp": temp,
                        "salinity": salinity,
                        "tds": tds,
                        "alkalinity": alkalinity,
                        "notes": notes,
                        "tested_by": user['id'],
                    }
                    BioflocDB.add_water_test(data, user['id'])
                    st.success("✅ Water test recorded successfully!")

                    ActivityLogger.log(
                        user_id=user['id'],
                        action_type='data_entry',
                        module_key='biofloc',
                        description=f"Added water test for tank {selected_tank}",
                        metadata=data
                    )
                except Exception as e:
                    st.error(f"Error saving water test: {e}")
                    ActivityLogger.log(
                        user_id=user['id'],
                        action_type='data_error',
                        module_key='biofloc',
                        description=str(e),
                        success=False
                    )

        st.markdown("#### Recent Water Tests")
        selected_tank_view = st.selectbox("Select Tank to View", list(tank_options.keys()), key="wt_view")
        test_data = BioflocDB.get_water_tests(tank_options[selected_tank_view])
        if test_data:
            st.dataframe(pd.DataFrame(test_data), use_container_width=True)
        else:
            st.info("No water test data available for this tank.")

    # ============================================================
    # 📈 TAB 2: GROWTH RECORDS
    # ============================================================
    with tabs[1]:
        st.markdown("#### Record Fish Growth")
        with st.form("growth_form"):
            col1, col2 = st.columns(2)
            selected_tank = col1.selectbox("Select Tank", list(tank_options.keys()), key="gr_tank")
            record_date = col2.date_input("Record Date", datetime.now().date())

            col3, col4, col5 = st.columns(3)
            biomass = col3.number_input("Current Biomass (kg)", 0.0, 10000.0, step=1.0)
            fish_count = col4.number_input("Fish Count", 0, 100000, step=1)
            mortality = col5.number_input("Mortality Count", 0, 1000, step=1)

            avg_weight = st.number_input("Average Weight (g)", 0.0, 2000.0, step=0.1)
            notes = st.text_area("Notes")

            submitted = st.form_submit_button("💾 Save Growth Record", type="primary")

            if submitted:
                try:
                    data = {
                        "tank_id": tank_options[selected_tank],
                        "record_date": str(record_date),
                        "biomass_kg": biomass,
                        "fish_count": fish_count,
                        "avg_weight": avg_weight,
                        "mortality": mortality,
                        "notes": notes,
                        "recorded_by": user['id']
                    }
                    BioflocDB.add_growth_record(data, user['id'])
                    st.success("✅ Growth record saved successfully!")

                    ActivityLogger.log(
                        user_id=user['id'],
                        action_type='data_entry',
                        module_key='biofloc',
                        description=f"Added growth record for tank {selected_tank}",
                        metadata=data
                    )
                except Exception as e:
                    st.error(f"Error saving growth record: {e}")

        st.markdown("#### Growth History")
        selected_tank_view = st.selectbox("Select Tank to View", list(tank_options.keys()), key="gr_view")
        growth_data = BioflocDB.get_growth_records(tank_options[selected_tank_view])
        if growth_data:
            st.dataframe(pd.DataFrame(growth_data), use_container_width=True)
        else:
            st.info("No growth records available.")

    # ============================================================
    # 🍽️ TAB 3: FEED LOGS
    # ============================================================
    with tabs[2]:
        st.markdown("#### Record Feed Log")
        with st.form("feed_form"):
            col1, col2 = st.columns(2)
            selected_tank = col1.selectbox("Select Tank", list(tank_options.keys()), key="feed_tank")
            feed_date = col2.date_input("Feed Date", datetime.now().date())

            feed_type = st.text_input("Feed Type")
            col3, col4 = st.columns(2)
            quantity = col3.number_input("Feed Quantity (kg)", 0.0, 1000.0, step=0.1)
            feeding_time = col4.selectbox("Feeding Time", ["Morning", "Afternoon", "Evening"])

            notes = st.text_area("Notes")
            submitted = st.form_submit_button("💾 Save Feed Log", type="primary")

            if submitted:
                try:
                    data = {
                        "tank_id": tank_options[selected_tank],
                        "feed_date": str(feed_date),
                        "feed_type": feed_type,
                        "quantity_kg": quantity,
                        "feeding_time": feeding_time,
                        "notes": notes,
                        "logged_by": user['id']
                    }
                    BioflocDB.add_feed_log(data, user['id'])
                    st.success("✅ Feed log saved successfully!")
                except Exception as e:
                    st.error(f"Error saving feed log: {e}")

        st.markdown("#### Feed History")
        selected_tank_view = st.selectbox("Select Tank to View", list(tank_options.keys()), key="feed_view")
        feed_data = BioflocDB.get_feed_logs(tank_options[selected_tank_view])
        if feed_data:
            st.dataframe(pd.DataFrame(feed_data), use_container_width=True)
        else:
            st.info("No feed records available.")

    # ============================================================
    # 📊 TAB 4: TANK OVERVIEW
    # ============================================================
    with tabs[3]:
        st.markdown("#### Tank Overview")
        for t in tanks:
            st.markdown(f"##### {t['tank_name']} (Capacity: {t['capacity_m3']} m³)")
            tests = BioflocDB.get_water_tests(t['id'])
            growth = BioflocDB.get_growth_records(t['id'])

            if tests:
                last_test = tests[0]
                st.write(f"**Last Test:** {last_test['test_date']} | **pH:** {last_test['ph']} | **DO:** {last_test.get('do', '—')} mg/L | **Temp:** {last_test.get('temp', '—')}°C")
            else:
                st.write("_No water test data yet._")

            if growth:
                last_growth = growth[0]
                st.write(f"**Biomass:** {last_growth['biomass_kg']} kg | **Fish Count:** {last_growth['fish_count']} | **Mortality:** {last_growth['mortality']}")
            else:
                st.write("_No growth data yet._")

            st.markdown("---")

    # ============================================================
    # 📤 TAB 5: EXPORT
    # ============================================================
    with tabs[4]:
        st.markdown("#### Export Tank Data")
        selected_export_tank = st.selectbox("Select Tank", list(tank_options.keys()), key="export_tank")
        test_data = BioflocDB.get_water_tests(tank_options[selected_export_tank])
        growth_data = BioflocDB.get_growth_records(tank_options[selected_export_tank])
        feed_data = BioflocDB.get_feed_logs(tank_options[selected_export_tank])

        export_dict = {
            "Water Tests": pd.DataFrame(test_data),
            "Growth Records": pd.DataFrame(growth_data),
            "Feed Logs": pd.DataFrame(feed_data)
        }

        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            for sheet, df in export_dict.items():
                if not df.empty:
                    df.to_excel(writer, index=False, sheet_name=sheet)
        output.seek(0)

        st.download_button(
            label="📥 Download Excel Report",
            data=output,
            file_name=f"biofloc_export_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # ----------------------------------------------------------
    # ✅ Log module access
    # ----------------------------------------------------------
    ActivityLogger.log(
        user_id=user['id'],
        action_type='module_use',
        module_key='biofloc',
        description="Accessed Biofloc module"
    )
