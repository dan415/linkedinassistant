

<h3> About publications </h3>

One of the main features in V2.0 is the saving of publications in database. One of the main reasons for this
is storing all the history. I figure it could be useful to derive tendencies and some form of recommendation system 
for the type of posts to promote to the user. Therefore, publications can have different `state` in database:

- DRAFT: Publication source content has been extracted but actual publication is yet to be produced
- PENDING_APPROVAL: Publication content has been produced and is available to review by the user
- PUBLISHED: Publication has been published to LinkedIn
- DISCARDED: Publication has been discarded by the user

Other important metadata fields are:
- `last_updated`: Last time the publication was updated in some way
- `creation_date`: Creation datetime
- `image`: Can contain the image bytes encoded in base 64 for the selected publication image

All publications have the field `publication_id`. This ID not only uniquely identifies
the actual post, but also identifies the conversation thread ID used by LangChain's memory saver object
in order to keep track of the different conversations. Therefore, we can have as many different conversations as
publications. 

Normally, LangChain conversations are kept in-memory, and lost after restart of the system, as they are not meant to 
"out-live" a session (except for the long-term memory, which is not related to this). For this use case, we do want to be 
able to recover the conversation and switch in between them as long as the publication has not been either published or discarded.
So, our agent will always have the last messages available as context for the publication that we are working with at the moment.

For managing posts, we use the PublicationsIterator class in order to perform CRUD operations on them, and to be able
to access them in a **circular linked list** manner.