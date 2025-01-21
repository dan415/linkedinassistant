
<h2> Google News </h2>

This Content Search Engine is based on the [Rapid API](https://rapidapi.com/).

This Content Search Engine is used to retrieve information from 
Google News.

<h3> Configuration </h3>

The configuration is located inside the `config` collection the field `config_name`: `"information-sources-rapid-google_news"`. It contains the following parameters:

* `limit`: The maximum number of results to retrieve from the API.
* `url`: The URL of the Rapid API source.
* `host`: The host of the Rapid API source.
* `max_results`: The maximum number of results to retrieve from the API.
* `minimum_length`: The minimum length of the contents. Papers with content less than this number of characters are filtered out
* `count_requests`: An integer counter that keeps track of the number of requests made to the API. This is used to keep track of the number of requests made to the API, and to disable the source when the limit is reached.
* `topics`: A list of topics to search for. Every topic is a "normal" passed to medium's search engine.
* `execution_period`: The period of time in seconds to wait before executing the source again.
* `period_datetime`: The beginning of the last period.
* `last_run_time`: The time of the last execution of the source.
* `period`: The period of time for resetting the counter of requests to the API.


<h3> Algorithm </h3>


1. **Initialization**:
   - Start with a list of topics to search.
   - Prepare an empty list to store all results.

2. **Iterate Over Topics**:
   - For each topic:
     - Create a payload with search parameters (e.g., topic text, region, and maximum results).
     - Make an API request to fetch Google News results.

3. **Process Each Result**:
   - For each result in the API response:
     - Extract and format key fields (e.g., summary, link).
     - Use the `get_text` method to fetch and extract the full article content from the result's URL.
     - Enrich the result with additional metadata (e.g., information source).

4. **Save Processed Results**:
   - If a `save_callback` function is provided:
     - Validate the processed result.
     - Save the result using the callback.

5. **Return Results**:
   - Combine all successfully processed results into a single list.
   - Return the list of results.