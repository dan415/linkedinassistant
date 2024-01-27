

<h2> Sources Handler</h2>

The Sources Handler class is responsible for handling the sources. It is responsible for the following:

1. Run search engines for each source asynchronously and concurrently.
2. Sleep for a specified amount of time between searches.


Supported information sources are loaded from the config.json file. Sources defined in the confif file need
to exist as Enum Items of InformationSource class inside information/sources/information_source.py.
The Enum string value is used in order to load the sources from:

```json
{    
  "active_sources": [
        "medium", "arxiv", "google_news", "manual"
    ]
}
```

Changing this list will change the sources that are loaded.


The output from sources may vary from source to source, but retrieved information is always stored as json inside the publications_directory.
Once they get processed by the Publications handler, they get moved to the pending approval directory.
