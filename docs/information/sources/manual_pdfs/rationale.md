

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

The configuration file is located inside the `config` collection the field `config_name`: `"information-sources-manual_pdf"`. It contains the following parametes:


* `minimum_length`: The minimum length of the contents. Papers with content less than this number of characters are filtered out
* `paragraph_min_length`: The minimum length of the paragraphs. Paragraphs with content less than this number of characters are filtered out
* `input_directory`: The directory in BlackBlaze B2 where the PDFs to be processed are located. Defaults to `Information/Sources/Manual/Input`
* `output_directory`: The directory in BlackBlaze B2 where the PDFs that have been processed are moved to. Defaults to `Information/Sources/Manual/Output`
* `provider`: Right now it can only be `Langchain-RAG`. This defines the RAG agent used to extract the context that will be used in order to generate publications. ColBert has been deprecated and as of now only Langchain-RAG is supported
* `pdf_extractor_provider`: Can be either `docling` or `pypdf`. More detailed information on the different pdf extractor providers on the pdf section.

<h3> Algorithm </h3>

1. **Initialization**:
   - Authenticate with the B2 storage service using the `pdf_manager`.
   - Retrieve a list of files from the `input_directory` in BlackBlaze B2
   - Filter the files to identify PDFs.

2. **Iterate Over PDFs**:
   - For each PDF in the filtered list:
     1. **Download Content**:
        - Use the `get_pdf_content` method to download the PDF content as raw bytes.
     2. **Extract Information**:
        - Use the `extract_pdf_info` method to extract metadata and relevant content from the PDF.
     3. **Save Valid Content**:
        - If a `save_callback` is provided, validate and save the extracted information.
     4. **Move Processed PDF**:
        - Move the processed PDF file from the `input_directory` to the `output_directory`. (Located in BlackBlaze B2)
        
3. **Return Results**:
   - Combine all successfully processed and extracted content into a single list.
   - Return the list of extracted results.
