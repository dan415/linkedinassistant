
<h2> Medium </h2>

This Content Search Engine is based on the [Rapid API](https://rapidapi.com/).

This Content Search Engine is used to retrieve information from Medium articles.

<h3> Configuration </h3>

The configuration file is located inside the `config` collection the field `config_name`: `"information-sources-rapid-medium"`. It contains the following parameters:

* `limit`: The maximum number of results to retrieve from the API.
* `period`: The period of time to search for in days.
* `url`: The URL of the Rapid API source.
* `host`: The host of the Rapid API source.
* `max_results`: The maximum number of results to retrieve from the API.
* `minimum_length`: The minimum length of the contents. Papers with content less than this number of characters are filtered out
* `count_requests`: An integer counter that keeps track of the number of requests made to the API. This is used to keep track of the number of requests made to the API, and to disable the source when the limit is reached.
* `topics`: A list of topics to search for. Every topic is a "normal" passed to medium's search engine.

<h3> Algorithm </h3>

1. **Initialization**:
   - Start with a list of topics to search.
   - Prepare an empty list to store all results.

2. **Iterate Over Topics**:
   - For each topic:
     - Call the `research_topic` method to fetch related Medium articles.

3. **Research a Topic**:
   - Query Medium's API with the topic to retrieve a list of articles.
   - For each article:
     - Retrieve article metadata using `get_article_info` (e.g., title, subtitle, author, publication date).
     - Fetch the article's content using `get_article_content`.
     - Enrich the article with additional metadata (e.g., information source).
     - Append the processed article to the results list.
     - If a `save_callback` is provided, validate and save the processed article.

4. **Return Results**:
   - Combine all results from processed topics into a single list.
   - Return the list of results.