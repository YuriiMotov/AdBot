# AdBot
Telegram bot that can forward you messages from different Telegram groups by filtering them based on your keywords.

This is a study project I'm developing to practice using various libraries, but it can also be useful.


## Libraries used
 - aiogram-dialog 2.0.0
 - aiogram 3.0.0
 - telethon
 - SQLAlchemy (async)
 - APScheduler


## How it works
There are two parts that work in parallel:
 - telegram client (based on the telethon library), that collects messages from configured group chats and channels and stores them in the DB.
 - telegram bot (aiogram-dialog), that manages user settings (keywords, subscription status) and forwards messages to users.

User starts conversation with the bot by using '/start' command. This shows the menu as shown below:

![](/resources/menu.png "Menu")

If you click the "Manage Keywords" menu button, the "Manage Keywords" menu section will open.

![](/resources/keywords-manage.png "Keywords management")

Here you can add keywords. Just write the keyword and click send.

![](/resources/add-keyword.png "Add keyword")

or remove some keywords (click 'remove keywords' and choose keywords to remove (one of the buttons with the keyword text and a red cross)).

![](/resources/remove-keyword.png "Remove keyword")

After configuring the keywords, user can return to the top-level menu and enable subscription by clicking the 'Enable subscription' button. The subscription status will be changed to 'Subscription state: '✅ enabled'.

![](/resources/subscription-enabled.png "Subscription enabled")

After that bot will filter all new messages in monitored chats and forward them to the user based on the user's keywords.

But forwarding is suspended while menu is open. There is a warning message at the bottom of the menu, that also shows the number of messages in the forwarding queue.

![](/resources/forwarding-queue.png "Forwarding queue")

To receive these messages, you need to close the menu. Or it will be automatically closed after 2 minutes of user inactivity.

![](/resources/menu-closed.png "Menu closed")

Now the messages will be forwarded to the user.

![](/resources/message-received.png "Message received")


## Future plans
 - [DONE] switch to an asynchronous database
 - add more e2e tests
 - add multilanguage support
 - divide all chats into categories and let the user choose which ones he wants to subscribe to
 - notifying the administrator of critical errors
 - create FastAPI and Flask interfaces (just to practice using these libraries)
 - create other types of message collectors (from Facebook groups and other web sources)



# How to run in docker
 - Download to local system (`git clone https://github.com/YuriiMotov/AdBot.git`)
 - create `.env` file and fill it (use `.env_example` as an example)
 - create docker image (execute command `sudo docker build -t adbot .`)
 - run system (command `sudo docker compose up -d`)