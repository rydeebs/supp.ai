import requests
from bs4 import BeautifulSoup
import time
import re # Regular expressions for finding text
import logging

# --- Configuration ---
# Delay to be polite to servers. Increase if getting blocked. Crucial for Amazon/Walmart.
REQUEST_DELAY_SECONDS = 3
HEADERS = {
    # Using a common browser User-Agent can help avoid simple blocks
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Cache-Control': 'max-age=0',
}

# --- Logging Setup ---
# Configure logging (optional, but helpful for debugging)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Helper Functions ---

def fetch_page(url):
    """Fetches the HTML content of a given URL."""
    logging.info(f"Attempting to fetch: {url}")
    try:
        response = requests.get(url, headers=HEADERS, timeout=25) # Increased timeout
        # Check if the request was successful
        response.raise_for_status()
        logging.info(f"Successfully fetched {url} with status code {response.status_code}")
        # Check content type to avoid trying to parse non-HTML (like images directly)
        if 'text/html' not in response.headers.get('Content-Type', ''):
            logging.warning(f"Content-Type for {url} is not text/html: {response.headers.get('Content-Type')}")
            # Depending on your needs, you might return None or the raw content
            # For this scraper, we primarily want HTML
            return None
        return response.text
    except requests.exceptions.Timeout:
        logging.error(f"Timeout error fetching {url}")
        return None
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP error fetching {url}: {e.status_code} {e.response.reason}")
        # Specific handling for common blocking codes
        if e.response.status_code == 403: # Forbidden
             logging.error("-> Access Forbidden (403). Likely blocked by anti-scraping measures.")
        elif e.response.status_code == 404: # Not Found
             logging.error("-> Page Not Found (404).")
        elif e.response.status_code == 503: # Service Unavailable
             logging.error("-> Service Unavailable (503). May be temporary or anti-scraping.")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"General error fetching {url}: {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred during fetch for {url}: {e}")
        return None

def find_text_near_keyword(soup, keywords, tag_types=['p', 'div', 'span', 'li', 'td', 'section', 'article']):
    """
    Tries to find text content located near specified keywords within given tag types.
    Improved logic to check siblings, parents, and specific structures.
    NOTE: This is a generic approach. Site-specific selectors are usually more reliable.
    """
    found_text = [] # Collect potential matches
    try:
        # 1. Find headings (h1-h6) with the keyword and get the *following sibling element's text*
        for keyword in keywords:
            headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'], string=re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE))
            for heading in headings:
                content_element = heading.find_next_sibling()
                while content_element and (not content_element.name or not content_element.get_text(strip=True)): # Skip empty/non-existent tags
                    content_element = content_element.find_next_sibling()

                if content_element:
                    text = content_element.get_text(separator=' ', strip=True)
                    if len(text) > 15: # Basic sanity check
                        found_text.append(text)
                        # Often the first good match is enough
                        # return text # Uncomment if you want to return the first match immediately

        # 2. Find elements containing the keyword directly and check siblings/parents
        for keyword in keywords:
            # Use lambda for flexibility - check text within specified tag types
            elements = soup.find_all(lambda tag: tag.name in tag_types and re.search(r'\b' + re.escape(keyword) + r'\b', tag.get_text(), re.IGNORECASE))
            for element in elements:
                # Option A: Check next sibling
                sibling = element.find_next_sibling()
                if sibling and sibling.get_text(strip=True):
                    text = sibling.get_text(separator=' ', strip=True)
                    if len(text) > 15 and text not in found_text:
                        found_text.append(text)

                # Option B: Check parent's text, if it's reasonably sized and contains keyword near start
                parent = element.parent
                if parent:
                    parent_text = parent.get_text(separator=' ', strip=True)
                    kw_pos = parent_text.lower().find(keyword.lower())
                    # Avoid grabbing huge chunks of unrelated text
                    if kw_pos != -1 and kw_pos < 200 and len(parent_text) > 20 and len(parent_text) < 5000 and parent_text not in found_text:
                       found_text.append(parent_text)

                # Option C: The element itself (if it's substantial)
                element_text = element.get_text(separator=' ', strip=True)
                if len(element_text) > 20 and element_text not in found_text and keyword.lower() in element_text.lower():
                     found_text.append(element_text)


    except Exception as e:
        logging.warning(f"Error during keyword search: {e}")

    # Prioritize longer, more relevant texts if multiple found
    if not found_text:
        return None

    # Simple way to choose the longest result, assuming it's most complete
    # More sophisticated ranking could be added (e.g., based on keyword proximity)
    found_text.sort(key=len, reverse=True)
    return found_text[0] # Return the longest match


def parse_ingredients(soup):
    """Attempts to parse ingredients from the BeautifulSoup object."""
    # Added more keyword variations
    ingredient_keywords = [
        'ingredients', 'supplement facts', 'other ingredients',
        'nutrition facts', 'components', 'composition', 'contains'
        # Add site-specific terms if needed, e.g., 'What\'s Inside'
    ]
    # Site-specific selectors (EXAMPLES - replace with actual selectors found via inspection)
    # if soup.find('div', class_='ingredient-list-class'):
    #     return soup.find('div', class_='ingredient-list-class').get_text(separator=' ', strip=True)
    # if soup.select_one('#ingredients-section-id'):
    #     return soup.select_one('#ingredients-section-id').get_text(separator=' ', strip=True)

    ingredients = find_text_near_keyword(soup, ingredient_keywords)

    if ingredients:
        # Basic check: Target URL might only give "Creatine Monohydrate." in text.
        # This is a very specific check, might need refinement.
        if "Creatine Monohydrate." in ingredients and len(ingredients) < 50:
             logging.warning("Found only basic ingredient text, full details might be in an image.")
        return ingredients
    else:
        logging.warning("Could not find ingredients using keyword search.")
        # Add a fallback for Target's specific structure if needed
        target_details = soup.find('h3', string=re.compile("Ingredients", re.IGNORECASE))
        if target_details and target_details.find_next_sibling('div'):
             ing_text = target_details.find_next_sibling('div').get_text(separator=' ', strip=True)
             if ing_text:
                 logging.info("Found potential ingredients in Target specific structure.")
                 return ing_text

    return "Ingredients not found (check HTML structure or image)"


def parse_directions(soup):
    """Attempts to parse directions from the BeautifulSoup object."""
    direction_keywords = [
        'directions', 'suggested use', 'how to use', 'usage',
        'recommended dose', 'instructions', 'serving suggestion'
    ]
    # Site-specific selectors (EXAMPLES)
    # if soup.find('div', id='directions-for-use'):
    #     return soup.find('div', id='directions-for-use').get_text(separator=' ', strip=True)

    directions = find_text_near_keyword(soup, direction_keywords)

    if directions:
        return directions
    else:
        logging.warning("Could not find directions using keyword search.")
        return "Directions not found (check HTML structure or image)"

# --- Main Scraping Function (callable) ---

def scrape_single_url(url):
    """
    Scrapes a single URL for ingredients and directions.
    Returns a dictionary with results.
    """
    # Basic URL validation
    if not isinstance(url, str) or not url.startswith(('http://', 'https://')):
        logging.warning(f"Invalid URL format: {url}")
        return {
            'URL': url,
            'Ingredients': 'Invalid URL format',
            'Directions': 'Invalid URL format',
            'Status': 'Failed - Invalid URL'
        }

    html_content = fetch_page(url)
    # Add delay *after* fetching, before heavy parsing, to respect servers
    logging.info(f"Waiting {REQUEST_DELAY_SECONDS} seconds before processing...")
    time.sleep(REQUEST_DELAY_SECONDS)

    if html_content:
        try:
            # Use lxml for better performance and handling of broken HTML
            soup = BeautifulSoup(html_content, 'lxml')

            ingredients = parse_ingredients(soup)
            directions = parse_directions(soup)

            # Log success based on finding *something*
            status = 'Success'
            if ingredients.startswith("Ingredients not found") and directions.startswith("Directions not found"):
                status = 'Partial Success - Data likely incomplete or in images'
            elif ingredients.startswith("Ingredients not found"):
                 status = 'Partial Success - Ingredients missing'
            elif directions.startswith("Directions not found"):
                 status = 'Partial Success - Directions missing'


            logging.info(f"-> Scrape result for {url}: Status={status}")
            return {
                'URL': url,
                'Ingredients': ingredients,
                'Directions': directions,
                'Status': status
            }

        except Exception as e:
            logging.error(f"Error parsing HTML for {url}: {e}")
            return {
                'URL': url,
                'Ingredients': 'Parsing Error',
                'Directions': 'Parsing Error',
                'Status': f'Failed - Parsing Error ({e})'
            }
    else:
        # Fetch error details are logged in fetch_page
        return {
            'URL': url,
            'Ingredients': 'Fetch Error',
            'Directions': 'Fetch Error',
            'Status': 'Failed - Could not fetch URL'
        }

# Note: No `if __name__ == "__main__":` block here,
# as this file is intended to be imported as a module.
