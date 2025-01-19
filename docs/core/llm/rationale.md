<h2> LLM Components </h2>

This section contains the documentation for the LLM module. The LLM module is composed of two components:

- The **langchain agent**, which is the main component, in charge of actually using ChatGPT in order to generate the content.

- The **retrieval agent**, which is in charge of converting the raw and extensive content material from the pdfs
into a relevant context the agent can use in order to create a post. (For shorter sources this step is not used and the content
is fed whole)


Right at the moment, we consider the following LLM options:

- OpenAI (Chat models, base (instruct and Dall-E) models, embedding models)
- Google Gen AI (Chat models, base (instruct) models, embedding models)
- Groq (Chat Models)

Obviously, for models to work you need to have defined their respective API keys inside
the vault secrets. Respectively:

`GROQ_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`

and have installed the dependencies for each one of them, respectively:

`langchain_groq`, `langchain_openai`, `langchain-google-genai`

*NOTE: For image generation, only Dall-E has been tested. Compatibility for other
image generation models from other providers will be ensured in following updates*

The design for constructing different LLM configurations is the following:

`NEW_OPTION = "ALIAS-TYPE-PROVIDER"`

or

`NEW_OPTION = "ALIAS-PROVIDER"`

for base models, meant for instruct operations or image generation models like Dall-E 3


Where ALIAS gives "uniqueness" to the configuration, and must be followed by
a supported provider. As of now, `openai`, `groq` and `google` (Google Gen AI) are supported.

Note: langchain only implements chat models for groq as of now.

Then, we can write into the configuration any parameter that the model accepts, for example:

```json
  {
  "config_name":"mini-chat-openai",
  "temperature":{"$numberDouble":"0.5"},
  "model_name":"gpt-4o-mini",
  "top_p":{"$numberInt":"1"},
  "frequency_penalty":{"$numberDouble":"0.0"},
  "presence_penalty":{"$numberDouble":"0.0"}
}
```

or

```json
  {
  "config_name":"llama3370b-chat-groq",
  "temperature":{"$numberDouble":"0.5"},
  "model_name":"llama-3.3-70b-versatile",
  "top_p":{"$numberInt":"1"}
}
```

or 

```json
    {
  "config_name":"gemini1.5-embeddings-google",
  "model":"models/embedding-001"
  }
```


