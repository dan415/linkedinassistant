import logging
from abc import ABC
from functools import wraps
import requests
from src.core.constants import SecretKeys
from src.core.exceptions import VaultError
from src.information.sources.base import ContentSearchEngine
from src.core.vault.hashicorp import VaultClient


def rate_limited_operation(func):
    """
    Decorator to enforce a rate limit on API operations.

    It checks if the number of requests has exceeded the limit before executing the function.
    If the limit is reached, it raises an exception.

    Args:
        func (callable): The function to wrap.

    Returns:
        callable: The wrapped function.
    """

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        self.reload_config()

        if self.limit and self.count_requests >= self.limit:
            self.logger.info(
                f"Limit reached: {self.count_requests}/{self.limit}"
            )
            raise Exception("Limit reached")

        self.increment_request_count()
        result = func(self, *args, **kwargs)
        self.save_config()
        return result

    return wrapper


class RapidSource(ContentSearchEngine, ABC):
    """
    Represents a base class for sources that utilize RapidAPI services.

    This class provides common behaviors and utility functions for working with RapidAPI-based
    content search engines. It can serve as a blueprint for implementing APIs with shared
    functionalities such as rate limiting, request handling, and filtering results.

    Attributes:
        information_source (InformationSource): The source of information for the content search engine.
        host (str): The API host address.
        url (str): The API endpoint URL.
        limit (int): The maximum number of requests allowed (default is unlimited).
        count_requests (int): Counter for the number of requests made.
        topics (list): Topics to query or filter.
        max_results (int): Maximum number of results to retrieve per query.
        request_timeout (int): Timeout duration for API requests in seconds.
    """

    def __init__(self, logger: logging.Logger):
        super().__init__(logger)
        self.host = ""
        self.url = ""
        self.limit = None
        self.count_requests = 0
        self.topics = []
        self.max_results = 25
        self.request_timeout = 30

    def get_api_key(self):
        """
        Retrieve the API key for RapidAPI services from a secure vault.

        Returns:
            str: The API key for accessing RapidAPI services.

        Raises:
            RuntimeError: If the API key cannot be retrieved.
        """
        try:
            return VaultClient().get_secret(SecretKeys.RAPID_API_KEY)
        except VaultError as e:
            self.logger.error(f"Failed to retrieve the API key: {e}")
            raise RuntimeError(
                "Could not retrieve the RapidAPI key. Please check the vault configuration."
            )

    @property
    def config_schema(self):
        return (
            super().config_schema.rsplit("-", 1)[0]
            + f"-rapid-{self.information_source.value}"
        )

    def increment_request_count(self):
        self.count_requests += 1

    def reset_request_count(self):
        self.count_requests = 0

    def reset(self):
        self.reset_request_count()
        super().reset()

    @rate_limited_operation
    def execute_rapid_request(
        self, url, params=None, payload=None, extra_headers=None
    ):
        """
        Execute a request to a RapidAPI endpoint with optional payload and headers.

        Args:
            url (str): The URL of the RapidAPI endpoint.
            params (dict, optional): Query parameters for GET requests.
            payload (dict, optional): JSON payload for POST requests.
            extra_headers (dict, optional): Additional headers to include in the request.

        Returns:
            requests.Response: The response object from the HTTP request.
        """
        headers = self.get_headers()
        if extra_headers:
            headers.update(extra_headers)
        if payload:
            return requests.post(
                url, headers=headers, json=payload, timeout=self.request_timeout
            )
        else:
            return requests.get(
                url,
                params=params,
                headers=headers,
                timeout=self.request_timeout,
            )

    def get_headers(self):
        """
        Generate the required headers for RapidAPI requests.

        Returns:
            dict: Headers including the API key and host information.
        """
        return {
            "x-rapidapi-key": self.get_api_key(),
            "x-rapidapi-host": self.host,
        }

    def filter(self, results):
        """
        Filter the results to remove entries without valid content or title.

        Args:
            results (list): The list of results to filter.

        Returns:
            list: Filtered results containing only entries with valid titles and content exceeding the minimum length.
        """
        return list(
            filter(
                lambda x: x.get("title", "") != "",
                filter(
                    lambda x: len(x.get("content", "")) > self.minimum_length,
                    results,
                ),
            )
        )
