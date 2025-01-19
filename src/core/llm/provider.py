import os
from langchain_core.language_models import BaseLanguageModel
from src.core.config.manager import ConfigManager
from src.core.vault.hashicorp import VaultClient


class LLMProvider:
    _vault_client = VaultClient()
    _config_manager = ConfigManager()
    _RETRY_ATTEMPTS = 3

    LLM_ENGINE_MAP: dict[str, str] = {
        "chat-openai": "langchain_openai.ChatOpenAI",
        "chat-google": "langchain_google_genai.chat_models.ChatGoogleGenerativeAI",
        "chat-groq": "langchain_groq.chat_models.ChatGroq",
        "embeddings-openai": "langchain_openai.OpenAIEmbeddings",
        "embeddings-google": "langchain_google_genai.embeddings.GoogleGenerativeAIEmbeddings",
        "google": "langchain_google_genai.GoogleGenerativeAI",
        "openai": "langchain_openai.OpenAI",
        "dalle-openai": "langchain_community.utilities.dalle_image_generator.DallEAPIWrapper",
        "chat-custom": "langchain_openai.ChatOpenAI"  # Some models can be accesed through ChatOpenAI \
        # if base url and api_key are provided
    }

    @classmethod
    def build(cls, config_name: str) -> BaseLanguageModel:
        """Get an LLM engine instance based on the provider string.

        The provider string must specify two components:
        1. Type (e.g., chat, embeddings, or omit for the base client)
        2. Provider (e.g., openai, groq, googleai)

        :param: config_name (str): The provider string in the format "type-provider".

        :return: An instance of the corresponding LLM engine class.

        :raise ValueError: If the provider string is invalid or unsupported.
        """

        if "-" not in config_name:
            raise ValueError(f"Invalid provider string format: {config_name}. Expected format: 'type-provider'.")

        identifier_and_provider = config_name.split("-", 1)
        if len(identifier_and_provider) != 2:
            raise ValueError(f"Invalid provider string format: {config_name}. Expected format: 'type-provider'.")

        identifier, type_and_provider = identifier_and_provider

        if "-" in type_and_provider:
            provider = type_and_provider.split("-", 1)[1]
        else:
            provider = type_and_provider

        engine_path = cls.LLM_ENGINE_MAP.get(type_and_provider)
        if engine_path is None:
            raise ValueError(f"Provider {provider} is not supported.")

        config = cls._config_manager.load_config(config_name)

        if not config:
            raise ValueError(f"No config found for config name {config_name}")

        # If api_key name provided in config, use that as api_key and pass it as argument, else infer it from provider
        # and set it as argument.This logic is meant for custom providers that can adapt to others providers
        # For example: Deepseek can be accessed using ChatOpenAI class and passing it the deepseek api_key and base_url
        # as arguments. This is also True for groq
        api_key_name = config.pop("api_key", None)
        if api_key_name:
            config["api_key"] = cls._vault_client.get_secret(api_key_name)
        else:
            llm_name = provider.upper()
            api_key_name = f"{llm_name}_API_KEY"
            os.environ[api_key_name] = cls._vault_client.get_secret(api_key_name)

        config = cls._config_manager.load_config(config_name)

        # Dynamically import the specified class
        module_name, class_name = engine_path.rsplit(".", 1)
        module = __import__(module_name, fromlist=[class_name])

        engine_class = getattr(module, class_name)
        engine_object = engine_class(**config)

        return engine_object
