import re
import sys
import time
from functools import wraps
from hvac.exceptions import InvalidPath
from origamibot.listener import Listener
from origamibot import OrigamiBot
from origamibot.core.teletypes import Message, Document
from src.core.config.manager import ConfigManager
from src.core.constants import SecretKeys, PublicationState, FileManagedFolders
from src.core.exceptions import FetchFileException, DownloadFileException
from src.core.file_manager.b2 import B2Handler
from src.core.utils.logging import ServiceLogger
from src.core.vault.hashicorp import VaultClient
from src.core.publications import PublicationIterator
from src.information.searcher import SourcesHandler
from src.information.sources.rapid.youtube.pool import YoutubeUrlPool
from src.linkedin.publisher import LinkedinPublisher
from pyngrok import ngrok
import requests
from src.core.llm.conversation.agent import LangChainGPT
import io
import datetime
import threading
from typing import Optional
import src.core.utils.functions as F
from src.telegram.constants import (
    MSG_START,
    MSG_HEALTHCHECK,
    MSG_CLEARED,
    MSG_ERROR_CLEAR,
    MSG_NO_SUGGESTIONS,
    MSG_SAME_SUGGESTION_SELECTED,
    MSG_INVALID_INDEX,
    MSG_ERROR_SELECTING_SUGGESTION,
    MSG_NO_CURRENT_SUGGESTION,
    MSG_SEARCH_ENGINE_ACTIVATED,
    MSG_SEARCH_ENGINE_ACTIVATED_ERR,
    MSG_SEARCH_ENGINE_STOPPED,
    MSG_SEARCH_ENGINE_STOPPED_ERR,
    MSG_ERROR_LOADING_SUGGESTION,
    CONFIG_SCHEMA,
    MSG_ERROR_PUBLISH,
    MSG_PUBLISH_SUCCESS,
    MSG_CONV_ID_NOT_SET,
    MSG_IMAGE_NOT_PASSED,
    MSG_IMAGE_RECEIVED_SUCCESS,
    MSG_NO_IMAGES_FOR_PUBLICATION,
    MSG_ERROR,
    MSG_INVALID_URL,
    MSG_COMMAND_NOT_FOUND,
    MSG_ERROR_COMMAND_BIND,
    NGROK_ADDRESS,
    MSG_ERROR_SENDING,
    MSG_ERROR_COMMAND,
    NGROK_PROTOCOL,
    MSG_FILE_RECEIVED_SUCCESS,
    MSG_ERROR_YOUTUBE,
)


logger = ServiceLogger(__name__)


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


def restricted(func):
    """
    This decorator makes sure that the incoming message comes from THE known chat. When no chat_id exists. First to
    start the service is the one to get recorded. The chat_id is stored as a secret in Vault

    """

    @wraps(func)
    def wrapper(self, message: Message, *args, **kwargs):
        if self.state.chat_id and message.chat.id != self.state.chat_id:
            logger.warning(
                f"""Unauthorized access to the bot for message with chat_id {message.chat.id}, which is \
            different from {self.state.chat_id}.
            Message: {str(message)}
            """
            )
            return
        return func(self, message, *args, **kwargs)

    return wrapper


class OrigamiBotExtended(OrigamiBot):
    _REQUEST_TIMEOUT = 10  # Timeout duration for HTTP requests, in seconds.

    def __init__(self, token: str):
        """
        Initializes the OrigamiBotExtended class.

        Args:
            token (str): The Telegram bot token.
        """
        super().__init__(token)
        self.file_manager = B2Handler()

    def _get_file_path(self, file_id: str) -> str:
        """
        Fetch the file path from the Telegram API using the file ID.

        Args:
            file_id (str): The unique identifier of the file.

        Returns:
            str: The path of the file on Telegram's servers.

        Raises:
            FetchFileException: If the API response indicates an error.
        """
        url = f"https://api.telegram.org/bot{self.token}/getFile?file_id={file_id}"
        response = requests.get(url, timeout=self._REQUEST_TIMEOUT)
        result = response.json()
        if result["ok"]:
            return result["result"]["file_path"]
        else:
            raise FetchFileException(result)

    def _download_file(self, file_path: str) -> bytes:
        """
        Download the file content from the Telegram file path.

        Args:
            file_path (str): The file path obtained from Telegram.

        Returns:
            bytes: The binary content of the downloaded file.

        Raises:
            DownloadFileException: If the download fails.
        """
        url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
        response = requests.get(url, timeout=self._REQUEST_TIMEOUT)
        if response.status_code == 200:
            return response.content
        else:
            raise DownloadFileException(response.json())

    def get_file(self, document: Document) -> Optional[bytes]:
        """
        Retrieve a file using its document object from Telegram.

        Args:
            document (Document): The document object containing file information.

        Returns:
            bytes: The binary content of the file, or None if an error occurs.
        """
        try:
            file_path = self._get_file_path(document.file_id)
            return self._download_file(file_path)
        except (FetchFileException, DownloadFileException) as ex:
            logger.error(str(ex))
            return None

    def process_pdf(
        self, document: Document, save_folder: str
    ) -> Optional[str]:
        """
        Process a PDF document and upload it to the specified folder.

        Args:
            document (Document): The document object representing the PDF.
            save_folder (str): The folder where the PDF should be saved.

        Returns:
            str: The result of the upload operation, or None if processing fails.
        """
        file_bytes = self.get_file(document)
        if file_bytes:
            return self.file_manager.upload_from_bytes(
                file_bytes, f"{save_folder}/{document.file_name}"
            )
        return None

    def process_image(self, image: Document) -> bytes:
        """
        Process an image file by encoding it in base64.

        Args:
            image (Document): The image object to process.

        Returns:
            bytes: The base64-encoded content of the image.
        """
        file_bytes = self.get_file(image)
        return file_bytes

    def send_publication(self, chat_id: int, publication: dict) -> None:
        """
        Send a publication (message and optional image) to a specific chat.

        Args:
            chat_id (int): The Telegram chat ID where the publication will be sent.
            publication (dict): A dictionary containing the content and optional image.
        """
        self.send_message(chat_id, publication["content"])
        if publication.get("image", None):
            self.send_photo(chat_id, io.BytesIO(publication["image"]))


class BotState:
    """
    This class manages the state of the bot, including the chat ID, publication suggestions, and their states.

    It tracks whether suggestions are blocked, maintains conversation threads for publications, and manages settings for
    automatic suggestion generation. Methods are decorated with @stateful to ensure the config file reflects
    the updated state.
    """

    def __init__(self):
        self.cool_off_time: Optional[str] = None
        self.suggestion_period: Optional[int] = None
        self.chat_id: Optional[int] = None
        self.auth_address: Optional[str] = None
        self.conversation_id = None
        self.publications_manager = Optional[PublicationIterator]
        self.llm_agent = LangChainGPT(logger=logger)
        self.mutex = threading.Lock()
        self.vault_client = VaultClient()
        self.config_client = ConfigManager()

        logger.debug("Reloading config")
        config = self.config_client.load_config(CONFIG_SCHEMA)

        for key in config.keys():
            if key in self.__dict__.keys():
                self.__setattr__(key, config[key])

        if self.conversation_id:
            self.llm_agent.conversation_id = self.conversation_id

        try:
            self.chat_id = self.vault_client.get_secret(
                SecretKeys.TELEGRAM_CHAT_ID
            )
            if self.chat_id == "":
                self.chat_id = None
            else:
                self.chat_id = int(self.chat_id)
        except InvalidPath:
            self.chat_id = None
        self.publications_manager = PublicationIterator(
            PublicationState.PENDING_APPROVAL, logger=logger
        )

    @stateful
    def set_conversation_id(self, conversation_id):
        self.conversation_id = conversation_id
        self.llm_agent.conversation_id = self.conversation_id

    @stateful
    def reset(self) -> None:
        """
        Resets the state of the bot, clearing conversation memory and resetting key flags.
        """
        logger.info("Resetting state")
        with self.mutex:
            self.llm_agent.memory.clear(self.llm_agent.conversation_id)
            self.llm_agent.conversation_id = None
            self.conversation_id = None
            self.cool_off_time = None

    @stateful
    def set_chat_id(self, chat_id: int) -> None:
        """
        Sets the chat ID for user interaction.

        Args:
            chat_id (int): The ID of the chat to associate with the bot.
        """
        logger.info("Setting chat id")
        with self.mutex:
            self.chat_id = chat_id
            self.vault_client.create_or_update_secret(
                SecretKeys.TELEGRAM_CHAT_ID, self.chat_id
            )

    def get_cool_off_time(self) -> Optional[str]:
        """
        Checks if suggestions are currently blocked.

        Returns:
            Optional[bool | str]: True if suggestions are blocked manually, string datetime if the suggestions
            are in cool-off stage
            or false otherwise
        """
        with self.mutex:
            return self.cool_off_time

    @stateful
    def set_cool_off_time(self) -> None:
        """
        Checks if suggestions are currently blocked.

        Returns:
            Optional[bool | str]: True if suggestions are blocked manually, string datetime if the suggestions are in
            cool-off stage
            or false otherwise
        """
        with self.mutex:
            self.cool_off_time = datetime.datetime.now().isoformat()

    @stateful
    def release_cool_off_time(self) -> None:
        """
        Checks if suggestions are currently blocked.

        Returns:
            Optional[bool | str]: True if suggestions are blocked manually, string datetime if the suggestions
            are in cool-off stage
            or false otherwise
        """
        with self.mutex:
            self.cool_off_time = None

    def get_chat_id(self) -> Optional[int]:
        """
        Retrieves the current chat ID.

        Returns:
            Optional[int]: The current chat ID.
        """
        with self.mutex:
            return self.chat_id


class BotsCommands:
    """

    This class is used to define the bot commands. The bot commands are used to interact with the bot via the Telegram
    chat. These commands allow users to execute special functions, like starting the bot, stopping the bot, publishing,
    listing suggestions, etc.

    Commands take the form /command_name, where command_name is the name of the actual method that will be called.

    """
    _MAX_MESSAGE_LENGTH = 4096
    _MAX_LISTABLE = 40
    _COMMAND_DESCRIPTIONS = {
        "start": "Start the bot and initialize interaction.",
        "healthcheck": "Check if the bot is operational.",
        "clear": "Clear the current publication and reset the bot's memory.",
        "list": "List all available suggestions.",
        "select": "Select a specific suggestion by its index. E.g '/select 6'",
        "previous": "Load the previous suggestion.",
        "next": "Load the next suggestion.",
        "clear_image": "Clear the current image associated with a publication.",
        "current": "Retrieve the current suggestion and its details.",
        "activate_search_engine": "Activate the search engine.",
        "stop_search_engine": "Deactivate the search engine.",
        "publish": "Publish the current suggestion to LinkedIn.",
        "set_image": "You must send an image with this command as caption. Set an image for the current publication.",
        "help": "List all available bot commands (including this one).",
        "images": "Retrieve and display images associated with the current publication.",
        "add_youtube": "Add a YouTube URL for transcript processing. E.g ''/add_youtube https://youtube...''",
        "update": "Updates the current publication with the last message sent by the bot",
    }

    def __init__(
        self,
        bot: OrigamiBotExtended,
        publisher: LinkedinPublisher,
        bot_state: BotState,
    ):
        """
        Initialize the BotsCommands instance.

        :param bot: Instance of the bot interface for sending messages and interacting with the chat.
        :param publisher: Publisher object for handling publication logic.
        :param bot_state: State management object for maintaining the bot's operational state.
        """
        self.bot = bot
        self.publisher = publisher
        self.state = bot_state

        # Initialize URL pool for YouTube transcripts
        self.youtube_url_pool = YoutubeUrlPool()

    def start(self, message: Message):
        """
        Start the bot. This is the first command to initialize bot interaction.

        :param message: The message object received from the chat.
        :return: None
        """
        logger.info("Starting operation triggered")
        if self.state.chat_id is None and message.chat.id:
            self.state.set_chat_id(message.chat.id)
        self.bot.send_message(
            self.state.chat_id, MSG_START.format(message.chat.id)
        )

    def send_message(self, chat_id: int, message: str):
        """
        Send a message to a specific chat. If the message length exceeds 4096,
        it will be split into multiple messages at the last space before the limit.
        """

        while len(message) > self._MAX_MESSAGE_LENGTH:
            # Last space before the limit
            split_index = message.rfind(' ', 0, self._MAX_MESSAGE_LENGTH)

            # If no space is found, split at the limit
            if split_index == -1:
                split_index = self._MAX_MESSAGE_LENGTH

            self.bot.send_message(chat_id, message[:split_index])
            message = message[split_index:].lstrip()

        self.bot.send_message(chat_id, message)

    def help(self, message: Message):
        """
        Provide a list of available bot commands along with their descriptions.

        :param message: The message object received from the chat.
        :return: None
        """

        response = "\nUsage:\n" + "\n".join(
            [
                f"/{cmd} - {desc}"
                for cmd, desc in self._COMMAND_DESCRIPTIONS.items()
            ]
        )

        self.bot.send_message(self.state.chat_id, response)

    def update(self, message):
        """
        Updates the publication content with the content of the last response. Before, this was done automatically,
        as the bot is instructed to respond only with the publication content always. However, this approach gives
        more control to the user and flexibility when talking with the agent. Another approach would be to set a tool
        to update the publication content and leave the decision of updating up to the agent, but for now I feel it
        is unnecessary.

        :param message: The message object received from the chat.
        :return: None
        """
        messages = self.state.llm_agent.agent.get_state(
            {"configurable": {"thread_id": self.state.conversation_id}}
        ).values.get("messages")
        if messages:
            last_message = messages[-1].content
            formatted_publication = F.boldify_unicode(last_message)
            self.state.publications_manager.update_content(
                self.state.conversation_id, formatted_publication
            )
            self.current(message)

    def healthcheck(self, message: Message):
        """
        Perform a health check to verify if the bot is operational.

        :param message: The message object received from the chat.
        :return: None
        """
        logger.info("Healthcheck triggered")
        self.bot.send_message(self.state.chat_id, MSG_HEALTHCHECK)

    def clear(self, message: Message, index=None):
        """
        Clear the current publication and reset the bot's memory for new suggestions.

        :param message: The message object received from the chat.
        :param index: The index of the suggestion to clear. If None, the current suggestion is cleared.
        :return: None
        """
        logger.info("Clear triggered")
        try:
            if not index or index == self.state.publications_manager.current_index():
                self.state.publications_manager.update_state(
                    self.state.conversation_id, PublicationState.DISCARDED
                )
                self.state.reset()

                # Move the cursor back to the last element so that
                # the next call to next() does not skip the next element
                # which has advanced one spot due to the current element being removed
                self.state.publications_manager.last()
            else:
                publication = self.state.publications_manager.select(index)
                self.state.publications_manager.update_state(
                    publication["publication_id"], PublicationState.DISCARDED
                )
            self.bot.send_message(self.state.chat_id, MSG_CLEARED)
        except Exception as e:
            logger.error(f"Error clearing publication: {e}")
            self.bot.send_message(self.state.chat_id, MSG_ERROR_CLEAR.format(e))

    def list(self, message: Message):
        """
        List all available suggestions in the suggestion pool.

        :param message: The message object received from the chat.
        :return: None
        """
        logger.info("List triggered")
        lista = [
                    f"{element[0]}: {element[1].get('title', '')}"
                    for element in self.state.publications_manager.list()
                    if element[1].get('title', '')
                ]
        cant_show_all = len(lista) > self._MAX_LISTABLE
        lista_shortened = lista[:min(self._MAX_LISTABLE, len(lista))]
        if len(lista_shortened) > 0:
            logger.info("Suggestions:\n\n%s", "\n".join(lista_shortened))
            self.bot.send_message(
                self.state.chat_id,
                "Suggestions:\n\n{}".format("\n".join(lista_shortened)),
            )
            if cant_show_all:
                self.bot.send_message(
                    self.state.chat_id,
                    f"Showing only the first {self._MAX_LISTABLE} suggestions. "
                    f"There's actually {len(lista)} suggestions.",
                )
        else:
            logger.info("No suggestions to be listed")
            self.bot.send_message(self.state.chat_id, MSG_NO_SUGGESTIONS)

    def select(self, message: Message, index: int):
        """
        Select a specific suggestion by its index from the suggestion pool.

        :param message: The message object received from the chat.
        :param index: The index of the suggestion to select.
        :return: None
        """
        logger.info("Select triggered")
        try:
            current = self.state.publications_manager.select(index)
            if current["publication_id"] == self.state.conversation_id:
                self.bot.send_message(
                    self.state.chat_id, MSG_SAME_SUGGESTION_SELECTED
                )
            elif current:
                self.state.set_conversation_id(current["publication_id"])
                self.bot.send_publication(self.state.chat_id, current)
            else:
                self.bot.send_message(self.state.chat_id, MSG_INVALID_INDEX)
        except Exception as e:
            logger.error("Error selecting suggestion: %s", e)
            self.bot.send_message(
                self.state.chat_id, MSG_ERROR_SELECTING_SUGGESTION
            )

    def previous(self, message: Message):
        """
        Select the previous suggestion in the suggestion history.

        :param message: The message object received from the chat.
        :return: None
        """
        logger.info("Previous triggered")
        try:
            current = self.state.publications_manager.last()
            if (
                current["publication_id"] == self.state.conversation_id
                or not current
            ):
                self.bot.send_message(self.state.chat_id, MSG_NO_SUGGESTIONS)
            else:
                self.state.set_conversation_id(current["publication_id"])
                self.bot.send_publication(self.state.chat_id, current)
        except Exception as e:
            logger.error(
                f"Error loading previous suggestion: {type(e).__name__} - {e}."
            )
            self.bot.send_message(
                self.state.chat_id, "Error loading previous suggestion"
            )

    def next(self, message: Message):
        """
        Select the next suggestion in the suggestion history.

        :param message: The message object received from the chat.
        :return: None
        """
        logger.info("Next triggered")
        try:
            current = next(self.state.publications_manager, None)
            if (
                current["publication_id"] == self.state.conversation_id
                or not current
            ):
                self.bot.send_message(self.state.chat_id, MSG_NO_SUGGESTIONS)
            else:
                self.state.set_conversation_id(current["publication_id"])
                self.bot.send_publication(self.state.chat_id, current)
        except Exception as e:
            logger.error(
                f"Error loading next suggestion: {type(e).__name__} - {e}."
            )
            self.bot.send_message(
                self.state.chat_id, MSG_ERROR_LOADING_SUGGESTION
            )

    def clear_image(self, message: Message):
        """
        Clear the currently generated image associated with a publication.

        :param message: The message object received from the chat.
        :return: None
        """
        try:
            self.state.llm_agent.image = None
            self.state.publications_manager.update_image(
                self.state.conversation_id, None
            )
            self.bot.send_message(self.state.chat_id, "Image cleared")
        except Exception as e:
            logger.error("Error clearing image: %s", e)
            self.bot.send_message(self.state.chat_id, "Error clearing image")

    def current(self, message: Message):
        """
        Retrieve the current suggestion and its details.

        :param message: The message object received from the chat.
        :return: None
        """

        if self.state.conversation_id:
            current = self.state.publications_manager.get(
                self.state.conversation_id
            )
            if current:
                self.bot.send_publication(self.state.chat_id, current)
                return
            self.state.reset()
        self.bot.send_message(self.state.chat_id, MSG_NO_CURRENT_SUGGESTION)

    def activate_search_engine(self, message: Message):
        """
        This command sets the attribute for 'information' config active as True. This means that the search sources
        program will execute when is due

        :param message: The message object received from the chat.
        :return: None
        """
        result = self.state.config_client.update_config_key(
            SourcesHandler.CONFIG_SCHEMA, key="active", value=True
        )
        if result:
            self.bot.send_message(
                self.state.chat_id, MSG_SEARCH_ENGINE_ACTIVATED
            )
        else:
            self.bot.send_message(
                self.state.chat_id, MSG_SEARCH_ENGINE_ACTIVATED_ERR
            )

    def stop_search_engine(self, message: Message):
        """
        This command sets the attribute for 'information' config active as True. This freezes up search sources program

        :param message: The message object received from the chat.
        :return: None
        """
        result = self.state.config_client.update_config_key(
            SourcesHandler.CONFIG_SCHEMA, key="active", value=False
        )
        if result:
            self.bot.send_message(self.state.chat_id, MSG_SEARCH_ENGINE_STOPPED)
        else:
            self.bot.send_message(
                self.state.chat_id, MSG_SEARCH_ENGINE_STOPPED_ERR
            )

    def publish(self, message: Message):
        """
        Publish the current suggestion to LinkedIn. Ensures the user is authenticated before publishing.

        :param message: The message object received from the chat.
        :return: None
        """
        if not self.state.conversation_id:
            self.bot.send_message(self.state.chat_id, MSG_NO_CURRENT_SUGGESTION)
            return

        if self.publisher.needs_auth():
            self.bot.send_message(
                self.state.chat_id,
                f"You need to authenticate first. Please click on this link: {self.state.auth_address}",
            )
            return

        try:
            current = self.state.publications_manager.get(
                self.state.conversation_id
            )

            if not current:
                self.bot.send_message(
                    self.state.chat_id, MSG_NO_CURRENT_SUGGESTION
                )
                self.state.reset()
                return

            publication = current.get("content", None)
            image = current.get("image", None)
            self.publisher.publish(publication, image)
            self.state.publications_manager.update_state(
                self.state.conversation_id, PublicationState.PUBLISHED
            )

            self.bot.send_message(self.state.chat_id, MSG_PUBLISH_SUCCESS)
            self.state.reset()
            self.state.set_cool_off_time()

        except Exception as e:
            logger.error(f"Failed to publish: {e}")
            self.bot.send_message(
                self.state.chat_id, MSG_ERROR_PUBLISH.format(str(e))
            )

    def set_image(self, message: Message):
        """
        This command is meant to be called alongside an image. The user sends an image with this command, and
        that image is set as the publication image for the current suggestion

        :param message: Message from the user
        :return:
        """
        if not message.photo:
            self.bot.send_message(self.state.chat_id, MSG_IMAGE_NOT_PASSED)
        elif (
            not self.state.conversation_id
            or not self.state.publications_manager.get(
                self.state.conversation_id
            )
        ):
            self.bot.send_message(self.state.chat_id, MSG_CONV_ID_NOT_SET)
            return
        else:
            encoded_bytes = self.bot.process_image(
                message.photo[-1]
            )  # version of highest resolution available
            result = self.state.publications_manager.update_image(
                self.state.conversation_id, encoded_bytes
            )
            self.bot.send_message(
                self.state.chat_id,
                MSG_IMAGE_RECEIVED_SUCCESS if result else MSG_ERROR,
            )

    def images(self, message: Message):
        """
        This function searches stored images for current publication in B2 File Storage system and sends them to the
        user if any. Images get stored in B2 only for sources processed with Docling

        :param message: Message from the user
        :return:
        """
        if not self.state.conversation_id:
            self.bot.send_message(self.state.chat_id, MSG_CONV_ID_NOT_SET)
            return
        folder = "/".join(
            [FileManagedFolders.IMAGES_FOLDER, self.state.conversation_id]
        )
        images = self.bot.file_manager.list_folder_contents(folder)

        if not images:
            self.bot.send_message(
                self.state.chat_id, MSG_NO_IMAGES_FOR_PUBLICATION
            )
            return

        for image in images:
            image_bytes = self.bot.file_manager.download(image["path"])
            self.bot.send_photo(self.state.chat_id, io.BytesIO(image_bytes))

    def add_youtube(self, message: Message, youtube_url: str):
        """
        Add a YouTube URL to the transcript retriever pool for processing.

        :param message: The message object received from the chat.
        :param youtube_url: The YouTube URL to add for processing.
        :return: None
        """
        try:
            # Enhanced validation for YouTube URL
            if not re.match(
                r"^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+$",
                youtube_url,
            ):
                self.bot.send_message(self.state.chat_id, MSG_INVALID_URL)
                return

            # Add URL to the pool
            self.youtube_url_pool.add_url(youtube_url)
            self.bot.send_message(
                self.state.chat_id,
                f"YouTube video added to processing queue: {youtube_url}",
            )

        except Exception as e:
            logger.error(f"Error processing YouTube URL: {str(e)}")
            self.bot.send_message(self.state.chat_id, MSG_ERROR_YOUTUBE)


class MessageListener(Listener):
    """
    This class is used to listen to messages. It is used to listen to messages and send them to the LLMChain agent.
    They get added to the conversation thread and the response is sent back to the user.
    """

    _commands = list(
        filter(lambda x: not x.startswith("__"), BotsCommands.__dict__.keys())
    )

    def __init__(self, bot, state):
        self.bot = bot
        self.state = state

    def respond(self, chat_id, response):
        """
        This function standardizes response mechanism. Respond, and if there is an image ready for the user send it
        as well and set it as the publication image for the current suggestion.

        :param chat_id: chat to respond to. Even though right now this is trivial because it can be obtained from the
        state
        :param response: Text message from the bot to send to the user
        :return:
        """
        self.bot.send_message(chat_id, response)

        if self.state.llm_agent.image:
            self.state.publications_manager.update_image(
                self.state.conversation_id, self.state.llm_agent.image
            )
            photo = io.BytesIO(self.state.llm_agent.image)
            photo.seek(0)
            self.bot.send_photo(chat_id, photo)
            self.state.llm_agent.image = None

    # This decorator here makes sure no unauthorized user gets access to any command or triggers a response
    @restricted
    def on_message(self, message: Message):
        """
        On message received. This is used to listen to messages and send them to the LLMChain agent.
        :param message: message received
        :return:
        """
        logger.info("Message received")
        encoded_images = []

        if not message.text and message.caption:
            message.text = message.caption

        if message.text and message.text.startswith("/"):
            if not message.text[1:].split(" ")[0] in self._commands:
                self.bot.send_message(self.state.chat_id, MSG_COMMAND_NOT_FOUND)
            return

        elif (
            message.document and message.document.mime_type == "application/pdf"
        ):
            result = self.bot.process_pdf(
                message.document, FileManagedFolders.INPUT_PDF_FOLDER
            )
            self.bot.send_message(
                self.state.chat_id,
                MSG_FILE_RECEIVED_SUCCESS if result else MSG_ERROR,
            )
            return
        elif message.photo:
            encoded_images.append(self.bot.process_image(message.photo[-1]))

        # Prevent loading of suggestions and that kind of thing while the bot is processing the message
        with self.state.mutex:
            response = self.state.llm_agent.call(
                message.text, images=encoded_images
            )

        self.respond(self.state.chat_id, response)

    def on_command_failure(
        self, message: Message, err=None
    ):  # When command fails
        """
        On command failure. This is used to send a message to the user when a command fails.
        :param message: Message from the user
        :param err: error from the command
        :return:
        """
        logger.error("Command failed")
        if err is None:
            self.bot.send_message(self.state.chat_id, MSG_ERROR_COMMAND_BIND)
        else:
            self.bot.send_message(
                self.state.chat_id, MSG_ERROR_COMMAND.format(err)
            )


class TeleLinkedinBot:
    """
    This class is used to define the bot. It is used to define the bot and run it. It also handles the LinkedIn
    Publisher object in order to trigger a publication, and exposes the auth server on the internet via NGrok
    on port 5000Note that my NGrok domain is persistent throughout NGrok sessions, so I can use the same domain
    for the auth server. For this you need to create an account on NGrok and get a token.

    Also note that in order for this class to be accessible through Telegram you need to create the Telegram Bot
    on the app and that you need to create a LinkedIn app and get the client id and client secret. You also need to
    specify a redirect uri for the LinkedIn app. This redirect uri needs to be the same as the one used in
    the auth server.

    All of this is documented on the readthedocs page though.
    """

    def __init__(self):

        self.bot = None
        self.state = None
        self.vault_client = VaultClient()
        self.publisher = LinkedinPublisher()
        self.config_client = ConfigManager()
        self.token = self.vault_client.get_secret(SecretKeys.TELEGRAM_BOT_TOKEN)
        self.ngrok_token = self.vault_client.get_secret(SecretKeys.NGROK_TOKEN)
        self.domain = self.vault_client.get_secret(SecretKeys.NGROK_DOMAIN)

    def __enter__(self):
        """
        Expose the auth server on the internet via NGrok on port 5000. Using the enter/exit functions is convenient
        because it will automatically disconnect the tunnel when the program is finished.
        :return: self
        """
        logger.info("Reloading config")
        self.reload_config()
        ngrok.set_auth_token(self.ngrok_token)
        logger.info("Opening connection with Ngrok")
        self.http_tunnel = ngrok.connect(
            addr=NGROK_ADDRESS, proto=NGROK_PROTOCOL, domain=self.domain
        )

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Disconnect the tunnel when the program is finished.
        :param exc_type:
        :param exc_value:
        :param traceback:
        :return:
        """
        if exc_type is not None:
            logger.error(
                f"Exiting with exception: {exc_type.__name__}: {exc_value}",
                exc_info=(exc_type, exc_value, traceback),
            )
        else:
            logger.info("Exiting context manager normally.")

        if self.bot:
            logger.info("Disconnecting ngrok")
            ngrok.disconnect(self.http_tunnel.public_url)
            logger.info("Killing ngrok")
            ngrok.kill()
            logger.info("Stopping bot")
            sys.exit()

    def reload_config(self):
        """Reload the configuration."""
        logger.info("Reloading config")
        config = self.config_client.load_config(CONFIG_SCHEMA)

        logger.info("Setting attributes")
        for key in config.keys():
            if key in self.__dict__.keys():
                self.__setattr__(key, config[key])

        logger.info("Initializing bot")
        self.bot = OrigamiBotExtended(self.token)
        logger.info("Setting up state")
        self.state = BotState()
        self.state.auth_address = f"https://{self.domain}"
        logger.info("Attaching listener")
        self.bot.add_listener(MessageListener(self.bot, self.state))
        logger.info("Attaching commands")
        self.bot.add_commands(
            BotsCommands(self.bot, self.publisher, self.state)
        )
        logger.info("Starting bot")
        self.bot.start()
        logger.info("Bot Started")

    def can_propose_new_suggestions(self):
        """
        This method checks that suggestions_are_block does not return False or None, then if it is a string, it will be
        a datetime defining when the last post was published, and will use the suggestion_period to check if the
        cool off time has passed

        :return: boolean: If new publications can be proposed to the user
        """
        return not self.state.conversation_id and (
            not self.state.cool_off_time
            or (
                datetime.datetime.now()
                > (
                    datetime.datetime.fromisoformat(self.state.cool_off_time)
                    + datetime.timedelta(days=self.state.suggestion_period)
                )
            )
        )

    def run(self, stop_event: threading.Event = None):
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
        while not stop_event or not stop_event.is_set():
            time.sleep(5)
            chat_id = self.state.get_chat_id()
            if not chat_id:
                logger.info("Chat ID not set, start the conversation first")
                continue

            if not self.can_propose_new_suggestions():
                continue

            logger.info("Proposing new suggestions")
            self.state.release_cool_off_time()
            try:
                if self.state.conversation_id:
                    self.state.publications_manager.center_iterator(
                        self.state.conversation_id
                    )
                current = next(self.state.publications_manager, None)
                if current:
                    logger.info("Sending next suggestion")
                    self.state.set_conversation_id(current["publication_id"])
                    self.bot.send_publication(chat_id, current)
                else:
                    logger.info("No new suggestions for now")
                    self.bot.send_message(chat_id, MSG_NO_SUGGESTIONS)
            except Exception as e:
                logger.error("Error sending suggestion: %s", e)
                self.bot.send_message(chat_id, MSG_ERROR_SENDING.format(e))
                self.state.reset()

        logger.info("Bot loop exited because of stop event")


def run(stop_event: threading.Event = None):
    """
    Main function

    :param stop_event: An event used to signal when to stop the bot gracefully
    :return:
    """
    logger.info("Starting bot script")
    with TeleLinkedinBot() as bot:
        bot.run(stop_event)


if __name__ == "__main__":
    try:
        run()
        logger.info("Exiting Run function")
    except Exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        logger.error(
            f"Exiting with exception: {exc_type.__name__}: {exc_value}",
            exc_info=(exc_type, exc_value, exc_traceback),
        )
