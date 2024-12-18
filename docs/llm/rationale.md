
<h2> LLM Modules </h2>

This section contains the documentation for the LLM module. The LLM module is composed of two components:

- The langchain agent, which is the main component, in charge of actually using ChatGPT in order to generate the content.
- The ColBERT agent, which is in charge of the information retrieval part of the LLM module.

In following updates, the structure of the LLM module will be generalized in order to add more
information retrieval methods, and more conversational agents. 


<h3> ColBERT Agent </h3>

ColBERT is a _fast_ and _accurate_ retrieval model, enabling scalable BERT-based search over large text collections in tens of milliseconds.

Our ColBERT agent is based on [colBERT V2](https://github.com/stanford-futuredata/ColBERT), version 0.2.0.
They already include a very detailed documentation, so we will not go into detail here.


<h3> Langchain Agent </h3>

The Langchain agent is based on a langchain Chain for OpenAI models (which will be extended for more models in the future).
It is as well based on two components:
- A chat prompt template consisting on a system prompt and a user prompt.
- A memory, which is injected into the user prompt and stores the historical context of the conversation.


<h4> Chat Prompt Template </h4>

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

Note: When installing this program as a service, Deberta V2 by default will not compile as TorchScript requires the source code to be available.
For this reason, I have added a patch in order to switch @torch.jit.script for @torch.jit._script_if_tracing. The model
will supposedly be slower, but it will work. If you want to use the model in TorchScript, you can remove the patch from the code.

On src/llm/ColBERT/modelling/hf_colbert.py:


```python
def script_method(fn, _rcb=None):
    return fn


def script(obj, optimize=True, _frames_up=0, _rcb=None):
    return obj


import torch.jit
script_method1 = torch.jit.script_method
script1 = torch.jit.script_if_tracing
torch.jit.script_method = script_method
torch.jit.script = script
```

<h2> Langchain Agent Configuration </h2>

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


<h2> ColBERT Agent Configuration </h2>

The configuration file is located in the `llm/ColBERT` folder, and is named `config.json`. It contains the following parameters:

* `k`: The number of documents to retrieve from the index.
* `queries`: The queries to use for the query-document retrieval. This is a list of strings.
* `kmeans_iters`: The number of iterations to use for the k-means clustering algorithm.
* `document_max_length`: The maximum length of the document to index.