

<h2> Arxiv </h2>

This Content Search Engine is based on the [Arxiv API](https://arxiv.org/help/api/index). 
The API is used to retrieve the information of the papers, and the search engine is used to index the information and provide a search interface.

It searches papers in the Arxiv API, filtering by by the topics specified in config, including results only from last week and with a set maximum of results.
The Arxiv API returns the papers' metadata in XML format, which is then converted to json. From there, we also download the PDF bytes of the paper
and pass it directly to the Adobe PDF Services API. 

After that, we add the paper content to the json, and index using the ColBert model. Then the model is queried with the colbert queries in order
to retrieve the meaningful information that we want to use for generating the publication later on.

<h3> Configuration </h3>

The configuration file is located inside the `config` collection the field `config_name`: `"information-sources-arxiv"`. It contains the following parametes:

* `max_results`: The maximum number of results to retrieve from the API.
* `url`: The URL of the Arxiv API.
* `minimum_length`: The minimum length of the contents. Papers with content less than this number of characters are filtered out
* `paragraph_min_length`: The minimum length of the paragraphs. Paragraphs with content less than this number of characters are filtered out
* `topics`: A list of topics to search for. The topics are used to filter the results from the API. Only papers that contain at least one of the topics are retrieved.
    Some of these topic codes are:
    - cat:cs.AI: Artificial Intelligence
    - cat:cs.CL: Computation and Language
    - cat:cs.GT: Computer Science and Game Theoryç
    - cat:cs.CV: Computer Vision and Pattern Recognition
    - cat:cs.ET: Emerging Technologies
    - cat:cs.IR: Information Retrieval
    - cat:cs.LG: Machine Learning
    - cat:cs.NE: Neural and Evolutionary Computing
    - cat:cs.PL: Programming Languages
    - cat:cs.RO: Robotics
* `period`: The period of time to search for in days.
* `provider`: Right now it can only be `Langchain-RAG`. This defines the RAG agent used to extract the context that will be used in order to generate publications. ColBert has been deprecated and as of now only Langchain-RAG is supported
* `pdf_extractor_provider`: Can be either `docling` or `pypdf`. More detailed information on the different pdf extractor providers on the pdf section.

<h3> Algorithm </h3>

1. **Build Search Query**:
   - Construct the query URL using:
     - Topics (categories to search for).
     - Time period (date range of interest).
     - Sorting preference (e.g., relevance).
     - Maximum number of results to fetch.

2. **Send API Request**:
   - Perform an HTTP GET request to the Arxiv API using the constructed query URL.
   - If the request fails or returns a non-200 status code, log an error and stop processing.

3. **Extract Metadata**:
   - Parse the XML response using `extract_from_xmls`.
   - Extract metadata for each paper, including title, authors, publication date, summary, and link.

4. **Process Each Paper**:
   - For each extracted paper:
     1. Convert the paper's abstract link to a PDF download link.
     2. Download the PDF file.
     3. Extract text content from the PDF using the `PDFExtractorProvider`.
     4. Use the `DocumentRetrieverProvider` to process the text, identifying important paragraphs.
     5. Append the processed content to the paper's metadata.

5. **Save Valid Results**:
   - If a `save_callback` is provided, validate and save each processed paper.

6. **Return Results**:
   - Compile all successfully processed papers into a single list.
   - Return the list of results.