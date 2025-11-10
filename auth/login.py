"""
Login Page and Authentication UI
Farm Management System

VERSION: 1.1.0 - Added password reset functionality
"""
import streamlit as st
from auth.session import SessionManager
import streamlit.components.v1 as components

def show_login_page():
    """Display login page"""

    # Check for password recovery tokens in URL
    # Use JavaScript to extract hash parameters since Streamlit can't access them directly
    recovery_token = extract_recovery_token()

    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        # If there's a recovery token, show password reset form
        if recovery_token:
            show_password_reset_form(recovery_token)
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


def extract_recovery_token():
    """Extract recovery token from URL hash using JavaScript"""

    # JavaScript to read URL hash and extract access_token and type
    js_code = """
    <script>
        // Get the URL hash
        const hash = window.location.hash;

        // Parse the hash parameters
        const params = new URLSearchParams(hash.substring(1));
        const accessToken = params.get('access_token');
        const type = params.get('type');

        // If it's a recovery token, send it to Streamlit
        if (type === 'recovery' && accessToken) {
            // Store in session storage for Streamlit to read
            sessionStorage.setItem('recovery_token', accessToken);

            // Reload without the hash to clean up URL
            window.history.replaceState(null, null, window.location.pathname);
        }
    </script>
    """

    # Inject JavaScript
    components.html(js_code, height=0)

    # Check if recovery token exists in session state
    if 'recovery_token_extracted' not in st.session_state:
        st.session_state.recovery_token_extracted = False
        # On first load, the JS hasn't run yet, so rerun after a moment
        if not st.session_state.recovery_token_extracted:
            st.session_state.recovery_token_extracted = True
            st.rerun()

    # Try to get from query params as fallback (Supabase might add it there too)
    query_params = st.query_params
    if 'access_token' in query_params and query_params.get('type') == 'recovery':
        return query_params['access_token']

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
    with st.spinner("Resetting password..."):
        success, message = SessionManager.reset_password(recovery_token, new_password)

        if success:
            st.success("✅ Password reset successful! You can now login with your new password.")
            st.info("Click below to go to login page")
            if st.button("Go to Login", use_container_width=True, type="primary"):
                # Clear the recovery token from session
                if 'recovery_token_extracted' in st.session_state:
                    del st.session_state.recovery_token_extracted
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
