"""
Database configuration and connection utilities for Supabase
Farm Management System

VERSION HISTORY:
1.4.0 - Enhanced ActivityLogger with email resolution - 10/11/25
      ADDITIONS:
      - Optional user_email parameter to ActivityLogger.log()
      - Automatic email resolution from session state
      - Fallback to auth API if session unavailable
      IMPROVEMENTS:
      - Activity logs now show actual user email instead of "Unknown"
      - Better error handling with detailed error messages
      - Input validation for user_id and action_type
      - More verbose debugging output

1.3.0 - Added improved BioflocDB class with validation, caching, and views - 08/11/25
      ADDITIONS:
      - BioflocDB class with full CRUD operations
      - Input validation at database layer
      - Caching for tank list (5-minute TTL)
      - Statistical methods (tank summaries, overdue alerts)
      - Batch operations for efficiency
      - Update/delete methods with ownership verification
      - Uses dissolved_oxygen instead of "do" column
      IMPROVEMENTS:
      - All methods return (bool, str) tuples for better error handling
      - Type hints on all methods
      - Removed duplicate activity logging
      - Better error messages
1.2.0 - Fixed user management (create, update, delete), enhanced error handling - 05/11/25
      FIXES:
      - Fixed create_user() to properly work with Supabase Auth admin.create_user()
      - Added update_user() method for editing user profiles
      - Added delete_user() method with proper cleanup
      - Improved error handling and validation
      - Added helper methods for auth operations
      CHANGES:
      - create_user() now generates temp password and sends reset email
      - update_user() allows editing name, role, and active status
      - delete_user() removes from both auth.users and user_profiles
      - Better error messages with specific failure reasons
1.1.0 - Added module management methods (update_module_order, create_user, get_logs) - 03/11/25
      ADDITIONS:
      - ModuleDB.update_module_order() for reordering modules
      - UserDB.create_user() (initial version, fixed in 1.2.0)
      - ActivityLogger.get_logs() with flexible filtering
1.0.0 - Hybrid permission system with UserPermissionDB class - 30/10/25
      INITIAL:
      - Database singleton pattern
      - UserDB, RoleDB, ModuleDB base classes
      - UserPermissionDB for user-specific permissions
      - ActivityLogger for audit trails
"""
import streamlit as st
from supabase import create_client, Client
from typing import Optional, Dict, List, Any, Tuple
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
# USER MANAGEMENT
# ============================================================

class UserDB:
    """
    User-related database operations
    
    VERSION: 1.2.0 - Fixed user management with proper Supabase Auth integration
    """
    
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
        """Get all modules accessible to a user (hybrid permission check)"""
        try:
            db = Database.get_client()
            # Use the new view that handles hybrid permissions
            response = (db.table('user_accessible_modules')
                       .select('*')
                       .eq('user_id', user_id)
                       .order('display_order')
                       .execute())
            return response.data if response.data else []
        except Exception as e:
            st.error(f"Error fetching user modules: {str(e)}")
            return []
    
    @staticmethod
    def create_user_profile(user_id: str, email: str, full_name: str, role_id: int) -> bool:
        """
        Create a new user profile after Supabase auth registration
        
        Args:
            user_id: UUID from Supabase Auth
            email: User's email address
            full_name: User's full name
            role_id: Role ID to assign
            
        Returns:
            True if successful, False otherwise
        """
        try:
            db = Database.get_client()
            data = {
                'id': user_id,
                'full_name': full_name,
                'role_id': role_id,
                'is_active': True
            }
            db.table('user_profiles').insert(data).execute()
            return True
        except Exception as e:
            st.error(f"Error creating user profile: {str(e)}")
            return False
    
    @staticmethod
    def update_user_profile(user_id: str, updates: Dict) -> bool:
        """
        Update user profile information (legacy method - use update_user instead)
        
        Args:
            user_id: User's UUID
            updates: Dictionary of fields to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            db = Database.get_client()
            db.table('user_profiles').update(updates).eq('id', user_id).execute()
            return True
        except Exception as e:
            st.error(f"Error updating user profile: {str(e)}")
            return False
    
    @staticmethod
    def get_all_users() -> List[Dict]:
        """
        Get all users with their profiles and roles
        
        Returns:
            List of user dictionaries with profile and role info
        """
        try:
            db = Database.get_client()
            
            # Join user_profiles with roles
            response = db.table('user_profiles') \
                .select('*, roles(role_name)') \
                .execute()
            
            if response.data:
                users = []
                for profile in response.data:
                    # Get email from auth.users
                    try:
                        user_response = db.auth.admin.get_user_by_id(profile['id'])
                        email = user_response.user.email if user_response.user else 'Unknown'
                    except:
                        email = 'Unknown'
                    
                    users.append({
                        'id': profile['id'],
                        'email': email,
                        'full_name': profile.get('full_name'),
                        'role_id': profile.get('role_id'),
                        'role_name': profile['roles']['role_name'] if profile.get('roles') else 'Unknown',
                        'is_active': profile.get('is_active', True),
                        'created_at': profile.get('created_at'),
                        'updated_at': profile.get('updated_at')
                    })
                
                return users
            
            return []
            
        except Exception as e:
            st.error(f"Error fetching users: {str(e)}")
            return []
    
    @staticmethod
    def get_non_admin_users() -> List[Dict]:
        """Get all non-admin users (for permission management)"""
        try:
            all_users = UserDB.get_all_users()
            return [u for u in all_users if u.get('role_name') != 'Admin']
        except Exception as e:
            st.error(f"Error fetching non-admin users: {str(e)}")
            return []
    
    @staticmethod
    def create_user(email: str, full_name: str, role_id: int) -> bool:
       """
       Create user with auto-confirmed email (workaround for restricted Supabase Auth)
       NO SUPABASE DASHBOARD ACCESS NEEDED
       """
       try:
           db = Database.get_client()
        
           # Generate secure temporary password
           temp_password = ''.join(
               secrets.choice(string.ascii_letters + string.digits + string.punctuation) 
               for _ in range(20)
           )
        
           # Create user with AUTO-CONFIRMED email (bypasses restrictions)
           try:
               auth_response = db.auth.admin.create_user({
                   "email": email,
                   "password": temp_password,
                   "email_confirm": True,  # ← KEY CHANGE: True instead of False
                   "user_metadata": {
                       "full_name": full_name
                   }
               })
           except Exception as auth_error:
               error_msg = str(auth_error).lower()
            
               if "already registered" in error_msg or "already exists" in error_msg:
                   st.error(f"❌ Email {email} already exists")
                   return False
               elif "invalid email" in error_msg:
                   st.error(f"❌ Invalid email: {email}")
                   return False
               else:
                   st.error(f"❌ Auth error: {str(auth_error)}")
                   st.info("💡 Using auto-confirm workaround...")
                   return False
        
           if not auth_response.user:
               st.error("❌ Failed to create user")
               return False
        
           user_id = auth_response.user.id
        
           # Create user profile
           profile_data = {
               'id': user_id,
               'full_name': full_name,
               'role_id': role_id,
               'is_active': True
           }
        
           try:
               profile_response = db.table('user_profiles').insert(profile_data).execute()
            
               if not profile_response.data:
                   st.error("❌ Failed to create profile")
                   try:
                       db.auth.admin.delete_user(user_id)
                   except:
                       pass
                   return False
           except Exception as profile_error:
               st.error(f"❌ Profile error: {str(profile_error)}")
               try:
                   db.auth.admin.delete_user(user_id)
               except:
                   pass
               return False
        
           # Success!
           st.success("✅ User created successfully!")
           st.success(f"🔓 User can login immediately")
        
           # Show temporary password
           with st.expander("🔑 Temporary Password (click to view)", expanded=False):
               st.code(temp_password, language=None)
               st.warning("⚠️ Share this password with the user securely")
               st.info("💡 User should change password after first login")
        
           return True
        
       except Exception as e:
           st.error(f"❌ Error: {str(e)}")
           return False
    
    @staticmethod
    def update_user(user_id: str, full_name: str, role_id: int, is_active: bool) -> bool:
        """
        Update user profile information
        
        NEW in v1.2.0: Dedicated method for updating user details
        
        Args:
            user_id: User's UUID
            full_name: New full name
            role_id: New role ID
            is_active: New active status
            
        Returns:
            True if successful, False otherwise
        """
        try:
            db = Database.get_client()
            
            update_data = {
                'full_name': full_name,
                'role_id': role_id,
                'is_active': is_active,
                'updated_at': datetime.now().isoformat()
            }
            
            response = db.table('user_profiles') \
                .update(update_data) \
                .eq('id', user_id) \
                .execute()
            
            if not response.data:
                st.error("❌ No user found with that ID")
                return False
            
            return True
            
        except Exception as e:
            st.error(f"❌ Error updating user: {str(e)}")
            return False
    
    @staticmethod
    def delete_user(user_id: str) -> bool:
        """
        Delete user from both user_profiles and Supabase Auth
        
        NEW in v1.2.0: Properly removes user from all systems
        
        Args:
            user_id: User's UUID to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            db = Database.get_client()
            
            # Step 1: Delete from user_profiles first
            # (This should cascade to related tables if FK constraints are set up)
            try:
                profile_response = db.table('user_profiles') \
                    .delete() \
                    .eq('id', user_id) \
                    .execute()
                
                if not profile_response.data:
                    st.warning("⚠️ No user profile found to delete")
            except Exception as profile_error:
                st.error(f"❌ Error deleting user profile: {str(profile_error)}")
                return False
            
            # Step 2: Delete from Supabase Auth
            # Note: This requires admin privileges (service_role key)
            try:
                db.auth.admin.delete_user(user_id)
            except Exception as auth_error:
                # If auth deletion fails, profile is already deleted
                # This is not ideal but not critical
                st.warning(f"⚠️ User profile deleted but auth deletion failed: {str(auth_error)}")
                st.info("💡 You may need to manually delete the user from Supabase Auth dashboard")
            
            return True
            
        except Exception as e:
            st.error(f"❌ Error deleting user: {str(e)}")
            return False
    
    @staticmethod
    def deactivate_user(user_id: str) -> bool:
        """Deactivate a user account"""
        return UserDB.update_user_profile(user_id, {'is_active': False})
    
    @staticmethod
    def activate_user(user_id: str) -> bool:
        """Activate a user account"""
        return UserDB.update_user_profile(user_id, {'is_active': True})
    
    @staticmethod
    def get_all_roles() -> List[Dict]:
        """Get all available roles (wrapper for RoleDB)"""
        return RoleDB.get_all_roles()


# ============================================================
# ROLE & PERMISSIONS
# ============================================================

class RoleDB:
    """Role and permission related database operations"""
    
    @staticmethod
    def get_all_roles() -> List[Dict]:
        """Get all available roles (should only be Admin and User now)"""
        try:
            db = Database.get_client()
            response = (db.table('roles')
                       .select('*')
                       .in_('role_name', ['Admin', 'Manager', 'User'])
                       .execute())
            return response.data if response.data else []
        except Exception as e:
            st.error(f"Error fetching roles: {str(e)}")
            return []
    
    @staticmethod
    def get_role_permissions(role_id: int) -> List[Dict]:
        """Get all module permissions for a role"""
        try:
            db = Database.get_client()
            response = (db.table('role_permissions')
                       .select('*, modules(*)')
                       .eq('role_id', role_id)
                       .execute())
            return response.data if response.data else []
        except Exception as e:
            st.error(f"Error fetching role permissions: {str(e)}")
            return []
    
    @staticmethod
    def update_role_permission(role_id: int, module_id: int, can_access: bool) -> bool:
        """Update permission for a role-module combination"""
        try:
            db = Database.get_client()
            # Try to update first
            response = (db.table('role_permissions')
                       .update({'can_access': can_access})
                       .eq('role_id', role_id)
                       .eq('module_id', module_id)
                       .execute())
            
            # If no rows affected, insert new permission
            if not response.data:
                db.table('role_permissions').insert({
                    'role_id': role_id,
                    'module_id': module_id,
                    'can_access': can_access
                }).execute()
            
            return True
        except Exception as e:
            st.error(f"Error updating role permission: {str(e)}")
            return False


class UserPermissionDB:
    """
    User-specific module permission operations (HYBRID SYSTEM)
    
    VERSION: 1.0.0 - Initial implementation with hybrid permissions
    """
    
    @staticmethod
    def get_user_permissions(user_id: str) -> List[Dict]:
        """Get all module permissions for a specific user"""
        try:
            db = Database.get_client()
            response = (db.table('user_module_permissions')
                       .select('*, modules(*)')
                       .eq('user_id', user_id)
                       .execute())
            return response.data if response.data else []
        except Exception as e:
            st.error(f"Error fetching user permissions: {str(e)}")
            return []
    
    @staticmethod
    def get_user_permissions_detail(user_id: str) -> List[Dict]:
        """Get detailed permission info for a user (includes all modules)"""
        try:
            db = Database.get_client()
            response = (db.table('user_permissions_detail')
                       .select('*')
                       .eq('user_id', user_id)
                       .order('display_order')
                       .execute())
            return response.data if response.data else []
        except Exception as e:
            st.error(f"Error fetching user permissions detail: {str(e)}")
            return []
    
    @staticmethod
    def update_user_permission(user_id: str, module_id: int, can_access: bool, 
                              granted_by: str) -> bool:
        """Grant or revoke module access for a user"""
        try:
            db = Database.get_client()
            
            if can_access:
                # Grant access - upsert
                data = {
                    'user_id': user_id,
                    'module_id': module_id,
                    'can_access': True,
                    'granted_by': granted_by
                }
                db.table('user_module_permissions').upsert(
                    data,
                    on_conflict='user_id,module_id'
                ).execute()
            else:
                # Revoke access - delete the permission row
                db.table('user_module_permissions').delete().match({
                    'user_id': user_id,
                    'module_id': module_id
                }).execute()
            
            return True
        except Exception as e:
            st.error(f"Error updating user permission: {str(e)}")
            return False
    
    @staticmethod
    def bulk_update_user_permissions(user_id: str, module_ids: List[int], 
                                    granted_by: str) -> bool:
        """Set all permissions for a user at once (replaces existing)"""
        try:
            db = Database.get_client()
            
            # Delete all existing permissions for this user
            db.table('user_module_permissions').delete().eq('user_id', user_id).execute()
            
            # Insert new permissions
            if module_ids:
                permissions = [
                    {
                        'user_id': user_id,
                        'module_id': module_id,
                        'can_access': True,
                        'granted_by': granted_by
                    }
                    for module_id in module_ids
                ]
                db.table('user_module_permissions').insert(permissions).execute()
            
            return True
        except Exception as e:
            st.error(f"Error bulk updating user permissions: {str(e)}")
            return False
    
    @staticmethod
    def get_all_user_permissions() -> List[Dict]:
        """Get permissions for all users (admin panel overview)"""
        try:
            db = Database.get_client()
            response = (db.table('user_permissions_detail')
                       .select('*')
                       .order('email', 'display_order')
                       .execute())
            return response.data if response.data else []
        except Exception as e:
            st.error(f"Error fetching all user permissions: {str(e)}")
            return []
    
    @staticmethod
    def has_module_access(user_id: str, module_key: str) -> bool:
        """Check if a specific user has access to a specific module"""
        try:
            db = Database.get_client()
            
            # Check if user is admin
            user_profile = UserDB.get_user_profile(user_id)
            if user_profile and user_profile.get('role_name') == 'Admin':
                return True
            
            # Check user_accessible_modules view
            response = (db.table('user_accessible_modules')
                       .select('module_key')
                       .eq('user_id', user_id)
                       .eq('module_key', module_key)
                       .execute())
            
            return len(response.data) > 0 if response.data else False
        except Exception as e:
            st.error(f"Error checking module access: {str(e)}")
            return False


# ============================================================
# MODULE MANAGEMENT
# ============================================================

class ModuleDB:
    """
    Module related database operations
    
    VERSION: 1.1.0 - Added update_module_order method
    """
    
    @staticmethod
    def get_all_modules() -> List[Dict]:
        """Get all available modules"""
        try:
            db = Database.get_client()
            response = (db.table('modules')
                       .select('*')
                       .order('display_order')
                       .execute())
            return response.data if response.data else []
        except Exception as e:
            st.error(f"Error fetching modules: {str(e)}")
            return []
    
    @staticmethod
    def get_active_modules() -> List[Dict]:
        """Get all active modules"""
        try:
            db = Database.get_client()
            response = (db.table('modules')
                       .select('*')
                       .eq('is_active', True)
                       .order('display_order')
                       .execute())
            return response.data if response.data else []
        except Exception as e:
            st.error(f"Error fetching active modules: {str(e)}")
            return []
    
    @staticmethod
    def add_module(module_name: str, module_key: str, description: str, 
                   icon: str = '⚙️', display_order: int = 99) -> bool:
        """Add a new module to the system"""
        try:
            db = Database.get_client()
            data = {
                'module_name': module_name,
                'module_key': module_key,
                'description': description,
                'icon': icon,
                'display_order': display_order,
                'is_active': True
            }
            db.table('modules').insert(data).execute()
            return True
        except Exception as e:
            st.error(f"Error adding module: {str(e)}")
            return False
    
    @staticmethod
    def update_module(module_id: int, updates: Dict) -> bool:
        """Update module information"""
        try:
            db = Database.get_client()
            db.table('modules').update(updates).eq('id', module_id).execute()
            return True
        except Exception as e:
            st.error(f"Error updating module: {str(e)}")
            return False
    
    @staticmethod
    def toggle_module_status(module_id: int, is_active: bool) -> bool:
        """Activate or deactivate a module"""
        return ModuleDB.update_module(module_id, {'is_active': is_active})
    
    @staticmethod
    def update_module_order(module_id: int, display_order: int) -> bool:
        """
        Update the display order of a module
        
        NEW in v1.1.0
        """
        return ModuleDB.update_module(module_id, {'display_order': display_order})


# ============================================================
# ACTIVITY LOGGER
# ============================================================

class ActivityLogger:
    """
    Activity logging database operations
    
    VERSION: 1.1.0 - Added flexible get_logs method
    """
    
    @staticmethod
    def log(user_id: str, action_type: str, module_key: str = None,
            description: str = None, metadata: Dict = None, success: bool = True,
            user_email: str = None) -> bool:
        """
        Log user activity

        Args:
            user_id: User's UUID
            action_type: Type of action (e.g., 'login', 'add_item')
            module_key: Module identifier
            description: Human-readable description
            metadata: Additional data as dict
            success: Whether action succeeded
            user_email: Optional user email (if not provided, will try to fetch from session or auth)
        """
        try:
            # Validate inputs
            if not user_id:
                print("Warning: ActivityLogger.log called without user_id")
                return False

            if not action_type:
                print("Warning: ActivityLogger.log called without action_type")
                return False

            db = Database.get_client()

            # Get user email - use provided or try to fetch
            if not user_email:
                user_email = 'Unknown'

                # Try to get from Streamlit session state first
                try:
                    import streamlit as st
                    if 'user' in st.session_state and st.session_state.user:
                        if 'email' in st.session_state.user:
                            user_email = st.session_state.user['email']
                except:
                    pass

                # If still unknown, try auth API (this might fail)
                if user_email == 'Unknown':
                    try:
                        user_response = db.auth.admin.get_user_by_id(user_id)
                        if user_response and user_response.user and user_response.user.email:
                            user_email = user_response.user.email
                    except Exception as email_error:
                        print(f"Info: Could not fetch user email for {user_id}: {str(email_error)}")

            log_data = {
                'user_id': str(user_id),  # Ensure it's a string
                'user_email': user_email,
                'action_type': action_type,
                'description': description,
                'module_key': module_key,
                'success': success,
                'metadata': metadata if metadata else None
            }

            # Insert with service role (bypasses RLS)
            result = db.table('activity_logs').insert(log_data).execute()

            # Check if insert was successful
            if result.data:
                print(f"✓ Activity logged: {action_type} by {user_email}")
                return True
            else:
                print(f"Warning: Activity log insert returned no data")
                return False

        except Exception as e:
            # Show detailed error for debugging
            error_msg = f"❌ Activity log error: {str(e)}"
            print(error_msg)

            # Show in Streamlit for debugging (will remove once fixed)
            try:
                st.error(f"⚠️ Activity logging failed: {str(e)}")
            except:
                pass  # In case st is not available

            return False
    
    @staticmethod
    def get_user_activity(user_id: str, limit: int = 50) -> List[Dict]:
        """Get recent activity for a specific user"""
        try:
            db = Database.get_client()
            response = (db.table('activity_logs')
                       .select('*')
                       .eq('user_id', user_id)
                       .order('created_at', desc=True)
                       .limit(limit)
                       .execute())
            return response.data if response.data else []
        except Exception as e:
            st.error(f"Error fetching activity logs: {str(e)}")
            return []
    
    @staticmethod
    def get_all_activity(limit: int = 100) -> List[Dict]:
        """Get recent activity for all users (admin only)"""
        try:
            db = Database.get_client()
            response = (db.table('activity_logs')
                       .select('*')
                       .order('created_at', desc=True)
                       .limit(limit)
                       .execute())
            return response.data if response.data else []
        except Exception as e:
            st.error(f"Error fetching activity logs: {str(e)}")
            return []
    
    @staticmethod
    def get_module_activity(module_key: str, limit: int = 50) -> List[Dict]:
        """Get recent activity for a specific module"""
        try:
            db = Database.get_client()
            response = (db.table('activity_logs')
                       .select('*')
                       .eq('module_key', module_key)
                       .order('created_at', desc=True)
                       .limit(limit)
                       .execute())
            return response.data if response.data else []
        except Exception as e:
            st.error(f"Error fetching module activity: {str(e)}")
            return []
    
    @staticmethod
    def get_logs(days: int = 7, user_id: str = None, module_key: str = None) -> List[Dict]:
        """
        Get activity logs with optional filters
        
        NEW in v1.1.0 - Flexible filtering by days, user, and module
        
        Args:
            days: Number of days to look back
            user_id: Optional user ID filter
            module_key: Optional module key filter
            
        Returns:
            List of log dictionaries
        """
        try:
            db = Database.get_client()
            
            # Calculate date threshold
            since_date = datetime.now() - timedelta(days=days)
            
            query = db.table('activity_logs') \
                .select('*') \
                .gte('created_at', since_date.isoformat()) \
                .order('created_at', desc=True)
            
            # Apply optional filters
            if user_id:
                query = query.eq('user_id', user_id)
            if module_key:
                query = query.eq('module_key', module_key)
            
            response = query.execute()
            return response.data if response.data else []
            
        except Exception as e:
            st.error(f"Error fetching activity logs: {str(e)}")
            return []
    
    @staticmethod
    def get_module_logs(module_key: str, days: int = 30) -> List[Dict]:
        """
        Get recent activity for a specific module (wrapper for compatibility)
        
        Args:
            module_key: Module key to filter by
            days: Number of days to look back
            
        Returns:
            List of log dictionaries
        """
        return ActivityLogger.get_logs(days=days, module_key=module_key)


# ============================================================
# BIOFLOC AQUACULTURE DATABASE OPERATIONS
# ============================================================

class BioflocDB:
    """
    Database operations for Biofloc Aquaculture Module
    
    VERSION: 1.3.0
    DATE: 2025-11-08
    
    CHANGES FROM V1.2.2:
    - Fixed column name: "do" → "dissolved_oxygen"
    - Added input validation before database insert
    - Added batch operations for efficiency
    - Added statistical methods (tank summaries, overdue alerts)
    - Added update/delete methods
    - Removed duplicate activity logging (let module handle it)
    - Added caching for tank list
    - Better error messages
    """
    
    # Cache for tanks (refresh every 5 minutes)
    _tanks_cache = None
    _tanks_cache_time = None
    _cache_duration = 300  # seconds
    
    # ============================================================
    # TANK MANAGEMENT
    # ============================================================
    
    @staticmethod
    def get_tanks(force_refresh: bool = False) -> List[Dict]:
        """
        Fetch all active tanks with caching
        
        Args:
            force_refresh: Force cache refresh
            
        Returns:
            List of tank dictionaries
        """
        try:
            # Check cache
            now = datetime.now()
            if (not force_refresh and 
                BioflocDB._tanks_cache is not None and 
                BioflocDB._tanks_cache_time is not None):
                elapsed = (now - BioflocDB._tanks_cache_time).total_seconds()
                if elapsed < BioflocDB._cache_duration:
                    return BioflocDB._tanks_cache
            
            # Fetch from database
            db = Database.get_client()
            resp = (db.table('biofloc_tanks')
                   .select('*')
                   .eq('is_active', True)
                   .order('tank_number')
                   .execute())
            
            # Update cache
            BioflocDB._tanks_cache = resp.data or []
            BioflocDB._tanks_cache_time = now
            
            return BioflocDB._tanks_cache
            
        except Exception as e:
            st.error(f"Error fetching tanks: {str(e)}")
            return []
    
    @staticmethod
    def get_tank_by_id(tank_id: int) -> Optional[Dict]:
        """Get single tank by ID"""
        try:
            tanks = BioflocDB.get_tanks()
            for tank in tanks:
                if tank['id'] == tank_id:
                    return tank
            return None
        except Exception:
            return None
    
    # ============================================================
    # WATER TESTS
    # ============================================================
    
    @staticmethod
    def add_water_test(data: Dict, user_id: str) -> Tuple[bool, str]:
        """
        Insert a new water test record with validation
        
        Args:
            data: Water test data dictionary
            user_id: User performing the test
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Validate required fields
            if 'tank_id' not in data or 'test_date' not in data:
                return False, "Tank ID and test date are required"
            
            # Validate pH range
            if 'ph' in data and data['ph'] is not None:
                if not (0 <= data['ph'] <= 14):
                    return False, "pH must be between 0 and 14"
            
            # Validate temperature
            if 'temp' in data and data['temp'] is not None:
                if not (0 <= data['temp'] <= 50):
                    return False, "Temperature must be between 0 and 50°C"
            
            # Validate salinity
            if 'salinity' in data and data['salinity'] is not None:
                if not (0 <= data['salinity'] <= 50):
                    return False, "Salinity must be between 0 and 50 ppt"
            
            # Validate non-negative values
            numeric_fields = ['dissolved_oxygen', 'ammonia', 'nitrite', 'nitrate', 'tds', 'alkalinity']
            for field in numeric_fields:
                if field in data and data[field] is not None:
                    if data[field] < 0:
                        return False, f"{field.replace('_', ' ').title()} cannot be negative"
            
            # Ensure tested_by is set
            data['tested_by'] = user_id
            
            # Insert record
            db = Database.get_client()
            db.table('biofloc_water_tests').insert(data).execute()
            
            return True, "Water test recorded successfully"
            
        except Exception as e:
            error_msg = f"Error adding water test: {str(e)}"
            st.error(error_msg)
            return False, error_msg
    
    @staticmethod
    def get_water_tests(tank_id: int, limit: int = 50) -> List[Dict]:
        """
        Retrieve water test records for a specific tank
        
        Args:
            tank_id: Tank ID
            limit: Maximum number of records to return
            
        Returns:
            List of water test dictionaries
        """
        try:
            db = Database.get_client()
            resp = (db.table('biofloc_water_tests')
                   .select('*')
                   .eq('tank_id', tank_id)
                   .order('test_date', desc=True)
                   .limit(limit)
                   .execute())
            return resp.data or []
        except Exception as e:
            st.error(f"Error fetching water tests: {str(e)}")
            return []
    
    @staticmethod
    def get_latest_water_test(tank_id: int) -> Optional[Dict]:
        """Get the most recent water test for a tank"""
        try:
            tests = BioflocDB.get_water_tests(tank_id, limit=1)
            return tests[0] if tests else None
        except Exception:
            return None
    
    @staticmethod
    def update_water_test(test_id: int, updates: Dict, user_id: str) -> Tuple[bool, str]:
        """Update an existing water test record"""
        try:
            db = Database.get_client()
            
            # Verify user owns this record
            existing = (db.table('biofloc_water_tests')
                       .select('tested_by')
                       .eq('id', test_id)
                       .execute())
            
            if not existing.data:
                return False, "Water test not found"
            
            if existing.data[0]['tested_by'] != user_id:
                return False, "You can only update your own water tests"
            
            # Update record
            updates['updated_at'] = datetime.now().isoformat()
            db.table('biofloc_water_tests').update(updates).eq('id', test_id).execute()
            
            return True, "Water test updated successfully"
            
        except Exception as e:
            return False, f"Error updating water test: {str(e)}"
    
    @staticmethod
    def delete_water_test(test_id: int, user_id: str) -> Tuple[bool, str]:
        """Delete a water test record"""
        try:
            db = Database.get_client()
            
            # Verify user owns this record
            existing = (db.table('biofloc_water_tests')
                       .select('tested_by')
                       .eq('id', test_id)
                       .execute())
            
            if not existing.data:
                return False, "Water test not found"
            
            if existing.data[0]['tested_by'] != user_id:
                return False, "You can only delete your own water tests"
            
            # Delete record
            db.table('biofloc_water_tests').delete().eq('id', test_id).execute()
            
            return True, "Water test deleted successfully"
            
        except Exception as e:
            return False, f"Error deleting water test: {str(e)}"
    
    # ============================================================
    # GROWTH RECORDS
    # ============================================================
    
    @staticmethod
    def add_growth_record(data: Dict, user_id: str) -> Tuple[bool, str]:
        """
        Insert a new growth tracking record with validation
        
        Args:
            data: Growth record data dictionary
            user_id: User recording the data
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Validate required fields
            if 'tank_id' not in data or 'record_date' not in data:
                return False, "Tank ID and record date are required"
            
            # Validate non-negative values
            numeric_fields = ['biomass_kg', 'fish_count', 'avg_weight', 'mortality']
            for field in numeric_fields:
                if field in data and data[field] is not None:
                    if data[field] < 0:
                        return False, f"{field.replace('_', ' ').title()} cannot be negative"
            
            # Ensure recorded_by is set
            data['recorded_by'] = user_id
            
            # Insert record
            db = Database.get_client()
            db.table('biofloc_growth_records').insert(data).execute()
            
            return True, "Growth record saved successfully"
            
        except Exception as e:
            error_msg = f"Error adding growth record: {str(e)}"
            st.error(error_msg)
            return False, error_msg
    
    @staticmethod
    def get_growth_records(tank_id: int, limit: int = 50) -> List[Dict]:
        """Retrieve growth records for a tank"""
        try:
            db = Database.get_client()
            resp = (db.table('biofloc_growth_records')
                   .select('*')
                   .eq('tank_id', tank_id)
                   .order('record_date', desc=True)
                   .limit(limit)
                   .execute())
            return resp.data or []
        except Exception as e:
            st.error(f"Error fetching growth records: {str(e)}")
            return []
    
    @staticmethod
    def get_latest_growth(tank_id: int) -> Optional[Dict]:
        """Get the most recent growth record for a tank"""
        try:
            records = BioflocDB.get_growth_records(tank_id, limit=1)
            return records[0] if records else None
        except Exception:
            return None
    
    # ============================================================
    # FEED LOGS
    # ============================================================
    
    @staticmethod
    def add_feed_log(data: Dict, user_id: str) -> Tuple[bool, str]:
        """
        Insert a new feed log record with validation
        
        Args:
            data: Feed log data dictionary
            user_id: User logging the feed
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Validate required fields
            if 'tank_id' not in data or 'feed_date' not in data:
                return False, "Tank ID and feed date are required"
            
            if 'feed_type' not in data or not data['feed_type']:
                return False, "Feed type is required"
            
            if 'quantity_kg' not in data or data['quantity_kg'] <= 0:
                return False, "Quantity must be greater than 0"
            
            # Validate feeding time
            if 'feeding_time' in data and data['feeding_time']:
                if data['feeding_time'] not in ['Morning', 'Afternoon', 'Evening']:
                    return False, "Feeding time must be Morning, Afternoon, or Evening"
            
            # Ensure logged_by is set
            data['logged_by'] = user_id
            
            # Insert record
            db = Database.get_client()
            db.table('biofloc_feed_logs').insert(data).execute()
            
            return True, "Feed log saved successfully"
            
        except Exception as e:
            error_msg = f"Error adding feed log: {str(e)}"
            st.error(error_msg)
            return False, error_msg
    
    @staticmethod
    def get_feed_logs(tank_id: int, limit: int = 50) -> List[Dict]:
        """Retrieve feed logs for a tank"""
        try:
            db = Database.get_client()
            resp = (db.table('biofloc_feed_logs')
                   .select('*')
                   .eq('tank_id', tank_id)
                   .order('feed_date', desc=True)
                   .limit(limit)
                   .execute())
            return resp.data or []
        except Exception as e:
            st.error(f"Error fetching feed logs: {str(e)}")
            return []
    
    # ============================================================
    # STATISTICS & SUMMARIES
    # ============================================================
    
    @staticmethod
    def get_tank_overview() -> List[Dict]:
        """
        Get overview of all tanks using the view
        Includes latest test, growth, and overdue alerts
        """
        try:
            db = Database.get_client()
            resp = db.table('biofloc_tank_overview').select('*').execute()
            return resp.data or []
        except Exception as e:
            st.error(f"Error fetching tank overview: {str(e)}")
            return []
    
    @staticmethod
    def get_overdue_tanks() -> List[Dict]:
        """Get tanks with water tests overdue (>48 hours)"""
        try:
            overview = BioflocDB.get_tank_overview()
            return [tank for tank in overview if tank.get('test_overdue', False)]
        except Exception:
            return []
    
    @staticmethod
    def get_feed_summary_today() -> List[Dict]:
        """Get today's feed consumption per tank"""
        try:
            db = Database.get_client()
            resp = db.table('biofloc_feed_today').select('*').execute()
            return resp.data or []
        except Exception as e:
            st.error(f"Error fetching feed summary: {str(e)}")
            return []
    
    @staticmethod
    def get_feed_summary_week() -> List[Dict]:
        """Get this week's feed consumption per tank"""
        try:
            db = Database.get_client()
            resp = db.table('biofloc_feed_this_week').select('*').execute()
            return resp.data or []
        except Exception as e:
            st.error(f"Error fetching weekly feed summary: {str(e)}")
            return []
    
    @staticmethod
    def get_tank_statistics(tank_id: int) -> Dict:
        """
        Get comprehensive statistics for a single tank
        
        Returns:
            Dictionary with stats like total tests, avg pH, etc.
        """
        try:
            db = Database.get_client()
            
            # Get test count and averages
            tests = BioflocDB.get_water_tests(tank_id, limit=1000)
            
            stats = {
                'total_tests': len(tests),
                'avg_ph': 0,
                'avg_do': 0,
                'avg_temp': 0,
                'latest_test': None,
            }
            
            if tests:
                stats['latest_test'] = tests[0].get('test_date')
                
                # Calculate averages
                ph_vals = [t['ph'] for t in tests if t.get('ph') is not None]
                do_vals = [t['dissolved_oxygen'] for t in tests if t.get('dissolved_oxygen') is not None]
                temp_vals = [t['temp'] for t in tests if t.get('temp') is not None]
                
                if ph_vals:
                    stats['avg_ph'] = round(sum(ph_vals) / len(ph_vals), 2)
                if do_vals:
                    stats['avg_do'] = round(sum(do_vals) / len(do_vals), 2)
                if temp_vals:
                    stats['avg_temp'] = round(sum(temp_vals) / len(temp_vals), 2)
            
            # Get growth data
            growth_records = BioflocDB.get_growth_records(tank_id, limit=1000)
            stats['total_growth_records'] = len(growth_records)
            
            if growth_records:
                latest = growth_records[0]
                stats['current_biomass'] = latest.get('biomass_kg', 0)
                stats['current_fish_count'] = latest.get('fish_count', 0)
                stats['total_mortality'] = sum(g.get('mortality', 0) for g in growth_records)
            
            # Get feed data
            feed_logs = BioflocDB.get_feed_logs(tank_id, limit=1000)
            stats['total_feed_logs'] = len(feed_logs)
            stats['total_feed_kg'] = sum(f.get('quantity_kg', 0) for f in feed_logs)
            
            return stats
            
        except Exception as e:
            st.error(f"Error calculating tank statistics: {str(e)}")
            return {}
    
    # ============================================================
    # BATCH OPERATIONS
    # ============================================================
    
    @staticmethod
    def bulk_add_water_tests(tests: List[Dict], user_id: str) -> Tuple[int, int]:
        """
        Add multiple water tests at once
        
        Args:
            tests: List of water test dictionaries
            user_id: User performing the tests
            
        Returns:
            Tuple of (success_count, error_count)
        """
        success_count = 0
        error_count = 0
        
        for test in tests:
            test['tested_by'] = user_id
            success, msg = BioflocDB.add_water_test(test, user_id)
            if success:
                success_count += 1
            else:
                error_count += 1
        
        return success_count, error_count
