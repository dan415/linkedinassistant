import threading
from typing import Any, Dict, Optional, List

from pymongo import MongoClient
from pymongo.synchronous.collection import Collection
from pymongo.synchronous.database import Database

from ..constants import CONFIGS_COLLECTION, SecretKeys
from ..utils.logging import ServiceLogger
from ..vault.hashicorp import VaultClient

logger = ServiceLogger(__name__)


class ConfigManager:
    _instance = None
    _instance_lock = threading.Lock()  # Class-level lock for singleton pattern
    _operation_lock = threading.Lock()  # Lock for thread-safe operations

    def __new__(cls):
        if not cls._instance:
            with cls._instance_lock:
                if not cls._instance:
                    logger.debug("Creating new ConfigManager instance")
                    cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            with self._instance_lock:
                if not hasattr(self, '_initialized'):
                    logger.debug("Initializing ConfigManager")
                    vault_client = VaultClient()
                    client: MongoClient = MongoClient(vault_client.get_secret(SecretKeys.MONGO_URI))
                    self.db: Database = client.get_database(vault_client.get_secret(SecretKeys.MONGO_DATABASE))
                    self.db_client: Collection = self.db[CONFIGS_COLLECTION]
                    self._initialized = True

    def save_config(self, config_name: str, config_data: Dict[str, Any]) -> bool:
        """
        Save a configuration to MongoDB in a thread-safe manner.

        :param: config_name: Name of the configuration
        :param: config_data: Configuration data to save

        :returns: bool: True if save was successful, False otherwise
        """
        logger.debug("Accessing operation lock for save_config")
        with self._operation_lock:
            try:
                logger.debug(f"Saving config '{config_name}'")
                existing_config = self.db_client.find_one({'config_name': config_name})

                if existing_config:
                    logger.debug(f"Updating existing config '{config_name}'")
                    return self.db_client.update_one({'config_name': config_name},
                                                     {"$set": config_data}).modified_count > 0
                else:
                    logger.debug(f"Creating new config '{config_name}'")
                    config_data['config_name'] = config_name
                    self.db_client.insert_one(config_data)
                    return True
            except Exception as e:
                logger.error(f"Error saving config '{config_name}': {str(e)}")
                return False

    def load_config(self, config_name: str, return_id: bool = False) -> Optional[Dict[str, Any]]:
        """
        Load a configuration from MongoDB in a thread-safe manner.

        :param: config_name: Name of the configuration to load
        :param: return_id: Whether to include the MongoDB ID in the returned data

        :returns: Optional[Dict[str, Any]]: Configuration data if found, None otherwise
        """
        logger.debug("Accessing operation lock for load_config")
        with self._operation_lock:
            try:
                logger.debug(f"Loading config '{config_name}'")
                config = self.db_client.find_one({'config_name': config_name})

                if config:
                    logger.debug(f"Config '{config_name}' found")
                    del config['config_name']
                    if not return_id:
                        del config["_id"]
                else:
                    logger.warning(f"Config '{config_name}' not found")
                return config
            except Exception as e:
                logger.error(f"Error loading config '{config_name}': {str(e)}")
                return None

    def delete_config(self, config_name: str) -> bool:
        """
        Delete a configuration from MongoDB in a thread-safe manner.

        :param: config_name: Name of the configuration to delete

        :returns: bool: True if deletion was successful, False otherwise
        """
        logger.debug("Accessing operation lock for delete_config")
        with self._operation_lock:
            try:
                logger.debug(f"Deleting config '{config_name}'")
                result = self.db_client.delete_one({'config_name': config_name}).deleted_count
                if result > 0:
                    logger.debug(f"Config '{config_name}' successfully deleted")
                else:
                    logger.debug(f"Config '{config_name}' not found")
                return result > 0
            except Exception as e:
                logger.error(f"Error deleting config '{config_name}': {str(e)}")
                return False

    def list_configs(self) -> List[str]:
        """
        List all available configuration names in a thread-safe manner.

        :returns: List[str]: List of configuration names
        """
        logger.debug("Accessing operation lock for list_configs")
        with self._operation_lock:
            try:
                logger.debug("Listing all configs")
                configs = [doc['config_name'] for doc in self.db_client.find({}, {'config_name': 1})]
                logger.debug(f"Found {len(configs)} configs")
                return configs
            except Exception as e:
                logger.error(f"Error listing configs: {str(e)}")
                return []

    def update_config_key(self, config_name: str, key: str, value: Any) -> bool:
        """
        Update a single key-value pair in a configuration in a thread-safe manner.

        :param: config_name: Name of the configuration to update
        :param: key: Configuration key to update
        :param: value: New value for the key

        :returns: bool: True if update was successful, False otherwise
        """
        logger.debug("Accessing operation lock for update_config_key")
        try:
            logger.debug(f"Updating key '{key}' in config '{config_name}'")
            config = self.load_config(config_name)

            if config is None:
                logger.debug(f"Config '{config_name}' not found")
                return False

            config[key] = value
            return self.save_config(config_name, config)
        except Exception as e:
            logger.error(f"Error updating key '{key}' in config '{config_name}': {str(e)}")
            return False
