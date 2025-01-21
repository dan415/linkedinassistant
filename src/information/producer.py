import threading
import time
from src.core.config.manager import ConfigManager
from src.core.constants import PublicationState
from src.core.publications import PublicationIterator
from src.core.llm.conversation.agent import LangChainGPT
from src.core.utils.logging import ServiceLogger

logger = ServiceLogger(__name__)


class PublicationsHandler:
    """
    Class in charge of taking raw documents obtained from sources and outputting a publication draft.
    This class orchestrates the process of loading, processing, and updating publication drafts.
    """

    _CONFIG_SCHEMA = "information"  # Configuration schema name used for loading configuration settings

    def __init__(self):
        # Initialize the handler with default values and prepare all components
        self.active = True  # Indicates if the handler is actively processing
        self.publications_collection = (
            ""  # Placeholder for the publications collection name
        )
        self.langchain_gpt = LangChainGPT(
            logger=logger
        )  # GPT-based agent to process publications
        self.config_client = (
            ConfigManager()
        )  # Client for managing configuration settings
        logger.debug("Handler initialized with default values")
        self.reload_config()  # Load configuration settings on initialization
        self.publications_manager = PublicationIterator(
            PublicationState.DRAFT, logger=logger
        )  # Iterator to handle publication drafts
        logger.debug("Publications manager initialized")

    def run(self, stop_event: threading.Event = None):
        """
        Main loop of the program, runs indefinitely to process publication ideas.
        The loop continues until terminated manually, checking the active flag and processing accordingly.

        :param stop_event: An event used to signal when to stop the bot gracefully
        """
        logger.info("Initializing publications handler")
        try:
            while not stop_event or not stop_event.is_set():
                logger.debug(f"Handler active state: {self.active}")
                if self.active:
                    logger.debug("Processing publication ideas")
                    self.process_publication_ideas()  # Process drafts if the handler is active
                else:
                    logger.info("Publications handler is not active")
                logger.debug("Sleeping")
                time.sleep(5)

            logger.info("Producer loop exited because of stop event triggered")
        except KeyboardInterrupt:
            logger.info(
                "Publications handler terminated by user"
            )  # Graceful termination message

    def _upload_publication(self, publication, content):
        """
        Update the publication's content and state in the database.
        :param publication:  The publication to update
        :param content: The content to update the publication with
        """
        self.publications_manager.update_content(
            publication_id=publication["publication_id"],
            content=content,
        )  # Save the generated content
        logger.info(
            f"Content updated for publication ID: {publication['publication_id']}"
        )
        self.publications_manager.update_state(
            publication_id=publication["publication_id"],
            state=PublicationState.PENDING_APPROVAL,
        )  # Mark publication as pending approval
        logger.info(
            f"State updated to PENDING_APPROVAL for publication ID: {publication['publication_id']}"
        )

    def _produce_publication(self, publication):
        """
        Generate content for a publication draft using LangChainGPT.
        :param publication: The publication to generate content for
        """
        try:
            content = self.langchain_gpt.produce_publication(
                publication
            )  # Generate content for the draft
            logger.debug(
                f"Generated content for publication ID: {publication['publication_id']}"
            )
            self._upload_publication(
                publication, content
            )  # Update the publication
        except Exception as e:
            logger.error(
                f"Failed to process publication {publication['publication_id']}: {e}"
            )  # Log errors

    def process_publication_ideas(self, stop_event: threading.Event = None):
        """
        Iterate through publication drafts and use LangChainGPT to produce content.
        Updates the publication's content and state, with error handling for failures.

        :param stop_event: An event used to signal when to stop the bot gracefully
        """
        for publication in self.publications_manager:

            # gracefully stop in the middle of processing a publication
            if stop_event and stop_event.is_set():
                logger.info(
                    "Stop event called in the middle of processing a publication"
                )
                break

            logger.debug(
                f"Processing publication ID: {publication['publication_id']}"
            )
            self._produce_publication(publication)

    def reload_config(self):
        """
        Reload the configuration.
        Fetches settings from the configuration manager and updates class attributes dynamically.
        """
        logger.debug("Reloading config")
        config = self.config_client.load_config(
            self._CONFIG_SCHEMA
        )  # Load configuration from the specified schema
        for key in config.keys():
            self.__setattr__(
                key, config[key]
            )  # Dynamically assign configuration values to class attributes
            logger.debug(f"Config key {key} set to {config[key]}")


def run(stop_event: threading.Event = None):
    """
    Run the main function.
    Initializes and starts the PublicationsHandler's main loop.

    :param stop_event: An event used to signal when to stop the bot gracefully
    """
    logger.debug("Starting main function")
    PublicationsHandler().run(stop_event)
    logger.info("Exiting Run function")


if __name__ == "__main__":
    logger.info("Initializing publications handler script")
    run()
