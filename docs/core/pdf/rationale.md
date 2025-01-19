

<h3> PDF module </h3>

This module is used to get the pdf text file. In the prior version I used Adobe PDF Extractor API. However, more often than
not, I would run into API usage limits, so I decided it was not worth it to use it and switched to PyPDF. Recently,
Docling library was released, bringing great capabilities with advanced extraction formats with OCR, from table structures, etc. So 
I wanted to include this as a brand-new option. Therefore, as of now, lightweight and straightforward Pypdf2 method and more complex
and consuming Docling methods are supported.

Arxiv and Manual PDFs search engines take the configuration field `pdf_extractor_provider` which 
can take one of `pypdf` or `docling`.

<h3> Docling Configuration </h3>

The Docling pdf extractor can be further customized in order to select specific functionalities of the library. The document is located inside the `config` collection the field `config_name`: `"docling"`.

```json
  {
  "config_schema":"docling",
  "do_table_structure":true,
  "do_ocr":false,
  "generate_picture_images":true,
  "table_former_mode":"accurate"
}
```

- `do_table_structure`: If set to True, table structures are extracted
- `table_former_mode`: can be either `accurate` or `fast`. If defines the method for extracting table structures 
- `do_ocr`: If set to True, OCR recognition will be performed in order to extract text from images. Useful for scanned pdfs
- `generate_picture_images`: If set to True, images will be extracted and will be available to be selected for the post image

All of these configurations affect content extraction performance and resource utilization. 
