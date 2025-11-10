"""
Login Page and Authentication UI
Farm Management System

VERSION: 1.2.0 - Added Forgot Password flow with in-app email request
"""
import streamlit as st
from auth.session import SessionManager
import streamlit.components.v1 as components

def show_login_page():
    """Display login page"""

    # Check for password recovery tokens in URL
    recovery_token = extract_recovery_token()

    # Check if user wants to reset password
    if 'show_forgot_password' not in st.session_state:
        st.session_state.show_forgot_password = False

    # Center the form
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        # If there's a recovery token, show password reset form
        if recovery_token:
            show_password_reset_form(recovery_token)
        # If user clicked forgot password, show email input
        elif st.session_state.show_forgot_password:
            show_forgot_password_form()
        else:
            # Show normal login form
            st.markdown("# 🌾 Farm Management Login")
            st.markdown("---")

            with st.form("login_form"):
                email = st.text_input("Email", placeholder="your.email@farm.com")
                password = st.text_input("Password", type="password")
                submit = st.form_submit_button("Login", use_container_width=True, type="primary")

                if submit:
                    if not email or not password:
                        st.error("Please enter both email and password")
                    else:
                        handle_login(email, password)

            # Forgot password link
            st.markdown("---")
            col_a, col_b, col_c = st.columns([1, 1, 1])
            with col_b:
                if st.button("🔑 Forgot Password?", use_container_width=True):
                    st.session_state.show_forgot_password = True
                    st.rerun()


def show_forgot_password_form():
    """Display forgot password form"""
    st.markdown("# 🔑 Forgot Password")
    st.markdown("---")
    st.info("Enter your email address and we'll send you a password reset link")

    with st.form("forgot_password_form"):
        email = st.text_input("Email Address", placeholder="your.email@farm.com")
        submit = st.form_submit_button("Send Reset Link", use_container_width=True, type="primary")

        if submit:
            if not email:
                st.error("Please enter your email address")
            else:
                handle_forgot_password(email)

    # Back to login link
    st.markdown("---")
    if st.button("← Back to Login", use_container_width=True):
        st.session_state.show_forgot_password = False
        st.rerun()


def handle_forgot_password(email: str):
    """Send password reset email"""
    from config.database import Database

    with st.spinner("Sending reset link..."):
        try:
            db = Database.get_client()

            # Send password reset email
            db.auth.reset_password_email(email)

            st.success("✅ Password reset link sent! Check your email.")
            st.info("**Important:** After clicking the reset link in your email:\n\n"
                   "1. Look at your browser's address bar\n"
                   "2. If you see a `#` in the URL, **replace it with `?`**\n"
                   "3. Press Enter to reload the page\n"
                   "4. The password reset form will appear\n\n"
                   "Example: Change `...app/#access_token=...` to `...app/?access_token=...`")

        except Exception as e:
            error_msg = str(e)
            if "User not found" in error_msg or "not found" in error_msg.lower():
                st.error("❌ No account found with this email address")
            else:
                st.error(f"❌ Error sending reset link: {error_msg}")


def extract_recovery_token():
    """Extract recovery token from URL query params"""

    # Check if we already extracted the token in session state
    if 'recovery_token' in st.session_state and st.session_state.recovery_token:
        return st.session_state.recovery_token

    # Check if token is in query params (user manually converted # to ?)
    query_params = st.query_params
    if 'access_token' in query_params and query_params.get('type') == 'recovery':
        token = query_params['access_token']
        # Store in session state
        st.session_state.recovery_token = token
        return token

    return None


def show_password_reset_form(recovery_token: str):
    """Display password reset form"""
    st.markdown("# 🔐 Reset Your Password")
    st.markdown("---")
    st.info("Please enter your new password below")

    with st.form("password_reset_form"):
        new_password = st.text_input("New Password", type="password",
                                     help="Minimum 6 characters")
        confirm_password = st.text_input("Confirm New Password", type="password")
        submit = st.form_submit_button("Reset Password", use_container_width=True, type="primary")

        if submit:
            if not new_password or not confirm_password:
                st.error("Please fill in both password fields")
            elif len(new_password) < 6:
                st.error("Password must be at least 6 characters long")
            elif new_password != confirm_password:
                st.error("Passwords do not match")
            else:
                handle_password_reset(recovery_token, new_password)


def handle_password_reset(recovery_token: str, new_password: str):
    """
    Handle password reset with recovery token
    Args:
        recovery_token: Recovery token from Supabase
        new_password: New password to set
    """
    import time

    with st.spinner("Resetting password..."):
        success, message = SessionManager.reset_password(recovery_token, new_password)

        if success:
            st.success("✅ Password reset successful! You can now login with your new password.")
            st.info("Redirecting to login page...")

            # Clear recovery token from session state and query params
            if 'recovery_token' in st.session_state:
                del st.session_state.recovery_token
            st.query_params.clear()

            # Wait a moment for user to see the success message
            time.sleep(2)
            st.rerun()
        else:
            st.error(f"❌ {message}")


def handle_login(email: str, password: str):
    """
    Handle login attempt
    Args:
        email: User's email
        password: User's password
    """
    with st.spinner("Logging in..."):
        success, error_message = SessionManager.login(email, password)
        
        if success:
            st.success("✅ Login successful! Redirecting...")
            st.rerun()
        else:
            st.error(f"❌ {error_message}")


def show_logout_button():
    """Display logout button in sidebar"""
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        SessionManager.logout()
        st.rerun()


def show_user_info():
    """Display current user info in sidebar"""
    profile = SessionManager.get_user_profile()
    user = SessionManager.get_user()
    
    if profile and user:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 👤 User Info")
        st.sidebar.write(f"**Name:** {profile.get('full_name', 'N/A')}")
        st.sidebar.write(f"**Email:** {user.get('email')}")
        st.sidebar.write(f"**Role:** {profile.get('role_name', 'N/A')}")
        st.sidebar.markdown("---")
