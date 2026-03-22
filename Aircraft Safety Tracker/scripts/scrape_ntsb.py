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

NTSB_SOURCE_URL = os.environ.get("NTSB_SOURCE_URL", "https://www.ntsb.gov/_layouts/ntsb.aviation/index.aspx")
MAX_PAGES = int(os.environ.get("NTSB_MAX_PAGES", "5"))
OUTPUT_FILE = "data/raw/ntsb_incidents.json"
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


def extract_ntsb_id(text):
    match = re.search(r"\b[A-Z]{3}\d{2}[A-Z]{2}\d+\b", text or "")
    return match.group(0) if match else None


def extract_pdf_url(detail_url, client):
    detail_soup = get_soup(detail_url, client)
    if not detail_soup:
        return None
    for anchor in detail_soup.find_all("a", href=True):
        href = anchor["href"]
        absolute_url = urljoin(detail_url, href)
        if absolute_url.lower().endswith(".pdf") or ".pdf?" in absolute_url.lower():
            return absolute_url
        if "dms" in absolute_url.lower() and "document" in absolute_url.lower():
            return absolute_url
    return None


def parse_ntsb_row(columns, detail_url, client):
    cells = [column.get_text(" ", strip=True) for column in columns]
    event_date = cells[0] if len(cells) > 0 else None
    location = cells[1] if len(cells) > 1 else None
    make_model = cells[2] if len(cells) > 2 else None
    probable_cause = cells[3] if len(cells) > 3 else None
    ntsb_id = extract_ntsb_id(" ".join(cells))
    pdf_report_url = extract_pdf_url(detail_url, client) if detail_url else None

    return {
        "source_name": "NTSB",
        "source_url": detail_url or NTSB_SOURCE_URL,
        "ntsb_id": ntsb_id,
        "event_date": event_date,
        "location": location,
        "make_model": make_model,
        "probable_cause": probable_cause,
        "pdf_report_url": pdf_report_url
    }


def find_next_page_url(soup, current_url):
    next_link = soup.find("a", attrs={"rel": "next"})
    if not next_link:
        next_link = soup.find("a", string=re.compile(r"next", re.IGNORECASE))
    if not next_link or not next_link.get("href"):
        return None
    return urljoin(current_url, next_link["href"])


def scrape_ntsb():
    incidents = []
    current_url = NTSB_SOURCE_URL
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
                    if len(columns) < 3:
                        continue
                    detail_anchor = row.find("a", href=True)
                    detail_url = urljoin(current_url, detail_anchor["href"]) if detail_anchor else current_url
                    incidents.append(parse_ntsb_row(columns, detail_url, client))
                    rows_added += 1
                    time.sleep(0.7)

            logger.info(f"Parsed {rows_added} NTSB records from {current_url}")
            pages_scraped += 1
            current_url = find_next_page_url(soup, current_url)
            time.sleep(1.0)

    return incidents


def main():
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    incidents = scrape_ntsb()
    with open(OUTPUT_FILE, "w") as output:
        json.dump(incidents, output, indent=2)
    logger.info(f"Saved {len(incidents)} NTSB incidents to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
