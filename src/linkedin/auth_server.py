import json
import logging
import os
import urllib.parse

import requests
from flask import Flask, render_template_string, request
from pyngrok import ngrok

from src.utils.log_handler import TruncateByTimeHandler

app = Flask(__name__)
PWD = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(PWD, '..', ".."))
LOGGING_DIR = os.path.join(PROJECT_DIR, "logs") if os.name != 'nt' else os.path.join(r"C:\\", "ProgramData", "linkedin_assistant", "logs")
FILE = os.path.basename(__file__)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = TruncateByTimeHandler(filename=os.path.join(LOGGING_DIR, f'{FILE}.log'), encoding='utf-8', mode='a+')
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter(f'%(asctime)s - %(name)s - {__name__} - %(levelname)s - %(message)s'))
logger.addHandler(handler)
config_dir = os.path.join(r"C:\\", "ProgramData", "linkedin_assistant", "linkedin", "config.json") if os.name == 'nt' else os.path.join(PWD, "config.json")

def requires_authorization():
    """
    Redirects to the authorization page. This is the first step in the oauth2 process.
    :return:
    """
    logger.info(f'Getting authorization')
    scope = urllib.parse.quote('openid email profile w_member_social')
    auth_url = f"https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}/callback&state=12345&scope={scope}"
    return render_template_string(
        f'''
        <h1>Linkedin Authentication</h1>
        <a href="{auth_url}">
        Click here to authenticate
        </a>
        '''
    )


def get_linkedin_id(access_token):
    """
    Get the linkedin id given the access token.
    :param access_token:
    :return:
    """
    logger.info(f'Getting linkedin id')
    api_url = 'https://api.linkedin.com/v2/userinfo'
    linkedin_id = None
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Connection': 'Keep-Alive',
        'Content-Type': 'application/json',
    }
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        logger.info(f'Linkedin id obtained')
        linkedin_id = response.json()['sub']
        logger.info(f'Linkedin id obtained')
    else:
        logger.error(f'Error: {response.status_code} {response.text}')
    return linkedin_id


def get_access_token(auth_code, redirect_uri, client_id, client_secret):
    """
    Get the access token given the authorization code.
    :param auth_code:  authorization code
    :param redirect_uri:  redirect uri
    :param client_id: client id is the api key retrieved from linkedin.
    :param client_secret:  client secret is the api secret retrieved from linkedin.
    :return:  access token and linkedin id
    """
    access_token = None
    linkedin_id = None
    url = 'https://www.linkedin.com/oauth/v2/accessToken'
    params = {
        'grant_type': 'authorization_code',
        'code': auth_code,
        'redirect_uri': f'{redirect_uri}/callback',
        'client_id': client_id,
        'client_secret': client_secret
    }
    logger.info(f'Getting access token')
    response = requests.post(url, data=params)

    if response.status_code == 200:
        access_token = response.json()['access_token']
        logger.info(f'Access token obtained')
        linkedin_id = get_linkedin_id(access_token)
    else:
        logger.error(f'Error: {response.status_code} {response.text}')
    return access_token, linkedin_id


@app.route('/')
def linkedin_authentication():
    """
    Route to the authentication page.
    :return:
    """
    logger.info(f'Getting authentication page')
    return requires_authorization()


@app.route('/callback', methods=['GET'])
def callback():
    """
    Callback route. It is called after the user has authorized the application. It gets the code and
    saves the access token and the linkedin id in the config file. This token is needed in order to be able to publish
    and expires every once in a while
    :return:  callback result page
    """
    logger.info(f'Getting callback')
    with open(config_dir, "r") as f:
        config = json.load(f)
    code = request.args.get('code')
    logger.info(f'Callback received')
    client_id = config["client_id"]
    client_secret = config["client_secret"]
    redirect_uri = config["redirect_uri"]
    access_token, linkedin_id = get_access_token(
        auth_code=code,
        redirect_uri=redirect_uri,
        client_id=client_id,
        client_secret=client_secret
    )

    config["access_token"] = access_token
    config["linkedin_id"] = linkedin_id
    with open(os.path.join(PWD, "config.json"), "w") as f:
        json.dump(config, f, default=str, indent=4)

    with open(os.path.join(PWD, "html", "callback_result.html"), "r") as f:
        page = f.read()
    return render_template_string(page)


if __name__ == '__main__':
    """
    This is the main function. It starts the server and ngrok to expose the server to the internet. We use 
    ngrok because we need to specify a redirect uri in the linkedin app, and it needs to be a public url.
    
    The code that exposes the API is on the Telegram bot.
    
    Beware that this is not secure, what I do is to allow traffic only from my phone MAC address, so that only I can
    access the server.
    """
    logger.info("Initializing linkedin authentication server")
    with open(config_dir, "r") as f:
        config = json.load(f)
    client_id = config["client_id"]
    redirect_uri = config["redirect_uri"]
    del config
    app.run(host='localhost', port=5000)
