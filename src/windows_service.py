import threading
import time
from src.core.constants import SERVICE_NAME
import sys
import servicemanager
import win32event
import win32service
import win32serviceutil
from src import main
from src import logger


class LinkedinAssistantService(win32serviceutil.ServiceFramework):
    """
    LinkedIn Assistant Windows Service class. It is used to run the LinkedIn Assistant as a Windows Service.
    """
    _svc_name_ = SERVICE_NAME
    _svc_display_name_ = 'Linkedin Assistant'
    _svc_description_ = 'Linkedin Assistant'
    _svc_start_type_ = win32service.SERVICE_AUTO_START

    def __init__(self, args):
        """
        Initialize the LinkedIn Assistant Windows Service.

        :param args: Command-line arguments passed to the service.
        """
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.stop_signal = threading.Event()
        self.retry_delay = 60  # Retry after 60 seconds on failure
        self.max_retries = 10  # Maximum number of retries
        self.worker_thread = None

    def GetAcceptedControls(self):
        result = win32serviceutil.ServiceFramework.GetAcceptedControls(self)
        result |= win32service.SERVICE_ACCEPT_PRESHUTDOWN
        return result

    def run(self):
        """
        Run the LinkedIn Assistant service in a threaded environment.
        """
        logger.info("Starting service.")

        def service_worker():
            """
            Worker function to run the main logic of the service in a thread.
            """
            retries = 0
            while not self.stop_signal.is_set() and retries < self.max_retries:
                try:
                    logger.info("Running Linkedin Assistant.")
                    main.run(self.stop_signal)
                except Exception as e:
                    logger.error(f"Error in Linkedin Assistant: {e}")
                    retries += 1
                    if retries >= self.max_retries:
                        logger.error("Maximum retries reached. Exiting service.")
                        break
                    if not self.stop_signal.is_set():
                        logger.info(
                            f"Service will retry in {self.retry_delay} seconds "
                            f"(Attempt {retries}/{self.max_retries})...")
                        time.sleep(self.retry_delay)

        self.worker_thread = threading.Thread(target=service_worker, daemon=True)
        self.worker_thread.start()

    def SvcDoRun(self):
        """
        Entry point for the service.

        This method is called by the Windows Service Manager to start the service and manage its lifecycle.
        """
        try:
            logger.info("Reporting State Running")
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, '')
            )

            self.run()

            win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)
        except Exception as e:
            logger.error(f"Service failed to run: {e}")
            self.cleanup()

    def SvcStop(self):
        """
        Stop the LinkedIn Assistant service.

        This method signals all running components to terminate and reports the service as stopping.
        """
        try:
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            # Signal all components to stop
            self.stop_signal.set()
            win32event.SetEvent(self.hWaitStop)
            logger.info("Service stop requested.")
            if self.worker_thread and self.worker_thread.is_alive():
                self.worker_thread.join()
        except Exception as e:
            logger.error(f"Error during service stop: {e}")

    def cleanup(self):
        """
        Perform cleanup operations for the service.

        Ensures handles are released and the service status is reported as stopped.
        """
        try:
            logger.info("Cleaning up service.")
            self.ReportServiceStatus(win32service.SERVICE_STOPPED)
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STOPPED,
                (self._svc_name_, '')
            )
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


if __name__ == '__main__':
    """
    Main entry point for the service.

    If called without arguments, it initializes the service. Otherwise, it handles command-line arguments for
    installing or removing the service.
    """
    if len(sys.argv) == 1:
        logger.info("Starting service without arguments")
        servicemanager.Initialize()
        logger.info("Preparing to host service")
        servicemanager.PrepareToHostSingle(LinkedinAssistantService)
        logger.info("Dispatching")
        servicemanager.StartServiceCtrlDispatcher()
    else:
        logger.info("Handling command line")
        win32serviceutil.HandleCommandLine(LinkedinAssistantService)
