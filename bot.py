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
# messageId: {content:content, server_id:server_id, channel_id:channel_id, scheduled_time:scheduled_time}


def list_doc_message():
    return db.all()


def edit_doc_message(message_id, client_server_id, channel_ids, content, scheduled_time):
    message = db.get(doc_id=message_id)
    if client_server_id != message.get("server_id"):
        raise Exception("This message does not exist")

    message.update({'content': content,
                    'scheduled_time': scheduled_time,
                    "channel_ids": channel_ids}, doc_id=message_id)


def add_doc_message(server_id, channel_ids, content, scheduled_time):
    db.insert({'content': content,
               'scheduled_time': scheduled_time,
               "server_id": server_id,
               "channel_ids": channel_ids})


def remove_doc_message(message_id, client_server_id):
    message = db.get(doc_id=message_id)
    if client_server_id != message.get("server_id"):
        raise Exception("This message does not exist")
    db.remove(doc_ids=[int(message_id)])


@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')


async def add_reaction(ctx): await ctx.message.add_reaction("✅")


@bot.command()
async def ping(ctx):
    await ctx.send('Pong')
    await add_reaction(ctx)


def parse_time(givenTime):
    # example time: 6/11/2022-7:31
    date_time_str = f'{givenTime}:00'

    date_time_obj = datetime.strptime(
        date_time_str, '%m/%d/%Y-%H:%M:%S')

    return date_time_obj.timestamp()


def check_stop(stop: str):
    if stop == "quit":
        return True
    return False


async def has_perms(ctx):
    has_perms = ctx.author.permissions_in(ctx.channel).manage_channels
    if not has_perms:
        await ctx.send("You do not have permission to use this command.")
    return has_perms


@ bot.command()
async def remove(ctx, id):
    if not await has_perms(ctx):
        return
    remove_doc_message(id, ctx.guild.id)
    await add_reaction(ctx)


@ bot.command()
async def list(ctx):
    if not await has_perms(ctx):
        return
    all_messages = list_doc_message()

    if not all_messages:
        await ctx.send("You have no messages :(")
        return

    for message in all_messages:
        if message.get("server_id") != ctx.guild.id:
            continue
        dt = datetime.fromtimestamp(message.get("scheduled_time"))
        content = message.get("content")
        channels = ' '.join(message.get("channel_ids"))
        embed = discord.Embed(
            title=f"Scheduled for {dt}", description=f"{content} \n \n Sending To: {channels} \n Message Id: {message.doc_id}")
        await ctx.send(embed=embed)
    await add_reaction(ctx)


@ bot.command()
async def add(ctx, time: parse_time):
    if not await has_perms(ctx):
        return

    def check(msg):
        return msg.channel == ctx.channel and msg.author == ctx.author

    await ctx.send("What channels do you want to send the message to? Write quit if you want to exit.")
    channels = await bot.wait_for('message', timeout=60, check=check)
    if check_stop(channels):
        await ctx.send("Exiting... To restart, rerun the command")
        return

    channels_list = channels.content.split()
    for one_channel in channels_list:
        match = re.match(r'<#[0-9]{18}>', one_channel)
        if not match.group(0):
            await ctx.send(f'{one_channel} is not a valid channel format')
            return
        await ctx.send(one_channel)
    msg = await ctx.send("Are these the correct channels? Make sure that I have permission to write in those channels!")
    await msg.add_reaction('👍')
    await msg.add_reaction('👎')
    reaction, user = await bot.wait_for('reaction_add', timeout=120,
                                        check=lambda reaction, user: (reaction.emoji == '👍' or reaction.emoji == '👎') and user == ctx.author)
    if reaction.emoji == '👎':
        await ctx.send("Exiting... To restart, rerun the command")
        return
    await ctx.send('Perfect! Now write the exact message that you want to send. Write quit if you want to exit.')

    msg_content = await bot.wait_for('message', timeout=120, check=check)
    if check_stop(msg_content):
        await ctx.send("Exiting... To restart, rerun the command")
        return

    await ctx.send(msg_content.content)
    msg_confirm = await ctx.send("Does this look like the message you want to send?")
    await msg_confirm.add_reaction('👍')
    await msg_confirm.add_reaction('👎')
    reaction, user = await bot.wait_for('reaction_add', timeout=120,
                                        check=lambda reaction, user: (reaction.emoji == '👍' or reaction.emoji == '👎') and user == ctx.author)
    if reaction.emoji == '👎':
        await ctx.send("Exiting... To restart, rerun the command")
        return
    await ctx.send('Amazing! We are going to add your message. Use f!list to see your scheduled messages')
    add_doc_message(ctx.guild.id, channels_list, msg_content.content, time)
    await add_reaction(ctx)


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
async def main_loop():
    await bot.wait_until_ready()
    try:
        allMessages = list_doc_message()
        if not allMessages:
            return
        for message in allMessages:
            if not time.time() >= message.get("scheduled_time") + 14400:
                return
            for channel in message.get("channel_ids"):
                await bot.get_channel(
                    int(channel[2:-1])).send(message.get("content"))
                db.remove(doc_ids=[message.doc_id])
    except Exception as e:
        print(repr(e))

if __name__ == '__main__':
    main_loop.start()
    bot.run(os.getenv('DISCORD_TOKEN'))
