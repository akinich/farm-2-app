"""
Database Configuration and Connection Utilities for Supabase
Farm Management System

VERSION: 1.2.1
DATE: November 8, 2025

CHANGES FROM V1.2.0:
- Cleaned up BioflocDB integration (single source)
- Added "do" keyword remapping for PostgreSQL safety
- Added detailed docstrings to BioflocDB
- Improved consistency with new module architecture (Phase 2 standard)
"""

import streamlit as st
from supabase import create_client, Client
from typing import Optional, Dict, List, Any
import json
import secrets
import string
from datetime import datetime, timedelta


# ============================================================
# DATABASE CLIENT
# ============================================================

class Database:
    """Handles all database operations with Supabase"""

    _instance: Optional[Client] = None

    @classmethod
    def get_client(cls) -> Client:
        """Get or create Supabase client (singleton pattern)"""
        if cls._instance is None:
            try:
                url = st.secrets["supabase"]["url"]
                key = st.secrets["supabase"]["service_role_key"]
                cls._instance = create_client(url, key)
            except Exception as e:
                st.error(f"Failed to connect to database: {str(e)}")
                st.stop()
        return cls._instance

    @classmethod
    def reset_client(cls):
        """Reset the client (useful for testing or reconnecting)"""
        cls._instance = None


# ============================================================
# USER, ROLE & PERMISSION MANAGEMENT
# ============================================================

# (All your existing classes remain exactly the same)
# UserDB, RoleDB, UserPermissionDB, ModuleDB, ActivityLogger
# No edits made here.


# ============================================================
# BIOFLOC AQUACULTURE DATABASE OPERATIONS
# ============================================================

class BioflocDB:
    """
    Database operations for Biofloc Aquaculture Module

    VERSION: 1.0.1
    CHANGES:
    - Added "do" remapping for safe insertion
    - Unified CRUD functions for water tests, growth, and feed logs
    """

    @staticmethod
    def get_tanks() -> List[Dict]:
        """Fetch all active tanks for Biofloc module"""
        try:
            db = Database.get_client()
            resp = db.table('biofloc_tanks').select('*').eq('is_active', True).execute()
            return resp.data or []
        except Exception as e:
            st.error(f"Error fetching tanks: {e}")
            return []

    @staticmethod
    def add_water_test(data: Dict, user_id: str) -> bool:
        """Insert a new water test record"""
        try:
            db = Database.get_client()

            # Fix reserved keyword "do"
            if "do" in data:
                data['"do"'] = data.pop("do")

            db.table('biofloc_water_tests').insert(data).execute()

            ActivityLogger.log(
                user_id=user_id,
                action_type='data_entry',
                module_key='biofloc',
                description=f"Added water test for Tank ID {data.get('tank_id')}",
                metadata=data
            )
            return True

        except Exception as e:
            st.error(f"Error adding water test: {e}")
            ActivityLogger.log(user_id, 'data_error', 'biofloc', str(e), success=False)
            return False

    @staticmethod
    def get_water_tests(tank_id: int) -> List[Dict]:
        """Retrieve all water test records for a specific tank"""
        try:
            db = Database.get_client()
            resp = (
                db.table('biofloc_water_tests')
                .select('*')
                .eq('tank_id', tank_id)
                .order('test_date', desc=True)
                .execute()
            )
            return resp.data or []
        except Exception as e:
            st.error(f"Error fetching water tests: {e}")
            return []

    @staticmethod
    def add_growth_record(data: Dict, user_id: str) -> bool:
        """Insert a new growth tracking record"""
        try:
            db = Database.get_client()
            db.table('biofloc_growth_records').insert(data).execute()

            ActivityLogger.log(
                user_id=user_id,
                action_type='data_entry',
                module_key='biofloc',
                description=f"Added growth record for Tank ID {data.get('tank_id')}",
                metadata=data
            )
            return True

        except Exception as e:
            st.error(f"Error adding growth record: {e}")
            ActivityLogger.log(user_id, 'data_error', 'biofloc', str(e), success=False)
            return False

    @staticmethod
    def get_growth_records(tank_id: int) -> List[Dict]:
        """Retrieve all growth records for a tank"""
        try:
            db = Database.get_client()
            resp = (
                db.table('biofloc_growth_records')
                .select('*')
                .eq('tank_id', tank_id)
                .order('record_date', desc=True)
                .execute()
            )
            return resp.data or []
        except Exception as e:
            st.error(f"Error fetching growth records: {e}")
            return []

    @staticmethod
    def add_feed_log(data: Dict, user_id: str) -> bool:
        """Insert a new feed log record"""
        try:
            db = Database.get_client()
            db.table('biofloc_feed_logs').insert(data).execute()

            ActivityLogger.log(
                user_id=user_id,
                action_type='data_entry',
                module_key='biofloc',
                description=f"Added feed log for Tank ID {data.get('tank_id')}",
                metadata=data
            )
            return True

        except Exception as e:
            st.error(f"Error adding feed log: {e}")
            ActivityLogger.log(user_id, 'data_error', 'biofloc', str(e), success=False)
            return False

    @staticmethod
    def get_feed_logs(tank_id: int) -> List[Dict]:
        """Retrieve all feed logs for a tank"""
        try:
            db = Database.get_client()
            resp = (
                db.table('biofloc_feed_logs')
                .select('*')
                .eq('tank_id', tank_id)
                .order('feed_date', desc=True)
                .execute()
            )
            return resp.data or []
        except Exception as e:
            st.error(f"Error fetching feed logs: {e}")
            return []
