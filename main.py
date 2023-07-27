import discord
from discord.ext import commands
import apraw
import random
from discord.ext import commands
import asyncio
import pyfiglet
from termcolor import colored
from datetime import datetime
import time
import yaml
import os

intents = discord.Intents.all()

bot = commands.Bot(command_prefix=">", intents=intents)

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user.name}')

async def send_random_troll(ctx):
    # 1 in 100 chance of running
    if random.randint(1, 100) != 1:
        return False

    troll_dir = "trolls/"
    files = [f for f in os.listdir(troll_dir) if os.path.isfile(os.path.join(troll_dir, f))]

    if not files:
        return False

    random_file = random.choice(files)
    with open(os.path.join(troll_dir, random_file), 'rb') as f:
        picture = discord.File(f)
        await ctx.send(file=picture)
    
    return True

@bot.command(name='ascii', help="😁 Make ascii", usage='text')
async def ascii(ctx, *, text: str):
    if len(text) > 15:
        await ctx.send("Error: Text is too long (max 50 characters).")
    else:
        # Generate the ASCII art from the given text
        ascii_art = pyfiglet.figlet_format(text)

        # Send the ASCII art as a message
        await ctx.send(f"```{ascii_art}```")

snipes = {}

@bot.event
async def on_message_delete(message):
    global snipes  # Use the global dictionary
    channel_id = str(message.channel.id)
    snipes[channel_id] = {
        'message': message.content,
        'snipee_id': message.author.id 
    }
    print(f'{message.author} just deleted {message.content}')

@bot.command()
async def snipe(ctx):
    global snipes  # Use the global dictionary

    channel_id = str(ctx.channel.id)
    if channel_id in snipes:
        message_content = snipes[channel_id]['message']
        snipee = await bot.fetch_user(snipes[channel_id]['snipee_id'])
        sniped_by = ctx.author

        snipe_message = f"Message by {snipee}: `{message_content}`\nSniped by {sniped_by}"

        await ctx.send(snipe_message)
    else:
        await ctx.send("No message found to snipe in this channel.")

is_game_running = False  # Flag to check if the game is running or not
potato_holder = None  # Variable to keep track of the current potato holder

is_game_running = False  # Flag to check if the game is running or not
potato_holder = None  # Variable to keep track of the current potato holder
potato_hold_start = None  # Variable to keep track of when the potato was passed

@bot.command()
async def hotpotato(ctx):
    global is_game_running
    global potato_holder
    global potato_hold_start
    if is_game_running:
        await ctx.send("A game is already running!")
        return

    is_game_running = True
    members = [m for m in ctx.guild.members if not m.bot]  # Get all non-bot members
    potato_holder = random.choice(members)  # Choose a member at random
    potato_hold_start = time.time()  # Record the time when the potato was passed
    await ctx.send(f'@everyone a game of hot potato has started and {potato_holder.mention} is currently it. They have 30 seconds to pass it on before they get burned. Mention a user to pass it on. You have 30 seconds before the game ends!')

    # Countdown from 30
    for i in range(60, 0, -1):
        await asyncio.sleep(1)
        if time.time() - potato_hold_start >= 10:  # The potato holder has had the potato for more than 5 seconds
            await ctx.send(f'Game over! {potato_holder.mention} held the hot potato for too long and got burned!')
            is_game_running = False  # The game is over
            potato_holder = None  # Reset the potato holder
            return
        if i % 5 == 0:  # Every 5 seconds, send an update
            await ctx.send(f'{i} seconds left...')

    # End the game
    await ctx.send(f'Game over! {potato_holder.mention} was holding the hot potato and got burned!')
    is_game_running = False  # The game is over
    potato_holder = None  # Reset the potato holder

@bot.event
async def on_message(message):
    global is_game_running
    global potato_holder
    global potato_hold_start
    if is_game_running and message.author == potato_holder and message.mentions:
        # The potato holder mentioned someone, pass the potato
        new_potato_holder = message.mentions[0]  # The first mentioned user is the new potato holder
        if new_potato_holder.bot:
            # The mentioned user is a bot, don't pass the potato and send an error message
            await message.channel.send(f"Sorry, {message.author.mention}, you can't pass the potato to a bot!")
            return
        potato_holder = new_potato_holder  # Update the current potato holder
        potato_hold_start = time.time()  # Record the time when the potato was passed
        await message.channel.send(f'{potato_holder.mention}, you have the potato! You have 5 seconds to pass it on!!!')
    await bot.process_commands(message)  # Continue processing commands

with open("config.yml", "r") as f:
    config = yaml.safe_load(f)

reddit = apraw.Reddit(
    client_id=config["reddit"]["client_id"],
    client_secret=config["reddit"]["client_secret"],
    user_agent=config["reddit"]["user_agent"],
    username=config["reddit"]["username"],
    password=config["reddit"]["password"]
)

async def fetch_submission(reddit, subreddit):
    sr = await reddit.subreddit(subreddit)
    posts = sr.hot(limit=100)
    submissions = []

    async for post in posts:
        if not post.stickied:
            submissions.append(post)

    if not submissions:
        return None

    post_index = random.randint(0, len(submissions) - 1)
    return submissions[post_index]

async def send_embed(ctx, subreddit, submission):
    embed = discord.Embed(
        title=submission.title,
        url=f'https://www.reddit.com{submission.permalink}',
        colour=discord.Colour(0x8d30e3),
        description=submission.selftext if submission.is_self else ""
    )
    embed.set_author(name=f'/r/{subreddit} | {await submission.author()}', icon_url="https://www.redditinc.com/assets/images/site/reddit-logo.png")
    
    if submission.is_self:
        pass
    elif submission.url.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
        embed.set_image(url=submission.url)
    elif submission.media:
        if 'reddit_video' in submission.media:
            video_url = submission.media['reddit_video']['fallback_url']
            embed.description = f"[Click here to watch the video]({video_url})"
        elif 'oembed' in submission.media:
            embed.description = f"[Click here to view the content]({submission.url})"
    
    await ctx.send(embed=embed)

async def subreddit_exists(reddit, subreddit_name):
    try:
        await reddit.subreddit(subreddit_name)
        return True
    except Exception:
        return False

@bot.command('reddit', help="😁 Sends a random post from the specified subreddit", usage="subreddit")
@commands.cooldown(1, 5, commands.BucketType.user)
async def reddit_command(ctx, subreddit: str):
    troll_triggered = await send_random_troll(ctx)
    if troll_triggered:
        return
    async with ctx.typing():
        message = await ctx.send("Getting your post... Reddit is a little slow :pensive: please be patient... ")

        # Replace spaces with underscores
        subreddit = subreddit.replace(" ", "_")

        if not await subreddit_exists(reddit, subreddit):
            await message.delete()
            await ctx.send(f"The subreddit '{subreddit}' does not exist.")
            return

        try:
            submission = await fetch_submission(reddit, subreddit)
        except Exception as e:
            print(f"Error fetching submission: {e}")
            submission = None

        if submission is None:
            await message.delete()
            await ctx.send(f"Unable to fetch a submission from the subreddit '{subreddit}'.")
            return

        if submission.over_18 and not ctx.channel.is_nsfw():
            await message.delete()
            await ctx.send("The post I found is marked as NSFW, but this is not an NSFW channel. Please try again in an NSFW channel.")
            return

        await message.delete()
        await send_embed(ctx, subreddit, submission)


bot.run('MTEzNDExNjIzNDk2MzcxNDA2OQ.GwTyTK.2kJA2_vG8RIiGAoUv_eX5ZtMK7Q151rat01j44')
