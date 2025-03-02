import requests
from bs4 import BeautifulSoup
import random
import os
from fake_useragent import UserAgent
import logging
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('minister_agendas.log')
    ]
)
logger = logging.getLogger(__name__)

# Initialize UserAgent for random browser/device mimicking
ua = UserAgent()

# Base URL
BASE_URL = "https://www.quebec.ca/gouvernement/gouvernement-ouvert/transparence-performance/agenda-membres-conseil-ministres"

# Directories to save CSV files
OUTPUT_DIR = "minister_agendas"
ACTIVE_MINISTERS_DIR = os.path.join(OUTPUT_DIR, "active")
INACTIVE_MINISTERS_DIR = os.path.join(OUTPUT_DIR, "inactive")
os.makedirs(ACTIVE_MINISTERS_DIR, exist_ok=True)
os.makedirs(INACTIVE_MINISTERS_DIR, exist_ok=True)

def get_random_headers():
    """Generate random headers with different User-Agent"""
    return {
        "User-Agent": ua.random,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://www.google.com/",
        "Connection": "keep-alive"
    }

def download_csv(url, filename, is_active=True):
    """Download CSV file with random headers"""
    try:
        headers = get_random_headers()
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        output_dir = ACTIVE_MINISTERS_DIR if is_active else INACTIVE_MINISTERS_DIR
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'wb') as f:
            f.write(response.content)
        logger.info(f"Downloaded: {filename} to {'active' if is_active else 'inactive'} directory")
        logger.debug(f"Used User-Agent: {headers['User-Agent']}")
    except requests.RequestException as e:
        logger.error(f"Failed to download {filename}: {e}")

def get_minister_links(soup, section_id):
    """Extract minister links from specified section"""
    section = soup.select_one(f"div#{section_id}")
    if not section:
        logger.debug(f"No section found with id: {section_id}")
        return []
    
    minister_items = section.select("ul.ministres-list li.ministre-item a")
    # Get just the last part of the href (minister name)
    links = []
    for item in minister_items:
        if href := item.get('href'):
            # Extract just the minister name part
            minister_path = href.split('/')[-1]
            links.append(minister_path)
    logger.debug(f"Found {len(links)} links in section {section_id}")
    return links

def get_csv_link(page_url):
    """Find CSV download link on minister's detail page"""
    headers = get_random_headers()
    response = requests.get(page_url, headers=headers)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    logger.debug(f"Looking for CSV link on page: {page_url}")
    
    # Find links containing both 'csv' and 'agenda' in their text
    all_links = soup.find_all('a')
    for link in all_links:
        text = ' '.join(link.get_text().split())  # Normalize whitespace
        href = link.get('href')
        logger.debug(f"Checking link - Text: '{text}', href: '{href}'")
        if 'csv' in text.lower() and 'agenda' in text.lower():
            if href:
                full_url = urljoin(page_url, href)
                logger.debug(f"Found CSV link: {href} -> {full_url}")
                return full_url
    
    logger.debug(f"No CSV link found for {page_url}")
    return None

def main():
    logger.info("Starting minister agenda download process")
    
    # Get main page
    headers = get_random_headers()
    response = requests.get(BASE_URL, headers=headers)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Step 2a: Get active ministers' links
    active_minister_links = get_minister_links(soup, "ministres-actifs")
    logger.info(f"Found {len(active_minister_links)} active ministers")
    
    # Step 3a: Get inactive ministers' links
    inactive_minister_links = get_minister_links(soup, "anciens-membres")
    logger.info(f"Found {len(inactive_minister_links)} inactive ministers")
    
    # Process active ministers
    for minister_path in active_minister_links:
        try:
            minister_url = f"{BASE_URL}/{minister_path}"
            csv_url = get_csv_link(minister_url)
            if csv_url:
                csv_filename = csv_url.split('/')[-1]
                download_csv(csv_url, csv_filename, is_active=True)
            else:
                logger.warning(f"No CSV link found for active minister {minister_path}")
        except Exception as e:
            logger.error(f"Error processing active minister {minister_path}: {e}", exc_info=True)
    
    # Process inactive ministers
    for minister_path in inactive_minister_links:
        try:
            minister_url = f"{BASE_URL}/{minister_path}"
            csv_url = get_csv_link(minister_url)
            if csv_url:
                csv_filename = csv_url.split('/')[-1]
                download_csv(csv_url, csv_filename, is_active=False)
            else:
                logger.warning(f"No CSV link found for inactive minister {minister_path}")
        except Exception as e:
            logger.error(f"Error processing inactive minister {minister_path}: {e}", exc_info=True)

    logger.info("Minister agenda download process completed")

if __name__ == "__main__":
    main()