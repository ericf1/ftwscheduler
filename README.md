# FTW Scheduler Bot

A Discord bot for scheduling messages to send.

Features
---
- Easy to understand prompts
- Consistant
- Easy to use

Important Notes When Running The Bot
---
Note that the time for addMessage is military time (24-hours). All time is localized to EST you can use an online converter for now (this may change later). 

Time is formatted like this: ``mm/dd/YY-HH:MM``. You should check to see if your time is right by doing f!list when you have saved your message.

Messages that are scheduled before right now will automatically send.

The message-id is given when you do f!list.

Commands
---
FTW Scheduler Bot's prefix is ``f!``, add it to the start of any of this bot's command. All of the commands are case-sensitive.

| Command | Arguments | Description | Example |
|---------|-----------|-------------|---------|
| list | None | Lists out all of the messages that your server has scheduled and information about the messages | ``f!list``|
| addMessage | ``{formatted-time}`` | Answer and react to the series of prompts to save your message into the database | ``f!addMessage 4/2/2003-13:11``|
| removeMessage |``{message-id}`` | Removes the message based on its id | ``f!remove 1`` | 
| ping | None | Pong | ``s!ping`` |

