
<h2> Langchain Agent </h2>

The Langchain agent is based on a langchain Chain for OpenAI models (which will be extended for more models in the future).
It is as well based on two components:
- A chat prompt template consisting on a system prompt and a user prompt.
- A memory, which is injected into the user prompt and stores the historical context of the conversation.


<h3> Chat Prompt Template </h3>

As previously said, the chat prompt template is composed of two parts:

- The system prompt: The system instructs the agent to encompass creating engaging posts on relevant news, papers, 
and articles identified by an automated ideas retrieval pipeline. Tasked with an adept writing 
style that consistently captivates readers, the agent receives the pipeline's output, generate initial posts, 
and subsequently undergoes a meticulous review process led by the Data Scientist. This entails a 
collaborative loop where the Data Scientist may either approve, reject, or request changes to the 
post. It is said to it that its proficiency lies in not only crafting attention-grabbing content but also excelling at 
summarizing key article points concisely. Moreover, it is told it specializes in elucidating innovative ideas, 
particularly those related to state-of-the-art techniques. As per the given prompt, it is poised 
to dive into the creation of a post centered around the specified article, applying its unique 
style and expertise to deliver compelling and informative content. All this in the context of being
an assistant for a Data Scientist role. 
- User prompt: The user prompt only contains two placeholders:
  - "chat_history": This placeholder is replaced by the memory of the agent, which is the historical context of the conversation.
  - "input": This placeholder is replaced with the user agent message.

However, when the publications handler goes to generate the first message, which would be the initial post generation, 
a custom prompt template is built from the keys of the json representing the post. Remember that the post is a json at this point.
For example: 

```json
{
  "title": "This is the title",
  "author": "This is the author",
  "date": "This is the date",
  "description": "This is the description",
  "content": "This is the content"
}
```

<h3> Langchain Agent Configuration </h3>

The configuration file is located in the `llm/langchain_agent` folder, and is named `config.json`. It contains the following parameters:

* `environment`:
  * `OPENAI_API_KEY`: The OpenAI API key to use.
  * `OPENAI_API_TYPE`: The OpenAI API type to use. See the OpenAI API documentation for more information.
  * `OPENAI_API_VERSION`: The OpenAI API version to use, e.g: `2020-05-03` is supported.
  * `OPENAI_API_BASE`: The OpenAI API base URL to use, if using Azure Open AI studio, this should be your deployment url
* `openai_configs`: This is a dictionary with whatever the OpenAI class needs to initialize. This is passed directly to the OpenAI class. e.g: model temperature, penalty, etc.
* `max_conversation_length`: The maximum length of the conversation. This is used to limit the memory of the agent at n previous messages.
* `system_prompt_template`: The system prompt template to use. This is the system prompt described in the previous section. This prompt can be safely changed to 
* `human_message_template`: The human message template to use. This is the user prompt described in the previous section. This should not be changed.


