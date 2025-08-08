import requests
import json
import aiohttp
import asyncio
import math
import logging
from discord import Embed
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Optional

SERIES_API_ENDPOINT = "https://ranobedb.org/api/v0/series"
VOLUMES_API_ENDPOINT = "https://ranobedb.org/api/v0/books/"
IMAGES_ENDPOINT = "https://images.ranobedb.org/"
BOOKWALKER_ENDPOINT = "https://bookwalker.jp/series/"

logger = logging.getLogger(__name__)

####### Misc Functions 1 #######

def convert_to_date(date_str, vname_or_sid=None):
    date_str = str(date_str)
    try:
        d = datetime.strptime(date_str, "%Y%m%d").date()
        return d
    except ValueError:
        if date_str[-2:] == "99":                   # Some volumes on the site have their release dates as 99
            date_str = date_str[:-2]+"25"           # This is just a quick workaround until the API fixed it
        logger.info(f"Series ID or Volume Name: [{vname_or_sid}] had incorrect date. Replaced with '25'")
        d = datetime.strptime(date_str, "%Y%m%d").date()
        return d


######## Data Classes ########

@dataclass
class Volume:
    id: int
    lang: str
    title_jp: str
    title_en: Optional[str]
    sort_order: int
    jp_release_date: Optional[date] = None
    en_release_date: Optional[date] = None

    @classmethod
    def from_series_json(cls, series_json: dict) -> 'Volume':
        if series_json["lang"] == "en":
            en_release_date = convert_to_date(series_json["c_release_dates"]["en"], series_json.get("title"))
        else:
            en_release_date = None
        return cls(
            id=series_json["id"],
            lang=series_json["lang"],
            title_jp=series_json["title_orig"],
            title_en=series_json["title"],
            sort_order=series_json["sort_order"],
            jp_release_date=convert_to_date(series_json["c_release_dates"]["ja"], series_json.get("title")),
            en_release_date=en_release_date
        )

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
    licensed: bool
    volumes: List[Volume] = field(default_factory=list)

    @classmethod
    def from_json(cls, data: dict) -> 'Series':
        series_data = data["series"]
        volumes = [Volume.from_series_json(vol) for vol in series_data.get("books", [])]
        tags = [tag["name"].capitalize() for tag in series_data.get("tags", [])]
        first_released = str(convert_to_date(series_data.get("start_date"),series_data.get("id"))) + " (JP)"
        latest_released = str(volumes[-1].jp_release_date) + " (JP)"
        if series_data["lang"]=='ja':
            licensed = False
            desc = series_data.get("book_description", {}).get("description_ja")
        else:
            licensed = True
            desc = series_data.get("book_description", {}).get("description")
        bookwalker_id = str(series_data.get("bookwalker_id"))
        bookwalker_url = BOOKWALKER_ENDPOINT+bookwalker_id if bookwalker_id is not None else None
        return cls(
            id=series_data["id"],
            title=series_data["title"],
            original_title=series_data.get("title_orig"),
            romaji=series_data.get("romaji"),
            original_romaji=series_data.get("romaji_orig"),
            description=desc,
            publication_status=series_data.get("publication_status"),
            first_released=first_released,
            latest_released=latest_released,
            image_url=IMAGES_ENDPOINT+series_data["books"][0]["image"]["filename"],
            bookwalker_url=bookwalker_url,
            lang=series_data["lang"],
            tags=tags,
            licensed=licensed,
            volumes=volumes
        )

####### Misc Functions 2 #######

def create_embed(color, title, description, publication_status, first_released, latest_released, image, bw_url, tags):
    embed = Embed(color=color, title=title, description=description)
    embed.set_image(url=image)
    embed.add_field(name="Publication Status", value=publication_status.capitalize(), inline=True)
    embed.add_field(name="First Release", value=first_released, inline=True)
    embed.add_field(name="Latest Release", value=latest_released, inline=True)
    embed.set_footer(text="Data fetched from RanobeDB")
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
    vol_rel_dates_jp = {}
    vol_rel_dates_en = {}
    latest_vol_jp = None
    latest_vol_en = None
    for vol in sorted(series.volumes, key=lambda v: v.sort_order):
        vol_rel_dates_jp[vol.sort_order] = vol.jp_release_date
        latest_vol_jp = vol.title_jp
        if vol.lang == "en":
            vol_rel_dates_en[vol.sort_order] = vol.en_release_date
            latest_vol_en = vol.title_en
    predict = True if series.publication_status == "ongoing" else False
    if series.lang == 'ja':
        description = f"***{series.romaji}***\n\n"+series.description+"\n\n"
        embed =  create_embed(10216,series.title,description,series.publication_status,series.first_released,series.latest_released,series.image_url,series.bookwalker_url,series.tags)
    else:
        description = f"***{series.original_title} | {series.original_romaji}***\n\n"+series.description+"\n\n"
        embed =  create_embed(15204352,series.title,description,series.publication_status,series.first_released,series.latest_released,series.image_url,series.bookwalker_url,series.tags)
    return (embed, vol_rel_dates_jp, vol_rel_dates_en, predict, series.title, latest_vol_jp, latest_vol_en)

async def search_series(title, sort, licensed):
    params = {
        'q': title,
        'sort': sort,
        'limit': 100
    }
    if licensed == 'Licensed':
        params.update({'rl': 'en'})
    elif licensed == 'Unlicensed':
        params.update({'rlExclude': 'en'})
    else:
        pass
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
    elif count>5800:
        return "More than 6000 results.\nBe more specific with the search terms."
    else:
        all_data = await fetch_all_results_async(SERIES_API_ENDPOINT, total_pages, params)
        paged_dict = paginate_results(all_data)
        return(count,paged_dict)