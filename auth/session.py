"""
Session Management with User Permissions
Farm Management System

VERSION: 1.2.0
DATE: November 10, 2025
CHANGES FROM V1.1.0:
- Added reset_password() method for password recovery
- Supports password reset via recovery token from email
- Logs password reset activity

CHANGES FROM V1.0.0:
- Removed is_manager() method (lines 177-184 from old code)
- Cleaned up Manager role references
- Simplified permission system to Admin + User only
"""
import streamlit as st
from typing import Dict, List, Optional, Tuple
from config.database import Database, UserDB, ModuleDB, ActivityLogger


class SessionManager:
    """
    Manages user sessions and permissions
    Permission system:
    - Admins: Automatic access to all modules
    - Users: Check user_module_permissions table
    """
    
    @staticmethod
    def init_session():
        """Initialize session state variables"""
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        if 'user' not in st.session_state:
            st.session_state.user = None
        if 'profile' not in st.session_state:
            st.session_state.profile = None
        if 'accessible_modules' not in st.session_state:
            st.session_state.accessible_modules = []
        if 'current_module' not in st.session_state:
            st.session_state.current_module = None
    
    @staticmethod
    def login(email: str, password: str) -> Tuple[bool, str]:
        """
        Handle user login with email and password
        Args:
            email: User's email
            password: User's password
        Returns:
            Tuple of (success: bool, error_message: str)
        """
        try:
            # Get Supabase client
            supabase = Database.get_client()
            
            # Attempt to sign in with Supabase Auth
            response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if not response.user:
                return False, "Invalid email or password"
            
            # Create user dict
            user_dict = {
                'id': response.user.id,
                'email': response.user.email
            }
            
            # Get user profile from database
            profile = UserDB.get_user_profile(user_dict['id'])
            
            if not profile:
                return False, "User profile not found. Please contact administrator."
            
            if not profile.get('is_active', False):
                return False, "Your account is inactive. Please contact administrator."
            
            # Set session state
            st.session_state.authenticated = True
            st.session_state.user = user_dict
            st.session_state.profile = profile
            
            # Load accessible modules
            st.session_state.accessible_modules = SessionManager._load_accessible_modules(
                user_dict['id'], 
                profile
            )
            
            # Log successful login
            ActivityLogger.log(
                user_id=user_dict['id'],
                action_type='login',
                module_key='auth',
                description=f"User {profile.get('full_name', user_dict['email'])} logged in"
            )
            
            return True, ""
            
        except Exception as e:
            error_message = str(e)
            
            # Handle specific Supabase auth errors
            if "Invalid login credentials" in error_message:
                return False, "Invalid email or password"
            elif "Email not confirmed" in error_message:
                return False, "Please verify your email address before logging in"
            elif "User not found" in error_message:
                return False, "No account found with this email"
            else:
                return False, f"Login failed: {error_message}"

    @staticmethod
    def reset_password(recovery_token: str, new_password: str) -> Tuple[bool, str]:
        """
        Reset user password using recovery token
        Args:
            recovery_token: Recovery token from password reset email
            new_password: New password to set
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Get Supabase client
            supabase = Database.get_client()

            # Use the recovery token to create an authenticated session
            # Then update the user's password
            auth_response = supabase.auth.set_session(recovery_token, recovery_token)

            if not auth_response or not auth_response.user:
                return False, "Invalid or expired recovery token"

            # Update password using the authenticated session
            update_response = supabase.auth.update_user({
                "password": new_password
            })

            if update_response.user:
                # Log the password reset
                ActivityLogger.log(
                    user_id=auth_response.user.id,
                    action_type='password_reset',
                    module_key='auth',
                    description="User reset password via recovery link",
                    user_email=auth_response.user.email
                )

                # Sign out the temporary session
                supabase.auth.sign_out()

                return True, "Password reset successful"
            else:
                return False, "Failed to update password"

        except Exception as e:
            error_message = str(e)

            # Handle specific errors
            if "expired" in error_message.lower():
                return False, "Recovery link has expired. Please request a new password reset."
            elif "invalid" in error_message.lower():
                return False, "Invalid recovery link. Please request a new password reset."
            else:
                return False, f"Password reset failed: {error_message}"

    @staticmethod
    def _load_accessible_modules(user_id: str, profile: Dict) -> List[Dict]:
        """
        Load modules user can access
        - Admins: Get all active modules
        - Users: Get modules from user_module_permissions
        """
        try:
            role_name = profile.get('role_name', '').lower()
            
            # Admins get all modules
            if role_name == 'admin':
                return ModuleDB.get_all_modules()
            
            # Users: Get assigned modules
            else:
                return UserDB.get_user_modules(user_id)
                
        except Exception as e:
            st.error(f"Error loading modules: {str(e)}")
            return []
    
    @staticmethod
    def logout():
        """Handle user logout"""
        try:
            # Log logout action
            if st.session_state.get('user'):
                ActivityLogger.log(
                    user_id=st.session_state.user['id'],
                    action_type='logout',
                    module_key='auth',
                    description=f"User logged out"
                )
            
            # Clear session
            st.session_state.authenticated = False
            st.session_state.user = None
            st.session_state.profile = None
            st.session_state.accessible_modules = []
            st.session_state.current_module = None
            
        except Exception as e:
            st.error(f"Logout error: {str(e)}")
    
    @staticmethod
    def is_authenticated() -> bool:
        """Check if user is authenticated"""
        return st.session_state.get('authenticated', False)
    
    @staticmethod
    def is_logged_in() -> bool:
        """Check if user is logged in (alias for is_authenticated)"""
        return SessionManager.is_authenticated()
    
    @staticmethod
    def get_user() -> Optional[Dict]:
        """Get current user"""
        return st.session_state.get('user')
    
    @staticmethod
    def get_user_profile() -> Optional[Dict]:
        """Get current user profile"""
        return st.session_state.get('profile')
    
    @staticmethod
    def is_admin() -> bool:
        """Check if current user is admin"""
        profile = st.session_state.get('profile')
        if profile:
            return profile.get('role_name', '').lower() == 'admin'
        return False
    
    @staticmethod
    def get_accessible_modules() -> List[Dict]:
        """Get list of modules user can access"""
        return st.session_state.get('accessible_modules', [])
    
    @staticmethod
    def has_module_access(module_key: str) -> bool:
        """
        Check if user has access to a specific module
        """
        # Admin always has access
        if SessionManager.is_admin():
            return True
        
        # Check if module is in user's accessible modules
        accessible_modules = st.session_state.get('accessible_modules', [])
        return any(m.get('module_key') == module_key for m in accessible_modules)
    
    @staticmethod
    def require_module_access(module_key: str):
        """
        Require module access or stop execution
        Use this at the start of each module's show() function
        """
        if not SessionManager.has_module_access(module_key):
            st.error("⛔ Access Denied")
            st.warning("You don't have permission to access this module.")
            st.info("Contact your administrator if you need access.")
            st.stop()
    
    @staticmethod
    def require_admin():
        """Require admin access or stop execution"""
        if not SessionManager.is_admin():
            st.error("⛔ Admin Access Required")
            st.warning("This section is only accessible to administrators.")
            st.stop()
    
    @staticmethod
    def set_current_module(module_key: str):
        """Set the current active module"""
        st.session_state.current_module = module_key
    
    @staticmethod
    def get_current_module() -> Optional[str]:
        """Get the current active module key"""
        return st.session_state.get('current_module')
