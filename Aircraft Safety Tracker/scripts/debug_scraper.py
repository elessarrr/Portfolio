import httpx
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://aviation-safety.net/database/type/",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1"
}

URL = "https://aviation-safety.net/asndb/types/A"

def test_fetch():
    try:
        with httpx.Client(follow_redirects=True) as client:
            logger.info(f"Fetching {URL}...")
            response = client.get(URL, headers=HEADERS)
            logger.info(f"Status: {response.status_code}")
            if response.status_code == 200:
                logger.info("Success! checking for Airbus links...")
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find Airbus links
                for a in soup.find_all('a', href=True):
                    if a.text.strip().startswith("Airbus "):
                        logger.info(f"Found Airbus: {a.text.strip()} | Href: {a['href']}")
    except Exception as e:
        logger.error(f"Exception: {e}")

if __name__ == "__main__":
    test_fetch()
