import os
import threading
import time
from typing import Any, Dict, Optional

import requests
from retry import retry
import src.core.utils.functions as F
from src.core.vault.exceptions import (
    VaultError,
    AuthenticationError,
    ResourceNotFoundException,
    ConfigurationError,
    RateLimitError
)

FILE = os.path.basename(__file__)
logger = F.get_logger(dump_to=FILE)


class VaultClient:
    _instance = None
    _lock = threading.Lock()

    # API endpoints
    _HCP_AUTH_URL = "https://auth.idp.hashicorp.com/oauth/token"
    _HCP_API_VERSION = "2023-11-28"

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    logger.info("Creating new VaultClient instance")
                    cls._instance = super(VaultClient, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.organization = os.getenv('HCP_ORGANIZATION')
        self.project = os.getenv('HCP_PROJECT')
        self.app = os.getenv('HCP_APP')
        self.hcp_client_id = os.getenv('HCP_CLIENT_ID')
        self.hcp_client_secret = os.getenv('HCP_CLIENT_SECRET')
        self.access_token: Optional[str] = None

        # Cache configuration
        self._cache: Dict[str, tuple[Any, float]] = {}  # {key: (value, timestamp)}
        self._cache_ttl = 300  # 5 minutes TTL for cached secrets

        if not all([self.organization, self.project, self.app, self.hcp_client_id, self.hcp_client_secret]):
            logger.error("Missing required environment variables")
            raise ConfigurationError(
                "Missing required environment variables. Please ensure all required variables are set: "
                "HCP_ORGANIZATION, HCP_PROJECT, HCP_APP, HCP_CLIENT_ID, HCP_CLIENT_SECRET"
            )

        logger.info("Initializing VaultClient with organization: %s, project: %s, app: %s",
                    self.organization, self.project, self.app)
        self.endpoint = f"https://api.cloud.hashicorp.com/secrets/{self._HCP_API_VERSION}/organizations/{self.organization}/projects/{self.project}/apps/{self.app}"
        self._initialized = True
        self.authenticate()

    def authenticate(self) -> None:
        """Authenticate with HCP and get an access token."""
        logger.info("Authenticating with HCP")
        self.access_token = self.__get_hcp_token()
        logger.info("Successfully authenticated with HCP")

    def clear_cache(self) -> None:
        """Clear the secret cache."""
        logger.info("Clearing secret cache")
        with self._lock:
            self._cache.clear()

    def _is_cache_valid(self, key: str) -> bool:
        """Check if a cached value is still valid."""
        if key not in self._cache:
            return False
        _, timestamp = self._cache[key]
        return time.time() - timestamp < self._cache_ttl

    @retry(AuthenticationError, tries=3, delay=1)
    def get_secret(self, key: str) -> Any:
        """
        Get a secret from Vault with caching.

        Args:
            key: Specific key to retrieve from the secret

        Returns:
            The secret value or None if not found
            
        Raises:
            AuthenticationError: If authentication fails
            ResourceNotFoundException: If the secret is not found
            RateLimitError: If the API rate limit is exceeded
            VaultError: For other vault-related errors
        """
        # Check cache first
        with self._lock:
            if self._is_cache_valid(key):
                logger.debug("Cache hit for key: %s", key)
                return self._cache[key][0]
            elif key in self._cache:
                logger.debug("Cache expired for key: %s", key)
                del self._cache[key]

        logger.info("Fetching secret for key: %s", key)
        # If not in cache or expired, fetch from vault
        endpoint = f"{self.endpoint}/secrets/{key}:open"

        try:
            response = requests.get(endpoint, headers={
                "Authorization": f"Bearer {self.access_token}"
            })

            if response.status_code == 204:
                logger.warning("Secret not found for key: %s", key)
                raise ResourceNotFoundException(f"Secret '{key}' not found", response)
            elif response.status_code == 401:
                logger.warning("Authentication failed while fetching secret: %s", key)
                self.authenticate()
                raise AuthenticationError("Authentication failed", response)
            elif response.status_code == 429:
                logger.error("Rate limit exceeded while fetching secret: %s", key)
                raise RateLimitError("Too many requests to the vault API", response)
            elif response.status_code != 200:
                logger.error("Failed to get secret %s: %s - %s", key, response.status_code, response.text)
                raise VaultError(f"Failed to get secret: {response.status_code} - {response.text}", response)

            value = response.json().get("secret", {}).get("static_version", {}).get("value")
            if value is None:
                logger.warning("Secret exists but has no value for key: %s", key)
                raise ResourceNotFoundException(f"Secret '{key}' exists but has no value", response)

            # Cache the result with current timestamp
            with self._lock:
                self._cache[key] = (value, time.time())
            logger.info("Successfully fetched and cached secret for key: %s", key)
            return value

        except requests.RequestException as e:
            logger.error("Network error while fetching secret %s: %s", key, str(e))
            raise VaultError(f"Network error while fetching secret: {str(e)}")

    @retry(AuthenticationError, tries=3, delay=1)
    def create_or_update_secret(self, key: str, value: Any) -> bool:
        """
        Create or update a secret in the vault.
        
        Args:
            key: The secret key
            value: The secret value
            
        Returns:
            bool: True if successful
            
        Raises:
            AuthenticationError: If authentication fails
            RateLimitError: If the API rate limit is exceeded
            VaultError: For other vault-related errors
        """
        logger.info("Creating/updating secret for key: %s", key)
        endpoint = f"{self.endpoint}/secret/kv"

        try:
            response = requests.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {self.access_token}"
                },
                data={
                    "name": key,
                    "value": value
                }
            )

            if response.status_code == 401:
                logger.error("Authentication failed while creating/updating secret: %s", key)
                self.authenticate()
                raise AuthenticationError("Authentication failed", response)
            elif response.status_code == 429:
                logger.error("Rate limit exceeded while creating/updating secret: %s", key)
                raise RateLimitError("Too many requests to the vault API", response)
            elif response.status_code != 200:
                logger.error("Failed to create/update secret %s: %s - %s", key, response.status_code, response.text)
                raise VaultError(f"Failed to create/update secret: {response.status_code} - {response.text}", response)

            # Clear the cache entry for this key
            with self._lock:
                self._cache.pop(key, None)

            logger.info("Successfully created/updated secret for key: %s", key)
            return True

        except requests.RequestException as e:
            logger.error("Network error while creating/updating secret %s: %s", key, str(e))
            raise VaultError(f"Network error while updating secret: {str(e)}")

    def __get_hcp_token(self) -> str:
        """
        Retrieve an access token for the Hashicorp Cloud Platform (HCP).
        
        Returns:
            str: The access token if successful
            
        Raises:
            ConfigurationError: If client credentials are not set
            AuthenticationError: If authentication fails
            RateLimitError: If the API rate limit is exceeded
            VaultError: For other vault-related errors
        """
        logger.info("Retrieving HCP access token")
        if not self.hcp_client_id or not self.hcp_client_secret:
            logger.error("Missing HCP client credentials")
            raise ConfigurationError("HCP_CLIENT_ID and HCP_CLIENT_SECRET environment variables must be set")

        data = {
            "grant_type": "client_credentials",
            "client_id": self.hcp_client_id,
            "client_secret": self.hcp_client_secret,
            "audience": "https://api.hashicorp.cloud"
        }

        try:
            response = requests.post(self._HCP_AUTH_URL, data=data)

            if response.status_code == 401:
                logger.error("Invalid client credentials")
                raise AuthenticationError("Invalid client credentials", response)
            elif response.status_code == 429:
                logger.error("Rate limit exceeded while retrieving token")
                raise RateLimitError("Too many authentication requests", response)
            elif response.status_code != 200:
                logger.error("Failed to retrieve token: %s - %s", response.status_code, response.text)
                raise VaultError(f"Failed to retrieve token: {response.status_code} - {response.text}", response)

            token = response.json().get("access_token")
            if not token:
                logger.error("No access token in response")
                raise VaultError("No access token in response", response)

            logger.info("Successfully retrieved HCP access token")
            return token

        except requests.RequestException as e:
            logger.error("Network error during authentication: %s", str(e))
            raise VaultError(f"Network error during authentication: {str(e)}")
