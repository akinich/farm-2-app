"""
Database Configuration and Connection Utilities for Supabase
Farm Management System

VERSION: 1.1.0
DATE: November 8, 2025
CHANGES FROM V1.0.0:
- Removed 'Manager' role from get_all_roles() (old line 401)
- Fixed user management (create, update, delete operations)
- Enhanced error handling for user operations
- Simplified to Admin + User roles only
- Removed WooCommerceDB class (not needed for farm app)
"""
import streamlit as st
from supabase import create_client, Client
from typing import Optional, Dict, List, Any
import json
import secrets
import string
from datetime import datetime, timedelta


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


class UserDB:
    """
    User-related database operations
    
    VERSION: 1.1.0 - Fixed user management with proper Supabase Auth integration
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
        """Get all modules accessible to a user"""
        try:
            db = Database.get_client()
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
        Create user with auto-confirmed email
        
        Args:
            email: User's email address
            full_name: User's full name
            role_id: Role ID to assign
            
        Returns:
            True if successful, False otherwise
        """
        try:
            db = Database.get_client()
            
            # Generate secure temporary password
            temp_password = ''.join(
                secrets.choice(string.ascii_letters + string.digits + string.punctuation) 
                for _ in range(20)
            )
            
            # Create user with AUTO-CONFIRMED email
            try:
                auth_response = db.auth.admin.create_user({
                    "email": email,
                    "password": temp_password,
                    "email_confirm": True,
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
            st.success("🔓 User can login immediately")
            
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
        
        Args:
            user_id: User's UUID to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            db = Database.get_client()
            
            # Step 1: Delete from user_profiles first
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
            try:
                db.auth.admin.delete_user(user_id)
            except Exception as auth_error:
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


class RoleDB:
    """Role and permission related database operations"""
    
    @staticmethod
    def get_all_roles() -> List[Dict]:
        """Get all available roles (Admin and User only)"""
        try:
            db = Database.get_client()
            # CHANGED FROM V1.0.0: Removed 'Manager' from role list
            response = (db.table('roles')
                       .select('*')
                       .in_('role_name', ['Admin', 'User'])
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
    """User-specific module permission operations"""
    
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


class ModuleDB:
    """Module related database operations"""
    
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
        """Update the display order of a module"""
        return ModuleDB.update_module(module_id, {'display_order': display_order})


class ActivityLogger:
    """Activity logging database operations"""
    
    @staticmethod
    def log(user_id: str, action_type: str, module_key: str = None, 
            description: str = None, metadata: Dict = None, success: bool = True) -> bool:
        """Log user activity"""
        try:
            db = Database.get_client()
            
            # Get user email
            try:
                user_response = db.auth.admin.get_user_by_id(user_id)
                user_email = user_response.user.email if user_response.user else 'Unknown'
            except:
                user_email = 'Unknown'
            
            log_data = {
                'user_id': user_id,
                'user_email': user_email,
                'action_type': action_type,
                'description': description,
                'module_key': module_key,
                'success': success,
                'metadata': metadata
            }
            
            db.table('activity_logs').insert(log_data).execute()
            return True
        except Exception as e:
            # Don't show error to user for logging failures
            print(f"Error logging activity: {str(e)}")
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
