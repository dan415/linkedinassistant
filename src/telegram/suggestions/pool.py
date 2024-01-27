import logging
import os
import pickle
from functools import wraps
import json

from src.utils.log_handler import TruncateByTimeHandler

PWD = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(PWD, "..", "..", ".."))
FILE = os.path.basename(__file__)
LOGGING_DIR = os.path.join(PROJECT_DIR, "logs") if os.name != 'nt' else os.path.join(r"C:\\", "ProgramData", "linkedin_assistant", "logs")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

handler = TruncateByTimeHandler(filename=os.path.join(LOGGING_DIR, f'{FILE}.log'), encoding='utf-8', mode='a+')
logger.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter(f'%(asctime)s - %(name)s - {__name__} - %(levelname)s - %(message)s'))
logger.addHandler(handler)
config_dir = os.path.join(r"C:\\", "ProgramData", "linkedin_assistant", "telegram", "suggestions", "config.json") if os.name == 'nt' else os.path.join(PWD, "config.json")

def stateful(func):
    """
    Decorator to update the config file after the execution of the function.
    :param func: function to decorate
    :return: decorated function
    """
    @wraps(func)
    def update_config(self, *args, **kwargs):
        self.update()
        result = func(self, *args, **kwargs)
        config = {}
        with open(config_dir, "w") as f:
            config["pool"] = [suggestion.to_dict() for suggestion in self.pool]
            if self.current:
                config["current"] = self.current.to_dict()
            else:
                config["current"] = None

            json.dump(config, f, default=str, indent=4)

        return result

    return update_config


class Suggestion:

    """
    Suggestion class. It is used to store the suggestions in the pool.
    It just stores the id, which would be the index and the path to the file.

    The get_content method is used to get the content of the suggestion, which needs to be loaded from the pickle
    """

    def __init__(self, id, path):
        self.id = id
        self.path = path

    def get_content(self):
        """
        Get the content of the suggestion. It is the last message of the conversation.
        :return: content of the suggestion
        """
        with open(self.path, "rb") as f:
            memory = pickle.load(f)
        return memory.chat_memory.messages[-1].content

    def __str__(self):
        """
        String representation of the suggestion. It is the content of the suggestion. This way I can represent
        a suggestion as string, which is convenient and easy to read.
        :return:
        """
        return f"{self.get_content()}"


    @classmethod
    def from_dict(cls, dict):
        """
        Factory method to create a suggestion from a dictionary.
        :param dict: dictionary with the suggestion, it needs to be in the form of
                     {"id": id, "path": path}. I could have achieved this passing them as kwargs but this is more
                     fun to write :) and it is more explicit and easy to read.
        :return:
        """
        if not dict:
            return None
        return cls(dict.get("id"), dict.get("path"))

    def to_dict(self):
        """
        Convert the suggestion to a dictionary.

        The idea is to be able to save the suggestion in a json file, so that it can be loaded later.
        :return: dictionary with the suggestion
        """
        return {"id": self.id, "path": self.path}


class SuggestionPool:
    """

    Suggestion pool. It is used to store the suggestions. It is a list of suggestions. It basically handles the loading of
    suggestions, saving of suggestions, and the ordering of the pool. Although called pool, it is actually a circular list of
    suggetions.

    """
    def __init__(self):
        """
        Initialize the suggestion pool. It loads the suggestions from the pending_approval directory.
        """
        self.pool = list()
        self.base_path = os.path.join(PROJECT_DIR, "res", "pending_approval")
        self.current = None

    def reload_config(self):
        """Reload the configuration."""
        logger.debug("Reloading config")
        with open(config_dir, "r") as f:
            config = json.load(f)

        self.pool = [Suggestion.from_dict(suggestion) for suggestion in config.get("pool")]
        self.current = Suggestion.from_dict(config.get("current"))
        if self.current not in self.pool:
            self.current = None

    @stateful
    def add(self, suggestion):
        """
        Add a suggestion to the pool.
        :param suggestion: suggestion to add
        :return:
        """
        if suggestion not in self.pool:
            self.pool[suggestion.id] = suggestion

    def append(self, suggestion):
        """
        Append a suggestion to the pool. The only difference from add is that this method is not stateful, which can be used
        in a context where the statefulness of it can cause an infinite loop.
        :param suggestion:
        :return:
        """
        if suggestion not in self.pool:
            self.pool.append(suggestion)

    @stateful
    def select(self, id):
        """
        Select a suggestion from the pool. It makes the suggestion the current suggestion.
        :param id: id of the suggestion to select (int)
        :return:
        """
        is_the_same = False
        try:
            tmp = self.pool[id]
            if tmp == self.current:
                is_the_same = True
            self.current = tmp
            return self.current, is_the_same
        except Exception as e:
            logger.error(e)
            return None

    @stateful
    def remove(self, id):
        """
        Remove a suggestion from the pool.
        :param id: id of the suggestion to remove (int)
        :return:
        """
        to_remove = self.pool.pop(id)
        if to_remove == self.current:
            self.current = None

        try:
            os.remove(os.path.join(self.base_path, to_remove.path))
        except Exception as e:
            logger.error(e)

    def __iter__(self):
        """
        Iterator of the pool.
        :return: the pool as iterator
        """
        return iter(self.pool)

    def __len__(self):
        """
        Length of the pool.
        :return: length of the pool
        """
        return len(self.pool)

    @stateful
    def next(self):
        """
        Get the next suggestion in the pool. It is circular, so if the current suggestion is the last one, it will return
        the first one.
        :return: current suggestion, and a boolean indicating if the current suggestion is the same as the next one
        """
        is_the_same = False
        if len(self.pool) == 0:
            self.current = None
        if self.current is None:
            self.current = self.pool[0] if len(self.pool) > 0 else None
        else:
            tmp = self.pool[(self.current.id + 1) % len(self.pool)]
            if tmp == self.current:
                is_the_same = True
            self.current = tmp
        return self.current, is_the_same

    @stateful
    def previous(self):
        """
        Get the previous suggestion in the pool. It is circular, so if the current suggestion is the first one, it will return
        the last one.
        :return: current suggestion, and a boolean indicating if the current suggestion is the same as the previous one
        """
        is_the_same = False
        if len(self.pool) == 0:
            self.current = None
        if self.current is None:
            self.current = self.pool[0] if len(self.pool) > 0 else None
        else:
            tmp = self.pool[(self.current.id - 1) % len(self.pool)]
            if tmp == self.current:
                is_the_same = True
            self.current = tmp
        return self.current, is_the_same

    def update(self):
        """
        Update the pool. It loads the suggestions from the pending_approval directory, and if the current suggestion is not
        in the pool, it sets it to None.

        :return:
        """
        for suggestion in os.listdir(self.base_path):
            if suggestion not in self.pool:
                self.append(Suggestion(len(self.pool), os.path.join(self.base_path, suggestion)))

        if self.current and self.current not in self.pool:
            self.current = None

        if self.current is None:
            self.current = self.pool[0] if len(self.pool) > 0 else None
