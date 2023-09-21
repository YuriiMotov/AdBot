# AdBot
Telegram bot that can forward you messages from different groups based on your keywords.

This is a study project I develop to practice using different libraries.
But it can also be useful.


## Libraries used
 - aiogram-dialog 2.0.0
 - aiogram 3.0.0
 - telethon
 - SQLAlchemy
 - APScheduler


## How it works
There are two parts that work in parallel:
 - telegram client (based on the `telethon` library), that fetches messages from configured group chats and channels and store them into DB.
 - telegram bot (aiogram-dialog), that manages user's settings (keywordsm subcription state) and forwards messages to users.

User starts conversation with the bot by using '/start' command. It shows menu as shown below:

![](/resources/menu.png "Menu")

By clicking the 'Manage keywords' menu button, keywords menagement menu section will be shown.

![](/resources/keywords-manage.png "Keywords management")

Here it`s possible to add keywords. Just write keyword and press send button. 

![](/resources/add-keyword.png "Add keyword")

or remove some keywords (click 'remove keywords' and choose keywords to remove (one of the buttons with keyword text and red cross)).

![](/resources/remove-keyword.png "Remove keyword")

After configuring the keywords, user can go back to the top level menu and enable subscription by clicking the 'Enable subscription' button. The subcription status will be changed to 'Subscription state: '✅ enabled'.

![](/resources/subscription-enabled.png "Subscription enabled")

After that bot will filter all new messages in followed chats and forward to user.

But forwarding is suspended while menu is open. There is a warning message in the bottom part of the menu, that also shows the number of messages in the forwarding queue.

![](/resources/forwarding-queue.png "Forwarding queue")

To recieve these messages you need to close the menu. Or it will be automatically closed after 2 minutes of user inactivity.

![](/resources/menu-closed.png "Menu closed")

Now messages will be forwarded to user.

![](/resources/message-received.png "Message received")



## Future plans
 - switch to async DB
 - add more e2e tests
 - add multilanguage support
 - divide all chats into categories and let the user choose which ones he wants to subscribe to
 - admin notification on critical errors
 - create FastAPI and Flask interfaces (just to practice using thos libraries)
 - create other types of message fetchers (from Facebook groups and other web-sources)
