import datetime
import json
import logging
import os
import sys
import threading
import time
from ast import literal_eval
from dataclasses import dataclass
from functools import wraps

from origamibot.listener import Listener
from origamibot import OrigamiBot as Bot
import re
from src.telegram.suggestions.pool import SuggestionPool
from pyngrok import ngrok

from src.linkedin.publisher import LinkedinPublisher
from src.llm.langchain_agent.langchainGPT import LangChainGPT
from src.utils.log_handler import TruncateByTimeHandler

MAX_RETRIES = 5
PWD = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(PWD, '..', ".."))
LOGGING_DIR = os.path.join(PROJECT_DIR, "logs") if sys.platform != 'win32' else os.path.join(r"C:\\", "ProgramData", "linkedin_assistant", "logs")
FILE = os.path.basename(__file__)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = TruncateByTimeHandler(filename=os.path.join(LOGGING_DIR, f'{FILE}.log'), encoding='utf-8', mode='a+')
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter(f'%(asctime)s - %(name)s - {__name__} - %(levelname)s - %(message)s'))
logger.addHandler(handler)

config_dir = os.path.join(PWD, "config.json") if sys.platform != 'win32' else os.path.join(r"C:\\", "ProgramData", "linkedin_assistant", "telegram",  "config.json")


def stateful(func):
    """
    Decorator to update the config file after a function is called.
    :param func:  function to decorate
    :return:  decorated function
    """
    logger.debug("Updating config")

    @wraps(func)
    def update_config(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        with open(config_dir) as f:
            config = json.load(f)

        with self.mutex:
            for key in config.keys():
                if key in self.__dict__.keys():
                    config[key] = getattr(self, key)

        with open(config_dir, "w") as f:
            json.dump(config, f, indent=4, default=str)

        return result

    return update_config


class BotState:
    """
    This class is used to store the state of the bot. It is used to store the chat id, the current suggestion, and the
    suggestions are blocked or not. For every publication (suggestion) there needs to be a conversation thread.
    Via Bot commands I can change the conversation thread, so I can finish "tuning" the publication and then publish it.

    The suggestions are in order, so I can go to the next or previous suggestion. I can also select a suggestion by index.
    Also, this state also saves information about when to automatically make suggestions, which would be when no suggestion is
    selected and after some time after a publication is made. The stateful decorator is used to update the config file after
    a function is called, so the file is always updated with the object state.

    """

    def __init__(self):
        self.suggestions_are_blocked = None
        self.chat_id = None
        self.just_published = False
        self.auth_address = None
        self.conversation_mode_on = False
        self.llm_agent = LangChainGPT()
        self.mutex = threading.Lock()
        self.pool = SuggestionPool()
        self.pool.update()
        logger.debug("Reloading config")
        with open(config_dir) as f:
            config = json.load(f)
        for key in config.keys():
            if key in self.__dict__.keys():
                self.__setattr__(key, config[key])
        if len(self.pool) > 0 and self.pool.current:
            self.llm_agent.load_memory(self.pool.current.path)

    @stateful
    def reset(self):
        """
        Reset the state.

        """
        logger.info("Resetting state")
        with self.mutex:
            self.suggestions_are_blocked = None
            self.just_published = False
            self.llm_agent.memory.clear()

    def is_conversation_mode(self):
        """
        Getter for the conversation mode flag.
        :return:
        """
        with self.mutex:
            return self.conversation_mode_on or self.pool.current is None

    @stateful
    def set_conversation_mode(self):
        """
        Setter for the conversation mode flag.
        :return:
        """
        logger.info("Setting conversation mode")
        with self.mutex:
            self.conversation_mode_on = True

    @stateful
    def set_assistant_mode(self):
        """
        Setter for the conversation mode flag.
        :return:
        """
        logger.info("Setting assistant mode")
        with self.mutex:
            self.conversation_mode_on = False

    @stateful
    def did_just_published(self, did_publish):
        """
        Set the just published flag. If set to True, the suggestions are blocked until blocking period ends
         and the memory is cleared. Clearing the memory means that the conversation thread is reset.
        :param did_publish:  True if just published, False otherwise

        """
        logger.info("Setting just published")
        with self.mutex:
            self.just_published = did_publish
            if did_publish:
                self.suggestions_are_blocked = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.llm_agent.memory.clear()

    @stateful
    def set_chat_id(self, chat_id):
        """
        Set the chat id. The chat id is used to send messages to the user.
        :param chat_id:
        :return:
        """
        logger.info("Setting chat id")
        with self.mutex:
            self.chat_id = chat_id

    @stateful
    def block_suggestions(self):
        """
        Block suggestions. This is used to block suggestions when the user is interacting with the bot.
        :return:
        """
        logger.info("Blocking suggestions")
        with self.mutex:
            self.suggestions_are_blocked = True

    @stateful
    def conversation_mode(self):
        """
        This is used in order to be able to interact with the bot without suggestions
        :return:
        """
        self.block_suggestions()
        self.set_conversation_mode()
        self.llm_agent.memory.clear()

    def assistant_mode(self):
        """
        This is used to go back to the assistant mode
        :return:
        """
        self.allow_suggestions()
        self.set_assistant_mode()
        self.llm_agent.memory.clear()
        if self.pool.current:
            self.llm_agent.load_memory(self.pool.current.path)

    @stateful
    def allow_suggestions(self):
        """
        Allow suggestions. This is used to allow suggestions when the user is not interacting with the bot.
        :return:
        """
        logger.info("Allowing suggestions")
        with self.mutex:
            self.suggestions_are_blocked = False

    def are_suggestions_blocked(self):
        """
        Getter for the suggestions are blocked flag.
        :return:
        """
        with self.mutex:
            return self.suggestions_are_blocked

    def get_chat_id(self):
        """
        Getter for the chat id.
        :return:
        """
        with self.mutex:
            return self.chat_id

    def has_just_published(self):
        """
        Getter for the just published flag.
        :return:
        """
        with self.mutex:
            return self.just_published


class BotsCommands:
    """

    This class is used to define the bot commands. The bot commands are used to interact with the bot via the telegram
    chat. These commands allow me to execute special functions, like starting the bot, stopping the bot, publishing, listing
    suggestions, etc.

    Commands take the form /command_name, where command_name is the name of the actual method that will be called.

    """

    def __init__(self, bot: Bot, publisher, bot_state):
        self.bot = bot
        self.publisher = publisher
        self.state = bot_state

    def start(self, message):
        """
        Start the bot. This is the first command that needs to be executed.
        :param message:  message received
        :return:
        """
        logger.info("Starting operation triggered")
        self.state.set_chat_id(message.chat.id)
        self.bot.send_message(
            message.chat.id, 'Welcome to the Linkedin Assistant Bot!')

    def healthcheck(self, message):
        """
        Healthcheck command. It is used to check if the bot is alive.
        :param message: message received
        :return:
        """
        logger.info("Healthcheck triggered")
        self.bot.send_message(
            message.chat.id, 'I am alive!')

    def allow(self, message):
        """
        Allow suggestions. This is used to allow for the bot to send suggestions when the user is not interacting with the bot.
        :param message: message received
        :return:
        """
        logger.info("Allowing suggestions")
        self.state.allow_suggestions()
        self.bot.send_message(
            message.chat.id, 'Suggestions allowed!')

    def stop(self, message):
        """
        Stop suggestions. This is used to stop the bot from sending suggestions when the user is interacting with the bot.
        :param message: message received
        :return:
        """
        logger.info("Stopping suggestions")
        self.state.block_suggestions()
        self.bot.send_message(
            message.chat.id, 'Stopping suggestions!')

    def converse(self, message):
        """
        Conversation mode. This is used to stop the bot from sending suggestions when the user is interacting with the bot.
        :param message: message received
        :return:
        """
        logger.info("Conversation mode")
        self.state.conversation_mode()
        self.bot.send_message(
            message.chat.id, 'Conversation mode!')

    def assist(self, message):
        """
        Assistant mode. This is used to stop the bot from sending suggestions when the user is interacting with the bot.
        :param message: message received
        :return:
        """
        logger.info("Assistant mode")
        self.state.assistant_mode()
        self.bot.send_message(
            message.chat.id, 'Assistant mode!')

    def clear(self, message):
        """
        Clear the current publication. This is used to clear the current publication, so that the bot can suggest a new one.
        The publication is discarded completely from the folder and the memory is cleared.
        :param message: message received
        :return:
        """
        logger.info("Clear triggered")
        try:
            self.state.pool.remove(self.state.pool.current.id)
            self.state.reset()
            self.bot.send_message(message.chat.id, "Cleared current publication")
        except Exception as e:
            self.bot.send_message(message.chat.id, f"Error clearing publication: {e}")

    def update(self, message):
        """
        Update the suggestions. This is used to update the suggestions. It will check for new suggestions in the folder.
        Updating the suggetions is necessary so the Suggestion Pool gets synchronized with the folder.
        :param message: message received
        :return:
        """
        logger.info("Update triggered")
        try:
            self.state.pool.update()
            self.bot.send_message(message.chat.id, "Updated suggestions")
        except Exception as e:
            self.bot.send_message(message.chat.id, f"Error updating suggestions: {e}")

    def list(self, message):
        """
        List the suggestions. This is used to list the suggestions. It will show the suggestions in the pool. with an index
        The index can then be used to select a suggestion.
        :param message: message received
        :return:
        """
        logger.info("List triggered")

        if len(self.state.pool) > 0:

            index_plus_suggestions = [f'{i}: {os.path.split(s.path)[-1]}' for i, s in enumerate(self.state.pool)]
            logger.info("Suggestions:\n\n%s", "\n".join(index_plus_suggestions))
            self.bot.send_message(message.chat.id, "Suggestions:\n\n{}:".format("\n".join(index_plus_suggestions)))
        else:
            self.bot.send_message(message.chat.id, "No suggestions to show")

    def select(self, message, index: int):
        """
        Select a suggestion. This is used to select a suggestion. It will load the memory of the selected suggestion.
        :param message: message received, It would only be the command part, but the actual
        message needs to be: "/select `index`"
        :param index: Index of the suggestion to select
        :return:
        """
        logger.info("Select triggered")
        try:

            current, isthesame = self.state.pool.select(index)
            if isthesame:
                self.bot.send_message(message.chat.id, "You selected the same suggestion")
            elif current:
                self.state.llm_agent.load_memory(current.path)
                self.bot.send_message(message.chat.id, str(current))
            else:
                self.bot.send_message(message.chat.id, "selected suggestion is out of bounds")
        except Exception as e:
            logger.error("Error selecting suggestion: %s", e)
            self.bot.send_message(message.chat.id, "Error selecting suggestion")

    def previous(self, message):
        """
        Select the previous suggestion. This is used to select the previous suggestion. It will load the memory of the selected suggestion.
        :param message: message received
        :return:
        """
        logger.info("Previous triggered")
        try:
            current, isthesame = self.state.pool.previous()
            if isthesame or not current:
                self.bot.send_message(message.chat.id, "No more suggestions")
            else:
                self.state.llm_agent.load_memory(current.path)
                self.bot.send_message(message.chat.id, str(current))
        except Exception as e:
            logger.error("Error loading previous suggestion: %s", e)
            self.bot.send_message(message.chat.id, "Error loading previous suggestion")

    def next(self, message):
        """
        Select the next suggestion. This is used to select the next suggestion. It will load the memory of the selected suggestion.
        :param message:
        :return:
        """
        logger.info("Next triggered")
        try:
            current, isthesame = self.state.pool.next()
            if isthesame or not current:
                self.bot.send_message(message.chat.id, "No more suggestions")
            else:
                self.state.llm_agent.load_memory(current.path)
                self.bot.send_message(message.chat.id, str(current))
        except Exception as e:
            logger.error("Error loading next suggestion: %s", e)
            self.bot.send_message(message.chat.id, "Error loading next suggestion")

    def conversation_mode(self, message):
        self.state.block_suggestions()


    def publish(self, message):
        """
        Publish the current suggestion. This is used to publish the current suggestion. It will post the suggestion to linkedin.
        If the user is not authenticated, it will send a message with the authentication link.
        :param message:
        :return:
        """
        logger.info("Publish triggered")
        publication = self.state.llm_agent.get_last_message()
        result = self.publisher.post(publication)
        if not result:
            self.bot.send_message(message.chat.id,
                                  f"Please, authenticate using this link: {self.state.auth_address}")
        else:
            self.bot.send_message(message.chat.id, "Published: \n\n{}".format(publication))
            self.state.pool.remove(self.state.pool.current.id)
        self.state.did_just_published(result)

    def current(self, message):
        """
        Get the current suggestion. This is used to get the current suggestion. It will show the current suggestion, so you actually know
        the content that you will upload to linkedin.
        :param message:
        :return:
        """
        logger.info("Get current publication")
        publication = self.state.llm_agent.get_last_message()
        if publication:
            self.bot.send_message(message.chat.id, publication)
        else:
            self.bot.send_message(message.chat.id, "No publication available yet")



    # IDEAS:
    """
    1. Send PDFs to the bot via Telegram, so they are added to the manual PDFs input folder and can be processed.
    2. When I implement Youtube as a source, I can send the link to the bot and it will be processed. This could also be done
    with Medium or any of the sources for that matter.
    
    """


class MessageListener(Listener):
    """
    This class is used to listen to messages. It is used to listen to messages and send them to the LLMChain agent.
    They get added to the conversation thread and the response is sent back to the user.
    """
    def __init__(self, bot, state):
        self.bot = bot
        self.state = state

    def on_message(self, message):
        """
        On message received. This is used to listen to messages and send them to the LLMChain agent.
        :param message: message received
        :return:
        """
        if message.text.startswith("/"):
            return
        logger.info("Message received")
        response = self.state.llm_agent.call(input=message.text, use_system_prompt=self.state.is_conversation_mode())
        self.bot.send_message(message.chat.id, response)
        if self.state.pool.current:
            self.state.llm_agent.save_memory(self.state.pool.current.path)

    def on_command_failure(self, message, err=None):  # When command fails
        """
        On command failure. This is used to send a message to the user when a command fails.
        :param message:
        :param err:
        :return:
        """
        logger.error("Command failed")
        if err is None:
            self.bot.send_message(message.chat.id,
                                  'Command failed to bind arguments!')
        else:
            self.bot.send_message(message.chat.id,
                                  f'Error in command:\n{err}')


class TeleLinkedinBot:
    """
    This class is used to define the bot. It is used to define the bot and run it. It also handles the Linkedin
    Publisher object in order to trigger a publication, and exposes the auth server on the internet via NGro on port 5000
    Note that my NGrok domain is persistent throughout NGrok sessions, so I can use the same domain for the auth server.
    For this you need to create an account on NGrok and get a token.

    Also note that in order for this class to be accesible through Telegram you need to create the Telegram Bot on the app
    and that you need to create a Linkedin app and get the client id and client secret. You also need to specify a redirect uri
    for the Linkedin app. This redirect uri needs to be the same as the one used in the auth server.

    All of this is documented on the readthedocs page though.
    """

    def __init__(self):
        self.token = ""
        self.username = ""
        self.name = ""
        self.bot = None
        self.suggestion_period = None
        self.ngrok_token = ""
        self.state = None
        self.publisher = LinkedinPublisher()
        self.domain = ""

        self.reload_config()

    def __enter__(self):
        """
        Expose the auth server on the internet via NGrok on port 5000. Using the enter/exit functions is convenient
        because it will automatically disconnect the tunnel when the program is finished.
        :return: self
        """
        ngrok.set_auth_token(self.ngrok_token)
        self.http_tunnel = ngrok.connect(addr="localhost:5000", proto="http", domain=self.domain)

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Disconnect the tunnel when the program is finished.
        :param exc_type:
        :param exc_value:
        :param traceback:
        :return:
        """
        ngrok.disconnect(self.http_tunnel.public_url)
        ngrok.kill()

    def reload_config(self):
        """Reload the configuration."""
        logger.info("Reloading config")
        with open(config_dir, "r") as f:
            config = json.load(f)

        for key in config.keys():
            if key in self.__dict__.keys():
                self.__setattr__(key, config[key])

        self.bot = Bot(self.token)
        self.state = BotState()
        self.state.auth_address = f'https://{self.domain}'
        self.bot.add_listener(MessageListener(self.bot, self.state))
        self.bot.add_commands(BotsCommands(self.bot, self.publisher, self.state))
        self.bot.start()

    def run(self):
        """
        Run the bot. This is used to run the bot. It will send a suggestion every suggestion_period days.
        The algorithm is as follows:
        1. Check if the bot has just published. If so, wait for suggestion_period days.
        2. Check if suggestions are blocked. If so, wait for 5 minutes in order to check again
        3. If suggestions are not blocked, update the suggestions and check if there are suggestions.
        4. If there are suggestions, send the current suggestion and block suggestions. Then the flow of the program
        is carried by the interaction with the user via Telegram.

        """
        logger.info("Starting bot")

        while True:
            time.sleep(5)
            chat_id = self.state.get_chat_id()
            logger.info("Chat id: %s", chat_id)
            if self.state.has_just_published():
                logger.info("Just published, waiting for %s days", self.suggestion_period)
                time.sleep(60 * 60 * 24 * self.suggestion_period)
                self.state.did_just_published(False)
            try:
                if not self.state.are_suggestions_blocked():
                    self.state.pool.update()
                    if len(self.state.pool) > 0:
                        current = self.state.pool.current

                        self.bot.send_message(chat_id, str(current))
                        self.state.block_suggestions()
                    else:
                        time.sleep(5 * 60)
                        logger.info(f"Suggestions are blocked")
            except Exception as e:
                logger.error("Error sending suggestion: %s", e)
                if chat_id:
                    self.bot.send_message(chat_id, "Error sending suggestion: {}".format(e))
                    self.state.reset()


if __name__ == '__main__':
    logger.info("Starting bot script")
    with TeleLinkedinBot() as bot:
        bot.run()
