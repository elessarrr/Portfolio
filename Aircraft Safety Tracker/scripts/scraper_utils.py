import httpx
from bs4 import BeautifulSoup
import time
import re
import logging
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BASE_URL = "https://aviation-safety.net"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def get_soup(url, client, *, max_retries=4, base_delay=2.0, sleep=time.sleep):
    """Fetch a URL and return a BeautifulSoup object.

    Handles HTTP 429 (Too Many Requests) with exponential backoff, respecting a
    `Retry-After` header when present. Without this, ASN rate-limiting silently
    drops incidents (the catch we hit on the big backfill run). Other errors are
    logged and return None as before.
    """
    for attempt in range(max_retries + 1):
        try:
            response = client.get(url, headers=HEADERS, timeout=30.0)
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

        if response.status_code == 429:
            if attempt < max_retries:
                retry_after = response.headers.get("Retry-After")
                try:
                    wait = float(retry_after) if retry_after else base_delay * (2 ** attempt)
                except (TypeError, ValueError):
                    wait = base_delay * (2 ** attempt)
                logger.warning(
                    f"429 Too Many Requests for {url}; backing off {wait:.1f}s "
                    f"(attempt {attempt + 1}/{max_retries})"
                )
                sleep(wait)
                continue
            logger.error(f"429 Too Many Requests for {url}: exhausted {max_retries} retries")
            return None

        try:
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
        return BeautifulSoup(response.text, 'html.parser')

    return None

def get_model_links(client, type_index_url, manufacturer_prefix):
    """Scrape the type index page to find links for target models."""
    logger.info(f"Fetching type index from {type_index_url}")
    soup = get_soup(type_index_url, client)
    if not soup:
        return {}

    model_links = {}
    
    # Look for links starting with /asndb/type/ and text starting with the manufacturer
    for link in soup.find_all('a', href=True):
        text = link.get_text().strip()
        href = link['href']
        
        if "/asndb/type/" in href and text.startswith(manufacturer_prefix):
            full_url = urljoin(BASE_URL, href)
            model_links[text] = full_url
            logger.info(f"Found model link: {text} -> {full_url}")

    return model_links

def scrape_incident_details(incident_url, client):
    """Scrape details (fatalities, narrative) from an incident page."""
    logger.info(f"  Scraping details: {incident_url}")
    soup = get_soup(incident_url, client)
    if not soup:
        return None, None

    narrative = "Narrative not available."
    fatalities = 0

    try:
        # Extract Narrative
        narrative_elem = soup.find(string=re.compile("Narrative"))
        if narrative_elem:
            container = narrative_elem.find_parent('div') or narrative_elem.find_parent('td')
            if container:
                full_text = container.get_text(separator="\n").strip()
                parts = full_text.split("Narrative:", 1)
                if len(parts) > 1:
                    narrative = parts[1].strip()
                    narrative = narrative.split("Sources:")[0].strip()
        
        # Extract Fatalities
        fat_elem = soup.find(string=re.compile("Fatalities:"))
        if fat_elem:
            parent = fat_elem.find_parent()
            if parent:
                fat_text = parent.get_text(separator=" ")
                match = re.search(r"Fatalities:?\s*(\d+)", fat_text, re.IGNORECASE)
                if match:
                    fatalities = int(match.group(1))
                else:
                    grandparent = parent.find_parent()
                    if grandparent:
                        gp_text = grandparent.get_text(separator=" ")
                        match = re.search(r"Fatalities:?\s*(\d+)", gp_text, re.IGNORECASE)
                        if match:
                            fatalities = int(match.group(1))
        
    except Exception as e:
        logger.warning(f"  Error parsing details for {incident_url}: {e}")

    # Rate limiting
    time.sleep(1.0) 
    return fatalities, narrative

def scrape_model_incidents(model_name, model_url, client, known_urls=frozenset()):
    """Scrape the list of incidents for a specific model.

    known_urls: set of asn_url values already in the DB. Any incident whose URL
    is in this set skips the expensive detail-page fetch entirely — making weekly
    runs fast (only truly new incidents require network calls).
    """
    logger.info(f"Scraping incidents for {model_name} from {model_url}")
    soup = get_soup(model_url, client)
    if not soup:
        return []

    incidents = []
    
    tables = soup.find_all('table')
    table = None
    
    for t in tables:
        header_text = t.get_text().lower()
        if "acc. date" in header_text and "operator" in header_text:
            table = t
            break
            
    if not table:
        table = soup.find('table', class_='infotable')
        
    if not table:
        if tables:
            table = max(tables, key=lambda t: len(t.find_all('tr')))
    
    if not table:
        logger.warning(f"No table found for {model_name}")
        return []

    rows = table.find_all('tr')
    logger.info(f"Found {len(rows)} rows for {model_name}")
    
    for row in rows[1:]: # Skip header
        cols = row.find_all('td')
        if len(cols) < 4:
            continue
            
        try:
            date_col = cols[0]
            date_text = date_col.get_text().strip()
            link_elem = date_col.find('a')
            
            if not link_elem:
                continue
                
            incident_url = urljoin(BASE_URL, link_elem['href'])
            
            aircraft_type = cols[1].get_text().strip()
            
            operator = "Unknown"
            location = "Unknown"
            category = "Unknown"
            
            if len(cols) >= 7:
                operator = cols[3].get_text().strip()
                location = cols[5].get_text().strip()
                category = cols[6].get_text().strip()
            
            if "database/record.php" not in incident_url and "wikibase" not in incident_url and "/asndb/" not in incident_url:
                logger.info(f"Skipping non-incident link: {incident_url}")
                continue

            if incident_url in known_urls:
                logger.debug(f"Skipping already-known incident: {incident_url}")
                continue

            fatalities, narrative = scrape_incident_details(incident_url, client)
            
            incident = {
                "model_name": model_name,
                "date": date_text,
                "type": aircraft_type,
                "operator": operator,
                "location": location,
                "category": category,
                "fatalities": fatalities,
                "narrative": narrative,
                "asn_url": incident_url
            }
            
            incidents.append(incident)
            logger.info(f"  Captured incident: {date_text} - {operator} ({fatalities} fatal)")
            
        except Exception as e:
            logger.error(f"Error parsing row for {model_name}: {e}")
            continue

    return incidents
