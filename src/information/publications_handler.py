import os
import src.core.utils.functions as F
from src.core.config.manager import ConfigManager
from src.information.constants import *
from src.information.publications import PublicationIterator
from src.llm.conversation.agent import LangChainGPT

FILE = os.path.basename(__file__)
logger = F.get_logger(dump_to=FILE)


class PublicationsHandler:
    """Class in charge of taking raw documents obtained from sources and outputting a publication draft"""
    def __init__(self):
        self.active = True
        self.process_sleep_time = 1
        self.langchain_gpt = LangChainGPT()
        self.config_schema = "information"
        self.publications_collection = ""
        self.config_client = ConfigManager()
        self.reload_config()
        self.publications_manager = PublicationIterator(self.publications_collection, PublicationState.DRAFT)

    def run(self):
        """
        Main loop of the program, runs indefinitely processing the ideas and waitng till next execution schedule
        """
        logger.info("Initializing publications handler")
        while True:
            if self.active:
                logger.info("Processing publication ideas")
                self.process_publication_ideas()
            else:
                logger.info("Publications handler is not active")
            logger.info("Sleeping")
            F.sleep(self.process_sleep_time)

    def process_publication_ideas(self):
        for publication in self.publications_manager:
            content = self.langchain_gpt.produce_publication(publication)
            self.publications_manager.update_content(
                publication_id=publication["publication_id"],
                content=content
            )
            self.publications_manager.update_state(
                publication_id=publication["publication_id"],
                state=PublicationState.PENDING_APPROVAL
            )

    def reload_config(self):
        """Reload the configuration."""
        logger.debug("Reloading config")
        config = self.config_client.load_config(self.config_schema)
        for key in config.keys():
            self.__setattr__(key, config[key])


def run():
    """Run the main function."""
    PublicationsHandler().run()


if __name__ == '__main__':
    logger.info("Initializing publications handler script")
    run()
