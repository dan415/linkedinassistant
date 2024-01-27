

<h2> Arxiv </h2>

This Content Search Engine is based on the [Arxiv API](https://arxiv.org/help/api/index). 
The API is used to retrieve the information of the papers, and the search engine is used to index the information and provide a search interface.


It searches papers in the Arxiv API, filtering by by the topics specified in config, including results only from last week and with a set maximum of results.
The Arxiv API returns the papers' metadata in XML format, which is then converted to json. From there, we also download the PDF bytes of the paper
and pass it directly to the Adobe PDF Services API. 

After that, we add the paper content to the json, and index using the ColBert model. Then the model is queried with the colbert queries in order
to retrieve the meaninful information that we want to use for generating the publication later on.

<h3> Configuration </h3>

The configuration file is located in the `information/sources/arxiv` folder, and is named `config.json`. It contains the following parametes:

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
* `colbert_max_total`: The maximum number of results to retrieve from the API when using the ColBERT model.
* `colbert_queries`: A list of queries to search for when using the ColBERT model. The queries are used to make the searches against the indexes created by ColBert

