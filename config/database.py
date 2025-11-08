"""
Database Configuration and Connection Utilities for Supabase
Farm Management System

VERSION: 1.2.2
DATE: November 8, 2025

CHANGES FROM V1.2.1:
- Fixed BioflocDB.add_water_test() to use plain 'do' column (no quotes)
- Normalized column key handling for Supabase/Postgres compatibility
- Verified RLS-safe and module-consistent structure
"""

import streamlit as st
from supabase import create_client, Client
from typing import Optional, Dict, List, Any
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

class UserDB:
    """User-related database operations"""

    @staticmethod
    def get_user_profile(user_id: str) -> Optional[Dict]:
        """Get user profile with role information"""
        try:
            db = Database.get_client()
            response = db.table('user_details').select('*').eq('id', user_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            st.error(f"Error fetching user profile: {str(e)}")
            return None

    @staticmethod
    def get_user_modules(user_id: str) -> List[Dict]:
        """Get all modules accessible to a user"""
        try:
            db = Database.get_client()
            response = (
                db.table('user_accessible_modules')
                .select('*')
                .eq('user_id', user_id)
                .order('display_order')
                .execute()
            )
            return response.data if response.data else []
        except Exception as e:
            st.error(f"Error fetching user modules: {str(e)}")
            return []


class RoleDB:
    """Role and permission related database operations"""

    @staticmethod
    def get_all_roles() -> List[Dict]:
        """Get all available roles (Admin and User only)"""
        try:
            db = Database.get_client()
            response = (
                db.table('roles')
                .select('*')
                .in_('role_name', ['Admin', 'User'])
                .execute()
            )
            return response.data if response.data else []
        except Exception as e:
            st.error(f"Error fetching roles: {str(e)}")
            return []


class UserPermissionDB:
    """User-specific module permission operations"""

    @staticmethod
    def has_module_access(user_id: str, module_key: str) -> bool:
        """Check if a specific user has access to a specific module"""
        try:
            db = Database.get_client()

            # Check if user is admin
            user_profile = UserDB.get_user_profile(user_id)
            if user_profile and user_profile.get('role_name') == 'Admin':
                return True

            # Check module permission
            response = (
                db.table('user_accessible_modules')
                .select('module_key')
                .eq('user_id', user_id)
                .eq('module_key', module_key)
                .execute()
            )
            return len(response.data) > 0 if response.data else False
        except Exception as e:
            st.error(f"Error checking module access: {str(e)}")
            return False


class ModuleDB:
    """Module related database operations"""

    @staticmethod
    def get_all_modules() -> List[Dict]:
        """Get all available modules"""
        try:
            db = Database.get_client()
            response = (
                db.table('modules')
                .select('*')
                .order('display_order')
                .execute()
            )
            return response.data if response.data else []
        except Exception as e:
            st.error(f"Error fetching modules: {str(e)}")
            return []

    @staticmethod
    def get_active_modules() -> List[Dict]:
        """Get all active modules"""
        try:
            db = Database.get_client()
            response = (
                db.table('modules')
                .select('*')
                .eq('is_active', True)
                .order('display_order')
                .execute()
            )
            return response.data if response.data else []
        except Exception as e:
            st.error(f"Error fetching active modules: {str(e)}")
            return []


# ============================================================
# ACTIVITY LOGGER
# ============================================================

class ActivityLogger:
    """Activity logging database operations"""

    @staticmethod
    def log(
        user_id: str,
        action_type: str,
        module_key: str = None,
        description: str = None,
        metadata: Dict = None,
        success: bool = True
    ) -> bool:
        """Log user activity"""
        try:
            db = Database.get_client()

            # Try to fetch user email for audit
            try:
                user_response = db.auth.admin.get_user_by_id(user_id)
                user_email = user_response.user.email if user_response.user else 'Unknown'
            except Exception:
                user_email = 'Unknown'

            log_data = {
                'user_id': user_id,
                'user_email': user_email,
                'action_type': action_type,
                'description': description,
                'module_key': module_key,
                'success': success,
                'metadata': metadata,
            }

            db.table('activity_logs').insert(log_data).execute()
            return True
        except Exception as e:
            print(f"Error logging activity: {str(e)}")
            return False


# ============================================================
# BIOFLOC AQUACULTURE DATABASE OPERATIONS
# ============================================================

class BioflocDB:
    """
    Database operations for Biofloc Aquaculture Module

    VERSION: 1.0.2
    CHANGES:
    - Updated add_water_test() to use plain 'do' column
    - Added metadata logging for inserts
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

            # Normalize DO key if user entered it with quotes
            if "do" not in data and '"do"' in data:
                data["do"] = data.pop('"do"')

            # Insert record
            db.table('biofloc_water_tests').insert(data).execute()

            # Log success
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


