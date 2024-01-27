

<h2> Manual PDF Input </h2>

This Content Search Engine is used to create posts from papers that you want to force the agent to process. The way to do this would be to add the PDF inside the 
designated input folder. Then, when the Sources Handler runs, it will detect the PDF and will create a post from it. The post will be stored in the pending approval folder.

The agent reads from the input folder, and pass the papers directly to the Adobe PDF Services API. After that, we add the paper content to the json, and index using the ColBert model. 
Then the model is queried with the colbert queries in order to retrieve the meaninful information that we want to use for generating 
the publication later on.

The sources handler will save the post in the pending approval folder, and will move the actual pdf from the input directory to the output directory. This is just 
to keep the input directory clean, and to avoid processing the same pdfs over and over again, and not to delete the pdfs. Also, it serves as 
a method to keep track of the pdfs that have been processed.


<h3> Configuration </h3>

The configuration file is located in the `information/sources/manual_pdfs` folder, and is named `config.json`. It contains the following parametes:


* `minimum_length`: The minimum length of the contents. Papers with content less than this number of characters are filtered out
* `paragraph_min_length`: The minimum length of the paragraphs. Paragraphs with content less than this number of characters are filtered out
* `colbert_max_total`: The maximum number of results to retrieve from the API when using the ColBERT model.
* `colbert_queries`: A list of queries to search for when using the ColBERT model. The queries are used to make the searches against the indexes created by ColBert
* `input_directory`: The directory where the PDFs to be processed are located.
* `output_directory`: The directory where the PDFs that have been processed are moved to.



