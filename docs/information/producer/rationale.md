

<h2>Publications Handler</h2>

This class is responsible for handling the publications. It is responsible for the following:

1. Walk the publications_directory
2. Process the publication, generating a publication idea using the LLM Module.
3. Save the publication inside `publications` collection with state `DRAFT`

It uses the `information` config document in the `config` collection in MongoDB

