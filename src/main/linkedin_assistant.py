import asyncio
import os
import signal
import subprocess
import sys
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
    # if sys.platform == 'win32':
    #     logger.info("Setting event loop policy.")

    tasks = [
        asyncio.create_task(__run_server(os.path.join(auth_server.__file__, auth_server.FILE), stop_event)),
        asyncio.create_task(__run_server(os.path.join(bot.__file__, bot.FILE), stop_event)),
        asyncio.create_task(
            __run_server(os.path.join(publications_handler.__file__, publications_handler.FILE), stop_event)),
        asyncio.create_task(__run_server(os.path.join(source_handler.__file__, source_handler.FILE), stop_event)),
    ]

    # signal.signal(signal.SIGTERM, handle_sigterm)
    # signal.signal(signal.SIGINT, handle_sigterm)
    # signal.signal(signal.SIGBREAK, handle_sigterm)

    logger.info("starting components.")
    await asyncio.gather(*tasks)
    logger.info("All components stopped.")


def run(stop_event):
    """
    Run the main function.
    :return:
    """
    logger.info("Starting linkedin assistant.")
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(__main(stop_event))


if __name__ == '__main__':
    """
    Run the main function.
    """
    stop_event = asyncio.Event()
    run(stop_event)
