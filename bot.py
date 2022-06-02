from dotenv import load_dotenv
from tinydb import TinyDB
import discord
from discord.ext import tasks, commands
import os
import re
from datetime import datetime
import time

load_dotenv()

bot = commands.Bot(command_prefix='f!')

db = TinyDB('schedule.json')

# schema:
# messageId: {content:content, server_id:serverId, channel_id:channelId, scheduled_time:scheduledTime}


def listDocMessage():
    return db.all()


def editDocMessage(messageId, clientServerId, channelIds, content, scheduledTime):
    message = db.get(doc_id=messageId)
    if clientServerId != message.get("server_id"):
        raise Exception("This message does not exist")

    message.update({'content': content,
                    'scheduled_time': scheduledTime,
                    "channel_ids": channelIds}, doc_id=messageId)


def addDocMessage(serverId, channelIds, content, scheduledTime):
    db.insert({'content': content,
               'scheduled_time': scheduledTime,
               "server_id": serverId,
               "channel_ids": channelIds})


def removeDocMessage(messageId, clientServerId):
    message = db.get(doc_id=messageId)
    if clientServerId != message.get("server_id"):
        raise Exception("This message does not exist")
    db.remove(doc_ids=[int(messageId)])


@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')


async def addReaction(ctx): await ctx.message.add_reaction("✅")


@bot.command()
async def ping(ctx):
    await ctx.send('Pong')
    await addReaction(ctx)


def parse_time(givenTime):
    # example time: 6/11/2022-7:31
    date_time_str = f'{givenTime}:00'

    date_time_obj = datetime.strptime(
        date_time_str, '%m/%d/%Y-%H:%M:%S')

    return date_time_obj.timestamp()


def checkStop(stop: str):
    if stop == "quit":
        return True
    return False


async def hasPerms(ctx):
    hasPerms = ctx.author.permissions_in(ctx.channel).manage_channels
    if not hasPerms:
        await ctx.send("You do not have permission to use this command.")
    return hasPerms


@ bot.command()
async def remove(ctx, id):
    if not await hasPerms(ctx):
        return
    removeDocMessage(id, ctx.guild.id)
    await addReaction(ctx)


@ bot.command()
async def list(ctx):
    if not await hasPerms(ctx):
        return
    allMessages = listDocMessage()

    if not allMessages:
        await ctx.send("You have no messages :(")
        return

    for message in allMessages:
        if message.get("server_id") != ctx.guild.id:
            continue
        dt = datetime.fromtimestamp(message.get("scheduled_time"))
        content = message.get("content")
        channels = ' '.join(message.get("channel_ids"))
        embed = discord.Embed(
            title=f"Scheduled for {dt}", description=f"{content} \n \n Sending To: {channels} \n Message Id: {message.doc_id}")
        await ctx.send(embed=embed)
    await addReaction(ctx)


@ bot.command()
async def add(ctx, time: parse_time):
    if not await hasPerms(ctx):
        return

    def check(msg):
        return msg.channel == ctx.channel and msg.author == ctx.author

    await ctx.send("What channels do you want to send the message to? Write quit if you want to exit.")
    channels = await bot.wait_for('message', timeout=60, check=check)
    if checkStop(channels):
        await ctx.send("Exiting... To restart, rerun the command")
        return

    channelsList = channels.content.split()
    for oneChannel in channelsList:
        match = re.match(r'<#[0-9]{18}>', oneChannel)
        if not match.group(0):
            await ctx.send(f'{oneChannel} is not a valid channel format')
            return
        await ctx.send(oneChannel)
    msg = await ctx.send("Are these the correct channels? Make sure that I have permission to write in those channels!")
    await msg.add_reaction('👍')
    await msg.add_reaction('👎')
    reaction, user = await bot.wait_for('reaction_add', timeout=120,
                                        check=lambda reaction, user: (reaction.emoji == '👍' or reaction.emoji == '👎') and user == ctx.author)
    if reaction.emoji == '👎':
        await ctx.send("Exiting... To restart, rerun the command")
        return
    await ctx.send('Perfect! Now write the exact message that you want to send. Write quit if you want to exit.')

    msgContent = await bot.wait_for('message', timeout=120, check=check)
    if checkStop(msgContent):
        await ctx.send("Exiting... To restart, rerun the command")
        return

    await ctx.send(msgContent.content)
    msgConfirm = await ctx.send("Does this look like the message you want to send?")
    await msgConfirm.add_reaction('👍')
    await msgConfirm.add_reaction('👎')
    reaction, user = await bot.wait_for('reaction_add', timeout=120,
                                        check=lambda reaction, user: (reaction.emoji == '👍' or reaction.emoji == '👎') and user == ctx.author)
    if reaction.emoji == '👎':
        await ctx.send("Exiting... To restart, rerun the command")
        return
    await ctx.send('Amazing! We are going to add your message. Use f!list to see your scheduled messages')
    addDocMessage(ctx.guild.id, channelsList, msgContent.content, time)
    await addReaction(ctx)


@ add.error
async def add_error(ctx, error):
    await ctx.send(repr(error))


@ remove.error
async def remove_error(ctx, error):
    await ctx.send(repr(error))


@ list.error
async def list_error(ctx, error):
    await ctx.send(repr(error))


@tasks.loop(seconds=1.0)  # repeat every 1 seconds
async def mainLoop():
    await bot.wait_until_ready()
    try:
        allMessages = listDocMessage()
        if allMessages:
            for message in allMessages:
                if time.time() >= message.get("scheduled_time") + 14400:
                    for channel in message.get("channel_ids"):
                        await bot.get_channel(
                            int(channel[2:-1])).send(message.get("content"))
                        db.remove(doc_ids=[message.doc_id])
    except Exception as e:
        print(repr(e))

if __name__ == '__main__':
    mainLoop.start()
    bot.run(os.getenv('DISCORD_TOKEN'))
