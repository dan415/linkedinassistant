
<h2> Langchain Agent </h2>

The Langchain agent is based on a langchain react agent for LLM models. Therefore,
the agent has access to tools.

<h3> About the conversation history </h3>

Each conversation thread is set to match the publication_id of one of the posts. 

For this, we use the method `produce_publication` which receives a publication with the publication id set.
This method also adds int the system prompt and the publication. This system prompt is preserved throughout the
conversation, as the trimming method is configured to maintain the system prompt.

If you are familiar with the `MemorySaver` and `BaseCheckpointSaver` classes (Checkpointer classes) in
LangGraph, what we do is carry out an implementation that achieves the checkpointing but instead of executing
in memory, it does so in MongoDB.

Therefore, all checkpoints are saved seamlessly inside MongoDB inside `checkpoint_writes` and  `checkpoints` 
collections. This way, we can always surf through the different conversations simply defining the parameter to `invoke`:

```json
{"configurable": {"thread_id": "whatever_publication_id"}}
```

*Note that this unrelated to what langchain defines as "long-term memory". This is basic conversation history handling, but 
with the advance of always preserving the state as long as the publication is not published to LinkedIn or discarded.
Upon the publication achieving one of these states, the conversation history is erased from database for storage optimization*

<h3> Response format </h3>
LinkedIn does not allow for Markdown format, but I find that most llms are better at formatting their responses in Markdown. 
So what I do to still be able to write formatted posts is to use a formatter to bold Markdown bold strings as unicode bold characters.

<h3> Multimodal input </h3>
If the model admits multimodal input (text and images domains), you will be able to pass in an image apart from
the text in the messages to the agent. 


<h3> Langchain Agent Configuration </h3>

The configuration file must be contained inside the `config` collection with the field `config_name`: `"llm-conversation-agent"`. It contains the following parameters:

* `max_conversation_length`: The maximum length of the conversation. This is used to limit the memory of the agent at n previous messages.
* `system_prompt_template`: The system prompt template is used in conjunction with the actual post (in json format) in order to generate the content. It gives the model the required instructions
* `tools`: Can be a list combination of any prebuilt langchain agent (that dont require api_keys and are supported by load_tools) + `create_image`. This tool is the implemented form of generating an image and setting it as the post image. The react agent expects the find at least one tool to use, so this list cannot be empty.
* `model_provider`: The chat model provider, can be any supported chat model
* `image_model_provider`: Image model provider, as of now, only `dalle-openai` is supported
* `image_generation_prompt`: Prompt for generating the images
* `trimming_strategy`: Can be one of `token` `message`.
* `apply_unicode_bold`: If set to True, message formatting for changing bold MarkDown strings to unicode bold characters will be used
* `max_tokens`: Max tokens to pass to the model. It is used to trim the conversation history when `trimming_strategy` is set to `token`
* `max_conversation_length`: Number of max allowed messages to be passed to the model. It is used to trim the conversation history when `trimming_strategy` is set to `message`


## About the Brave Search tool:

The Brave Search tool is a tool that allows you to search for information on the web. It is a privacy-focused search engine that does not track your searches. It is built on top of the Brave browser, which is a privacy-focused browser that blocks ads and trackers. The Brave Search tool is a great alternative to other search engines like Google, Bing, and Yahoo, which track your searches and use your data for targeted advertising. The Brave Search tool is open-source and transparent, so you can trust that your searches are private and secure.

1. You need to first log in to https://brave.com/search/api and obtain your api_key.
2. Then, you need to save the api key inside your secrets vault as "BRAVE_API_KEY".
3. Lastly, set the tool: "brave_tool" in the configuration file.
