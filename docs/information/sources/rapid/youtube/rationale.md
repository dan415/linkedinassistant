
<h2> Google News </h2>

This Content Search Engine is based on the [Rapid API](https://rapidapi.com/).

This Content Search Engine is used to retrieve information from Google News.

<h3> Configuration </h3>

The configuration file is located inside the `config` collection the field `config_name`: `"information-sources-rapid-youtube"`. It contains the following parameters:

* `limit`: The maximum number of results to retrieve from the API.
* `period`: The period of time to search for in days.
* `url`: The URL of the Rapid API source.
* `host`: The host of the Rapid API source.
* `minimum_length`: The minimum length of the contents. Papers with content less than this number of characters are filtered out
* `count_requests`: An integer counter that keeps track of the number of requests made to the API. This is used to keep track of the number of requests made to the API, and to disable the source when the limit is reached.

<h3> Algorithm </h3>

The URL pool is made of urls sent by the user through the bot. Whenever the
searching algorithm starts, it executes:

1. Start with the URL pool.
2. For each URL:
    1. Retrieve video metadata. 
    2. Fetch the transcript using an API.
    3.  Download a thumbnail (if possible).
    4. Organize this data into a structured format.
    5. Save the result (if required).
    6.  Pop URL from pool
3. Continue until all URLs in the pool are processed.
