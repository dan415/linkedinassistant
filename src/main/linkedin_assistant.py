import asyncio
import logging
import os
import signal
import subprocess
import sys

import src.information.publications_handler as publications_handler
import src.information.source_handler as source_handler
import src.linkedin.auth_server as auth_server
import src.telegram.bot as bot
from src.utils.log_handler import TruncateByTimeHandler

PWD = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(PWD, '..', ".."))
LOGGING_DIR = os.path.join(PROJECT_DIR, "logs") if sys.platform != 'win32' else os.path.join(r"C:\\", "ProgramData", "linkedin_assistant", "logs")

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

async def __run_server(file, stop_event):
    """
    Runs the python scripts as subprocesses. Then it waits for the stop event to be set to stop the execution.
    :param file: script to run
    :param stop_event: event to stop the execution

    """
    kwargs = {}
    kwargs["stdin"] = subprocess.DEVNULL
    kwargs['stdout'] = subprocess.PIPE
    kwargs['stderr'] = subprocess.STDOUT
    if sys.platform != 'win32':
        kwargs['preexec_fn'] = lambda: signal.signal(signal.SIGTERM, signal.SIG_IGN)
    else:
        kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP

    process = await asyncio.create_subprocess_shell(
        f"python {file}",
        **kwargs
    )

    while not stop_event.is_set():
        await process.communicate()
    process.terminate()
    await asyncio.sleep(1)



async def __main(stop_event):
    """
    Creeate the stop event and the tasks to run the servers. Then it waits for the stop event to be set to stop the
    execution.
    :return:
    """

    def handle_sigterm(signum, frame):
        logger.info("Received sigterm.")
        stop_event.set()

    logger.info("Starting linkedin assistant.")
    #asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    tasks = [
        asyncio.create_task(__run_server(os.path.join(auth_server.PWD, auth_server.FILE), stop_event)),
        asyncio.create_task(__run_server(os.path.join(bot.PWD, bot.FILE), stop_event)),
        asyncio.create_task(__run_server(os.path.join(publications_handler.PWD, publications_handler.FILE), stop_event)),
        asyncio.create_task(__run_server(os.path.join(source_handler.PWD, source_handler.FILE), stop_event)),
    ]

    if sys.platform != 'win32':
        signal.signal(signal.SIGTERM, handle_sigterm)
        signal.signal(signal.SIGINT, handle_sigterm)

    await asyncio.gather(*tasks)


def run(stop_event):
    """
    Run the main function.
    :return:
    """
    logger.info("Starting linkedin assistant.")
    asyncio.run(__main(stop_event))


if __name__ == '__main__':
    """
    Run the main function.
    """
    stop_event = asyncio.Event()
    run(stop_event)
