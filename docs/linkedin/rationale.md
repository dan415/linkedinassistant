

<h2> LinkedIn </h2>

This module is used to integrate with LinkedIn. It is used to authenticate the user and to give access to the LinkedIn API to post content.


<h3> Authentication </h3>

This module exposes two REST methods to authenticate the user with LinkedIn. The first one is used to get the URL to redirect the user to, and the second one is used to get the access token after the user has been redirected back to the application.

The authentication process is as follows: 
1. The user tries to publish content to LinkedIn.
2. The application checks if the user is authenticated. If not, it redirects the user to the authentication URL, exposed on "/". This sends the auth request to LinkedIn using the client_id and secret of the application.
3. After the user is redirected to the LinkedIn Authentication page, the user needs to log in with an account that is member of the page.
4. After the user logs in, LinkedIn redirects the user back to the application, with the access token as a parameter at "/callback".
5. The Callback saves the access token in the LinkedIn config file, and then the user can finally prompt to publish again, this time succesfully.

<h3> Configuration </h3>

The configuration file is located in the `information/sources/linkedin` folder, and is named `config.json`. It contains the following parameters:

* `client_id`: The client ID of the application. This is used to authenticate the user with LinkedIn.
* `client_secret`: The client secret of the application. This is used to authenticate the user with LinkedIn.
* `redirect_uri`: The redirect URI of the application. This is used to authenticate the user with LinkedIn.
* `access_token`: The access token of the user. This is used to authenticate the user with LinkedIn.
* `linkedin_id`: The LinkedIn ID of the page to post to. This is used to authenticate the user with LinkedIn.
* `footer`: The footer to add to the post. This is used to add a footer to the post. I use it to specify that the post was posted automatically by an AI