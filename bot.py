import os
from dotenv import load_dotenv
import discord
from discord import Option
from discord.ext import commands, pages

from bot_utils import fetch_series_info, search_series
from bot_ext import GraphButtonView, create_results_page

load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')
if not TOKEN:
    raise ValueError("Cannot find the token in the .env file. Make sure it is set properly.")

#Bot
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!?", intents=intents)

@bot.event
async def on_ready():
    await bot.sync_commands()
    print(f"{bot.user} is Online")
    print(f"Connected to {len(bot.guilds)} servers")


@bot.slash_command(name="search", description="Searches for Light Novels")
async def fetch(
    interaction:discord.Interaction,
    title: Option(str, "Title"),
    sort: Option(str, "Select sorting order", name='sort-by', choices=['Relevance desc', 'Relevance asc', 'Title asc', 'Title desc', 'Release date asc', 'Release date desc'], default='Relevance desc'),
    licensed: Option(bool, 'Select whether to display only licensed LNs', name='licensed-only', choices=[True, False], default=False)
):
    await interaction.response.defer()
    try:
        results = await search_series(title, sort, licensed)
        if results is None:
            await interaction.followup.send("No results found")
        elif isinstance(results, str):
            await interaction.followup.send(results)
        elif isinstance(results, tuple) and len(results)>2:
            embed, vol_rel_dates, predict, title, latest_vol = results
            button_view = GraphButtonView(vol_rel_dates, predict, title, latest_vol)
            await interaction.followup.send(embed=embed, view=button_view)
        else:
            count, search_results = results
            page_list = create_results_page(count, search_results)
            paginator = pages.Paginator(pages=page_list, show_disabled=False, loop_pages=True)
            await paginator.respond(interaction.interaction)
    except Exception as e:
        await interaction.followup.send("🚨 An unexpected error occurred.", ephemeral=True)
        import traceback
        traceback.print_exc()

bot.run(TOKEN)