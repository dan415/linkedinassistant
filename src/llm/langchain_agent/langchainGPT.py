import json
import logging
import os
import pickle

from langchain.prompts.chat import (
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain.chains import LLMChain
from langchain.llms.openai import OpenAI
from langchain.memory import ConversationBufferMemory
from langchain.prompts import ChatPromptTemplate
from langchain_community.chat_models import ChatOpenAI

from src.utils.log_handler import TruncateByTimeHandler

PWD = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(PWD, '..', "..", ".."))
LOGGING_DIR = os.path.join(PROJECT_DIR, "logs") if os.name != 'nt' else os.path.join(r"C:\\", "ProgramData", "linkedin_assistant", "logs")
FILE = os.path.basename(__file__)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = TruncateByTimeHandler(filename=os.path.join(LOGGING_DIR, f'{FILE}.log'), encoding='utf-8', mode='a+')
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter(f'%(asctime)s - %(name)s - {__name__} - %(levelname)s - %(message)s'))
logger.addHandler(handler)
config_dir = os.path.join(r"C:\\", "ProgramData", "linkedin_assistant", "llm",  "langchain_agent", "config.json") if os.name == 'nt' else os.path.join(PWD, "config.json")

def generate_process_document_template(prompt_dict):
    """Generate the process document template. Needed to generate the format string for the process document prompt

    :param prompt_dict:  dictionary with the prompt
    :return:  template string
    """
    template = ""
    for key in prompt_dict.keys():
        template += f" {key}: {prompt_dict[key]}"
    return template


class LangChainGPT:

    """
    LangChain GPT agent. It is a wrapper of the LLMChain class. It is used to interact with the LLMChain class.

    I made it so that the conversation can be pickled and saved, so that the conte
    """

    def __init__(self):
        self.openai_configs = None
        self.system_prompt_template = ""
        self.human_message_template = ""
        self.prompt = None
        self.conversation = None
        self.questions_template = ""
        self.max_conversation_length = 2
        self.memory = ConversationBufferMemory(memory_key="chat_history", input_key="input")
        self.reload_config()

    def get_last_message(self):
        """
        Return the last message of the conversation.

        :return: last message of the conversation
        """
        try:
            return self.memory.chat_memory.messages[-1].content
        except Exception as e:
            logger.error(e)
            return None

    def save_memory(self, path):
        """
        Save the memory to a pickle. The memory is the conversation history. That way the conversation context can be retrieved
        easily
        :param path:  path to save the memory
        """
        logger.info("Saving memory")
        with open(path, "wb") as f:
            pickle.dump(self.memory, f)

    def load_memory(self, path):
        """
        Load the memory from a pickle. The memory is the conversation history.
        :param path:  path to load the memory

        """
        logger.info("Loading memory")
        with open(path, "rb") as f:
            self.memory = pickle.load(f)
        self.reload_config()

    def trim_memory(self):
        """
        Trim the memory to the last two messages. This is done to avoid the memory to grow too much.

        """
        messages = self.memory.chat_memory.messages[-2:]
        self.memory.chat_memory.messages = messages

    def build_chat_prompt_template(self, prompt_dict: dict = None, use_system_prompt=True):
        """
        Build the chat prompt template. It is used to build the prompt for the LLMChain class.
        :param prompt_dict: dictionary with the prompt template fields
        :param use_system_prompt: whether to use the system prompt or not
        :return: chat prompt template
        """
        messages = []
        if use_system_prompt:
            messages.append(SystemMessagePromptTemplate.from_template(self.system_prompt_template))
        if prompt_dict is None:
            human_prompt = HumanMessagePromptTemplate.from_template(self.human_message_template)
        else:
            prompt_dict.update({"input": ""})
            template = generate_process_document_template(prompt_dict)
            human_prompt = HumanMessagePromptTemplate.from_template(template)
        messages.append(human_prompt)
        return ChatPromptTemplate(
            messages=messages
        )

    def call(self, prompt_dict=None, input="", use_system_prompt=True):
        """
        Call the LLMChain class. It is used to interact with the LLMChain class.
        :param prompt_dict: dictionary with the prompt template fields
        :param input: input to the LLMChain class
        :param use_system_prompt: whether to use the system prompt or not
        :return: Chat Response
        """
        try:
            self.trim_memory()
            self.conversation.prompt = self.build_chat_prompt_template(prompt_dict, use_system_prompt=use_system_prompt)
            if prompt_dict is None:
                prompt_dict = {}
            prompt_dict.update({"input": input})
            return self.conversation.predict(**prompt_dict)
        except Exception as e:
            logger.error(e)
            return str(e)



    def reload_config(self):
        """Reload the configuration."""
        logger.debug("Reloading config")
        with open(config_dir, "r") as f:
            config = json.load(f)

        for key in config.keys():
            if key == "environment":
                for env_key in config[key].keys():
                    os.environ[env_key] = config[key][env_key]
            else:
                self.__setattr__(key, config[key])

        self.prompt = ChatPromptTemplate(
            messages=[
                SystemMessagePromptTemplate.from_template(self.system_prompt_template),
                HumanMessagePromptTemplate.from_template(self.human_message_template),
            ]
        )
        self.conversation = LLMChain(
            llm=ChatOpenAI(**self.openai_configs if self.openai_configs else {}),
            prompt=self.prompt,
            verbose=False,
            memory=self.memory,

        )
