import os
from dotenv import load_dotenv
import discord
from discord import Option
from discord.ext import commands, pages

from bot_utils import fetch_series_info, search_series
from bot_ext import create_results_page

load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')

#Bot
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!?", intents=intents)

@bot.event
async def on_ready():
    await bot.sync_commands()
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------\n")


@bot.slash_command(name="search", description="Searches for Light Novels")
async def fetch(
    interaction:discord.Interaction,
    title: Option(str, "Title"),
    sort: Option(str, "Select sorting order", name='sort-by', choices=['Relevance desc', 'Relevance asc', 'Title asc', 'Title desc', 'Release date asc', 'Release date desc'], default='Relevance desc'),
    licensed: Option(bool, 'Select whether to display only licensed LNs', name='licensed-only', choices=[True, False], default=False)
):
    await interaction.response.defer()
    results = await search_series(title, sort, licensed)
    if results is None:
        await interaction.followup.send("No results found")
    elif isinstance(results, str):
        await interaction.followup.send(results)
    elif isinstance(results, tuple) and len(results)>2:
        (color, title, description, image, tags) = results
        emb = discord.Embed(color=color, title=title, description=description)
        emb.set_image(url=image)
        if tags:
            emb.add_field(name="Tags", value=", ".join(tags), inline=True)
        await interaction.followup.send(embed=emb)
    else:
        count, search_results = results
        page_list = create_results_page(count, search_results)
        paginator = pages.Paginator(pages=page_list, show_disabled=False, loop_pages=True)
        await paginator.respond(interaction.interaction)


bot.run(TOKEN)