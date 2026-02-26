import streamlit as st
from supabase import create_client, ClientOptions
from datetime import datetime, timedelta
import time
import re
import httpx
import socket
import urllib.parse


class AuthService:
    def __init__(self):
        try:
            url = st.secrets["SUPABASE_URL"]
            key = st.secrets["SUPABASE_KEY"]

            # Bypass ISP DNS Hijacking (Jio/Airtel) for Supabase
            try:
                host = urllib.parse.urlparse(url).netloc
                original_getaddrinfo = socket.getaddrinfo
                def patched_getaddrinfo(h, p, family=0, types=0, proto=0, flags=0):
                    if h == host:
                        return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('172.64.149.246', p))]
                    return original_getaddrinfo(h, p, family, types, proto, flags)
                socket.getaddrinfo = patched_getaddrinfo
            except Exception:
                pass

            custom_http_client = httpx.Client(
                timeout=httpx.Timeout(30.0, connect=10.0, read=30.0, write=15.0),
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10)
            )

            options = ClientOptions(
                postgrest_client_timeout=30,
                storage_client_timeout=30,
                function_client_timeout=30,
                httpx_client=custom_http_client
            )

            self.supabase = create_client(url, key, options=options)
        except Exception as e:
            st.error(f"Failed to initialize services: {str(e)}")
            raise e

    def try_restore_session(self):
        """Try to restore session from Supabase stored session."""
        try:
            # First try to restore from Streamlit session state tokens
            if "auth_token" in st.session_state and "refresh_token" in st.session_state:
                try:
                    self.supabase.auth.set_session(
                        st.session_state.auth_token, st.session_state.refresh_token
                    )
                except Exception as e:
                    # print(f"Set session failed: {e}")
                    pass

            # Check if Supabase has a stored session
            session = self.supabase.auth.get_session()
            if session and session.access_token:
                # If we have a session but it's not in state, restore it
                # Or if the token in state is stale/different, update it
                current_token = st.session_state.get("auth_token")
                if not current_token or current_token != session.access_token:
                    user = self.supabase.auth.get_user()
                    if user and user.user:
                        user_data = self.get_user_data(user.user.id)
                        if user_data:
                            st.session_state.auth_token = session.access_token
                            st.session_state.refresh_token = session.refresh_token
                            st.session_state.user = user_data
        except Exception:
            # If restoration fails, continue without session
            pass

    def validate_email(self, email):
        """Validate email format."""
        pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        return bool(re.match(pattern, email))

    def check_existing_user(self, email):
        """Check if user already exists."""
        try:
            result = (
                self.supabase.table("users").select("id").eq("email", email).execute()
            )
            return len(result.data) > 0
        except Exception:
            return False

    def sign_up(self, email, password, name):
        try:
            auth_response = self.supabase.auth.sign_up(
                {
                    "email": email,
                    "password": password,
                    "options": {"data": {"name": name}},
                }
            )

            if not auth_response.user:
                return False, "Failed to create user account"

            user_data = {
                "id": auth_response.user.id,
                "email": email,
                "name": name,
                "created_at": datetime.now().isoformat(),
            }


            # If we got a session immediately (email confirmation off), store it
            if auth_response.session:
                st.session_state.auth_token = auth_response.session.access_token
                st.session_state.refresh_token = auth_response.session.refresh_token
                st.session_state.user = user_data

            return True, user_data

        except Exception as e:
            error_msg = str(e).lower()
            if "duplicate" in error_msg or "already registered" in error_msg:
                return False, "Email already registered"
            return False, f"Sign up failed: {str(e)}"

    def sign_in(self, email, password):
        try:
            # Removed redundant sign_out() to reduce network latency during login
            
            auth_response = self.supabase.auth.sign_in_with_password(
                {"email": email, "password": password}
            )

            if auth_response and auth_response.user:
                # Get user data
                user_data = self.get_user_data(auth_response.user.id)
                if not user_data:
                    return False, "User data not found"

                # Store session info
                st.session_state.auth_token = auth_response.session.access_token
                st.session_state.refresh_token = auth_response.session.refresh_token
                st.session_state.user = user_data
                return True, user_data

            return False, "Invalid login response"
        except Exception as e:
            return False, str(e)

    def sign_out(self):
        """Sign out and clear all session data."""
        try:
            self.supabase.auth.sign_out()
        except Exception:
            pass

        try:
            from auth.session_manager import SessionManager

            SessionManager.clear_session_state()
            return True, None
        except Exception as e:
            return False, str(e)

    def get_user(self):
        try:
            return self.supabase.auth.get_user()
        except Exception:
            return None

    def create_session(self, user_id, title=None):
        try:
            current_time = datetime.now()
            default_title = f"{current_time.strftime('%d-%m-%Y')} | {current_time.strftime('%H:%M:%S')}"

            session_data = {
                "user_id": user_id,
                "title": title or default_title,
                "created_at": current_time.isoformat(),
            }
            result = self.supabase.table("chat_sessions").insert(session_data).execute()
            return True, result.data[0] if result.data else None
        except Exception as e:
            return False, str(e)

    def get_user_sessions(self, user_id):
        try:
            result = (
                self.supabase.table("chat_sessions")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .execute()
            )
            return True, result.data
        except Exception as e:
            st.error(f"Error fetching sessions: {str(e)}")
            return False, []

    def save_chat_message(self, session_id, content, role="user"):
        try:
            message_data = {
                "session_id": session_id,
                "content": content,
                "role": role,
                "created_at": datetime.now().isoformat(),
            }
            result = self.supabase.table("chat_messages").insert(message_data).execute()
            return True, result.data[0] if result.data else None
        except Exception as e:
            return False, str(e)

    def get_session_messages(self, session_id):
        try:
            result = (
                self.supabase.table("chat_messages")
                .select("*")
                .eq("session_id", session_id)
                .order("created_at")
                .execute()
            )
            return True, result.data
        except Exception as e:
            return False, str(e)

    def delete_session(self, session_id):
        try:
            self.supabase.table("chat_messages").delete().eq(
                "session_id", session_id
            ).execute()

            self.supabase.table("chat_sessions").delete().eq("id", session_id).execute()

            return True, None
        except Exception as e:
            st.error(f"Failed to delete session: {str(e)}")
            return False, str(e)

    def validate_session_token(self):
        """Validate existing session token with minimal network calls."""
        try:
            # Check if we've recently validated (within last 5 minutes)
            if "last_validation" in st.session_state:
                time_since_validation = datetime.now() - st.session_state.last_validation
                if time_since_validation < timedelta(minutes=5) and st.session_state.get("user"):
                    return st.session_state.user

            session = self.supabase.auth.get_session()
            if not session or not session.access_token:
                # Try to restore from state if supabase client lost it
                if "auth_token" in st.session_state and "refresh_token" in st.session_state:
                    try:
                        self.supabase.auth.set_session(
                            st.session_state.auth_token, st.session_state.refresh_token
                        )
                        session = self.supabase.auth.get_session()
                    except Exception:
                        pass

            if not session or not session.access_token:
                return None

            # If token matched and we have user data, just return it
            if session.access_token == st.session_state.get("auth_token") and st.session_state.get("user"):
                st.session_state.last_validation = datetime.now()
                return st.session_state.user

            # Fallback to network validation if needed
            user = self.supabase.auth.get_user()
            if not user or not user.user:
                return None

            user_data = self.get_user_data(user.user.id)
            if user_data:
                st.session_state.last_validation = datetime.now()
                # Update tokens in case they refreshed
                st.session_state.auth_token = session.access_token
                if session.refresh_token:
                    st.session_state.refresh_token = session.refresh_token
                st.session_state.user = user_data

            return user_data
        except Exception:
            return None

    def get_user_data(self, user_id):
        """Get user data from database."""
        try:
            response = (
                self.supabase.table("users")
                .select("*")
                .eq("id", user_id)
                .single()
                .execute()
            )
            return response.data if response else None
        except Exception:
            return None
