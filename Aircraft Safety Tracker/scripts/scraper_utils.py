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

def get_soup(url, client, retries=3, backoff_seconds=1.5):
    for attempt in range(1, retries + 1):
        try:
            response = client.get(url, headers=HEADERS, timeout=30.0)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            if attempt == retries:
                logger.error(f"Error fetching {url}: {e}")
                return None
            sleep_seconds = backoff_seconds * attempt
            logger.warning(f"Retry {attempt}/{retries} for {url} after error: {e}")
            time.sleep(sleep_seconds)


def extract_variant_name(model_name, aircraft_type):
    normalized_type = (aircraft_type or "").strip()
    if not normalized_type:
        return model_name

    if "(" in normalized_type and ")" in normalized_type:
        return normalized_type

    normalized_model = (model_name or "").strip()
    if normalized_model and normalized_type.lower().startswith(normalized_model.lower()):
        suffix = normalized_type[len(normalized_model):].strip()
        if suffix:
            return f"{normalized_model} {suffix}".strip()
        return normalized_model

    return normalized_type


def extract_incident_metadata(soup, narrative):
    page_text = soup.get_text(" ", strip=True) if soup else ""
    full_text = f"{page_text} {narrative or ''}"

    phase_patterns = {
        "takeoff": r"\btake[- ]?off\b|\binitial climb\b",
        "climb": r"\bclimb\b|\bclimbing\b",
        "cruise": r"\bcruise\b|\ben route\b",
        "descent": r"\bdescent\b|\bdescending\b",
        "approach": r"\bapproach\b|\bfinal\b",
        "landing": r"\blanding\b|\btouchdown\b",
        "taxi": r"\btaxi\b|\bground operations\b"
    }

    weather_patterns = {
        "IMC": r"\bimc\b|\binstrument meteorological conditions\b|\blow visibility\b",
        "VMC": r"\bvmc\b|\bvisual meteorological conditions\b|\bclear weather\b",
        "Thunderstorm": r"\bthunderstorm\b|\bstorm\b",
        "Icing": r"\bicing\b|\bice\b|\bfreezing\b",
        "Fog": r"\bfog\b|\bmist\b",
        "Rain": r"\brain\b|\bheavy rain\b",
        "Snow": r"\bsnow\b|\bblizzard\b"
    }

    phase_of_flight = None
    for phase, pattern in phase_patterns.items():
        if re.search(pattern, full_text, re.IGNORECASE):
            phase_of_flight = phase
            break

    weather_conditions = None
    for weather, pattern in weather_patterns.items():
        if re.search(pattern, full_text, re.IGNORECASE):
            weather_conditions = weather
            break

    return phase_of_flight, weather_conditions

def get_model_links(client, type_index_url, manufacturer_prefix):
    """Scrape the type index page to find links for target models."""
    logger.info(f"Fetching type index from {type_index_url}")
    soup = get_soup(type_index_url, client)
    if not soup:
        return {}

    model_links = {}
    
    manufacturer_prefix_normalized = (manufacturer_prefix or "").strip().lower()

    skipped_non_matching = 0
    skipped_empty_text = 0
    skipped_duplicate = 0
    captured = 0

    for link in soup.find_all('a', href=True):
        href = (link.get('href') or '').strip()
        if "/asndb/type/" not in href:
            continue

        text = (link.get_text() or '').replace('\xa0', ' ').strip()
        if not text:
            skipped_empty_text += 1
            continue

        if manufacturer_prefix_normalized and not text.lower().startswith(manufacturer_prefix_normalized):
            skipped_non_matching += 1
            continue

        full_url = urljoin(BASE_URL, href)
        if text in model_links:
            skipped_duplicate += 1
            continue

        model_links[text] = full_url
        captured += 1
        logger.debug(f"Found model link: {text} -> {full_url}")

    logger.info(
        "Discovered %s model links from %s (skipped: %s non-matching, %s empty-text, %s duplicates)",
        captured,
        type_index_url,
        skipped_non_matching,
        skipped_empty_text,
        skipped_duplicate,
    )

    return model_links

def scrape_incident_details(incident_url, client):
    logger.info(f"  Scraping details: {incident_url}")
    soup = get_soup(incident_url, client)
    if not soup:
        return None, None, {"phase_of_flight": None, "weather_conditions": None}

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

    phase_of_flight, weather_conditions = extract_incident_metadata(soup, narrative)
    time.sleep(1.0) 
    return fatalities, narrative, {
        "phase_of_flight": phase_of_flight,
        "weather_conditions": weather_conditions
    }

def scrape_model_incidents(model_name, model_url, client):
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

            fatalities, narrative, metadata = scrape_incident_details(incident_url, client)
            variant_name = extract_variant_name(model_name, aircraft_type)
            
            incident = {
                "model_name": model_name,
                "variant_name": variant_name,
                "date": date_text,
                "type": aircraft_type,
                "operator": operator,
                "location": location,
                "category": category,
                "fatalities": fatalities,
                "narrative": narrative,
                "phase_of_flight": metadata.get("phase_of_flight"),
                "weather_conditions": metadata.get("weather_conditions"),
                "asn_url": incident_url
            }
            
            incidents.append(incident)
            logger.info(f"  Captured incident: {date_text} - {operator} ({fatalities} fatal)")
            
        except Exception as e:
            logger.error(f"Error parsing row for {model_name}: {e}")
            continue

    return incidents
