

<h3> Adobe PDF module </h3>

This module is used to get the pdf text file. The reason why I use this API instead
of some free library is that this is one of the more accurate libraries I have seen at retrieving
the chapters/sections of a pdf file. It is not perfect, but it is the best I have seen so far.

Note that a PDF is unstructured data, so it is not possible to get the paragraphs of a PDF in one single way

What I do is call the API with the pdf bytes. The API is going to download the results on a file, that I do not want to keep, so I create a TemporaryDirectory and extract the results there.
Then I read the json that's in the Zip and return the chapters. The Temp dir is discarded so I do not need to
worry about deleting the files.

Note that this API has a limit per month, and any attempts will fail if the limit is reached.


<h3> Configuration </h3>

The configuration is stored in a json file named `config.json` inside ./pdf. It has the following format:

```json
{
  "client_credentials": {
    "client_id": "",
    "client_secret": ""
  },
  "service_principal_credentials": {
    "organization_id": ""
  }
}
```

These credentials are obtained from the Adobe Developer Console. More information on the Installation section.

<h3> Extraction </h3>

The extraction process is as follows:

I iterate through the elements of the generated json with the elements of the pdf. For
each element with regex pattern 
```regex
//Document/H1[\[*\]]*
`````

I consider to be a chapter title. For each chapter title, I iterate through the elements, obtaining 
elements with either paragraph pattern:

```regex
//Document/P(\[[\d]*\])?(?:/ParagraphSpan(\[\d]*\])?)?$
```

or bullet point pattern:

```regex
//Document/L*LBody$
```

and append them to the chapter if they are not of length 0.