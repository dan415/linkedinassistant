import base64
import datetime
import threading
import time
from functools import wraps
from origamibot.listener import Listener
from origamibot import OrigamiBot as Bot, OrigamiBot
from src.core.config.manager import ConfigManager
from src.core.constants import SecretKeys
from src.core.b2.b2_handler import B2Handler
from src.core.vault.hvault import VaultClient
from src.information.constants import PublicationState
from src.information.publications import PublicationIterator
from src.information.sources.rapid.youtube.pool import YoutubeUrlPool
from src.linkedin.publisher import LinkedinPublisher
from pyngrok import ngrok
import requests
from src.llm.conversation.agent import LangChainGPT
from src.telegram.constants import *
import src.core.utils.functions as F
from src.telegram.exceptions import DownloadFileException, FetchFileException
import io

FILE = os.path.basename(__file__)
logger = F.get_logger(dump_to=FILE)


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
        config = self.config_client.load_config(CONFIG_SCHEMA)

        with self.mutex:
            for key in config.keys():
                if key in self.__dict__.keys():
                    config[key] = getattr(self, key)

        self.config_client.save_config(CONFIG_SCHEMA, config)

        return result

    return update_config


class OrigamiBotExtended(OrigamiBot):

    def __init__(self, token):
        super().__init__(token)
        self.file_manager = B2Handler()

    def _get_file_path(self, file_id):
        url = f"https://api.telegram.org/bot{self.token}/getFile?file_id={file_id}"
        response = requests.get(url)
        result = response.json()
        if result['ok']:
            return result['result']['file_path']
        else:
            raise FetchFileException(result)

    def _download_file(self, file_path):
        url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.content
        else:
            raise DownloadFileException(response.json())

    def get_file(self, document):
        try:
            file_path = self._get_file_path(document.file_id)
            return self._download_file(file_path)
        except (FetchFileException, DownloadFileException) as ex:
            logger.error(ex.message)
            return None

    def process_pdf(self, document, save_folder):
        bytes = self.get_file(document)
        if bytes:
            return self.file_manager.upload_pdf_bytes(bytes, save_folder + "/" + document.file_name)
        return None

    def process_image(self, image):
        bytes = self.get_file(image)
        return base64.b64encode(bytes)

    def send_publication(self, chat_id, publication):
        self.send_message(chat_id, publication["content"])
        if publication["image"]:
            self.send_photo(chat_id, io.BytesIO(base64.b64decode(publication["image"])))


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
        self.manual_pdfs_dir = "Information/Sources/Manual/Input"
        self.publications_collection = ""
        self.llm_agent = LangChainGPT()
        self.mutex = threading.Lock()
        self.vault_client = VaultClient()
        self.config_client = ConfigManager()

        logger.debug("Reloading config")
        config = self.config_client.load_config(CONFIG_SCHEMA)

        for key in config.keys():
            if key in self.__dict__.keys():
                self.__setattr__(key, config[key])

        self.publications_manager = PublicationIterator(self.publications_collection, PublicationState.PENDING_APPROVAL)

    @stateful
    def reset(self):
        """
        Reset the state.

        """
        logger.info("Resetting state")
        with self.mutex:
            self.llm_agent.memory.clear(self.llm_agent.convesation_id)
            self.llm_agent.convesation_id = None
            self.suggestions_are_blocked = None
            self.just_published = False

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

    def __init__(self, bot: OrigamiBotExtended, publisher, bot_state):
        self.bot = bot
        self.publisher = publisher
        self.state = bot_state
        # Path for manual PDFs input directory

        # Initialize URL pool for YouTube transcripts
        self.youtube_url_pool = YoutubeUrlPool()

    def start(self, message):
        """
        Start the bot. This is the first command that needs to be executed.
        :param message:  message received
        :return:
        """
        logger.info("Starting operation triggered")
        self.state.set_chat_id(message.chat.id)
        self.bot.send_message(
            message.chat.id,
            MSG_START.format(message.chat.id)
        )

    def healthcheck(self, message):
        """
        Healthcheck command. It is used to check if the bot is alive.
        :param message: message received
        :return:
        """
        logger.info("Healthcheck triggered")
        self.bot.send_message(message.chat.id, MSG_HEALTHCHECK)

    def allow(self, message):
        """
        Allow suggestions. This is used to allow for the bot to send suggestions when the user is not interacting with the bot.
        :param message: message received
        :return:
        """
        logger.info("Allowing suggestions")
        self.state.allow_suggestions()
        self.bot.send_message(
            message.chat.id, MSG_SUGGESTIONS_ALLOWED
        )

    def stop(self, message):
        """
        Stop suggestions. This is used to stop the bot from sending suggestions when the user is interacting with the bot.
        :param message: message received
        :return:
        """
        logger.info("Stopping suggestions")
        self.state.block_suggestions()
        self.bot.send_message(
            message.chat.id, MSG_SUGGESTIONS_STOPPED
        )

    def clear(self, message):
        """
        Clear the current publication. This is used to clear the current publication, so that the bot can suggest a new one.
        The publication is discarded completely from the folder and the memory is cleared.
        :param message: message received
        :return:
        """
        logger.info("Clear triggered")
        try:
            self.state.publications_manager.update_state(self.state.llm_agent.conversation_id,
                                                         PublicationState.DISCARDED)
            self.state.reset()
            self.bot.send_message(message.chat.id, MSG_CLEARED)
        except Exception as e:
            self.bot.send_message(message.chat.id, f"Error clearing publication: {e}")

    def list(self, message):
        """
        List the suggestions. This is used to list the suggestions. It will show the suggestions in the pool. with an index
        The index can then be used to select a suggestion.
        :param message: message received
        :return:
        """
        logger.info("List triggered")

        if len(self.state.publications_manager) > 0:
            index_plus_suggestions = [f'{i}: {self.state.publications_manager.select(i)}' for i in
                                      range(len(self.state.publications_manager))]
            logger.info("Suggestions:\n\n%s", "\n".join(index_plus_suggestions))
            self.bot.send_message(message.chat.id, "Suggestions:\n\n{}:".format("\n".join(index_plus_suggestions)))
        else:
            self.bot.send_message(message.chat.id, MSG_NO_SUGGESTIONS)

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

            current = self.state.publications_manager.select(index)
            if current["publication_id"] == self.state.llm_agent.conversation_id:
                self.bot.send_message(message.chat.id, "You selected the same suggestion")
            elif current:
                self.state.llm_agent.conversation_id = current["publication_id"]
                self.bot.send_publication(message.chat.id, current)
            else:
                self.bot.send_message(message.chat.id, MSG_INVALID_INDEX)
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
            current = self.state.publications_manager.last()
            if current["publication_id"] == self.state.llm_agent.conversation_id or not current:
                self.bot.send_message(message.chat.id, MSG_NO_SUGGESTIONS)
            else:
                self.state.llm_agent.conversation_id = current["publication_id"]
                self.bot.send_publication(message.chat.id, current)
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
            current = next(self.state.publications_manager)
            if current["publication_id"] == self.state.llm_agent.conversation_id or not current:
                self.bot.send_message(message.chat.id, MSG_NO_SUGGESTIONS)
            else:
                self.state.llm_agent.conversation_id = current["publication_id"]
                self.bot.send_publication(message.chat.id, current)
        except Exception as e:
            logger.error("Error loading next suggestion: %s", e)
            self.bot.send_message(message.chat.id, "Error loading next suggestion")

    def clear_image(self, message):
        """Clear the currently generated image."""
        try:
            self.state.llm_agent.image = None
            self.state.publications_manager.update_image(self.state.llm_agent.conversation_id, None)
            self.bot.send_message(message.chat.id, "Image cleared")
        except Exception as e:
            logger.error("Error loading next suggestion: %s", e)
            self.bot.send_message(message.chat.id, "Error clearing image")

    def current(self, message):
        """
        Get the current suggestion. This is used to get the current suggestion. It will show the current suggestion,
        so you actually know the content that you will upload to linkedin.
        :param message:
        :return:
        """
        if not self.state.llm_agent.conversation_id:
            self.bot.send_message(message.chat.id, MSG_NO_CURRENT_SUGGESTION)
            return

        current = self.state.publications_manager.get(self.state.llm_agent.conversation_id)
        self.bot.send_publication(message.chat.id, current)

    def publish(self, message):
        """
        Publish the current suggestion. This is used to publish the current suggestion. It will post the suggestion to linkedin.
        If the user is not authenticated, it will send a message with the authentication link.
        :param message:
        :return:
        """

        if not self.state.llm_agent.conversation_id:
            self.bot.send_message(message.chat.id, MSG_NO_CURRENT_SUGGESTION)
            return

        if not self.publisher.is_authenticated():
            self.bot.send_message(message.chat.id,
                                  f"You need to authenticate first. Please click on this link: {self.state.auth_address}")
            return

        try:
            publication = self.state.publications_manager.get_content(self.state.llm_agent.conversation_id)
            image = self.state.publications_manager.get_image(self.state.llm_agent.conversation_id)

            if image:
                self.publisher.publish_with_image(publication, base64.b64decode(image))
            else:
                self.publisher.publish(publication)

            self.state.publications_manager.update_state(self.state.llm_agent.conversation_id,
                                                         PublicationState.PUBLISHED)

            self.bot.send_message(message.chat.id, MSG_PUBLISH_SUCCESS)
            self.state.reset()
            self.state.suggestions_are_blocked = False
            self.state.did_just_published = True

        except Exception as e:
            self.bot.send_message(message.chat.id, f"Failed to publish: {str(e)}")

    def add_youtube(self, message, youtube_url):
        """
        Add a YouTube URL to the transcript retriever pool.
        :param message: message received, format should be "/add_youtube <youtube_url>"
        :return:
        """
        try:
            # Basic validation for YouTube URL
            if not ('youtube.com' in youtube_url or 'youtu.be' in youtube_url):
                self.bot.send_message(message.chat.id, MSG_INVALID_URL)
                return

            # Add URL to the pool
            self.youtube_url_pool.add_url(youtube_url)
            self.bot.send_message(message.chat.id, f'YouTube video added to processing queue: {youtube_url}')

        except Exception as e:
            logger.error(f"Error processing YouTube URL: {str(e)}")
            self.bot.send_message(message.chat.id, 'Error processing YouTube URL. Please try again.')


class MessageListener(Listener):
    """
    This class is used to listen to messages. It is used to listen to messages and send them to the LLMChain agent.
    They get added to the conversation thread and the response is sent back to the user.
    """

    def __init__(self, bot, state):
        self.bot = bot
        self.state = state

    def respond(self, chat_id, response):
        self.bot.send_message(chat_id, response)

        if self.state.llm_agent.image:
            self.state.publications_manager.update_image(self.state.llm_agent.conversation_id,
                                                         self.state.llm_agent.image)
            photo = io.BytesIO(base64.b64decode(self.state.llm_agent.image))
            photo.seek(0)
            self.bot.send_photo(chat_id, photo)
            self.state.llm_agent.image = None
        else:
            self.state.publications_manager.update_content(self.state.llm_agent.conversation_id, response)

    def on_message(self, message):
        """
        On message received. This is used to listen to messages and send them to the LLMChain agent.
        :param message: message received
        :return:
        """
        logger.info("Message received")
        if message.text and message.text.startswith("/"):
            return
        elif message.document and message.document.mime_type == 'application/pdf':
            result = self.bot.process_pdf(message.document, self.state.manual_pdfs_dir)
            self.bot.send_message(message.chat.id,
                                  "File received succesfully!" if result else "Something went wrong, try later :(")
        elif message.photo:
            if self.state.llm_agent.conversation_id and self.state.publications_manager.get(
                    self.state.llm_agent.conversation_id):
                encoded_bytes = self.bot.process_image(message.photo)
                result = self.state.publications_manager.update_image(self.state.llm_agent.conversation_id,
                                                                      encoded_bytes)
                self.bot.send_message(message.chat.id,
                                      "Image updated succesfully" if result else "Something went wrong, try later :(")

        with self.state.mutex:  # Prevent loading of suggestions and that kind of thing while the bot is processing the message
            response = self.state.llm_agent.call(message.text)

        self.respond(message.chat.id, response)

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

        self.name = ""
        self.bot_name = ""
        self.bot = None
        self.suggestion_period = None
        self.state = None
        self.vault_client = VaultClient()
        self.publisher = LinkedinPublisher()
        self.config_client = ConfigManager()
        self.token = self.vault_client.get_secret(SecretKeys.TELEGRAM_BOT_TOKEN)
        self.ngrok_token = self.vault_client.get_secret(SecretKeys.NGROK_TOKEN)
        self.domain = self.vault_client.get_secret(SecretKeys.NGROK_DOMAIN)
        self.reload_config()

    def __enter__(self):
        """
        Expose the auth server on the internet via NGrok on port 5000. Using the enter/exit functions is convenient
        because it will automatically disconnect the tunnel when the program is finished.
        :return: self
        """
        ngrok.set_auth_token(self.ngrok_token)
        self.http_tunnel = ngrok.connect(addr=NGROK_ADDRESS, proto=NGROK_PROTOCOL, domain=self.domain)

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
        config = self.config_client.load_config(CONFIG_SCHEMA)

        for key in config.keys():
            if key in self.__dict__.keys():
                self.__setattr__(key, config[key])

        self.bot = OrigamiBotExtended(self.token)
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
                F.sleep(self.suggestion_period)
                self.state.did_just_published(False)
            try:
                if not self.state.are_suggestions_blocked():
                    self.state.publications_manager.refresh()
                    current = next(self.state.publications_manager)
                    if current:
                        suggestion = current["content"]
                        if suggestion:
                            self.state.llm_agent.conversation_id = current["publication_id"]
                            self.bot.send_publication(chat_id, suggestion)
                            self.state.block_suggestions()
                    else:
                        time.sleep(5 * 60)
                        logger.info(f"Suggestions are blocked")
            except Exception as e:
                logger.error("Error sending suggestion: %s", e)
                if chat_id:
                    self.bot.send_message(chat_id, "Error sending suggestion: {}".format(e))
                    self.state.reset()


def run():
    logger.info("Starting bot script")
    with TeleLinkedinBot() as bot:
        bot.run()


if __name__ == '__main__':
    run()
