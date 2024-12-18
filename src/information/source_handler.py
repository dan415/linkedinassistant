import datetime
import json
import logging
import os
import re
import threading
from functools import wraps

from src.core.config.manager import ConfigManager
from src.core.database.mongo import MongoDBClient
from src.information.publications import PublicationIterator
from src.information.sources.information_source import get_information_source_from_value
from src.information.sources.provider import ContentSearchEngineProvider
import src.core.utils.functions as F

FILE = os.path.basename(__file__)
logger = F.get_logger(dump_to=FILE)


def stateful(func):
    """
    This decorator makes sure that the config.json stays updated with whats on memory. The idea is that if I were
    to exit the program abruptly, (for example: If my laptop runs out of battery) the state information remains. This is meant
    to be used with methods that update state variables
    """

    @wraps(func)
    def update_config(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        self.save_config()
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
        self.publications_collection = ""
        self.config_schema = "information"
        self.config_client = ConfigManager()
        self.reload_config()
        self.publications_manager = PublicationIterator(self.publications_collection)

    def run(self):
        """Main loop of the class, it runs the search engines and sleeps until scheduled next execution"""
        logger.info("Initializing sources handler.")
        while True:
            if self.active:
                self.run_search_engines()
                logger.debug("Source handler sleeping.")
            F.sleep(self.sleep_time)

    def save_material(self, material):
        """Saves the processed material needed to create a publication. The material is saved in the publications directory

        :param material: material to be saved. It is a dictionary
        """

        logger.info(f"Saving material {material.get('title', '')}.")
        self.publications_manager.insert(material)
        logger.info(f"Saved material {material.get('title', '')}.")

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
        self.config_client.update_config_key(self.config_schema, "last_run_time", self.last_run_time)

    def reload_config(self):
        """Reload the configuration."""
        logger.debug("Reloading config")
        config = self.config_client.load_config(self.config_schema)

        for key in config.keys():
            if key == "active_sources":
                active_sources = config.get("active_sources", self.active_sources)
                has_changed = self.active_sources != active_sources
                self.active_sources = active_sources
                if has_changed:
                    self.init_active_sources()
            else:
                self.__setattr__(key, config[key])

    def save_config(self):
        config = self.config_client.load_config(self.config_schema)

        for key in config.keys():
            config[key] = getattr(self, key)

        self.config_client.save_config(self.config_schema, config)


def run():
    """Runs the sources handler"""
    SourcesHandler().run()


if __name__ == '__main__':
    run()
