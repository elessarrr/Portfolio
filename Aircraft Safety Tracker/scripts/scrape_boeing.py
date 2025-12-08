import httpx
from bs4 import BeautifulSoup
import time
import json
import os
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
TYPE_INDEX_URL = "https://aviation-safety.net/asndb/types/B"
TARGET_MODELS = ["Boeing"]  # We want all Boeing models now

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def get_soup(url, client):
    """Fetch a URL and return a BeautifulSoup object."""
    try:
        response = client.get(url, headers=HEADERS, timeout=30.0)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        logger.error(f"Error fetching {url}: {e}")
        return None

def get_model_links(client):
    """Scrape the type index page to find links for target Boeing models."""
    logger.info(f"Fetching type index from {TYPE_INDEX_URL}")
    soup = get_soup(TYPE_INDEX_URL, client)
    if not soup:
        return {}

    model_links = {}
    
    # New strategy for ASNDB pages
    # Look for links starting with /asndb/type/ and text starting with "Boeing"
    for link in soup.find_all('a', href=True):
        text = link.get_text().strip()
        href = link['href']
        
        if "/asndb/type/" in href and text.startswith("Boeing"):
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
        # Usually under a header "Narrative:" or similar div structure
        # ASN structure: often has <span class="caption">Narrative:</span> followed by text or <br>
        # Or an explicit header.
        
        # Strategy 1: Look for a header or span with "Narrative"
        narrative_elem = soup.find(string=re.compile("Narrative"))
        if narrative_elem:
            # The narrative text is usually in the parent container or following siblings
            # Often ASN puts it in a <div class="innertube"> or similar, or just after the span
            # Let's try to get the text of the parent container or the next element
            container = narrative_elem.find_parent('div') or narrative_elem.find_parent('td')
            if container:
                # Get all text, clean it up
                full_text = container.get_text(separator="\n").strip()
                # Try to isolate the part after "Narrative:"
                parts = full_text.split("Narrative:", 1)
                if len(parts) > 1:
                    narrative = parts[1].strip()
                    # Clean up common footer text if captured
                    narrative = narrative.split("Sources:")[0].strip()
        
        # Strategy 2: Extract Fatalities
        # Often in a table row: "Total: / Occupants:" or "Fatalities:"
        # Look for "Fatalities:" label
        fat_elem = soup.find(string=re.compile("Fatalities:"))
        if fat_elem:
            # Usually "Fatalities: 12 / Occupants: 150"
            parent = fat_elem.find_parent()
            if parent:
                fat_text = parent.get_text()
                # Extract the first number after "Fatalities:"
                match = re.search(r"Fatalities:\s*(\d+)", fat_text, re.IGNORECASE)
                if match:
                    fatalities = int(match.group(1))
        
    except Exception as e:
        logger.warning(f"  Error parsing details for {incident_url}: {e}")

    # Rate limiting
    time.sleep(1.0) 
    return fatalities, narrative

def scrape_model_incidents(model_name, model_url, client):
    """Scrape the list of incidents for a specific model."""
    logger.info(f"Scraping incidents for {model_name} from {model_url}")
    soup = get_soup(model_url, client)
    if not soup:
        return []

    incidents = []
    
    # ASN tables usually have class "infotable" or generic <table>
    # Strategy: Find the table that contains "acc. date" or "operator" in the header
    tables = soup.find_all('table')
    table = None
    
    for t in tables:
        # Check if header row exists and contains expected columns
        header_text = t.get_text().lower()
        if "acc. date" in header_text and "operator" in header_text:
            table = t
            break
            
    if not table:
        # Fallback to finding table with class 'infotable'
        table = soup.find('table', class_='infotable')
        
    if not table:
        # Last resort: use the table with the most rows
        if tables:
            table = max(tables, key=lambda t: len(t.find_all('tr')))
    
    if not table:
        logger.warning(f"No table found for {model_name}")
        return []

    # Iterate over rows, skipping header
    rows = table.find_all('tr')
    logger.info(f"Found {len(rows)} rows for {model_name}")
    
    for row in rows[1:]: # Skip header
        cols = row.find_all('td')
        if len(cols) < 4:
            # logger.info(f"Skipping row with {len(cols)} columns") # Reduce noise
            continue
            
        try:
            # Extract basic data
            # Col 0: Date (with link)
            date_col = cols[0]
            date_text = date_col.get_text().strip()
            link_elem = date_col.find('a')
            
            if not link_elem:
                # logger.info("Skipping row: No link in date column")
                continue
                
            incident_url = urljoin(BASE_URL, link_elem['href'])
            # logger.info(f"Checking incident URL: {incident_url}")
            
            # Col 1: Type
            aircraft_type = cols[1].get_text().strip()
            
            # Col 2: Registration (sometimes) or Operator
            # ASN columns vary. Usually: Date, Type, Registration, Operator, Fat., Location, Cat.
            # Let's verify header if possible, but assuming standard layout:
            # 0: Date, 1: Type, 2: Reg, 3: Operator, 4: Fat., 5: Location, 6: Cat
            
            operator = "Unknown"
            location = "Unknown"
            category = "Unknown"
            
            if len(cols) >= 7:
                operator = cols[3].get_text().strip()
                location = cols[5].get_text().strip()
                category = cols[6].get_text().strip()
            
            # Skip if date is just a year (sometimes index pages link to year pages)
            # If the link text is just a year (4 digits), we might need to drill down further.
            # However, the "type" page usually lists individual incidents.
            # Let's check if the URL looks like an incident (usually 'wikibase' or 'database/record.php' or 'asndb')
            if "database/record.php" not in incident_url and "wikibase" not in incident_url and "/asndb/" not in incident_url:
                logger.info(f"Skipping non-incident link: {incident_url}")
                continue

            # Deep dive for details
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

def main():
    output_file = "data/raw/boeing_incidents.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    all_incidents = []
    
    with httpx.Client() as client:
        # Step 1: Get links for target models
        model_links = get_model_links(client)
        
        # Step 2: Scrape each model
        for model_name, url in model_links.items():
            model_incidents = scrape_model_incidents(model_name, url, client)
            all_incidents.extend(model_incidents)
            # Save progress periodically
            with open(output_file, 'w') as f:
                json.dump(all_incidents, f, indent=2)
            
            # Pause between models
            time.sleep(2.0)

    logger.info(f"Scraping complete. Saved {len(all_incidents)} incidents to {output_file}")

if __name__ == "__main__":
    main()
