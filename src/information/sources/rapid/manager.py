import json
import os
import threading
from abc import ABC
from dataclasses import dataclass

from src.information.sources.information_source import ContentSearchEngine
import logging

from src.utils.log_handler import TruncateByTimeHandler

PWD = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(PWD, '..', "..", "..", ".." ))
LOGGING_DIR = os.path.join(PROJECT_DIR, "logs") if os.name != 'nt' else os.path.join(r"C:\\", "ProgramData", "linkedin_assistant", "logs")
FILE = os.path.basename(__file__)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = TruncateByTimeHandler(filename=os.path.join(LOGGING_DIR, f'{FILE}.log'), encoding='utf-8', mode='a+')
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter(f'%(asctime)s - %(name)s - {__name__} - %(levelname)s - %(message)s'))
logger.addHandler(handler)



def singleton(class_):
    instances = {}

    def wrapper(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]

    return wrapper


# Seems that rapidapi apis are indepenedent from each other, so they do not need to share the same counter, but I keep
# this code here just in case
# @singleton
# class Counter:
#
#     def __init__(self):
#         self.count_requests = 0
#         self.mutex = threading.Lock()
#
#     def update_count(self, value):
#         with self.mutex:
#             if value > 0:
#                 self.count_requests += value
#             else:
#                 self.count_requests = 0
#
#     def get_count(self):
#         with self.mutex:
#             return self.count_requests
#
#     def set_count(self, value):
#         with self.mutex:
#             self.count_requests = value


class RapidSource(ContentSearchEngine, ABC):
    """
    At the begginnin, I thought that the counter of requests should be shared between all the rapidapi sources, but it seems that
    every api subscription has its own request limit (so I made them inherit from a singleton, so I will leave this code here just in case. Anyhow it serves for any common behaviour
    rapid api sources might share.
    """

    def __init__(self, information_source):
        super().__init__(information_source)
    #     self.count_requests = Counter()
    #     self.count_requests = 0
    #
    # def set_count(self, value):
    #     #self.count_requests.set_count(value)
    #     self.count_requests = value
    #
    # def update_count(self, value):
    #     # self.count_requests.update_count(value)
    #     self.count_requests += value
    #
    #
    # def get_count(self):
    #     # return self.count_requests.get_count()
    #     return self.count_requests
    #
    # def reload_config(self, pwd):
    #     """Reload the configuration."""
    #     logger.info("Reloading config")
    #     with open(os.path.join(pwd, "config.json")) as f:
    #         config = json.load(f)
    #
    #     for key in config.keys():
    #         if key == "count_requests":
    #             count_requests = config.get("count_requests")
    #             self.set_count(max(count_requests, self.get_count()))
    #         else:
    #             self.__setattr__(key, config[key])
    #
    # def save_config(self, pwd):
    #     logger.info("Saving config")
    #     with open(os.path.join(pwd, "config.json"), "r") as f:
    #         config = json.load(f)
    #
    #     for key in config.keys():
    #         for key in config.keys():
    #             if key == "count_requests":
    #                 config[key] = self.get_count()
    #         config[key] = getattr(self, key)
    #
    #     with open(os.path.join(pwd, "config.json"), "w") as f:
    #         json.dump(config, f, default=str, indent=4)
