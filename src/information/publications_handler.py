import json
import logging
import os
import time
from src.llm.langchain_agent.langchainGPT import LangChainGPT
from src.utils.log_handler import TruncateByTimeHandler

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
config_dir = os.path.join(r"C:\\", "ProgramData", "linkedin_assistant", "information", "config.json") if os.name == 'nt' else os.path.join(PWD, "config.json")

class PublicationsHandler:
    """Class in charge of taking raw documents obtained from sources and outputting a publication draft"""
    def __init__(self):
        self.publication_ideas_dir = "res/publication_ideas"
        self.publications_pending_approval_directory = "res/pending_approval"
        self.active = True
        self.process_sleep_time = 60 * 60 * 24
        self.langchain_gpt = LangChainGPT()

    def __call__(self):
        self.reload_config()

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
            time.sleep(60 * 60 * 24 * self.process_sleep_time)

    def process_publication_ideas(self):
        self.__process_publication_ideas(os.path.join(os.path.join(*self.publication_ideas_dir.split("/"))))

    def __process_publication_ideas(self, source_dir):
        """
        Iterates through the publication ideas on source_dir and gives them to langgpt in order to create a draft for
        publication. Then saves them on pending publication directory
        :param source_dir: directory where ideas need to be retrieved from

        """
        logger.info("Processing publication ideas")
        for publication in os.listdir(source_dir):
            logger.info("Processing publication %s", publication)
            with open(os.path.join(source_dir, publication), "r") as f:
                publication_dict = json.load(f)
            if publication_dict:
                response = self.langchain_gpt.call(publication_dict, "Please, write a post")
                if response:
                    try:
                        self.langchain_gpt.save_memory(os.path.join(os.path.join(*self.publications_pending_approval_directory.split("/")), f'{publication}.pkl'))
                        os.remove(os.path.join(source_dir, publication))
                    except Exception as e:
                        logger.error("Error processing publication %s: %s", publication, e)

    def reload_config(self):
        """Reload the configuration."""
        logger.debug("Reloading config")
        with open(config_dir, "r") as f:
            config = json.load(f)
        for key in config.keys():
            if key in ["publication_ideas_dir", "publications_pending_approval_directory"]:
                self.__setattr__(key, os.path.join(*config[key].split("/")))
            self.__setattr__(key, config[key])


if __name__ == '__main__':
    logger.info("Initializing publications handler script")
    PublicationsHandler().run()
