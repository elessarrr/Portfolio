import httpx
import time
import json
import os
import logging
from scraper_utils import get_model_links, scrape_model_incidents

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

TYPE_INDEX_URL = "https://aviation-safety.net/asndb/types/B"
MANUFACTURER_PREFIX = "Boeing"

def main():
    output_file = "data/raw/boeing_incidents.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    all_incidents = []
    
    with httpx.Client() as client:
        # Step 1: Get links for target models
        model_links = get_model_links(client, TYPE_INDEX_URL, MANUFACTURER_PREFIX)
        
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
