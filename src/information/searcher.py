import datetime
import threading
import time
import uuid
from functools import wraps
from src.core.config.manager import ConfigManager
from src.core.constants import FileManagedFolders
from src.core.file_manager.b2 import B2Handler
from src.core.publications import PublicationIterator
import src.core.utils.functions as F
from src.core.utils.logging import ServiceLogger
from src.information.sources.base import InformationSource
from src.information.sources.provider import ContentSearchEngineProvider

logger = ServiceLogger(__name__)


def stateful(func):
    """
    Decorator to ensure that the configuration state is updated in the config.json file.
    If the program exits unexpectedly, the current state is preserved.
    This is intended for methods that modify state variables.
    """

    @wraps(func)
    def update_config(self, *args, **kwargs):
        result = func(self, *args, **kwargs)  # Execute the original function
        self.save_config()  # Save the updated configuration
        return result

    return update_config


def should_run(last_run_time, execution_period):
    """
    Helper function to determine if enough time has passed since the last run.
    :param last_run_time: The last run time as a string.
    :param execution_period: The execution period in days.
    :return: Boolean indicating if the handler should run.
    """
    if not last_run_time:
        return True
    last_run = datetime.datetime.strptime(last_run_time, "%Y-%m-%d %H:%M:%S")
    next_run_time = last_run + datetime.timedelta(days=execution_period)
    return datetime.datetime.now() >= next_run_time


class SourcesHandler:
    """
    Handles the concurrent execution of search engines to retrieve and process publication ideas.
    """
    CONFIG_SCHEMA = "information"

    def __init__(self):
        # Initialize basic attributes
        self.active = True  # Controls whether the handler is actively running
        # Initialize configuration and runtime parameters
        self.active_sources = []  # List of active sources to use
        self.search_engines = []  # Search engines corresponding to active sources
        self.execution_period = 1  # Minimum time period between executions (in days)
        self.one_by_one = True  # Process results immediately if True
        self.last_run_time = None  # Last time the handler was executed

        # Configuration schema and manager
        self.config_client = ConfigManager()

        # Load initial configuration and initialize the publication iterator
        self.reload_config()
        self.file_manager = B2Handler()
        self.publications_manager = PublicationIterator(logger=logger)

    def run(self, stop_event: threading.Event = None):
        """
        Main loop that runs the search engines and sleeps until the next scheduled execution.

        :param stop_event: Optional thread event to trigger graceful termination

        """
        logger.info("Initializing sources handler.")
        while not stop_event or not stop_event.is_set():
            if self.active:
                self.run_search_engines(stop_event)  # Execute all search engines
                logger.debug("Source handler sleeping.")
            time.sleep(5)
        logger.info("Searcher exited because of stop event triggered")

    def save_images(self, publication_id: str, images: list[bytes]):
        """
        Iterates through extracted images and uploads them to B2 under {publication_id}/Images
        :param publication_id: (str) Identifier of the publication
        :param images: (list[bytes])  List of images to be uploaded
        :return: Count of images uploaded
        """
        count = 0
        for image in images:
            try:
                dest_path = "/".join([
                    FileManagedFolders.IMAGES_FOLDER,
                    publication_id,
                    str(uuid.uuid4())
                ])
                logger.info(f"Saving image into {dest_path}")
                self.file_manager.upload_from_bytes(image, dest_path)
                count += 1
            except Exception as ex:
                logger.error(f"Error saving image: {ex}")
        return count

    def save_material(self, material):
        """
        Save the processed material needed to create a publication.

        :param material: A dictionary containing publication data to save.
        """
        logger.info(f"Saving material {material.get('title', '')}.")

        extracted_images = material.pop("extracted_images", [])
        logger.info(f"Material has {len(extracted_images)} images")
        publication_id = self.publications_manager.insert(material)  # Insert material into the collection

        if not publication_id:
            logger.warning("Could not save material")
            return

        if extracted_images:
            logger.info(f"Saving {len(extracted_images)} images for publication {publication_id}")
            saved_count = self.save_images(publication_id=publication_id, images=extracted_images)
            logger.info(f"{saved_count} images saved for publication {publication_id}")

    def init_active_sources(self):
        """
        Initialize active sources and create corresponding search engines.
        This is triggered whenever the active sources configuration changes.
        """
        logger.info("Initializing active sources")
        self.search_engines = []
        for x in self.active_sources:
            try:
                source_enum = F.get_enum_from_value(x, InformationSource)
                search_engine = ContentSearchEngineProvider.get_content_search_engine(source_enum)
                self.search_engines.append(search_engine)
            except Exception as e:
                logger.error(f"Failed to initialize source '{x}': {e}")

    def run_search_engine(self, search_engine, stop_event: threading.Event = None):
        """
        Run a specific search engine and process its results.

        :param stop_event: Optional thread event to trigger graceful termination
        :param search_engine: The search engine instance to execute.
        """
        try:
            logger.debug(f"Running search engine {search_engine}")
            results = search_engine.search(self.save_material if self.one_by_one else None, stop_event)
            if not self.one_by_one:
                results = search_engine.filter(results)  # Filter results if needed
                for result in results:
                    self.save_material(result)  # Save each result
            logger.debug(f"Finished running search engine {search_engine}")
        except Exception as e:
            logger.error(f"Error running search engine {search_engine}: {e}")

    @stateful
    def run_search_engines(self, stop_event: threading.Event = None):
        """
        Execute all search engines concurrently, ensuring the execution period is respected.

        :param stop_event: Optional thread event to trigger graceful termination
        """
        # Use helper function to check if the handler should run
        if not should_run(self.last_run_time, self.execution_period):
            logger.debug("Sources handler needs to wait more time to run.")
            return []

        threads = []
        for search_engine in self.search_engines:
            # Create a thread for each search engine
            threads.append(threading.Thread(name=search_engine, target=self.run_search_engine, args=[search_engine, stop_event]))

        self.last_run_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Update last run time
        self.update_last_run_time()  # Persist the updated time in the config

        for thread in threads:
            thread.start()  # Start all threads
        for thread in threads:
            thread.join()  # Wait for all threads to complete

        logger.info("Finished running search engines succesfully")

    def update_last_run_time(self):
        """
        Update the last run time in the configuration file.
        """
        self.config_client.update_config_key(self.CONFIG_SCHEMA, "last_run_time", self.last_run_time)

    def reload_config(self):
        """
        Reload the configuration and apply updates to the handler's state.
        """
        logger.debug("Reloading config")
        config = self.config_client.load_config(self.CONFIG_SCHEMA)

        for key, value in config.items():
            if key == "active_sources":
                active_sources = value
                has_changed = self.active_sources != active_sources
                self.active_sources = active_sources
                if has_changed:
                    self.init_active_sources()  # Reinitialize active sources if changed
            else:
                setattr(self, key, value)  # Update other attributes dynamically

    def save_config(self):
        """
        Save the current state to the configuration file.
        """
        config = self.config_client.load_config(self.CONFIG_SCHEMA)

        for key in config.keys():
            config[key] = getattr(self, key)  # Reflect current state in the config

        self.config_client.save_config(self.CONFIG_SCHEMA, config)  # Save to file


def run(stop_event: threading.Event = None):
    """
    Entry point to start the SourcesHandler.
    """
    SourcesHandler().run(stop_event)
    logger.info("Exiting Run function")


if __name__ == '__main__':
    run()
