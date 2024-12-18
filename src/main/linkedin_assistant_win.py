import os
from origamibot.core.sthread import StoppableThread
# Im just reusing the StoppableThread class from origamibot, given that they had it already
from time import sleep
import src.information.publications_handler as publications_handler
import src.information.source_handler as source_handler
import src.linkedin.auth.server as auth_server
import src.telegram.bot as bot
import src.core.utils.functions as F

FILE = os.path.basename(__file__)
logger = F.get_logger(dump_to=FILE)

"""
This main file is used to run all the servers at the same time. It is used to run the bot, the publications handler, the
source handler and the auth server at the same time. The idea is that the Windows service will run this file
"""

tasks = [
    auth_server.run,
    publications_handler.run,
    source_handler.run,
    bot.run
]


def run(stop_event):
    task_threads = []
    for task_function in tasks:
        thread = StoppableThread(
            target=task_function
        )
        task_threads.append(thread)
        thread.start()

    while True:
        if stop_event.is_set():
            logger.info("Requesting stop")
            for thread in task_threads:
                thread.stop()

            logger.info("Waiting for threads to stop")
            for thread in task_threads:
                thread.join()

            logger.info("All threads stopped, exiting")
            break

        sleep(2)

