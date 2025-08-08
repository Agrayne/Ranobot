import discord
from discord.ui import Select, View
from discord.ext.pages import Page
from bot_utils import fetch_series_info, create_embed
from graph import generate_graph
import logging

logger = logging.getLogger(__name__)


### Custom View and Selector Classes ###

class GraphButtonView(discord.ui.View):
    def __init__(self, vol_rel_dates_jp, vol_rel_dates_en, predict, title, latest_vol_jp, latest_vol_en):
        super().__init__()
        self.vol_rel_dates_jp = vol_rel_dates_jp
        self.vol_rel_dates_en = vol_rel_dates_en
        self.predict = predict
        self.title = title
        self.latest_vol_jp = latest_vol_jp
        self.latest_vol_en = latest_vol_en
    @discord.ui.button(label="Published Volume Graph", style=discord.ButtonStyle.secondary, emoji="📈")
    async def button_callback(self, button, interaction):
        try:
            await interaction.response.defer()
            if len(self.vol_rel_dates_jp) < 2:
                await interaction.followup.send("Series only has one volume. Graph cannot be generated")
                button.disabled = True
                await interaction.message.edit(view=self)
                return
            buf = generate_graph(self.vol_rel_dates_jp, self.vol_rel_dates_en, self.predict, self.title, self.latest_vol_jp, self.latest_vol_en)
            file = discord.File(buf, filename="chart.png")
            await interaction.followup.send(file=file)
            button.disabled = True
            await interaction.message.edit(view=self)
        except Exception as e:
            await interaction.followup.send("🚨 An unexpected error occurred.", ephemeral=True)
            logger.error(f"Error during graph generation for {self.title}", exc_info=True)

class ResultsSelector(Select):
    def __init__(self, page, results_dict):
        self.page = page
        self.results_dict = results_dict
        self.sn_dict = {(10*(self.page-1)+i): title for i, title in enumerate(self.results_dict, start=1)}
        super().__init__(
            placeholder = "Select the LN to get the info",
            min_values = 1,
            max_values = 1,
            options = [
                discord.SelectOption(
                    label=f"{sn}. {title}",
                    value=str(sn)
                ) if len(f"{sn}. {title}") < 90 else discord.SelectOption(
                    label=f"{sn}. {title[:80]}......",
                    value=str(sn)
                ) for sn, title in self.sn_dict.items()
            ]
        )
    async def callback(self, interaction):
        try:
            await interaction.response.defer()
            selected_sn = int(self.values[0])
            ln_name = self.sn_dict[selected_sn]
            ln_id = self.results_dict[ln_name]
            embed, vol_rel_dates_jp, vol_rel_dates_en, predict, title, latest_vol_jp, latest_vol_en = fetch_series_info(ln_id)
            button_view = GraphButtonView(vol_rel_dates_jp, vol_rel_dates_en, predict, title, latest_vol_jp, latest_vol_en)
            await interaction.message.edit(embed=embed, view=button_view)
        except discord.NotFound:
            await interaction.followup.send("❌ Message no longer exists. Please try searching again.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.followup.send("⚠️ Something went wrong with Discord's API.", ephemeral=True)
            logger.error(f"Discord HTTP error: {e}")
        except Exception as e:
            await interaction.followup.send("🚨 An unexpected error occurred.", ephemeral=True)
            logger.error(f"Error during graph generation for {title}", exc_info=True)


class ResultsView(View):
    def __init__(self, page, results_dict):
        super().__init__()
        item = ResultsSelector(page, results_dict)
        self.add_item(item)

### ------------------------------------------------------------- ###

def create_results_page(count, search_results):
    pages_list = []
    for page_no, results_dict in search_results.items():
        count_description = f"***Found {count} results***\n\n"
        s_list = [f"{(10*(page_no-1)+i)}. {title}" for i, title in enumerate(results_dict, start=1)]
        results_description = "\n".join(s_list)
        description = count_description + results_description
        page = Page(
            embeds=[
                discord.Embed(
                    title="**Search Results**",
                    description=description,
                    color=0x2f0045
                )
            ],
            custom_view=ResultsView(page_no, results_dict)
        )
        pages_list.append(page)
    return pages_list
