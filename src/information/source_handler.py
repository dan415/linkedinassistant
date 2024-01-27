import datetime
import json
import logging
import os
import re
import threading
import time
import uuid
from functools import wraps

from src.information.sources.information_source import get_information_source_from_value
from src.information.sources.provider import ContentSearchEngineProvider
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
config_dir = os.path.join(r"C:\\", "ProgramData", "linkedin_assistant", "information", "sources", "config.json") if os.name == 'nt' else os.path.join(PWD, "config.json")

def stateful(func):
    """
    This decorator makes sure that the config.json stays updated with whats on memory. The idea is that if I were
    to exit the program abruptly, (for example: If my laptop runs out of battery) the state information remains. This is meant
    to be used with methods that update state variables
    """
    @wraps(func)
    def update_config(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        logger.debug("Updating config of sources handler.")
        with open(config_dir, "r") as f:
            config = json.load(f)

        for key in config.keys():
            config[key] = getattr(self, key)

        with open(config_dir, "w") as f:
            json.dump(config, f, default=str, indent=4)

        return result

    return update_config


class SourcesHandler:
    """This class runs by concurrently executing different search engines in order to retrieve new pieces of publication ideas
    that will be proceseed in order to create the publications"""

    def __init__(self):
        self.active = True
        self.file = None
        self.pwd = os.path.dirname(os.path.abspath(__file__))
        self.project_dir = os.path.abspath(os.path.join(self.pwd, '..', ".."))
        self.active_sources = []
        self.search_engines = []
        self.execution_period = 1
        self.one_by_one = True
        self.last_run_time = None
        self.sleep_time = 1
        self.publications_directory = os.path.join("res", "publication_ideas")
        self.reload_config()

    def run(self):
        """Main loop of the class, it runs the search engines and sleeps until scheduled next execution"""
        logger.info("Initializing sources handler.")
        while True:
            if self.active:
                self.run_search_engines()
                logger.debug("Source handler sleeping.")
            time.sleep(self.sleep_time)

    def clean_title(self, title):
        """
        Clean the title. It removes special characters and makes it lower case.
        :param title:  title to be cleaned
        :return:
        """
        title = title.lower().strip()
        title = re.sub(r'[^a-zA-Z0-9_]', '_', title)
        title = title[0:min(len(title), 90)]
        return title

    def save_material(self, material):
        """Saves the processed material needed to create a publication. The material is saved in the publications directory

        :param material: material to be saved. It is a dictionary
        """

        title = self.clean_title(material["title"])
        logger.info(f"Saving material {title}.")
        # Cleans the title for the file name
        with open(os.path.join(self.project_dir, self.publications_directory, f"{title}.json"), "w") as f:
            json.dump(material, f, default=str, indent=4)
        logger.info(f"Saved material {title}.")

    def init_active_sources(self):
        """Initializes the active sources. This method is called when the active sources are changed.
        It creates the search engines that will be used to retrieve the publication ideas

        """
        logger.info("Initializing active sources")
        for source in list(map(lambda x: get_information_source_from_value(x), self.active_sources)):
            self.search_engines.append(ContentSearchEngineProvider.get_content_search_engine(source))

    def run_search_engine(self, search_engine):
        """
        Runs a search engine and saves the results
        :param search_engine: search engine to run
        :return:
        """
        try:
            logger.info(f"Running search engine {search_engine}")
            results = search_engine.search(self.save_material if self.one_by_one else None)
            if not self.one_by_one:
                results = search_engine.filter(results)
                for result in results:
                    self.save_material(result)
        except Exception as e:
            logger.error(e)

    @stateful
    def run_search_engines(self):
        """
        Runs all the search engines concurrently. It also makes sure that the search engines are not run more often than
        the execution period

        :return:
        """
        logger.info("Running search engines")
        if self.last_run_time and datetime.datetime.now() - datetime.timedelta(
                days=self.execution_period) < datetime.datetime.strptime(self.last_run_time, "%Y-%m-%d %H:%M:%S"):
            logger.debug("Sources handler needs to wait more time to run.")
            time.sleep(self.sleep_time * 3600 * 24)
            return []
        threads = []
        for search_engine in self.search_engines:
            threads.append(threading.Thread(target=self.run_search_engine, args=[search_engine]))
        self.last_run_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.update_last_run_time()
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    def update_last_run_time(self):
        """Updates the last run time on the config.json file"""
        with open(config_dir, "r") as f:
            config = json.load(f)
        config["last_run_time"] = self.last_run_time
        with open(config_dir, "w") as f:
            json.dump(config, f, default=str, indent=4)

    def reload_config(self):
        """Reload the configuration."""
        logger.debug("Reloading config")
        with open(config_dir, "r") as f:
            config = json.load(f)
        for key in config.keys():
            if key == "publications_directory":
                self.publications_directory = os.path.join(os.path.join(*self.publications_directory.split("/")))
            if key == "active_sources":
                active_sources = config.get("active_sources", self.active_sources)
                has_changed = self.active_sources != active_sources
                self.active_sources = active_sources
                if has_changed:
                    self.init_active_sources()
            else:
                self.__setattr__(key, config[key])


if __name__ == '__main__':
    logger.info("Initializing sources handler script")
    SourcesHandler().run()
