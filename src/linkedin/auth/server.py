import urllib.parse
from src.linkedin.constants import *
import requests
from flask import Flask, render_template_string, request
from src.core.vault.hvault import VaultClient
import src.core.utils.functions as F

FILE = os.path.basename(__file__)
logger = F.get_logger(dump_to=FILE)
vault_client = VaultClient()
app = Flask(__name__)


def requires_authorization():
    """
    Redirects to the authorization page. This is the first step in the oauth2 process.
    :return:
    """
    logger.info(f'Getting authorization')
    scope = urllib.parse.quote(' '.join(LINKEDIN_SCOPES))
    auth_url = f"{LINKEDIN_AUTH_URL}?response_type={DEFAULT_RESPONSE_TYPE}&client_id={vault_client.get_secret(LINKEDIN_CLIENT_ID_KEY)}&redirect_uri={vault_client.get_secret(LINKEDIN_REDIRECT_URI_KEY)}/callback&state={DEFAULT_STATE}&scope={scope}"
    return render_template_string(AUTH_PAGE_TEMPLATE.format(auth_url=auth_url))


def get_linkedin_id(access_token):
    """
    Get the linkedin id given the access token.
    :param access_token:
    :return:
    """
    logger.info(f'Getting linkedin id')
    linkedin_id = None
    headers = {**DEFAULT_HEADERS, 'Authorization': f'Bearer {access_token}'}

    try:
        response = requests.get(LINKEDIN_USER_INFO_URL, headers=headers)
        if response.status_code == 200:
            logger.info(f'Linkedin id obtained')
            linkedin_id = response.json()['sub']
            logger.info(f'Linkedin id obtained')
        else:
            logger.error(f'Error: {response.status_code} {response.text}')
    except Exception as e:
        logger.error(f'Error: {e}')

    return linkedin_id


def get_access_token(self, auth_code):
    """
    Get the access token given the authorization code.
    :param auth_code:  authorization code
    :return:  access token and linkedin id
    """
    access_token = None
    linkedin_id = None
    url = LINKEDIN_TOKEN_URL
    params = {
        'grant_type': 'authorization_code',
        'code': auth_code,
        'redirect_uri': f'{vault_client.get_secret(LINKEDIN_REDIRECT_URI_KEY)}/callback',
        'client_id': vault_client.get_secret(LINKEDIN_CLIENT_ID_KEY),
        'client_secret': vault_client.get_secret(LINKEDIN_CLIENT_SECRET_KEY)
    }
    logger.info(f'Getting access token')
    response = requests.post(url, data=params)

    if response.status_code == 200:
        access_token = response.json()['access_token']
        logger.info(f'Access token obtained')
        linkedin_id = self.get_linkedin_id(access_token)
    else:
        logger.error(f'Error: {response.status_code} {response.text}')
    return access_token, linkedin_id


def run():
    """
    This is the main function. It starts the server and ngrok to expose the server to the internet. We use
    ngrok because we need to specify a redirect uri in the linkedin app, and it needs to be a public url.

    The code that exposes the API is on the Telegram bot.

    Beware that this is not secure, what I do is to allow traffic only from my phone MAC address, so that only I can
    access the server.
    """
    logger.info("Initializing linkedin authentication server")
    app.run(host='localhost', port=5000)


@app.route('/')
def linkedin_authentication():
    """
    Route to the authentication page.
    :return:
    """
    logger.info(f'Getting authentication page')
    return requires_authorization()


@app.route('/callback')
def callback():
    """
    Callback route. It is called after the user has authorized the application. It gets the code and
    saves the access token and the linkedin id in the config file. This token is needed in order to be able to publish
    and expires every once in a while
    :return:  callback result page
    """
    auth_code = request.args.get('code')
    if not auth_code:
        return "No authorization code received", 400

    # Exchange auth code for access token
    params = {
        'grant_type': 'authorization_code',
        'code': auth_code,
        'redirect_uri': f'{vault_client.get_secret(LINKEDIN_REDIRECT_URI_KEY)}/callback',
        'client_id': vault_client.get_secret(LINKEDIN_CLIENT_ID_KEY),
        'client_secret': vault_client.get_secret(LINKEDIN_CLIENT_SECRET_KEY)
    }

    response = requests.post(LINKEDIN_TOKEN_URL, data=params)
    if response.status_code != 200:
        return "Failed to get access token", 400

    access_token = response.json().get('access_token')
    linkedin_id = get_linkedin_id(access_token)

    # Save tokens in vault
    vault_client.create_or_update_secret(LINKEDIN_ACCESS_TOKEN_KEY, access_token)
    vault_client.create_or_update_secret(LINKEDIN_ID_KEY, linkedin_id)

    with open(CALLBACK_RESULT_TEMPLATE, "r") as f:
        page = f.read()
    return render_template_string(page)


if __name__ == '__main__':
    """
    Run the main function.
    """
    run()
