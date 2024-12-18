import os
from abc import ABC, abstractmethod
import datetime
from enum import Enum
from functools import wraps
from typing import Callable
import numpy as np
from src.core.config.manager import ConfigManager
import src.core.utils.functions as F

FILE = os.path.basename(__file__)
logger = F.get_logger(dump_to=FILE)


def get_information_source_from_value(string_value):
    """Get the information source from the string value."""
    try:
        return InformationSource(string_value)
    except ValueError:
        logger.error(f"Information source {string_value} is not supported.")
        return None


class InformationSource(Enum):
    """Information sources."""
    ARXIV = "arxiv"
    # GMAIL = "gmail" # Not implemented Yet
    MEDIUM = "medium"
    GOOGLE_NEWS = "google_news"
    MANUAL = "manual"
    YOUTUBE = "youtube"


def requires_valid_period(func):
    """ Decorator that checks if the period is valid and if the limit has been reached. IT also updates the count of requests, This
    is important for sources that have a limit of requests per time period. (RAPID API)"""
    logger.debug("Checking period")

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        self.reload_config()
        if self.period_datetime and  datetime.datetime.now() - datetime.timedelta(days=self.period) < self.period_datetime:
            logger.info("Period is not valid")
            self.period_datetime = datetime.datetime.now()
            self.update_count(0)
            raise Exception("Period is not valid")
        elif self.count_requests >= self.limit:
            logger.info("Limit reached")
            raise Exception("Limit reached")
        self.update_count(1)
        result = func(self, *args, **kwargs)

        self.save_config()
        return result

    return wrapper


class ContentSearchEngine(ABC):
    """Searches for content in the information source.
        This is an abstract class to encapsulate the search engine and common methods for all search engines.
    """

    def __init__(self, information_source):
        """Initialize the searcher with the information source."""
        self.information_source = information_source
        self.count_requests = 0
        self.period = 1
        self.limit = np.inf
        self.period_datetime = None
        self.config = None
        self.pwd = None
        self.config_client = ConfigManager()


    def update_count(self, value):
        """Update the count of requests."""
        if value > 0:
            self.count_requests += value
        else:
            self.count_requests = 0

    @abstractmethod
    def search(self, save_callback: Callable) -> list:
        """Search for the query in the information source."""
        raise NotImplementedError

    @abstractmethod
    def filter(self, content):
        """Filter the content."""
        return NotImplementedError

    def reload_config(self):
        """Reload the configuration from the config.json file."""
        logger.debug("Reloading config")
        config = self.config_client.load_config(f"information-sources-{self.information_source.value}")
        for key in config.keys():
            if key != "count_requests":
                self.__setattr__(key, config[key])

    def save_config(self):
        config = self.config_client.load_config(f"information-sources-{self.information_source.value}")
        for key in config.keys():
            config[key] = getattr(self, key)

        self.config_client.save_config(f"information-sources-{self.information_source.value}", config)
