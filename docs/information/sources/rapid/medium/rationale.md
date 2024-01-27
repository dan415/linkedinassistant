
<h2> Medium </h2>

This Content Search Engine is based on the [Rapid API](https://rapidapi.com/).

This Content Search Engine is used to retrieve information from Medium articles.

<h3> Configuration </h3>

The configuration file is located in the `information/sources/rapid/medium` folder, and is named `config.json`. It contains the following parameters:

* `api_key`: The API key for the Rapid API source.
* `limit`: The maximum number of results to retrieve from the API.
* `period`: The period of time to search for in days.
* `url`: The URL of the Rapid API source.
* `host`: The host of the Rapid API source.
* `max_results`: The maximum number of results to retrieve from the API.
* `minimum_length`: The minimum length of the contents. Papers with content less than this number of characters are filtered out
* `count_requests`: An integer counter that keeps track of the number of requests made to the API. This is used to keep track of the number of requests made to the API, and to disable the source when the limit is reached.
* `topics`: A list of topics to search for. Every topic is a "normal" passed to medium's search engine.
