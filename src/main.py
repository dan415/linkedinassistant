import json
import os
import sys
import threading
import time
from threading import Event
from pymongo import MongoClient
import src.information.producer as publications_handler
import src.information.searcher as source_handler
import src.linkedin.auth_server as auth_server
import src.telegram.bot as bot
from src.core.constants import SecretKeys, COLLECTIONS_AND_INDICES, JSON_DIR
from src.core.vault.hashicorp import VaultClient
from src import logger


"""
This main file is used to run all the servers at the same time. It is used to run the bot, the publications handler, the
source handler and the auth server at the same time. The idea is that the Windows service will run this file
"""


def init():
    logger.info("Initializing LinkedInAssistant")
    vault_client = VaultClient()
    db_client = MongoClient(vault_client.get_secret(SecretKeys.MONGO_URI))
    db = db_client.get_database(vault_client.get_secret(SecretKeys.MONGO_DATABASE))

    for collection_name, indices in COLLECTIONS_AND_INDICES.items():
        if collection_name not in db.list_collection_names():
            db.create_collection(collection_name)
            logger.info(f"Created collection {collection_name}")
            collection = db[collection_name]
            logger.info("Creating indices")
            for index in indices:
                unique = index.pop("unique", False)
                collection.create_index(index, unique=unique)

                if collection_name == "config":
                    try:
                        with open(os.path.join(JSON_DIR, "default_configs.json"), 'r') as file:
                            default_configs = json.load(file)
                        collection.insert_many(default_configs)
                    except OSError as ex:
                        logger.warning(f"Could not load default configs succesfully due to {ex}")


def start_auth_server():
    """
    This function starts the authentication server with waitress on a thread.
    I don't pass the stop event to it because Waitress has no mechanism (that I know of) for shutting down gracefully.
    Therefore, I don't wait for it to stop before the main thread exits the program


    """
    logger.info("Starting aut server")
    threading.Thread(
        name="auth_server",
        target=auth_server.run
    ).start()


def run(stop_event: Event) -> None:
    """
    Run all tasks in separate threads and manage their lifecycle.

    :param stop_event: An event used to signal when to stop all tasks.
    """
    init()
    start_auth_server()
    tasks = [
        ("publications_handler", publications_handler.run),
        ("sources_handler", source_handler.run),
        ("bot", bot.run)
    ]
    task_threads = []
    for task_name, task_function in tasks:
        thread = threading.Thread(
            name=task_name,
            target=task_function,
            kwargs={"stop_event": stop_event}
        )
        task_threads.append(thread)
        thread.start()

    while not stop_event.is_set():
        time.sleep(2)

    logger.info("Waiting for threads to stop")
    for thread in task_threads:
        thread.join(timeout=5)

    logger.info("All threads stopped, exiting")
    sys.exit()


def main():
    """
    Main function, meant to be run as standalone script. Creates the thread and initializes the service

    """
    event = threading.Event()
    try:
        run(event)
    except KeyboardInterrupt:
        event.set()


if __name__ == '__main__':
    main()
