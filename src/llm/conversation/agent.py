import base64
import copy
import json
import os
import uuid
from langchain.agents import load_tools
from langchain_core.messages import trim_messages
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
import openai
import groq
from pymongo import MongoClient
from retry import retry

from src.core.config.manager import ConfigManager
from src.core.constants import SecretKeys
from src.llm.conversation.checkpointer import MongoDBSaver
from src.core.utils.functions import get_logger, is_function, get_function_by_name, boldify_unicode
from src.core.vault.hvault import VaultClient
from src.llm.provider import LLMProvider, LLM

FILE = os.path.basename(__file__)
logger = get_logger(dump_to=FILE)




class LangChainGPT:
    """
    LangChain GPT agent with ReAct and memory. It manages conversation history and uses ReAct reasoning.
    """
    _CONFIG_SCHEMA = "llm-conversation-agent"

    def __init__(self):
        self.tools = []
        self.agent = None
        self.llm = None
        self.memory = None
        self.model_provider = None
        self.image = None
        self.system_prompt_template = ""
        self.image_generation_prompt = ""
        self.conversation_id = None
        self.apply_unicode_bold = True  # If True, will substitute markdown bold for unicode bold characters
        self.max_conversation_length = None
        self.max_tokens = None
        self.trimming_strategy = None
        self.vault_client = VaultClient()
        self.config_client = ConfigManager()
        self.reload_config()

    def reload_config(self):
        """Reload the configuration."""
        logger.debug("Reloading config")

        config = self.config_client.load_config(self._CONFIG_SCHEMA)
        for key in config.keys():
            self.__setattr__(key, config[key])

        self.memory = MongoDBSaver(
            MongoClient(self.vault_client.get_secret(SecretKeys.MONGO_URI)),
            db_name=self.vault_client.get_secret(SecretKeys.MONGO_DATABASE)
        )
        self.llm = LLMProvider.build(self.model_provider)
        self._load_tools()
        self.agent = create_react_agent(
            self.llm,
            tools=self.tools,
            state_modifier=self.memory_trimmer,
            checkpointer=self.memory

        )

    @tool
    def generate_image(self, image_description):
        """
        Used to integrate with Dall-E 3 to generate an image
        :param image_description: Brief and relevant image description extracted from user input
        :return: Whether the operation was successful or not
        """
        try:
            dalle_model = LLMProvider.build(LLM.DALLE3_OPENAI)
            prompt = self.image_generation_prompt.format(description=image_description)
            self.image = dalle_model.images.generate(prompt=prompt, n=1, response_format="b64_json").data[0].b64_json
            return "Image generated succesfully, it will be displayed to the user"
        except Exception as ex:
            self.image = None
            logger.error(ex)
            return f"I could not generate an image due to {ex}"

    def _load_tools(self):
        tools_str = copy.deepcopy(self.tools)
        self.tools = []
        builtin_tools = []
        for tool in tools_str:
            if is_function(tool, obj=self):
                self.tools.append(get_function_by_name(tool, obj=self))
            else:
                builtin_tools.append(tool)
        if builtin_tools:
            self.tools.extend(load_tools(builtin_tools))

    @retry(delay=60, jitter=20, max_delay=120, tries=3, logger=logger,
           exceptions=(groq.RateLimitError, openai.RateLimitError))
    def __invoke(self, messages):
        if not self.conversation_id:
            self.conversation_id = str(uuid.uuid4())
        return self.agent.invoke(messages, {"configurable": {"thread_id": self.conversation_id}})

    def _format_response(self, messages):
        response = messages["messages"][-1].content
        return boldify_unicode(response) if self.apply_unicode_bold else response

    def produce_publication(self, publication: dict):

        if not self.conversation_id:
            self.conversation_id = publication["publication_id"]

        inputs = {"messages": [
            ("system", self.system_prompt_template),
            ("user", json.dumps(publication))
        ]}
        return self._format_response(self.__invoke(inputs))

    def memory_trimmer(self, state):
        if self.trimming_strategy != "token" and self.trimming_strategy != "message":
            raise ValueError("Trimming Strategy should either be 'token' or 'message'")
        messages = trim_messages(
            messages=state["messages"],
            token_counter=len if self.trimming_strategy == "message" else self.llm,
            strategy="last",
            max_tokens=self.max_conversation_length if self.trimming_strategy == "message" else self.max_tokens,
            start_on="human",
            end_on=("human", "tool"),
            include_system=True,
        )
        logger.debug(messages)
        return messages

    def call(self, input_message: str, images: list = None):
        """
        Call the agent to process the input message.
        :param images:
        :param input_message: The input string for the agent.
        :return: Agent response.
        """
        input_message = [
            {"type": "text", "text": input_message},
        ]
        if images:
            for image in images:
                input_message.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64.b64encode(image).decode('utf-8')}"}
                })
        return self._format_response(self.__invoke({"messages": [("user", input_message)]}))
