import base64
import copy
import json
import logging
import os
import uuid
from typing import Any, Dict, List, Optional, Union
import requests
from langchain_community.agent_toolkits.load_tools import load_tools
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import trim_messages
from langchain_core.tools import Tool
from langgraph.graph.graph import CompiledGraph
from langgraph.prebuilt import create_react_agent
from pymongo import MongoClient
from pydantic import BaseModel, Field
from src.core.config.manager import ConfigManager
from src.core.constants import SecretKeys
from src.core.llm.conversation.checkpointer import MongoDBSaver
import src.core.utils.functions as F
from src.core.utils.logging import ServiceLogger
from src.core.vault.hashicorp import VaultClient
from src.core.llm.provider import LLMProvider


class LangChainGPT:
    """
    LangChain GPT agent with ReAct and memory. It manages conversation history and uses ReAct reasoning.
    """

    _CONFIG_SCHEMA = "llm-conversation-agent"

    def __init__(
            self, logger: logging.Logger = ServiceLogger(__name__)
    ) -> None:
        # Initialize instance variables and load configuration
        self.logger = logger
        self.tools: List[Any] = []
        self.agent: Optional[CompiledGraph] = None
        self.llm: Optional[BaseLanguageModel] = None
        self.memory: Optional[MongoDBSaver] = None
        self.model_provider: Optional[str] = None
        self.image: Optional[bytes] = None
        self.image_model_provider = ""
        self.system_prompt_template: str = ""  # Template for system prompts
        self.image_generation_prompt: str = (
            ""  # Template for image generation prompts
        )
        self.conversation_id: Optional[str] = (
            None  # Unique ID for each conversation
        )
        self.apply_unicode_bold: bool = True  # Flag to toggle bold formatting
        self.max_conversation_length: Optional[int] = None
        self.max_tokens: Optional[int] = None
        self.trimming_strategy: Optional[str] = None

        # I first tried adding the @tool decorator over the method, which seemed neater.
        # However, doing that makes the method turn into a structured tool object BEFORE instantiating the class.
        # Therefore, the actual method gets loaded in as an unbound method. Can't think of way to get the agent to be
        # able to pass in the self argument, so I forced the method to be loaded during class instantiation,
        # which works as intended :)
        self.bound_tools = [
            Tool(
                name="create_image",
                func=self.generate_image,
                description="Used to integrate with Dall-E 3 to generate an image",
                args_schema=self.ImageGenerationInput,
            )
        ]

        self.vault_client: VaultClient = (
            VaultClient()
        )  # Initialize VaultClient for secrets
        self.config_client: ConfigManager = (
            ConfigManager()
        )  # Initialize ConfigManager
        self.reload_config()  # Load initial configuration

    class ImageGenerationInput(BaseModel):
        image_description: str = Field(
            description="A brief and detailed description of the image to generate."
        )

    def reload_config(self) -> None:
        """Reload the configuration."""
        self.logger.debug("Reloading config")

        # Load configuration schema and set attributes dynamically
        config: Dict[str, Any] = self.config_client.load_config(
            self._CONFIG_SCHEMA
        )
        for key in config.keys():
            self.__setattr__(key, config[key])

        # Set up MongoDB memory saver using secrets from Vault
        self.memory = MongoDBSaver(
            MongoClient(self.vault_client.get_secret(SecretKeys.MONGO_URI)),
            db_name=self.vault_client.get_secret(SecretKeys.MONGO_DATABASE),
        )

        # Initialize the LLM provider and tools
        self.llm = LLMProvider.build(self.model_provider)
        self._load_tools()

        # Create a ReAct agent with the configured tools and memory
        self.agent = create_react_agent(
            self.llm,
            tools=self.tools,
            state_modifier=self.memory_trimmer,
            checkpointer=self.memory,
        )

    def generate_image(self, image_description: str) -> str:
        """
        Used to integrate with Dall-E 3 to generate an image
        :param image_description: Brief and relevant image description extracted from user input
        :return: Whether the operation was successful or not
        """
        try:
            self.logger.info("Generating image")
            image_model = LLMProvider.build(self.image_model_provider)
            prompt: str = self.image_generation_prompt.format(
                description=image_description
            )
            image_urls = image_model.run(prompt)
            image_url = image_urls.split("\n")[0]
            result = requests.get(image_url, stream=True)
            self.logger.info(
                f"Tried to get image from url {image_url} with result {result.status_code}"
            )
            result.raise_for_status()
            self.image = result.content
            return (
                "Image generated successfully, it will be displayed to the user"
            )
        except Exception as ex:
            # Log errors and return failure message
            self.image = None
            self.logger.error(ex)
            return f"I could not generate an image due to {ex}"

    def brave_tool(self):
        """
        Tool to interact with Brave Search
        :return: BraveSearch instance
        """
        from langchain_community.tools import BraveSearch
        return BraveSearch.from_api_key(
            api_key=self.vault_client.get_secret(SecretKeys.BRAVE_API_KEY),
            search_kwargs={"count": 3}
        )

    def _load_tools(self) -> None:
        """Load tools dynamically based on configuration."""
        tools_list = copy.deepcopy(self.tools)
        self.tools = []
        builtin_tools: List[Any] = []

        # Separate custom and built-in tools
        for tool in tools_list:
            for bound_tool in self.bound_tools:  # methods as tools
                if tool == bound_tool.name:
                    self.tools.append(bound_tool)
                    break
            else:
                if F.is_function(tool, obj=self):  # other functions as tools
                    self.tools.append(F.get_function_by_name(tool, obj=self))
                else:
                    builtin_tools.append(tool)  # built-in tools

        # Load built-in tools
        if builtin_tools:
            self.tools.extend(load_tools(builtin_tools))

    def __invoke(self, messages: Dict[str, Any]) -> Union[dict[str, Any], Any]:
        """Invoke the ReAct agent with the given messages.

        :param: The input data for the graph.
        :returns: The output of the graph run. If stream_mode is "values", it returns the latest output.
            If stream_mode is not "values", it returns a list of output chunks.
        """
        # Ensure the conversation ID is set
        if not self.conversation_id:
            self.conversation_id = str(uuid.uuid4())

        return self.agent.invoke(
            messages, {"configurable": {"thread_id": self.conversation_id}}
        )

    def _format_response(self, messages: Dict[str, Any]) -> str:
        """Format the agent's response for output.

        :param: The input data for the graph.
        :returns: The unicode-bolded content response if 'self.apply_unicode_bold' is True else just the
        content response
        """
        response: str = messages["messages"][-1].content
        # Apply bold formatting if enabled
        return (
            F.boldify_unicode(response) if self.apply_unicode_bold else response
        )

    def produce_publication(self, publication: Dict[str, Any]) -> str:
        """Generate a response based on a publication input.

        :param: The publication dictionary as stored in MongoDB (Needs to be serializable though)

        :returns: The formatted produced publication content
        """
        # Use publication ID as conversation ID if not already set
        self.conversation_id = publication["publication_id"]
        publication_cp = copy.deepcopy(publication)
        publication_cp.pop("image", None)

        # Prepare input messages and invoke the agent
        inputs: Dict[str, Any] = {
            "messages": [
                ("system", self.system_prompt_template),
                ("user", json.dumps(publication_cp)),
            ]
        }
        return self._format_response(self.__invoke(inputs))

    def memory_trimmer(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Trim conversation memory based on the configured strategy.

        :param: The state of the graph

        :returns: The trimmed list of messages
        """
        if (
                self.trimming_strategy != "token"
                and self.trimming_strategy != "message"
        ):
            raise ValueError(
                "Trimming Strategy should either be 'token' or 'message'"
            )

        # Trim messages based on the strategy and limits
        messages = trim_messages(
            messages=state["messages"],
            token_counter=(
                len if self.trimming_strategy == "message" else self.llm
            ),
            strategy="last",
            max_tokens=(
                self.max_conversation_length
                if self.trimming_strategy == "message"
                else self.max_tokens
            ),
            start_on="human",
            end_on=("human", "tool"),
            include_system=True,
        )
        # Log the size of the trimmed messages for monitoring and debugging
        self.logger.debug(f"Trimmed messages size: {len(messages)}")
        self.logger.debug(messages)
        return messages

    def call(
            self, input_message: str, images: Optional[List[bytes]] = None
    ) -> str:
        """
        Call the agent to process the input message.
        :param input_message: The input string for the agent.
        :param images: Optional list of images as input.

        :return: Agent response.
        """
        # Construct input message payload
        input_message_payload: List[Dict[str, Any]] = [
            {"type": "text", "text": input_message},
        ]

        # Add image inputs if provided
        if images:
            for image in images:
                input_message_payload.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64.b64encode(image).decode('utf-8')}"
                        },
                    }
                )

        # Invoke the agent and return the formatted response
        return self._format_response(
            self.__invoke({"messages": [("user", input_message_payload)]})
        )
