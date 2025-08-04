import requests
import json
import aiohttp
import asyncio
import math
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Optional


SERIES_API_ENDPOINT = "https://ranobedb.org/api/v0/series"
VOLUMES_API_ENDPOINT = "https://ranobedb.org/api/v0/books/"
IMAGES_ENDPOINT = "https://images.ranobedb.org/"


# def parse_date_safe(date_val) -> Optional[date]:
#     """Safely parse a date string of format YYYYMMDD (e.g., 20241010)."""
#     if not date_val:
#         return None
#     date_str = str(date_val)[:8]  # Trim extra characters if any
#     try:
#         return datetime.strptime(date_str, "%Y%m%d").date()
#     except ValueError:
#         print(f"[!] Invalid date format: {date_str}")
#         return None


@dataclass
class Series:
    id: int
    title: str
    original_title: Optional[str]
    romaji: Optional[str]
    original_romaji: Optional[str]
    description: Optional[str]
    image_url: str
    lang: str
    tags: List[str]
    # volumes: List[Volume] = field(default_factory=list)

    @classmethod
    def from_json(cls, data: dict) -> 'Series':
        series_data = data["series"]
        tags = [tag["name"] for tag in series_data.get("tags", [])]
        if series_data["lang"]=='ja':
            desc = series_data.get("book_description", {}).get("description_ja")
        else:
            desc = series_data.get("book_description", {}).get("description")
        # volumes = [Volume.from_json(book) for book in series_data.get("books", [])]

        return cls(
            id=series_data["id"],
            title=series_data["title"],
            original_title=series_data.get("title_orig"),
            romaji=series_data.get("romaji"),
            original_romaji=series_data.get("romaji_orig"),
            description=desc,
            image_url=IMAGES_ENDPOINT+series_data["books"][0]["image"]["filename"],
            lang=series_data["lang"],
            tags=tags,
            # volumes=volumes
        )


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
        return (10216,series.title,description,series.image_url,series.tags)
    else:
        description = f"***{series.original_title} | {series.original_romaji}***\n\n"+series.description+"\n\n"
        return (15204352,series.title,description,series.image_url,series.tags)


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
