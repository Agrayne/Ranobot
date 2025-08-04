import discord
from discord.ui import Select, View
from discord.ext.pages import Page
from bot_utils import fetch_series_info, create_embed


# def create_embed(color, title, description, image, tags):
#     emb = discord.Embed(color=color, title=title, description=description)
#     emb.set_image(url=image)
#     if tags:
#         emb.add_field(name="Tags", value=", ".join(tags), inline=True)
#     return emb


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
        await interaction.response.defer()
        selected_sn = int(self.values[0])
        ln_name = self.sn_dict[selected_sn]
        ln_id = self.results_dict[ln_name]
        emb = fetch_series_info(ln_id)
        await interaction.message.edit(embed=emb, view=None)

class ResultsView(View):
    def __init__(self, page, results_dict):
        super().__init__()
        item = ResultsSelector(page, results_dict)
        self.add_item(item)



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

