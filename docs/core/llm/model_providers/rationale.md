

<h2>Model Configurations</h2>

Model configurations stored in the database are basically composed of two components: the `config_name` and the `config_schema`. The `config_name` is a string that identifies the configuration, while the rest of 
the document is the configuration itself and gets passed during the initialization of the model. Therefore, the configuration 
parameters are either keyword arguments for the model intialization or invocation.

The config-name is used to identify the necessary python module and class. It can have
2 parts separated by a hyphen. The first part is the unique identifier part of the configuration. The second part is the
provider of the configuration. For example, `mini` is the unique identifier and `chat-openai` is the provider.

Available models are:

- chat-openai: OpenAI chat model
- chat-google: Google chat model
- chat-groq: Groq Chat model
- embeddings-openai: Embeddings OpenAI Gen AI class
- embeddings-google: Embeddings Google Gen AI class
- google: Base Google Gen AI class. Only suitable for completions API
- openai: Base OpenAI class. Only suitable for completions API
- dalle-openai: DALL-E OpenAI class (Langchain Wrapper)
- chat-custom: Uses Chat OpenAI as well

Note: *chat-custom* is another alias for *chat-openai*. As OpenAI was the first chat model implemented, other providers 
follow the same standard, making it possible to use the same module for different providers.

chat custom only requires two additional parameters are passed:
- *base_url*: The URL of the chat model
- *api_key*: The name of the API key secret in the vault

Here is an example of a model configuration: 

```json
  {
    "config_name": "mini-chat-openai",
    "temperature": {
      "$numberDouble": "0.5"
    },
    "model_name": "gpt-4o-mini",
    "top_p": {
      "$numberInt": "1"
    },
    "frequency_penalty": {
      "$numberDouble": "0.0"
    },
    "presence_penalty": {
      "$numberDouble": "0.0"
    }
  }

```
