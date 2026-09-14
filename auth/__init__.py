"""Authentication module for shopping analyzer."""

from .browser_auth import extract_browser_cookies
from .file_auth import load_cookies_from_file
from .session_manager import setup_and_test_session, test_api_connection
from .auto_login import auto_login

__all__ = [
    "extract_browser_cookies",
    "load_cookies_from_file",
    "setup_and_test_session",
    "test_api_connection",
    "auto_login",
]
