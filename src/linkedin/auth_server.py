import logging
import os
import urllib.parse
from typing import Tuple
from jinja2 import Template
from src.core.constants import SecretKeys, HTML_DIR
import requests
from flask import Flask, request
from src.core.utils.logging import ServiceLogger
from src.core.vault.hashicorp import VaultClient
from waitress import serve

logger = ServiceLogger(__name__)


# Constants defining LinkedIn scopes and API endpoints
_LINKEDIN_SCOPES = ["openid", "email", "profile", "w_member_social"]
_DEFAULT_STATE = "12345"
_DEFAULT_RESPONSE_TYPE = "code"
_CALLBACK_RESULT_TEMPLATE = os.path.join(HTML_DIR, "callback_result.html")
_AUTH_PAGE_TEMPLATE_PATH = os.path.join(HTML_DIR, "auth.html")
_LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
_LINKEDIN_USER_INFO_URL = "https://api.linkedin.com/v2/userinfo"
_LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
_DEFAULT_HEADERS = {
    "Content-Type": "application/json",
    "X-Restli-Protocol-Version": "2.0.0",
}

# Constants for server configuration
_SERVER_HOST: str = "localhost"
_SERVER_PORT: int = 5000

vault_client = VaultClient()
app = Flask(__name__)


# Making own load template bc for some reason Flask developers decided the only way to load a template is using
# "/" as separator and not os.path.sep :)
def load_template(path):
    with open(path, "r") as fp:
        return Template(fp.read())


def requires_authorization() -> str:
    """
    Generates the LinkedIn OAuth2 authorization URL and serves the authentication page.
    :return: Rendered authentication HTML page.
    """
    logger.info("Generating authorization URL")
    scope = urllib.parse.quote(" ".join(_LINKEDIN_SCOPES))
    redirect_uri = "https://" + vault_client.get_secret(SecretKeys.NGROK_DOMAIN)
    auth_url = (
        f"{_LINKEDIN_AUTH_URL}?response_type={_DEFAULT_RESPONSE_TYPE}"
        f"&client_id={vault_client.get_secret(SecretKeys.LINKEDIN_CLIENT_ID)}"
        f"&redirect_uri={redirect_uri}/callback&state={_DEFAULT_STATE}&scope={scope}"
    )

    return load_template(_AUTH_PAGE_TEMPLATE_PATH).render(auth_url=auth_url)


def get_linkedin_id(access_token: str) -> str:
    """
    Retrieves the LinkedIn user ID using the provided access token.
    :param access_token: The OAuth2 access token.
    :return: LinkedIn's user ID if available, None otherwise.
    """
    truncated_token = access_token[:10] + "..." if access_token else "None"
    logger.info(f"Retrieving LinkedIn ID with token prefix: {truncated_token}")
    linkedin_id = None
    headers = {**_DEFAULT_HEADERS, "Authorization": f"Bearer {access_token}"}

    try:
        response = requests.get(_LINKEDIN_USER_INFO_URL, headers=headers)
        if response.status_code == 200:
            linkedin_id = response.json()["sub"]
            logger.info("Successfully retrieved LinkedIn ID")
        elif response.status_code == 401:
            logger.error("Unauthorized: Invalid or expired token.")
        elif response.status_code == 403:
            logger.error("Forbidden: Access denied.")
        elif response.status_code == 404:
            logger.error("Not Found: Endpoint does not exist.")
        else:
            logger.error(
                f"Unexpected error: {response.status_code} {response.text}"
            )
    except Exception as e:
        logger.error(f"Error while retrieving LinkedIn ID: {e}")

    return linkedin_id


@app.route("/")
def linkedin_authentication() -> str:
    """
    Serves the LinkedIn authentication page.
    :return: Rendered authentication HTML page.
    """
    logger.info("Serving authentication page")
    return requires_authorization()


@app.route("/callback")
def callback() -> Tuple[str, int]:
    """
    Handles the OAuth2 callback, exchanges the authorization code for an access token,
    and stores the token and LinkedIn user ID in the vault.
    :return: Rendered callback result HTML page.
    """
    auth_code = request.args.get("code")
    redirect_uri = "https://" + vault_client.get_secret(SecretKeys.NGROK_DOMAIN)
    if not auth_code:
        logger.error("Authorization code not received")
        return "No authorization code received", 400

    # Exchange the authorization code for an access token
    params = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": f"{redirect_uri}/callback",
        "client_id": vault_client.get_secret(SecretKeys.LINKEDIN_CLIENT_ID),
        "client_secret": vault_client.get_secret(
            SecretKeys.LINKEDIN_CLIENT_SECRET
        ),
    }

    response = requests.post(_LINKEDIN_TOKEN_URL, data=params)
    if response.status_code != 200:
        logger.error("Failed to exchange authorization code for access token")
        return "Failed to get access token", 400

    access_token = response.json().get("access_token")
    linkedin_id = get_linkedin_id(access_token)

    # Save the retrieved tokens and IDs in the vault
    vault_client.create_or_update_secret(
        SecretKeys.LINKEDIN_ACCESS_TOKEN, access_token
    )
    vault_client.create_or_update_secret(SecretKeys.LINKEDIN_ID, linkedin_id)

    logger.info("Successfully handled callback and saved credentials")
    return load_template(_CALLBACK_RESULT_TEMPLATE).render(), 200


def run() -> None:
    """
    Starts the Flask application to handle LinkedIn OAuth2 authentication.
    The server is exposed to the internet using ngrok for public accessibility.
    """
    waitress_logger = logging.getLogger("waitress")
    waitress_logger.handlers = []

    # Then I replace them with the other loggers and remove propagation
    waitress_logger.handlers = logger.handlers
    waitress_logger.setLevel(logger.level)
    waitress_logger.propagate = False
    serve(app, host=_SERVER_HOST, port=_SERVER_PORT)


if __name__ == "__main__":
    """
    Entry point to start the server.
    """
    run()
