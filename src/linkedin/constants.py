"""Constants for the LinkedIn module."""
import os

# Configuration Schema
LINKEDIN_CONFIG_SCHEMA = "linkedin"

# Vault Keys
LINKEDIN_CLIENT_ID_KEY = "LINKEDIN_CLIENT_ID"
LINKEDIN_CLIENT_SECRET_KEY = "LINKEDIN_CLIENT_SECRET"
LINKEDIN_REDIRECT_URI_KEY = "NGROK_DOMAIN"
LINKEDIN_ACCESS_TOKEN_KEY = "LINKEDIN_ACCESS_TOKEN"
LINKEDIN_ID_KEY = "LINKEDIN_LINKEDIN_ID"

# File Paths
HTML_DIR = os.path.join(os.path.dirname(__file__), "auth/html")
CALLBACK_RESULT_TEMPLATE = os.path.join(HTML_DIR, "callback_result.html")

# LinkedIn API Endpoints
LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_USER_INFO_URL = "https://api.linkedin.com/v2/userinfo"
LINKEDIN_SHARE_URL = "https://api.linkedin.com/v2/ugcPosts"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_REGISTER_UPLOAD_URL = 'https://api.linkedin.com/v2/assets?action=registerUpload'

# OAuth Configuration
LINKEDIN_SCOPES = ["openid", "email", "profile", "w_member_social"]
DEFAULT_STATE = "12345"
DEFAULT_RESPONSE_TYPE = "code"

# API Headers
DEFAULT_HEADERS = {
    'Content-Type': 'application/json',
    'X-Restli-Protocol-Version': '2.0.0'
}

# HTML Templates
AUTH_PAGE_TEMPLATE = '''
<h1>Linkedin Authentication</h1>
<a href="{auth_url}">Click here to authenticate</a>
'''
