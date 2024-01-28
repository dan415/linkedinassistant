import asyncio
import logging
import os
import signal
import subprocess
import sys
from origamibot.core.sthread import StoppableThread
# Im just reusing the StoppableThread class from origamibot, given that they had it already

from time import sleep

import win32event

import src.information.publications_handler as publications_handler
import src.information.source_handler as source_handler
import src.linkedin.auth_server as auth_server
import src.telegram.bot as bot
from src.utils.log_handler import TruncateByTimeHandler

PWD = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(PWD, '..', ".."))
LOGGING_DIR = os.path.join(PROJECT_DIR, "logs") if sys.platform != 'win32' else os.path.join(r"C:\\", "ProgramData",
                                                                                             "linkedin_assistant",
                                                                                             "logs")

FILE = os.path.basename(__file__)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = TruncateByTimeHandler(filename=os.path.join(LOGGING_DIR, f'{FILE}.log'), encoding='utf-8', mode='a+')
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter(f'%(asctime)s - %(name)s - {__name__} - %(levelname)s - %(message)s'))
logger.addHandler(handler)

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

