import logging
import threading
from abc import ABC, abstractmethod
import datetime
from enum import Enum
from functools import wraps
from typing import Callable
from src.core.config.manager import ConfigManager


class InformationSource(Enum):
    """Enum representing the available information sources."""

    ARXIV = "arxiv"
    MEDIUM = "medium"
    GOOGLE_NEWS = "google_news"
    MANUAL = "manual"
    YOUTUBE = "youtube"


def stateful(func):
    """Decorator to maintain state across function calls.
    This decorator is used to maintain state across function calls by
    storing the state in the object instance. It is useful for tracking
    the number of requests made and enforcing rate limits.

    :param: logger: logger to use
    """

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        self.save_config()
        return result

    return wrapper


def requires_valid_period(func):
    """Decorator to ensure valid request periods and enforce request limits.
    This decorator checks if the allowed period for requests is valid and whether
    the number of requests has reached the specified limit. It also updates the
    request count and saves configuration changes.

    :param: logger: logger to use
    """

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # Reload the configuration to ensure up-to-date parameters
        self.reload_config()

        # Check if the current period is still valid
        if not self.is_period_valid():
            self.logger.info("Period is not valid")
            self.reset()
            raise Exception("Period is not valid")

        self.period_datetime = datetime.datetime.now().isoformat()
        result = func(self, *args, **kwargs)
        return result

    return wrapper


class ContentSearchEngine(ABC):
    """Abstract base class for content search engines.
    This class encapsulates the common functionality for searching and filtering
    content from various information sources.
    """

    def __init__(self, logger: logging.Logger):
        """Initialize the search engine with the specified information source."""
        self.information_source = (
            None  # Source of information (e.g., ARXIV, YOUTUBE)
        )
        self.period = 1  # Define the period length in days
        self.period_datetime = (
            None  # Track the start time of the current period
        )
        self.minimum_length = None  # Minimum retrieved content length
        self.logger = logger
        self.config_client = ConfigManager()  # Manage configuration files

    def is_period_valid(self):
        """Check if the current period is still valid."""
        if self.period_datetime:
            return (
                    datetime.datetime.now() - datetime.timedelta(days=self.period)
            ) >= datetime.datetime.fromisoformat(self.period_datetime)
        return True

    @abstractmethod
    def search(
            self, save_callback: Callable, stop_event: threading.Event = None
    ) -> list:
        """Perform a search in the information source and return results.
        This method must be implemented by subclasses to define specific
        search functionality.
        """
        raise NotImplementedError

    @property
    def config_schema(self):
        return f"information-sources-{self.information_source.value}"

    def filter(self, content: list) -> list:
        """Filter the content based on minimum length requirements"""
        self.logger.info("Filtering %d content items", len(content))
        filtered = list(
            filter(
                lambda x: len(x.get("content", "")) > self.minimum_length,
                content,
            )
        )
        self.logger.info("%d items passed length filter", len(filtered))
        return filtered

    def reset(self):
        self.period_datetime = (
            datetime.datetime.now()
        )  # Reset period start time
        self.save_config()

    def reload_config(self):
        """Reload configuration settings from the associated config file."""
        self.logger.debug("Reloading config")
        try:
            # Load the configuration file specific to the information source
            config = self.config_client.load_config(self.config_schema)
            for key in config.keys():
                if key != "count_requests":  # Skip updating request count
                    self.__setattr__(
                        key, config[key]
                    )  # Dynamically update object attributes
        except FileNotFoundError:
            self.logger.error(
                f"Configuration file for {self.information_source.value} not found."
            )
            raise
        except Exception as e:
            self.logger.error(
                f"An error occurred while loading the configuration: {e}"
            )
            raise

    def save_config(self):
        """Save the current configuration settings to the associated config file."""
        try:
            # Load the existing configuration for modification
            config = self.config_client.load_config(self.config_schema)
            for key in config.keys():
                config[key] = getattr(
                    self, key
                )  # Update config values from object attributes

            # Save the modified configuration back to the file
            self.config_client.save_config(self.config_schema, config)
        except Exception as e:
            self.logger.error(
                f"An error occurred while saving the configuration: {e}"
            )
            raise

    def save_if_valid(self, save, result):
        """
        Saves the result if it is valid, some results might not have content, so they are not valid
        :param save:  callback to save the result
        :param result:  result to be saved

        """
        if len(result.get("content", "")) > self.minimum_length:
            save(result)
