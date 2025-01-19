
<h2> Information Searching Component</h2>

This module is responsible for searching for information using different sources.

<h3> Sources </h3>

The following sources are currently supported:

* Arxiv
* Google News
* Medium
* Youtube urls
* Inputted PDFS (from a directory)


The sources are handled by Sources Handler class. I intent to extend the sources to many more, and it is very easy to add 
more sources, thanks to the modular design of the program.

**Key aspects**
- All sources store their configurations in database. They get initialized before starting
the search algorithm, and after the execution is done, the current configuration is updated with the values for 
the keys stored within the source object.
- For a content to be considered as publication, the content must exceed the `minimum_length`.
- The search algorithm is run every `period` days, relative to `period_datetime`.



<h3> Configuration </h3>

The configuration file must be contained inside the `config` collection with the field `config_name`: `"information"`. The following parameters are available:

* `active_sources`: A list of strings containing the names of the sources to be loaded. The names must match the Enum string values of the InformationSource class.
* `execution_period`: Time on days between executions. This is used by the Source Handler class.
* `sleep_time`: Number of execution periods to wait between searches. Only used by Source Handler class.
* `process_sleep_time`: The time in seconds to wait between processes. Only used by Publications Handler class.
* `last_run_time`: The last time the program was run. This is used to calculate the time elapsed since the last run, and to determine if the program should run again.
* `one_by_one`: If set to true, the program will run the sources one by one, instead of running them concurrently. This is useful for debugging purposes.
* `active`: If set to false, the program will not run. This is useful for debugging purposes.
* `publications_collection`: Name of the collection in Mongo DB that stores the publications