
<h2> Telegram Bot</h2>

The idea of this bot is that it will allow to interact with the system from a Telegram client. The bot will allow to
chat with the LLM conversation agent, receive publication suggestions, ask the agent to change the publication drafts, 
discard drafts, and publish them.

The bot is based on the Origami Telegram Bot package, used for building Telegram bots in Python.

In order to be able to circle through conversation threads, the memory pickle of the LLM agents is actually the object that is stored
on the pending for approval directory. These are loaded and maintained in a circular list of suggestions. The bot will then
allow to move forward and backwards through the list of suggestions, and to approve, discard them or change them.

<h3> Publications Pool</h3>

The bot has access to all publications in state `PENDING`, which means that they are eligible for review, posting or otherwise
discarded. The posts are accessed with an iterator that retrieves the posts ordered by `creation_date`. The pool is circular, meaning
that if commands `/last` or `/next` are called on an edge post in the list, the index is set to the contrary edge post in the list.

<H3> Algorithm </H3>

The algorithm is as follows:


While True: 
   1. Check if the bot has just published. If so, wait for suggestion_period days.
   2. Check if suggestions are blocked. If so, wait for 5 minutes in order to check again
   3. If suggestions are not blocked, update the suggestions and check if there are suggestions.
   4. If there are suggestions, send the current suggestion and block suggestions. Then the flow of the program
   is carried by the interaction with the user via Telegram.


<h3> About the messages</h3>

The bot is able to process text messages along with images. If you send a pdf file to the bot, the bot 
will assume you want the pdf to be saved for the manual PDF extraction algorithm, and will be saved in BlackBlaze B2.

<h3> Bot State</h3>

This class is used to store the state of the bot. It is used to store the chat id, the current suggestion, and the
suggestions are blocked or not. For every publication (suggestion) there needs to be a conversation thread.
Via Bot commands I can change the conversation thread, so I can finish "tuning" the publication and then publish it.


As said on the Algorithm section, suggestions can be blocked. This is done in order to avoid the bot to send suggestions
when the user is already interacting with the bot. The bot will send a suggestion, and then block suggestions until the
user has finished interacting with the bot. This is done by setting the `suggestions_blocked` field to True. When the user
finishes interacting with the bot, the `suggestions_blocked` field is set to False, and the bot will send a new suggestion
if there is one available. Also, if the sending of suggestions fails,  suggestions get blocked in order to avoid the bot
sending failing continuously.

The Bot is now designed to respond to one person only. It obviously could respond to whoever sent messages to it, but in order 
to send suggestions (which do not require interaction with the user) it needs to know the chat id of the user. This is why
the bot is designed to respond to one person only. This is the purpose of the `TELEGRAM_CHAT_ID` secret.
It will be first set on `/start` command and it is to remain constant afterwards.


Setting the chat id as a secret makes the solution more robust to unauthorized access to the bot.

The suggestions are in order, so I can go to the next or previous suggestion. I can also select a suggestion by index.
Also, this state also saves information about when to automatically make suggestions, which would be when no suggestion is
selected and after some time after a publication is made. The stateful decorator is used to update the config file after
a function is called, so the file is always updated with the object state.

<h3> About restricted access</h3>

Access is restricted to only one chat ID (`TELEGRAM_CHAT_ID`), set on `/start` command and stored in the vault for secrets.
After that, only messages received from that chat will be attended This is handled with the `@restricted` decorator


<h3> Bot Commands</h3>

* `/start`: Starts the bot. It will **set the allowed chat_id if not already set**, send a welcome message and a suggestion if there is one available.
* `/next`: Sends the next suggestion (and changes the thread of conversation) if there is one available.
* `/previous`: Sends the previous suggestion (and changes the thread of conversation) if there is one available.
* `/select {index}`: Selects a suggestion by index. It will send the selected suggestion and change the thread of conversation.
* `/list`: Lists the suggestions in the pool with their index.
* `/publish`: Publishes the current suggestion to LinkedIn. If not authenticated, it will send a message with the link to the authentication page.
* `/allow`: Allows the bot to send suggestions. 
* `/stop`: Blocks the bot from sending suggestions.
* `/healthcheck`: Sends a message to the user (to see if the bot is alive).
* `/clear`: Discards the current suggestion.
* `/clear_image`: It will remove the current image for the post
* `/set_image`: Used along with an image in the message, it will set the passed image for the post to be published 
* `/add_youtube {url}`: Adds a youtube url to the youtube url pool in order for the video to get processed into a new post
* `/update`: Updates the current publication's content with the last message sent by the bot.
* `/current`: Sends the current suggestion. This is what will get published if the user uses the `/publish` command.
* `/activate_search_engine`: ables the search engine to execute
* `/stop_search_engine`: disables the search engine to execute
* `/images`: Lists the images available for the current post

<h3> Bot Configuration </h3>

The configuration file must be contained inside the `config` collection with the field `config_name`: `"telegram"`. It contains the following parameters:

* `suggestion_period`: Nº of days to wait after a post has been published in order to start suggesting new posts again
* `cool_off_time`: Time to wait in order to send a new publication to the user after the last one was published
