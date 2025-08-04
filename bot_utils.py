import requests
import json
import aiohttp
import asyncio
import math
from discord import Embed
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Optional

SERIES_API_ENDPOINT = "https://ranobedb.org/api/v0/series"
VOLUMES_API_ENDPOINT = "https://ranobedb.org/api/v0/books/"
IMAGES_ENDPOINT = "https://images.ranobedb.org/"
BOOKWALKER_ENDPOINT = "https://bookwalker.jp/series/"


######## Data Classes ########
@dataclass
class Series:
    id: int
    title: str
    original_title: Optional[str]
    romaji: Optional[str]
    original_romaji: Optional[str]
    description: Optional[str]
    publication_status: str
    first_released: date
    latest_released: Optional[date]
    image_url: str
    bookwalker_url: Optional[str]
    lang: str
    tags: List[str]
    # volumes: List[Volume] = field(default_factory=list)

    @classmethod
    def from_json(cls, data: dict) -> 'Series':
        series_data = data["series"]
        tags = [tag["name"].capitalize() for tag in series_data.get("tags", [])]
        if series_data["lang"]=='ja':
            desc = series_data.get("book_description", {}).get("description_ja")
        else:
            desc = series_data.get("book_description", {}).get("description")
        first_released = datetime.strptime(str(series_data.get("start_date")), "%Y%m%d").date()
        latest_released = datetime.strptime(str(series_data.get("books")[-1]["c_release_date"]), "%Y%m%d").date()
        bookwalker_id = str(series_data.get("bookwalker_id"))
        bookwalker_url = BOOKWALKER_ENDPOINT+bookwalker_id if bookwalker_id is not None else None
        # volumes = [Volume.from_json(book) for book in series_data.get("books", [])]
        return cls(
            id=series_data["id"],
            title=series_data["title"],
            original_title=series_data.get("title_orig"),
            romaji=series_data.get("romaji"),
            original_romaji=series_data.get("romaji_orig"),
            description=desc,
            publication_status=series_data.get("publication_status").capitalize(),
            first_released=first_released,
            latest_released=latest_released,
            image_url=IMAGES_ENDPOINT+series_data["books"][0]["image"]["filename"],
            bookwalker_url=bookwalker_url,
            lang=series_data["lang"],
            tags=tags,
            # volumes=volumes
        )

####### Misc Functions #######
def create_embed(color, title, description, publication_status, first_released, latest_released, image, bw_url, tags):
    embed = Embed(color=color, title=title, description=description)
    embed.set_image(url=image)
    embed.add_field(name="Publication Status", value=publication_status, inline=True)
    embed.add_field(name="First Release", value=first_released, inline=True)
    embed.add_field(name="Latest Release", value=latest_released, inline=True)
    if bw_url is not None:
        embed.add_field(name="Links", value=f"[Bookwalker (jp)]({bw_url})", inline=False)
    if tags:
        embed.add_field(name="Tags", value=", ".join(tags), inline=False)
    return embed

async def fetch_page(session, url, page, params):
    params.update({'page':page})
    async with session.get(url, params=params) as resp:
        return await resp.json()

async def fetch_all_results_async(api_base_url, total_pages, params):
    all_results = []
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_page(session, api_base_url, p, params) for p in range(1, total_pages + 1)]
        pages = await asyncio.gather(*tasks)
        for data in pages:
            for item in data["series"]:
                all_results.append((item["title"], item["id"]) if item['lang']=='en' else (item["romaji_orig"], item["id"]))
    return all_results

def paginate_results(flat_list, items_per_page=10):
    paginated = {}
    total_pages = math.ceil(len(flat_list) / items_per_page)
    for i in range(total_pages):
        chunk = flat_list[i * items_per_page : (i + 1) * items_per_page]
        paginated[i + 1] = {name: id_ for name, id_ in chunk}
    return paginated


def fetch_series_info(id):
    response = requests.get(SERIES_API_ENDPOINT+f'/{str(id)}')
    data = response.json()
    series = Series.from_json(data)
    if series.lang == 'ja':
        description = f"***{series.romaji}***\n\n"+series.description+"\n\n"
        embed =  create_embed(10216,series.title,description,series.publication_status,series.first_released,series.latest_released,series.image_url,series.bookwalker_url,series.tags)
        return embed
    else:
        description = f"***{series.original_title} | {series.original_romaji}***\n\n"+series.description+"\n\n"
        embed =  create_embed(15204352,series.title,description,series.publication_status,series.first_released,series.latest_released,series.image_url,series.bookwalker_url,series.tags)
        return embed

async def search_series(title, sort, licensed):
    params = {
        'q': title,
        'sort': sort,
        'limit': 100
    }
    if licensed:
        params.update({'rl': 'en'})
    response = requests.get(SERIES_API_ENDPOINT, params=params)
    result = response.json()
    count = int(result['count'])
    lns = result['series']
    total_pages = result['totalPages']
    if count<1:
        return None
    elif count==1:
        series_info = fetch_series_info(lns[0]['id'])
        return series_info
    elif count>6000:
        return "More than 6000 results.\nBe more specific with the search terms."
    else:
        all_data = await fetch_all_results_async(SERIES_API_ENDPOINT, total_pages, params)
        paged_dict = paginate_results(all_data)
        return(count,paged_dict)
