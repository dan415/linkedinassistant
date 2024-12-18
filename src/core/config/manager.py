import os
import threading
from typing import Any, Dict, Optional

from ..constants import CONFIGS_COLLECTION
from ..database.mongo import MongoDBClient
import src.core.utils.functions as F

FILE = os.path.basename(__file__)
logger = F.get_logger(dump_to=FILE)


class ConfigManager:
    _instance = None
    _instance_lock = threading.Lock()  # Class-level lock for singleton pattern
    _operation_lock = threading.Lock()  # Lock for thread-safe operations

    def __new__(cls):
        if not cls._instance:
            with cls._instance_lock:
                if not cls._instance:
                    logger.info("Creating new ConfigManager instance")
                    cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            with self._instance_lock:
                if not hasattr(self, '_initialized'):
                    logger.info("Initializing ConfigManager")
                    self.db_client = MongoDBClient(CONFIGS_COLLECTION)
                    self._initialized = True

    def save_config(self, config_name: str, config_data: Dict[str, Any]) -> bool:
        """
        Save a configuration to MongoDB in a thread-safe manner.
        
        Args:
            config_name: Name of the configuration
            config_data: Configuration data to save
            
        Returns:
            bool: True if save was successful, False otherwise
        """
        logger.debug("Accessing Operation Lock")
        with self._operation_lock:
            try:
                logger.info(f"Saving config '{config_name}'")
                existing_config = self.db_client.find_one({'config_name': config_name})

                if existing_config:
                    logger.info(f"Updating existing config '{config_name}'")
                    return self.db_client.update_one({'config_name': config_name},  config_data) > 0
                else:
                    logger.info(f"Creating new config '{config_name}'")
                    config_data['config_name'] = config_name
                    self.db_client.insert_one(config_data)
                    return True
            except Exception as e:
                logger.error(f"Error saving config '{config_name}': {str(e)}")
                return False

    def load_config(self, config_name: str, return_id=False) -> Optional[Dict[str, Any]]:
        """
        Load a configuration from MongoDB in a thread-safe manner.
        
        Args:
            config_name: Name of the configuration to load
            
        Returns:
            Optional[Dict[str, Any]]: Configuration data if found, None otherwise
        """
        logger.debug("Accessing Operation Lock")
        with self._operation_lock:
            try:
                logger.info(f"Loading config '{config_name}'")
                config = self.db_client.find_one( {'config_name': config_name})
                if config:
                    logger.info(f"Loaded config '{config_name}'")
                    del config['config_name']  # Remove the name field from the returned data
                    if not return_id:
                        del config["_id"]
                else:
                    logger.info(f"Config '{config_name}' not found")
                return config
            except Exception as e:
                logger.error(f"Error loading config '{config_name}': {str(e)}")
                return {}

    def delete_config(self, config_name: str) -> bool:
        """
        Delete a configuration from MongoDB in a thread-safe manner.
        
        Args:
            config_name: Name of the configuration to delete
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        logger.debug("Accessing Operation Lock")
        with self._operation_lock:
            try:
                logger.info(f"Deleting config '{config_name}'")
                result = self.db_client.delete_one({'config_name': config_name})
                if result > 0:
                    logger.info(f"Deleted config '{config_name}'")
                else:
                    logger.info(f"Config '{config_name}' not found")
                return result > 0
            except Exception as e:
                logger.error(f"Error deleting config '{config_name}': {str(e)}")
                return False

    def list_configs(self) -> list[str]:
        """
        List all available configuration names in a thread-safe manner.
        
        Returns:
            list[str]: List of configuration names
        """
        logger.debug("Accessing Operation Lock")
        with self._operation_lock:
            try:
                logger.info("Listing all configs")
                configs = [doc['config_name'] for doc in self.db_client.find({}, {'config_name': 1})]
                logger.info(f"Found {len(configs)} configs")
                return configs
            except Exception as e:
                logger.error(f"Error listing configs: {str(e)}")
                return []

    def update_config_key(self, config_name: str, key: str, value: Any) -> bool:
        """
        Update a single key-value pair in a configuration in a thread-safe manner.
        
        Args:
            config_name: Name of the configuration to update
            key: Configuration key to update
            value: New value for the key
            
        Returns:
            bool: True if update was successful, False otherwise
        """

        try:
            logger.info(f"Updating key '{key}' in config '{config_name}'")
            config = self.load_config(config_name)

            if config is None:
                logger.error(f"Config '{config_name}' not found")
                return False

            config[key] = value
            return self.save_config(config_name, config)

        except Exception as e:
            logger.error(f"Error updating key '{key}' in config '{config_name}': {str(e)}")
            return False
