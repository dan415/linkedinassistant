import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', "..")))

import asyncio
import src.core.utils.functions as F
import sys
import servicemanager
import win32event
import win32service
import win32serviceutil
from src.main import linkedin_assistant_win

FILE = os.path.basename(__file__)
logger = F.get_logger(dump_to=FILE)


class LinkedinAssistantService(win32serviceutil.ServiceFramework):
    """
    Linkedin Assistant Windows Service class. It is used to run the Linkedin Assistant as a Windows Service.
    """
    _svc_name_ = 'linkedin_assistant'
    _svc_display_name_ = 'Linkedin Assistant'
    _svc_description_ = 'Linkedin Assistant'
    _svc_start_type_ = win32service.SERVICE_AUTO_START

    def __init__(self, args):
        """
        Constructor of the Linkedin Assistant Windows Service class. It is used to run the Linkedin Assistant as a
        Windows Service.
        :param args:
        """
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.subprocess_stop_event = asyncio.Event()
        self.loop = None
        self.retry_delay = 60  # Retry after 60 seconds on failure

    def run(self):
        """
        Run the Linkedin Assistant as a Windows Service.
        """
        logger.info("Starting service.")
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        async def service_main():
            while True:
                try:
                    if win32event.WaitForSingleObject(self.stop_event, 0) == win32event.WAIT_OBJECT_0:
                        logger.info("Service stop requested.")
                        break

                    logger.info("Running Linkedin Assistant.")
                    # Run the assistant in a task
                    task = self.loop.create_task(linkedin_assistant_win.run(self.subprocess_stop_event))
                    await task

                except Exception as e:
                    logger.error(f"Error in Linkedin Assistant: {e}")
                    if not self.subprocess_stop_event.is_set():
                        logger.info(f"Service will retry in {self.retry_delay} seconds...")
                        await asyncio.sleep(self.retry_delay)
                    else:
                        break

        try:
            self.loop.run_until_complete(service_main())
        finally:
            self.cleanup()

    def SvcDoRun(self):
        """
        Run the Linkedin Assistant as a Windows Service.
        """
        try:
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, '')
            )
            self.run()
        except Exception as e:
            logger.error(f"Service failed to run: {e}")
            self.cleanup()

    def SvcStop(self):
        """
        Stop the Linkedin Assistant Windows Service.
        """
        try:
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            # Signal all components to stop
            self.subprocess_stop_event.set()
            win32event.SetEvent(self.stop_event)
            logger.info("Service stop requested.")
        except Exception as e:
            logger.error(f"Error during service stop: {e}")

    def cleanup(self):
        """
        Cleanup the Linkedin Assistant Windows Service.
        """
        try:
            logger.info("Cleaning up service.")
            if self.loop and self.loop.is_running():
                # Cancel all running tasks
                for task in asyncio.all_tasks(self.loop):
                    task.cancel()
                self.loop.stop()
                self.loop.close()

            # Close any open handles
            try:
                win32event.CloseHandle(self.stop_event)
            except Exception:
                pass

            self.ReportServiceStatus(win32service.SERVICE_STOPPED)
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


if __name__ == '__main__':
    """
      Run the Linkedin Assistant as a Windows Service.
    """
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(LinkedinAssistantService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(LinkedinAssistantService)
