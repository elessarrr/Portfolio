import httpx
import json
import logging
import os
import re
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

FAA_SOURCE_URL = os.environ.get("FAA_SOURCE_URL", "https://www.faa.gov/data_research/accident_incident")
MAX_PAGES = int(os.environ.get("FAA_MAX_PAGES", "5"))
OUTPUT_FILE = "data/raw/faa_incidents.json"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def get_soup(url, client, retries=3, backoff_seconds=1.5):
    for attempt in range(1, retries + 1):
        try:
            response = client.get(url, headers=HEADERS, timeout=30.0)
            response.raise_for_status()
            return BeautifulSoup(response.text, "html.parser")
        except Exception as error:
            if attempt == retries:
                logger.error(f"Failed to fetch {url}: {error}")
                return None
            sleep_for = backoff_seconds * attempt
            logger.warning(f"Retry {attempt}/{retries} for {url}: {error}")
            time.sleep(sleep_for)
    return None


def parse_faa_row(columns, source_url):
    cells = [column.get_text(" ", strip=True) for column in columns]
    date_text = cells[0] if len(cells) > 0 else None
    registration = cells[1] if len(cells) > 1 else None
    make_model = cells[2] if len(cells) > 2 else None
    location = cells[3] if len(cells) > 3 else None
    injury_level = cells[4] if len(cells) > 4 else None

    fatalities = 0
    if injury_level:
        fatality_match = re.search(r"(\d+)\s*fatal", injury_level, re.IGNORECASE)
        if fatality_match:
            fatalities = int(fatality_match.group(1))
        elif "fatal" in injury_level.lower():
            fatalities = 1

    return {
        "source_name": "FAA",
        "source_url": source_url,
        "date": date_text,
        "registration": registration,
        "make_model": make_model,
        "location": location,
        "injury_level": injury_level,
        "fatalities": fatalities
    }


def find_next_page_url(soup, current_url):
    next_link = soup.find("a", attrs={"rel": "next"})
    if not next_link:
        next_link = soup.find("a", string=re.compile(r"next", re.IGNORECASE))
    if not next_link or not next_link.get("href"):
        return None
    return urljoin(current_url, next_link["href"])


def scrape_faa():
    incidents = []
    current_url = FAA_SOURCE_URL
    pages_scraped = 0

    with httpx.Client(follow_redirects=True) as client:
        while current_url and pages_scraped < MAX_PAGES:
            soup = get_soup(current_url, client)
            if not soup:
                break

            rows_added = 0
            for table in soup.find_all("table"):
                for row in table.find_all("tr")[1:]:
                    columns = row.find_all("td")
                    if len(columns) < 4:
                        continue
                    incidents.append(parse_faa_row(columns, current_url))
                    rows_added += 1

            logger.info(f"Parsed {rows_added} FAA records from {current_url}")
            pages_scraped += 1
            current_url = find_next_page_url(soup, current_url)
            time.sleep(1.0)

    return incidents


def main():
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    incidents = scrape_faa()
    with open(OUTPUT_FILE, "w") as output:
        json.dump(incidents, output, indent=2)
    logger.info(f"Saved {len(incidents)} FAA incidents to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
