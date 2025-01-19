
<h2> Rapid Sources </h2>

This Content Search Engine is based on the [Rapid API](https://rapidapi.com/).

This is the base class for each of the rapid sources. All the Rapid API sources
share the same API key. 

For this reason, all Rapid API requests are wrapped with a decorator that retrieves the API Key
and counts the number of API calls. The nº of API calls on the other hand is not shared by the different
Rapid API services, so the `count_requests` field is stored for each one of the rapid API sources.

Therefore, even though all rapid API sources share the same API key, they do not share the same usage limit and calls to
one API servivce do not affect the limit for other services.
