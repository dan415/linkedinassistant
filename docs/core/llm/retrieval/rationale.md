
<h2> Langchain Agent </h2>

The Langchain agent is based on a langchain Chain for OpenAI models (which will be extended for more models in the future).
It is as well based on two components:
- A chat prompt template consisting on a system prompt and a user prompt.
- A memory, which is injected into the user prompt and stores the historical context of the conversation.

<h2> Algorithm </h2>

This algorithm is implemented as a langGraph workflow:

1. START: Begin the workflow.

2. Split Text:
- Input: Full text.
- Process: Split the input text into smaller, manageable chunks with overlap for context preservation.
- Output: List of text chunks.

3. Create Documents:
- Input: List of text chunks.
- Process: Convert each chunk into a Document object with metadata (e.g., chunk order).
- Output: List of Document objects. 

4. Summarize Documents:
- Input: List of Document objects.
- Process: Use a language model to summarize the documents, combining partial summaries into a cohesive one.
- Output: Document summary (string).

5. Generate Terms:
- Input: Document summary.
- Process: Generate a list of key terms or questions derived from the summary using a language model.
- Output: List of terms or questions. 

6. Create Vector Store:
- Input: List of Document objects.
- Process: Build a vector store using embeddings for efficient similarity searches.
- Output: Vector store (e.g., Chroma). 

7. Retrieve Relevant Chunks:
- Input: Vector store, list of terms or questions.
- Process: Perform similarity search for each term/question and retrieve relevant text chunks.
- Output: List of relevant text chunks. 

8. Answer Questions:
- Input: Relevant text chunks, list of terms or questions. 
- Process: Use a language model to generate answers for each question based on the relevant chunks.
- Output: List of Q&A pairs (questions and their corresponding answers).

9. Format Dialog:
- Input: List of Q&A pairs.
- Process: Format the questions and answers into a structured, readable dialog.
- Output: Formatted Q&A dialog (string).

10. Extract Title:
- Input: Full text or summary.
- Process: Extract the document's title using a language model.
- Output: Extracted title (string).

11. END: The workflow completes.
- Final Outputs
- Formatted Q&A Dialog: A structured conversation summarizing the document.
- Extracted Title: A concise title representing the document’s content.


<h3> Langchain Agent Configuration </h3>

The configuration file must be contained inside the `config` collection with the field `config_name`: `"llm-retrieval-langchain"`. It contains the following parameters:

* `chunk_size`: chunk size for text splits used in the `RecursiveCharacterTextSplitter`
* `chunk_overlap`: chunk overlapping in between text splits used in the `RecursiveCharacterTextSplitter`
* `embeddings_provider`: embedding model configuration defined in `configs`
* `model_provider`: **instruct or base** model configuration defined in `configs`
* `query_expansion_prompt`: this prompt utilizes the text summary in order to produce n relevant questions about the text for building an article. The generated questions are then used for the semantic search algorithm
* `answer_prompt`: This prompt uses each generated question and the returned relevant chunks of text from the vector search in order to respond to the question
* `title_extraction_prompt`: This prompt takes the first chunk of text and tries to extract or infer the title for the source
* `n_chunk_results`: chunks to return for each semantic search for each of the questions


*Note: Most of the prompt templates are formatted strings and are to be completed dynamically, if wanting to edit the prompts, the 
text within `{}` must not be removed from the string.*
