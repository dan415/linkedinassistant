import os
from enum import Enum
from typing import Type

import src.core.utils.functions as F
from src.core.config.manager import ConfigManager
from src.core.vault.hvault import VaultClient

FILE = os.path.basename(__file__)
logger = F.get_logger(dump_to=FILE)


class LLM(Enum):
    GROQ = "groq"
    CHAT_OPENAI = "chat-openai"
    MINICHAT_OPENAI = "minichat-openai"
    OPENAI = "openai"
    DALLE3_OPENAI = "dalle-openai"
    EMBEDDINGS_OPENAI = "embeddings-openai"





class LLMProvider:
    _vault_client = VaultClient()
    _config_manager = ConfigManager()

    @classmethod
    def build(cls, provider: LLM | str):
        """Get a content search engine for the information source."""
        if isinstance(provider, str):
            provider = F.get_enum_from_value(provider, LLM)

        logger.info("Getting LLM Model engine for %s", provider)

        llm_name = provider.value if "-" not in provider.value else provider.value.split("-")[1]
        key_name = f"{llm_name.upper()}_API_KEY"
        os.environ[key_name] = cls._vault_client.get_secret(key_name)

        config = cls._config_manager.load_config(provider.value)
        if provider == LLM.GROQ:
            from langchain_groq.chat_models import ChatGroq
            return ChatGroq(**config)
        if provider == LLM.CHAT_OPENAI or provider == LLM.MINICHAT_OPENAI:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(**config)
        elif provider == LLM.EMBEDDINGS_OPENAI:
            from langchain_openai import OpenAIEmbeddings
            return OpenAIEmbeddings(**config)
        elif provider == LLM.OPENAI or provider == LLM.DALLE3_OPENAI:
            from langchain_openai import OpenAI
            return OpenAI(**config)
        else:
            raise ValueError(f"Provider {provider} is not supported.")
