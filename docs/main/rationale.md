

<h2> Main Modules</h2>

This module only contains the main script that is run in order to run the different services 
that form the application. It creates the services as asyncio tasks and runs them in parallel.

<h3> Tasks </h3>

The main tasks that are run by this module are the following:

* Auth server: This task runs the authentication flask server that is used to authenticate users
  and to generate the access tokens that are used to publish on LinkedIn.
* Bot Agent: The Telegram Bot
* Publications Handler: This task is responsible for publishing the publications on LinkedIn
* Sources Handler: This task is responsible for retrieving the publications from the different sources