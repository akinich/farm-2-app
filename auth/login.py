"""
Login Page and Authentication UI
Farm Management System

VERSION: 1.1.3 - Added manual workaround and dual JavaScript injection
"""
import streamlit as st
from auth.session import SessionManager
import streamlit.components.v1 as components

def show_login_page():
    """Display login page"""

    # Check for password recovery tokens in URL
    # Use JavaScript to extract hash parameters since Streamlit can't access them directly
    recovery_token = extract_recovery_token()

    # Debug info and manual workaround
    query_params = st.query_params

    # Check if URL has recovery hash but wasn't converted to query params
    has_recovery_hash = False
    js_detection = """
    <script>
    if (window.location.hash.includes('type=recovery')) {
        // Signal to Streamlit that we have a hash
        window.parent.postMessage({type: 'recovery_hash_detected'}, '*');
    }
    </script>
    """
    st.markdown(js_detection, unsafe_allow_html=True)

    # Show debug info if we detect recovery-related params
    if 'access_token' in query_params or 'recovery_token' in st.session_state:
        st.sidebar.write("🔍 Debug Info:")
        st.sidebar.write(f"Query params: {dict(query_params)}")
        st.sidebar.write(f"Token in session: {'recovery_token' in st.session_state}")
        st.sidebar.write(f"Token found: {recovery_token is not None}")

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

            # Show manual recovery link instructions if needed
            st.info("💡 **Password Reset Link?** If you clicked a password reset link and it didn't work, try this:\n\n"
                   "1. Look at your browser's address bar\n"
                   "2. If you see a `#` in the URL, replace it with `?`\n"
                   "3. Press Enter to reload the page\n\n"
                   "Example: Change `...app/#access_token=...` to `...app/?access_token=...`")

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

    # Check if we already extracted the token in session state
    if 'recovery_token' in st.session_state and st.session_state.recovery_token:
        return st.session_state.recovery_token

    # Check if token is in query params (after JavaScript redirect)
    query_params = st.query_params
    if 'access_token' in query_params and query_params.get('type') == 'recovery':
        token = query_params['access_token']
        # Store in session state
        st.session_state.recovery_token = token
        return token

    # Try injecting JavaScript via markdown (more reliable in Streamlit Cloud)
    js_code = """
    <script>
    (function() {
        const hash = window.location.hash;

        if (hash && hash.includes('access_token') && hash.includes('type=recovery')) {
            // Parse hash parameters
            const params = new URLSearchParams(hash.substring(1));
            const accessToken = params.get('access_token');
            const type = params.get('type');

            if (type === 'recovery' && accessToken) {
                // Build new URL with query params
                const baseUrl = window.location.origin + window.location.pathname;
                const newUrl = baseUrl + '?access_token=' + encodeURIComponent(accessToken) + '&type=recovery';

                // Redirect immediately
                window.location.replace(newUrl);
            }
        }
    })();
    </script>
    """

    # Try both injection methods for reliability
    st.markdown(js_code, unsafe_allow_html=True)
    components.html(js_code, height=0)

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
                # Clear recovery token from session state and query params
                if 'recovery_token' in st.session_state:
                    del st.session_state.recovery_token
                st.query_params.clear()
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
