# scraper_module.py
import requests
from bs4 import BeautifulSoup
import time
import re
import logging

# --- Configuration (Keep as before) ---
REQUEST_DELAY_SECONDS = 3
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Cache-Control': 'max-age=0',
}

# --- Logging Setup (Keep as before) ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Constants ---
MIN_TEXT_LENGTH = 20 # Minimum characters to consider a result valid
MAX_PARENT_TEXT_LENGTH = 4000 # Max characters when grabbing parent text to avoid whole page sections
PARTIAL_INGREDIENTS_NOTE = " [Partial Data Possible - Check Image/Full Description]"

# --- Fetch Function (Keep as before) ---
def fetch_page(url):
    logging.info(f"Attempting to fetch: {url}")
    try:
        response = requests.get(url, headers=HEADERS, timeout=25)
        response.raise_for_status()
        logging.info(f"Successfully fetched {url} with status code {response.status_code}")
        if 'text/html' not in response.headers.get('Content-Type', ''):
            logging.warning(f"Content-Type for {url} is not text/html: {response.headers.get('Content-Type')}")
            return None
        return response.text
    # ... (rest of exception handling as before) ...
    except requests.exceptions.Timeout:
        logging.error(f"Timeout error fetching {url}")
        return None
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP error fetching {url}: {e.response.status_code} {e.response.reason}")
        if e.response.status_code == 403: logging.error("-> Access Forbidden (403). Likely blocked by anti-scraping measures.")
        elif e.response.status_code == 404: logging.error("-> Page Not Found (404).")
        elif e.response.status_code == 503: logging.error("-> Service Unavailable (503). May be temporary or anti-scraping.")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"General error fetching {url}: {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred during fetch for {url}: {e}")
        return None


# --- NEW: Scraping Strategy Helper Functions ---

def find_by_specific_attributes(soup, keyword_variations):
    """Strategy 1: Look for elements with id/class containing keywords."""
    try:
        for key in keyword_variations:
            # Regex to find id/class containing the keyword (case-insensitive)
            # Example: id="ingredients", class="product-ingredients", id="supplementFacts"
            elements = soup.find_all(lambda tag: tag.has_attr('id') and re.search(key, tag['id'], re.IGNORECASE) or \
                                                tag.has_attr('class') and any(re.search(key, c, re.IGNORECASE) for c in tag['class']))
            for element in elements:
                text = element.get_text(separator=' ', strip=True)
                if len(text) >= MIN_TEXT_LENGTH:
                    logging.info(f"Strategy 1 SUCCESS: Found via attribute matching '{key}'")
                    return text
    except Exception as e:
        logging.warning(f"Error in Strategy 1 (Attributes): {e}")
    return None

def find_by_heading_sibling(soup, keywords):
    """Strategy 2: Look for heading containing keyword, get next sibling's text."""
    try:
        heading_tags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'b']
        for keyword in keywords:
            # Find heading tags containing the keyword text
            headings = soup.find_all(heading_tags, string=re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE))
            for heading in headings:
                sibling = heading.find_next_sibling()
                # Find the *first* actual content sibling, skipping empty tags/navigable strings
                while sibling and (not sibling.name or not sibling.get_text(strip=True)):
                    sibling = sibling.find_next_sibling()

                if sibling:
                    text = sibling.get_text(separator=' ', strip=True)
                    if len(text) >= MIN_TEXT_LENGTH:
                        logging.info(f"Strategy 2 SUCCESS: Found via heading '{keyword}' + sibling")
                        return text
    except Exception as e:
        logging.warning(f"Error in Strategy 2 (Heading+Sibling): {e}")
    return None

def find_by_keyword_in_tag(soup, keywords):
    """Strategy 3: Look for p/div/li starting with the keyword."""
    try:
        tags_to_check = ['p', 'div', 'li']
        for keyword in keywords:
            # Regex: starts with optional whitespace, keyword, optional colon, whitespace
            pattern = re.compile(r'^\s*' + re.escape(keyword) + r':?\s+', re.IGNORECASE)
            elements = soup.find_all(tags_to_check, string=pattern)
            for element in elements:
                text = element.get_text(separator=' ', strip=True)
                if len(text) >= MIN_TEXT_LENGTH:
                    logging.info(f"Strategy 3 SUCCESS: Found via keyword '{keyword}' inside tag")
                    # Check if it looks like Olly's "Other Ingredients" case
                    if "other ingredients" in keyword.lower() and len(text) < 250: # Arbitrary short length check
                         return text + PARTIAL_INGREDIENTS_NOTE
                    return text
    except Exception as e:
        logging.warning(f"Error in Strategy 3 (KeywordInTag): {e}")
    return None

def find_by_definition_list(soup, keywords):
    """Strategy 4: Look for keyword in <dt>, get text from next <dd>."""
    try:
        for keyword in keywords:
            # Find <dt> tags containing the keyword
            dts = soup.find_all('dt', string=re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE))
            for dt in dts:
                dd = dt.find_next_sibling('dd')
                # Sometimes there might be non-DD siblings in between
                current = dt
                while not dd and current.find_next_sibling():
                    current = current.find_next_sibling()
                    if current.name == 'dd':
                        dd = current
                        break # Found it

                if dd:
                    text = dd.get_text(separator=' ', strip=True)
                    if len(text) >= MIN_TEXT_LENGTH:
                        logging.info(f"Strategy 4 SUCCESS: Found via definition list (<dt> '{keyword}')")
                        return text
    except Exception as e:
        logging.warning(f"Error in Strategy 4 (DefinitionList): {e}")
    return None

def find_by_parent_text(soup, keywords):
    """Strategy 5 (Fallback): Find element with keyword, get parent's text."""
    try:
        tags_to_check = ['p', 'div', 'span', 'li', 'td', 'section', 'article', 'b', 'strong']
        for keyword in keywords:
             # Find any element containing the keyword
            elements = soup.find_all(lambda tag: tag.name in tags_to_check and re.search(r'\b' + re.escape(keyword) + r'\b', tag.get_text(), re.IGNORECASE))
            for element in elements:
                parent = element.parent
                if parent:
                    parent_text = parent.get_text(separator=' ', strip=True)
                    # Check if keyword is near start and text isn't excessively long
                    kw_pos = parent_text.lower().find(keyword.lower())
                    if kw_pos != -1 and kw_pos < 200 and len(parent_text) >= MIN_TEXT_LENGTH and len(parent_text) <= MAX_PARENT_TEXT_LENGTH:
                        logging.info(f"Strategy 5 SUCCESS: Found via parent text containing '{keyword}'")
                        return parent_text
    except Exception as e:
        logging.warning(f"Error in Strategy 5 (ParentText): {e}")
    return None


# --- Main Parsing Functions (Using Strategies) ---

def parse_ingredients(soup, url):
    """Attempts to parse ingredients using multiple strategies."""
    logging.debug(f"Attempting to parse ingredients for {url}")
    # Define variations for attribute searching (Strategy 1)
    attribute_keywords = ['ingredient', 'supplement', 'nutrition', 'facts']
    # Define variations for text searching (Strategies 2, 3, 4, 5)
    text_keywords = [
        'ingredients', 'supplement facts', 'other ingredients',
        'nutrition facts', 'components', 'composition', 'contains',
        'what\'s inside' # Example of adding less common variations
    ]

    result = None

    # Try strategies in order of expected reliability
    if not result: result = find_by_specific_attributes(soup, attribute_keywords)
    if not result: result = find_by_heading_sibling(soup, text_keywords)
    if not result: result = find_by_keyword_in_tag(soup, text_keywords)
    if not result: result = find_by_definition_list(soup, text_keywords)
    if not result: result = find_by_parent_text(soup, text_keywords) # Last resort

    if result:
        # Basic cleanup: remove excessive whitespace/newlines
        result = re.sub(r'\s{2,}', ' ', result).strip()
        return result
    else:
        logging.warning(f"All strategies FAILED for ingredients on {url}")
        return "Ingredients not found (check HTML structure or image)"


def parse_directions(soup, url):
    """Attempts to parse directions using multiple strategies."""
    logging.debug(f"Attempting to parse directions for {url}")
    attribute_keywords = ['direction', 'usage', 'instruction', 'how-to', 'serving']
    text_keywords = [
        'directions', 'suggested use', 'how to use', 'usage',
        'recommended dose', 'instructions', 'serving suggestion',
        'how to take', 'suggested dosage'
    ]

    result = None

    # Try strategies in order
    if not result: result = find_by_specific_attributes(soup, attribute_keywords)
    if not result: result = find_by_heading_sibling(soup, text_keywords)
    if not result: result = find_by_keyword_in_tag(soup, text_keywords)
    if not result: result = find_by_definition_list(soup, text_keywords)
    if not result: result = find_by_parent_text(soup, text_keywords)

    if result:
        result = re.sub(r'\s{2,}', ' ', result).strip()
        return result
    else:
        logging.warning(f"All strategies FAILED for directions on {url}")
        return "Directions not found (check HTML structure or image)"


# --- Main Scraping Function (Largely unchanged, calls new parsers) ---

def scrape_single_url(url):
    """
    Scrapes a single URL for ingredients and directions using multi-strategy parsing.
    Returns a dictionary with results.
    """
    if not isinstance(url, str) or not url.startswith(('http://', 'https://')):
        logging.warning(f"Invalid URL format: {url}")
        return {'URL': url, 'Ingredients': 'Invalid URL format', 'Directions': 'Invalid URL format', 'Status': 'Failed - Invalid URL'}

    html_content = fetch_page(url)
    logging.info(f"Waiting {REQUEST_DELAY_SECONDS} seconds before processing {url}...")
    time.sleep(REQUEST_DELAY_SECONDS)

    if html_content:
        try:
            soup = BeautifulSoup(html_content, 'lxml')

            ingredients = parse_ingredients(soup, url)
            directions = parse_directions(soup, url)

            # Determine status based on findings
            status = 'Success'
            not_found_ingredients = ingredients.startswith("Ingredients not found")
            not_found_directions = directions.startswith("Directions not found")
            partial_ingredients = PARTIAL_INGREDIENTS_NOTE in ingredients

            if not_found_ingredients and not_found_directions:
                status = 'Failed - No Data Found via HTML Strategies'
            elif not_found_ingredients:
                status = 'Partial Success - Directions Found Only'
            elif not_found_directions:
                 status = 'Partial Success - Ingredients Found Only'
                 if partial_ingredients: status += " (Partial Possible)" # Indicate if only 'other' ingredients might be present
            elif partial_ingredients:
                 status = 'Partial Success - Directions & Partial Ingredients Found'

            # If both found and no partial note, it's full success (from HTML perspective)
            elif not partial_ingredients and not not_found_ingredients and not not_found_directions:
                 status = 'Success - Ingredients & Directions Found'


            logging.info(f"-> Scrape result for {url}: Status={status}")
            return {
                'URL': url,
                'Ingredients': ingredients,
                'Directions': directions,
                'Status': status
            }

        except Exception as e:
            logging.error(f"Error parsing HTML for {url}: {e}", exc_info=True)
            return {
                'URL': url,
                'Ingredients': 'Parsing Error',
                'Directions': 'Parsing Error',
                'Status': f'Failed - Parsing Error'
            }
    else:
        # Fetch error details logged in fetch_page
        return {
            'URL': url,
            'Ingredients': 'Fetch Error',
            'Directions': 'Fetch Error',
            'Status': 'Failed - Could not fetch URL'
        }
