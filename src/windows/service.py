import asyncio
import os
import sys
import threading

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', "..")))
import logging
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

import sys
import servicemanager
import win32event
import win32service
import win32serviceutil
from src.main import linkedin_assistant, linkedin_assistant_win


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

    def run(self):
        """
        Run the Linkedin Assistant as a Windows Service.
        :return:
        """
        logger.info("Starting service.")
        while True:
            try:
                if win32event.WaitForSingleObject(self.stop_event, 5000) == win32event.WAIT_OBJECT_0:
                    logger.info("Service stop requested.")
                    break
                logger.info("Running Linkedin Assistant.")
                linkedin_assistant_win.run(self.subprocess_stop_event)
            except Exception as e:
                logger.error(f"Error in Linkedin Assistant: {e}")
                self.stop_event.set()
                break

    def SvcDoRun(self):
        """
        Run the Linkedin Assistant as a Windows Service.
        :return:
        """
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE, servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, ''))
        self.run()

    def SvcStop(self):
        """
        Stop the Linkedin Assistant Windows Service.
        :return:
        """
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.subprocess_stop_event.set()
        win32event.SetEvent(self.stop_event)
        logger.info("Service stop requested.")

    def cleanup(self):
        """
        Cleanup the Linkedin Assistant Windows Service.
        """
        logger.info("Cleaning up service.")
        # Not needed rn
        self.ReportServiceStatus(win32service.SERVICE_STOPPED)


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
