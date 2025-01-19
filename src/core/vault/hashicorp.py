import os
import threading
from typing import Any, Optional
from pydantic.dataclasses import dataclass
from cachetools import TTLCache
import requests
import keyring
from retry import retry
from requests.exceptions import Timeout
from src.core.constants import SERVICE_NAME
from src.core.exceptions import (
    VaultError,
    AuthenticationError,
    ConfigurationError,
    RateLimitExceeded,
)
from src.core.utils.logging import ServiceLogger

logger = ServiceLogger(__name__)

HCP_ORGANIZATION = "HCP_ORGANIZATION"
HCP_PROJECT = "HCP_PROJECT"
HCP_APP = "HCP_APP"
HCP_CLIENT_ID = "HCP_CLIENT_ID"
HCP_CLIENT_SECRET = "HCP_CLIENT_SECRET"


@dataclass
class VaultConfig:
    organization: str
    project: str
    app: str
    hcp_client_id: str
    hcp_client_secret: str
    access_token: Optional[str] = None

    @classmethod
    def from_environment(cls):
        """Load configuration from environment variables."""
        return VaultConfig(
            organization=os.getenv(HCP_ORGANIZATION),
            project=os.getenv(HCP_PROJECT),
            app=os.getenv(HCP_APP),
            hcp_client_id=os.getenv(HCP_CLIENT_ID),
            hcp_client_secret=os.getenv(HCP_CLIENT_SECRET),
        )

    @classmethod
    def from_keyring(cls):
        """Load configuration from keyring."""
        organization = keyring.get_password(SERVICE_NAME, HCP_ORGANIZATION)
        project = keyring.get_password(SERVICE_NAME, HCP_PROJECT)
        app = keyring.get_password(SERVICE_NAME, HCP_APP)
        hcp_client_id = keyring.get_password(SERVICE_NAME, HCP_CLIENT_ID)
        hcp_client_secret = keyring.get_password(
            SERVICE_NAME, HCP_CLIENT_SECRET
        )

        if not all(
            [organization, project, app, hcp_client_id, hcp_client_secret]
        ):
            logger.error("Missing required keyring credentials")
            raise ConfigurationError(
                "Missing required keyring credentials. Please ensure all required variables are set in keyring: "
                "HCP_ORGANIZATION, HCP_PROJECT, HCP_APP, HCP_CLIENT_ID, HCP_CLIENT_SECRET"
            )

        return VaultConfig(
            organization=organization,
            project=project,
            app=app,
            hcp_client_id=hcp_client_id,
            hcp_client_secret=hcp_client_secret,
        )

    def save_on_keyring(self):
        """
        Method to store config on system's keyring
        """
        keyring.set_password(SERVICE_NAME, HCP_ORGANIZATION, self.organization)
        keyring.set_password(SERVICE_NAME, HCP_PROJECT, self.project)
        keyring.set_password(SERVICE_NAME, HCP_APP, self.app)
        keyring.set_password(SERVICE_NAME, HCP_CLIENT_ID, self.hcp_client_id)
        keyring.set_password(
            SERVICE_NAME, HCP_CLIENT_SECRET, self.hcp_client_secret
        )
        logger.info(f"Saved vault config on keyring for service {SERVICE_NAME}")


class VaultClient:
    _instance = None
    _lock = threading.Lock()

    _HCP_AUTH_URL = "https://auth.idp.hashicorp.com/oauth/token"
    _HCP_API_VERSION = "2023-11-28"
    _RETRY_TRIES = 3
    _RETRY_DELAY = 60
    _REQUEST_TIMEOUT = 10

    def __new__(cls, config: Optional[VaultConfig] = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    logger.info("Creating new VaultClient instance")
                    cls._instance = super(VaultClient, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, config: Optional[VaultConfig] = None):
        if self._initialized:
            return

        if config is None:
            logger.info(
                "No config provided, attempting to load from keyring with service name '%s'",
                SERVICE_NAME,
            )
            config = VaultConfig.from_keyring()

        self.config = config

        # Cache configuration using cachetools
        self._cache = TTLCache(maxsize=100, ttl=86400)  # Cache for a day

        if not all(
            [
                self.config.organization,
                self.config.project,
                self.config.app,
                self.config.hcp_client_id,
                self.config.hcp_client_secret,
            ]
        ):
            logger.error("Missing required configuration fields")
            raise ConfigurationError(
                "Missing required configuration fields. Please ensure all required fields are provided: "
                "organization, project, app, hcp_client_id, hcp_client_secret"
            )

        logger.info(
            "Initializing VaultClient with organization: %s, project: %s, app: %s",
            self.config.organization,
            self.config.project,
            self.config.app,
        )
        self.endpoint = (
            f"https://api.cloud.hashicorp.com/secrets/"
            f"{self._HCP_API_VERSION}/organizations/"
            f"{self.config.organization}/projects/"
            f"{self.config.project}/apps/{self.config.app}"
        )

        self._initialized = True
        self.authenticate()

    def authenticate(self):
        """Authenticate with HCP and get an access token."""
        logger.info("Authenticating with HCP")
        self.config.access_token = self.__get_hcp_token()
        logger.info("Successfully authenticated with HCP")

    def clear_cache(self):
        """Clear the secret cache."""
        logger.info("Clearing secret cache")
        self._cache.clear()

    @retry(
        (AuthenticationError, RateLimitExceeded),
        tries=_RETRY_TRIES,
        delay=_RETRY_DELAY,
        logger=logger,
    )
    def get_secret(self, key: str) -> Any:
        """
        Get a secret from Vault with caching.

        :param: key: Specific key to retrieve from the secret

        :returns: The secret value or None if not found

        :raises AuthenticationError: If authentication fails
        :raises ResourceNotFoundException: If the secret is not found
        :raises RateLimitError: If the API rate limit is exceeded
        :raises VaultError: For other vault-related errors
        """
        # Check cache first
        if key in self._cache:
            logger.debug("Cache hit for key: %s", key)
            return self._cache[key]

        logger.info("Fetching secret for key: %s", key)
        # If not in cache or expired, fetch from vault
        endpoint = f"{self.endpoint}/secrets/{key}:open"

        response = requests.get(
            endpoint,
            headers={"Authorization": f"Bearer {self.config.access_token}"},
            timeout=self._REQUEST_TIMEOUT,
        )

        if response.status_code == 401:
            logger.warning(
                "Authentication failed while fetching secret: %s", key
            )
            self.authenticate()
            raise AuthenticationError("Authentication failed", response)
        elif response.status_code != 200:
            logger.error(
                "Failed to get secret %s: %s - %s",
                key,
                response.status_code,
                response.text,
            )
            raise VaultError.from_status(response.status_code)

        value = (
            response.json()
            .get("secret", {})
            .get("static_version", {})
            .get("value")
        )
        self._cache[key] = value
        logger.info("Successfully fetched and cached secret for key: %s", key)
        return value

    @retry(
        (AuthenticationError, RateLimitExceeded),
        tries=_RETRY_TRIES,
        delay=_RETRY_DELAY,
        logger=logger,
    )
    def create_or_update_secret(self, key: str, value: Any) -> bool:
        """
        Create or update a secret in the vault.

        :param: key: The secret key
        :param: value: The secret value

        :returns: bool: True if successful

        :raises: AuthenticationError: If authentication fails
        :raises: RateLimitError: If the API rate limit is exceeded
        :raises: VaultError: For other vault-related errors
        """
        logger.info("Creating/updating secret for key: %s", key)
        endpoint = f"{self.endpoint}/secret/kv"

        response = requests.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {self.config.access_token}",
                "content-type": "application/json",
            },
            json={"name": key, "value": str(value)},
            timeout=self._REQUEST_TIMEOUT,
        )

        if response.status_code == 401:
            logger.error(
                "Authentication failed while creating/updating secret: %s", key
            )
            self.authenticate()
            raise AuthenticationError("Authentication failed", response)
        elif response.status_code != 200:
            logger.error(
                "Failed to get secret %s: %s - %s",
                key,
                response.status_code,
                response.text,
            )
            raise VaultError.from_status(response.status_code)

        # Clear the cache entry for this key
        self._cache.pop(key, None)
        logger.info("Successfully created/updated secret for key: %s", key)
        return True

    @retry(Timeout, tries=5, delay=2, backoff=3, jitter=(1, 3), logger=logger)
    def __get_hcp_token(self) -> str:
        """
        Retrieve an access token for the Hashicorp Cloud Platform (HCP).

        :returns: str: The access token if successful

        :raises: ConfigurationError: If client credentials are not set
        :raises: AuthenticationError: If authentication fails
        :raises: RateLimitError: If the API rate limit is exceeded
        :raises: VaultError: For other vault-related errors
        """
        logger.info("Retrieving HCP access token")
        if not self.config.hcp_client_id or not self.config.hcp_client_secret:
            logger.error("Missing HCP client credentials")
            raise ConfigurationError(
                "HCP_CLIENT_ID and HCP_CLIENT_SECRET environment variables must be set"
            )

        data = {
            "grant_type": "client_credentials",
            "client_id": self.config.hcp_client_id,
            "client_secret": self.config.hcp_client_secret,
            "audience": "https://api.hashicorp.cloud",
        }

        try:
            response = requests.post(
                self._HCP_AUTH_URL, data=data, timeout=self._REQUEST_TIMEOUT
            )
            response.raise_for_status()
        except Timeout:
            logger.warning("Request to HCP timed out")
            raise Timeout
        except requests.exceptions.RequestException as e:
            logger.error("Request failed: %s", str(e))
            raise VaultError(str(e))

        if response.status_code == 401:
            logger.error("Invalid client credentials")
            raise AuthenticationError("Invalid client credentials", response)
        elif response.status_code != 200:
            logger.error(
                "Failed to get secret %s: %s - %s",
                response.status_code,
                response.text,
            )
            raise VaultError.from_status(response.status_code)

        token = response.json().get("access_token")
        if not token:
            logger.error("No access token in response")
            raise VaultError("No access token in response", response)

        logger.info("Successfully retrieved HCP access token")
        return token
