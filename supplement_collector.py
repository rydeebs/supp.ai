import requests
import pandas as pd
import re
import os
import time
from PIL import Image
from io import BytesIO
from bs4 import BeautifulSoup
import hashlib
import json
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("supplement_collector.log"),
        logging.StreamHandler()
    ]
)

# Directory for storing images
IMAGES_DIR = "supplement_images"
os.makedirs(IMAGES_DIR, exist_ok=True)

# Dictionary to map ingredients to categories and subcategories
ingredient_category_map = {
    'l-theanine': ('Cognitive & Mental Health', 'Nootropics'),
    'alpha-gpc': ('Cognitive & Mental Health', 'Nootropics'),
    'bacopa': ('Cognitive & Mental Health', 'Nootropics'),
    'ginkgo biloba': ('Cognitive & Mental Health', 'Memory & Focus'),
    'lion\'s mane': ('Cognitive & Mental Health', 'Memory & Focus'),
    '5-htp': ('Cognitive & Mental Health', 'Mood Support'),
    'st. john\'s wort': ('Cognitive & Mental Health', 'Mood Support'),
    'sam-e': ('Cognitive & Mental Health', 'Mood Support'),
    'ashwagandha': ('Cognitive & Mental Health', 'Stress & Anxiety Relief'),
    'rhodiola': ('Cognitive & Mental Health', 'Stress & Anxiety Relief'),
    
    'beta-alanine': ('Fitness & Performance', 'Pre-Workout'),
    'citrulline': ('Fitness & Performance', 'Pre-Workout'),
    'bcaa': ('Fitness & Performance', 'Post-Workout / Recovery'),
    'glutamine': ('Fitness & Performance', 'Post-Workout / Recovery'),
    'creatine': ('Fitness & Performance', 'Muscle Building'),
    'protein': ('Fitness & Performance', 'Muscle Building'),
    'whey': ('Fitness & Performance', 'Muscle Building'),
    'cordyceps': ('Fitness & Performance', 'Endurance & Energy'),
    'caffeine': ('Fitness & Performance', 'Endurance & Energy'),
    
    'glucosamine': ('Joint & Bone Health', 'Joint Support'),
    'chondroitin': ('Joint & Bone Health', 'Joint Support'),
    'msm': ('Joint & Bone Health', 'Joint Support'),
    'calcium': ('Joint & Bone Health', 'Bone Strength'),
    'vitamin d3': ('Joint & Bone Health', 'Bone Strength'),
    'vitamin k2': ('Joint & Bone Health', 'Bone Strength'),
    
    'niacin': ('Heart & Circulatory Health', 'Cholesterol Support'),
    'red yeast rice': ('Heart & Circulatory Health', 'Cholesterol Support'),
    'coq10': ('Heart & Circulatory Health', 'Blood Pressure Support'),
    'magnesium': ('Heart & Circulatory Health', 'Blood Pressure Support'),
    'beetroot': ('Heart & Circulatory Health', 'Circulation Enhancers'),
    'garlic': ('Heart & Circulatory Health', 'Circulation Enhancers'),
    
    'vitamin c': ('Immune Support', 'General Immune Boosters'),
    'zinc': ('Immune Support', 'General Immune Boosters'),
    'elderberry': ('Immune Support', 'General Immune Boosters'),
    'olive leaf': ('Immune Support', 'Antivirals'),
    'echinacea': ('Immune Support', 'Antivirals'),
    'astragalus': ('Immune Support', 'Adaptogens'),
    'schisandra': ('Immune Support', 'Adaptogens'),
    
    'glutathione': ('Cellular Health & Longevity', 'Antioxidants'),
    'resveratrol': ('Cellular Health & Longevity', 'Antioxidants'),
    'nac': ('Cellular Health & Longevity', 'Antioxidants'),
    'pqq': ('Cellular Health & Longevity', 'Mitochondrial Support'),
    'ubiquinol': ('Cellular Health & Longevity', 'Mitochondrial Support'),
    'nmn': ('Cellular Health & Longevity', 'Telomere/Anti-aging'),
    'nr': ('Cellular Health & Longevity', 'Telomere/Anti-aging'),
    'fisetin': ('Cellular Health & Longevity', 'Telomere/Anti-aging'),
    
    'tongkat ali': ('Hormonal Support', 'Testosterone Boosters'),
    'd-aspartic acid': ('Hormonal Support', 'Testosterone Boosters'),
    'dim': ('Hormonal Support', 'Estrogen Balance'),
    'maca': ('Hormonal Support', 'Estrogen Balance'),
    'vitex': ('Hormonal Support', 'Estrogen Balance'),
    'iodine': ('Hormonal Support', 'Thyroid Support'),
    'selenium': ('Hormonal Support', 'Thyroid Support'),
    'l-tyrosine': ('Hormonal Support', 'Thyroid Support'),
    'black cohosh': ('Hormonal Support', 'Menopause & PMS'),
    'evening primrose': ('Hormonal Support', 'Menopause & PMS'),
    
    'probiotic': ('Digestive Health', 'Probiotics'),
    'lactobacillus': ('Digestive Health', 'Probiotics'),
    'bifidobacterium': ('Digestive Health', 'Probiotics'),
    'inulin': ('Digestive Health', 'Prebiotics'),
    'fos': ('Digestive Health', 'Prebiotics'),
    'xos': ('Digestive Health', 'Prebiotics'),
    'amylase': ('Digestive Health', 'Digestive Enzymes'),
    'lipase': ('Digestive Health', 'Digestive Enzymes'),
    'protease': ('Digestive Health', 'Digestive Enzymes'),
    'l-glutamine': ('Digestive Health', 'Gut Lining Support'),
    'licorice root': ('Digestive Health', 'Gut Lining Support'),
    
    'multivitamin': ('Vitamins & Minerals', 'Multivitamins'),
    'vitamin a': ('Vitamins & Minerals', 'Individual Vitamins'),
    'vitamin b': ('Vitamins & Minerals', 'Individual Vitamins'),
    'vitamin e': ('Vitamins & Minerals', 'Individual Vitamins'),
    'iron': ('Vitamins & Minerals', 'Individual Minerals'),
    'potassium': ('Vitamins & Minerals', 'Individual Minerals'),
    
    'spirulina': ('Greens & Superfoods', 'Greens Powders'),
    'chlorella': ('Greens & Superfoods', 'Greens Powders'),
    'kelp': ('Greens & Superfoods', 'Algae & Sea Vegetables'),
    'dulse': ('Greens & Superfoods', 'Algae & Sea Vegetables'),
    'acai': ('Greens & Superfoods', 'Reds/Berries Powders'),
    'goji': ('Greens & Superfoods', 'Reds/Berries Powders'),
    
    'melatonin': ('Sleep & Relaxation', 'Sleep Aids'),
    'gaba': ('Sleep & Relaxation', 'Sleep Aids'),
    'glycine': ('Sleep & Relaxation', 'Sleep Aids'),
    'valerian': ('Sleep & Relaxation', 'Relaxation Support'),
    'chamomile': ('Sleep & Relaxation', 'Relaxation Support'),
    
    'garcinia cambogia': ('Weight Management', 'Appetite Suppressants'),
    'green tea extract': ('Weight Management', 'Fat Burners'),
    'yohimbine': ('Weight Management', 'Fat Burners'),
    'l-carnitine': ('Weight Management', 'Metabolism Boosters'),
    
    'milk thistle': ('Detox & Cleanse', 'Liver Support'),
    'dandelion root': ('Detox & Cleanse', 'Liver Support'),
    'cilantro': ('Detox & Cleanse', 'Heavy Metal Detox'),
    'chlorella': ('Detox & Cleanse', 'Heavy Metal Detox'),
    'psyllium husk': ('Detox & Cleanse', 'Colon Cleanses'),
    'senna': ('Detox & Cleanse', 'Colon Cleanses')
}

# Function to fetch data from Open Food Facts API
def fetch_from_off(barcode):
    """
    Fetch supplement data from Open Food Facts API by barcode
    
    Parameters:
    - barcode (str): Product barcode
    
    Returns:
    - dict or None: Product data if found, None otherwise
    """
    logging.info(f"Fetching data for barcode {barcode} from Open Food Facts")
    
    url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 1:  # Product found
                product = data['product']
                logging.info(f"Found product: {product.get('product_name', 'Unknown')}")
                
                # Get all available images, prioritizing front image
                image_url = ''
                if 'image_front_url' in product and product['image_front_url']:
                    image_url = product['image_front_url']
                elif 'image_url' in product and product['image_url']:
                    image_url = product['image_url']
                elif 'images' in product and product['images']:
                    # Get first available image key
                    for img_key in product['images']:
                        if 'url' in product['images'][img_key]:
                            image_url = product['images'][img_key]['url']
                            break
                
                # Extract nutrition facts if available
                nutrition_facts = {}
                if 'nutriments' in product:
                    for key, value in product['nutriments'].items():
                        if not key.endswith('_100g') and not key.endswith('_serving'):
                            nutrition_facts[key] = value
                
                # Check for certifications in tags
                certifications = []
                if 'labels_tags' in product:
                    cert_keywords = ['organic', 'non-gmo', 'vegan', 'gluten-free', 'kosher', 'halal', 'fair-trade']
                    for tag in product['labels_tags']:
                        for keyword in cert_keywords:
                            if keyword in tag:
                                certifications.append(tag.replace('en:', '').title())
                
                return {
                    'barcode': barcode,
                    'brand': product.get('brands', ''),
                    'product_name': product.get('product_name', ''),
                    'ingredients': product.get('ingredients_text', ''),
                    'nutrition_facts': nutrition_facts,
                    'certifications': ', '.join(certifications) if certifications else '',
                    'image_url': image_url,
                    'serving_size': product.get('serving_size', ''),
                    'country_of_origin': product.get('countries', ''),
                    'allergens': product.get('allergens', '')
                }
            else:
                logging.info(f"No product found for barcode {barcode}")
        else:
            logging.warning(f"Error fetching data: {response.status_code}")
    except Exception as e:
        logging.error(f"Exception when fetching barcode {barcode}: {e}")
    
    return None

# Function to download and save product image
# Updated function to download both product and ingredient images
def download_product_images(product_data):
    """
    Download both main product image and ingredient image
    
    Parameters:
    - product_data (dict): Product data containing image URLs
    
    Returns:
    - dict: Updated product data with local image paths
    """
    updated_data = product_data.copy()
    
    # 1. Download main product image
    if product_data.get('image_url'):
        barcode = product_data.get('barcode', 'nobarcode')
        brand = product_data.get('brand', '')
        product_name = product_data.get('product_name', '')
        
        local_path = download_image(
            product_data['image_url'],
            barcode,
            brand,
            product_name,
            is_ingredient=False
        )
        
        if local_path:
            updated_data['local_image_path'] = local_path
    
    # 2. Download ingredient image (if available)
    if product_data.get('ingredient_image_url'):
        barcode = product_data.get('barcode', 'nobarcode')
        brand = product_data.get('brand', '')
        product_name = product_data.get('product_name', '')
        
        local_path = download_image(
            product_data['ingredient_image_url'],
            barcode,
            brand,
            product_name,
            is_ingredient=True
        )
        
        if local_path:
            updated_data['local_ingredient_image_path'] = local_path
    
    return updated_data

# Updated function to download and save a single image
def download_image(url, barcode, brand, product_name, is_ingredient=False):
    """
    Download and save supplement image
    
    Parameters:
    - url (str): Image URL
    - barcode (str): Product barcode
    - brand (str): Product brand
    - product_name (str): Product name
    - is_ingredient (bool): Whether this is an ingredient image
    
    Returns:
    - str or None: Local filepath if successful, None otherwise
    """
    if not url:
        logging.warning("No image URL provided for download")
        return None
    
    try:
        # Create a filename based on product info
        safe_brand = re.sub(r'[^\w\s-]', '', brand).strip().replace(' ', '_')
        safe_product = re.sub(r'[^\w\s-]', '', product_name).strip().replace(' ', '_')
        
        # Add suffix for ingredient images
        if is_ingredient:
            filename = f"{barcode}_{safe_brand}_{safe_product}_ingredients.jpg"
        else:
            filename = f"{barcode}_{safe_brand}_{safe_product}.jpg"
            
        filepath = os.path.join(IMAGES_DIR, filename)
        
        logging.info(f"Downloading image from {url}")
        
        # Download and save the image
        response = requests.get(url, stream=True, timeout=15)
        if response.status_code == 200:
            try:
                # Try to open and resize image
                img = Image.open(BytesIO(response.content))
                
                # Check if image is valid
                img.verify()
                img = Image.open(BytesIO(response.content))  # Need to reopen after verify
                
                # Resize to reasonable dimensions for mobile app
                max_size = (800, 800)
                img.thumbnail(max_size, Image.LANCZOS)
                
                # Save with optimized quality
                img.save(filepath, "JPEG", quality=85, optimize=True)
                logging.info(f"Successfully saved image to {filepath}")
                return filepath
            except Exception as e:
                logging.error(f"Error processing image: {e}")
                # Fallback: save original image
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                logging.info(f"Saved original image to {filepath}")
                return filepath
        else:
            logging.warning(f"Failed to download image: HTTP {response.status_code}")
    except Exception as e:
        logging.error(f"Error downloading image for {barcode}: {e}")
    
    return None

# Function to fetch supplement image from alternative sources if Open Food Facts fails
def fetch_supplement_image(brand, product_name, barcode):
    """
    Attempt to find supplement image from alternative sources
    
    Parameters:
    - brand (str): Product brand
    - product_name (str): Product name
    - barcode (str): Product barcode
    
    Returns:
    - str or None: Image URL if found, None otherwise
    """
    if not brand and not product_name:
        logging.warning("Cannot search for image without brand or product name")
        return None
    
    logging.info(f"Searching for image of {brand} {product_name}")
    
    # Try Google Custom Search API (requires API key)
    def try_google_search(query):
        """Try to find supplement image using Google Custom Search API"""
        try:
            # Replace with your actual API key and CSE ID
            api_key = "YOUR_GOOGLE_API_KEY"
            cse_id = "YOUR_CSE_ID"
            
            # Check if API key is configured
            if api_key == "YOUR_GOOGLE_API_KEY":
                logging.warning("Google API key not configured, skipping Google search")
                return None
            
            url = f"https://www.googleapis.com/customsearch/v1"
            params = {
                'key': api_key,
                'cx': cse_id,
                'q': query,
                'searchType': 'image',
                'num': 1,
                'imgSize': 'medium',
                'imgType': 'photo',
                'safe': 'active'
            }
            
            logging.info(f"Performing Google image search for '{query}'")
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'items' in data and len(data['items']) > 0:
                    image_url = data['items'][0]['link']
                    logging.info(f"Found image via Google: {image_url}")
                    return image_url
                else:
                    logging.info("No image results from Google search")
            else:
                logging.warning(f"Google API returned status code: {response.status_code}")
        except Exception as e:
            logging.error(f"Error in Google image search: {e}")
        return None
    
    # Try common retailer websites using web scraping
    def try_retailer_scraping(brand, product):
        """Try to find supplement image by scraping retailer websites"""
        retailers = [
            {'name': 'amazon', 'url': f"https://www.amazon.com/s?k={brand}+{product}+supplement"},
            {'name': 'iherb', 'url': f"https://www.iherb.com/search?kw={brand}+{product}"},
            {'name': 'vitaminshop', 'url': f"https://www.vitaminshoppe.com/search?search={brand}+{product}"},
            {'name': 'gnc', 'url': f"https://www.gnc.com/search?q={brand}+{product}"}
        ]
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        
        for retailer in retailers:
            try:
                logging.info(f"Trying to scrape image from {retailer['name']}")
                response = requests.get(retailer['url'], headers=headers, timeout=15)
                
                if response.status_code != 200:
                    logging.warning(f"Failed to access {retailer['name']}: HTTP {response.status_code}")
                    continue
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Different selectors for different retailers
                if retailer['name'] == 'amazon':
                    img_tags = soup.select('img.s-image')
                    if img_tags and len(img_tags) > 0 and 'src' in img_tags[0].attrs:
                        image_url = img_tags[0]['src']
                        logging.info(f"Found image on Amazon: {image_url}")
                        return image_url
                
                elif retailer['name'] == 'iherb':
                    img_tags = soup.select('div.product-inner img')
                    for img in img_tags:
                        if 'src' in img.attrs and 'product' in img['src'].lower():
                            image_url = img['src']
                            logging.info(f"Found image on iHerb: {image_url}")
                            return image_url
                
                elif retailer['name'] == 'vitaminshop':
                    img_tags = soup.select('img.product-image')
                    if img_tags and len(img_tags) > 0 and 'src' in img_tags[0].attrs:
                        image_url = img_tags[0]['src']
                        logging.info(f"Found image on Vitamin Shoppe: {image_url}")
                        return image_url
                
                elif retailer['name'] == 'gnc':
                    img_tags = soup.select('img.product-image')
                    if img_tags and len(img_tags) > 0 and 'src' in img_tags[0].attrs:
                        image_url = img_tags[0]['src']
                        logging.info(f"Found image on GNC: {image_url}")
                        return image_url
                
                logging.info(f"No suitable image found on {retailer['name']}")
            
            except Exception as e:
                logging.error(f"Error scraping {retailer['name']}: {e}")
        
        logging.warning("Could not find image on any retailer site")
        return None
    
    # Clean brand and product name for search
    cleaned_brand = brand.replace(',', '').replace('&', 'and') if brand else ""
    cleaned_product = product_name.replace(',', '').replace('&', 'and') if product_name else ""
    
    # Skip if data is insufficient
    if not cleaned_brand and not cleaned_product:
        return None
    
    # Build search query
    search_query = f"{cleaned_brand} {cleaned_product} supplement"
    
    # Try Google search first (if configured)
    image_url = try_google_search(search_query)
    
    # If Google search failed, try retailer websites
    if not image_url:
        image_url = try_retailer_scraping(cleaned_brand, cleaned_product)
    
    # If both methods failed, log it
    if not image_url:
        logging.warning(f"Could not find any image for {brand} {product_name}")
    
    return image_url

# Function to determine category based on ingredients
def categorize_supplement(ingredients_text):
    """
    Determine supplement category and subcategory based on ingredients
    
    Parameters:
    - ingredients_text (str): Ingredient list text
    
    Returns:
    - tuple: (main_category, subcategory)
    """
    if not ingredients_text:
        return "Uncategorized", "General"
    
    ingredients_lower = ingredients_text.lower()
    
    # Count ingredient matches by category
    category_matches = {}
    subcategory_matches = {}
    
    for ingredient, (category, subcategory) in ingredient_category_map.items():
        if ingredient in ingredients_lower:
            # Increment category count
            if category in category_matches:
                category_matches[category] += 1
            else:
                category_matches[category] = 1
            
            # Increment subcategory count with (category, subcategory) as key
            key = (category, subcategory)
            if key in subcategory_matches:
                subcategory_matches[key] += 1
            else:
                subcategory_matches[key] = 1
    
    # If no matches found
    if not category_matches:
        # Try to match common supplement keywords
        common_keywords = {
            'vitamin': ('Vitamins & Minerals', 'Individual Vitamins'),
            'mineral': ('Vitamins & Minerals', 'Individual Minerals'),
            'probiotic': ('Digestive Health', 'Probiotics'),
            'protein': ('Fitness & Performance', 'Muscle Building'),
            'herb': ('Cognitive & Mental Health', 'Stress & Anxiety Relief'),
            'extract': ('Immune Support', 'General Immune Boosters'),
            'oil': ('Heart & Circulatory Health', 'Cholesterol Support')
        }
        
        for keyword, (category, subcategory) in common_keywords.items():
            if keyword in ingredients_lower:
                return category, subcategory
        
        # Still no match
        logging.info(f"Could not categorize supplement with ingredients: {ingredients_text[:100]}...")
        return "Uncategorized", "General"
    
    # Find most frequent category
    best_category = max(category_matches.items(), key=lambda x: x[1])[0]
    
    # Find most frequent subcategory within the best category
    best_subcategory = None
    max_count = 0
    
    for (cat, subcat), count in subcategory_matches.items():
        if cat == best_category and count > max_count:
            max_count = count
            best_subcategory = subcat
    
    logging.info(f"Categorized as {best_category} > {best_subcategory}")
    return best_category, best_subcategory

# Enhanced scraper specifically improved for retailer websites
def scrape_product_from_url(brand_name, product_name, product_url):
    """
    Scrape supplement data directly from a product webpage with focus on ingredients and images
    
    Parameters:
    - brand_name (str): Initial brand name guess (will be updated if better info found)
    - product_name (str): Initial product name guess (will be updated if better info found)
    - product_url (str): Direct URL to the product page on the website
    
    Returns:
    - dict: Product data including image URLs and ingredients
    """
    logging.info(f"Scraping data from {product_url}")
    
    if not product_url:
        logging.error("No product URL provided")
        return None
    
    # Initialize product data with provided info
    product_data = {
        'brand': brand_name,
        'product_name': product_name,
        'website': product_url,
        'image_url': '',
        'ingredients': '',
        'ingredient_image_url': '',  # For ingredient label image
        'directions': '',
        'warnings': '',
        'serving_size': '',
        'certifications': '',
        'gmp_certified': False,
        'third_party_tested': False,
        'allergen_free': False,
        'vegan': False,
        'gluten_free': False,
        'non_gmo': False,
        'organic': False,
        'country_of_origin': '',
    }
    
    # Identify retailer from URL to use appropriate scraping strategy
    retailer = "unknown"
    if "target.com" in product_url:
        retailer = "target"
    elif "amazon.com" in product_url:
        retailer = "amazon"
    elif "walmart.com" in product_url:
        retailer = "walmart"
    elif "gnc.com" in product_url:
        retailer = "gnc"
    elif "vitaminshoppe.com" in product_url:
        retailer = "vitaminshoppe"
    elif "iherb.com" in product_url:
        retailer = "iherb"
    
    logging.info(f"Detected retailer: {retailer}")
    
    # Set up headers to mimic a browser request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0'
    }
    
    try:
        # Fetch the page content
        response = requests.get(product_url, headers=headers, timeout=20)
        
        if response.status_code != 200:
            logging.error(f"Failed to access URL: HTTP {response.status_code}")
            return product_data
        
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract domain for relative URL resolution
        domain = extract_domain(product_url)
        
        #---------------------------------------------------------------------------
        # 1. EXTRACT ACCURATE BRAND AND PRODUCT NAME
        #---------------------------------------------------------------------------
        
        # Retailer-specific extractors for brand and product name
        if retailer == "target":
            # Target usually has a clear brand name at the top
            brand_elements = soup.select('[data-test="product-brand"]')
            if brand_elements:
                product_data['brand'] = brand_elements[0].get_text(strip=True)
            
            # Get product title
            title_elements = soup.select('[data-test="product-title"]')
            if title_elements:
                product_data['product_name'] = title_elements[0].get_text(strip=True)
                
        elif retailer == "amazon":
            # Try to find brand from the "Brand" info section
            brand_sections = soup.find_all('tr', class_='a-spacing-small')
            for section in brand_sections:
                if section.find(text=re.compile('Brand|Marca')):
                    brand_value = section.find('td', class_='a-span9')
                    if brand_value:
                        product_data['brand'] = brand_value.get_text(strip=True)
                        break
            
            # If not found, try the byline
            if not product_data['brand'] or product_data['brand'] == brand_name:
                byline = soup.select('#bylineInfo')
                if byline:
                    brand_text = byline[0].get_text(strip=True)
                    # Extract brand name from "Brand: Optimum Nutrition"
                    if ':' in brand_text:
                        product_data['brand'] = brand_text.split(':', 1)[1].strip()
                    else:
                        product_data['brand'] = brand_text
            
            # Get product title
            title_element = soup.select('#productTitle')
            if title_element:
                product_data['product_name'] = title_element[0].get_text(strip=True)
                
        elif retailer == "walmart":
            # Walmart often shows brand in the product specs section
            brand_sections = soup.find_all('div', class_='specTable-value')
            for section in brand_sections:
                if section.find_previous('div', class_='specTable-label') and 'brand' in section.find_previous('div', class_='specTable-label').get_text().lower():
                    product_data['brand'] = section.get_text(strip=True)
                    break
            
            # Get product title
            title_elements = soup.select('h1.prod-ProductTitle')
            if title_elements:
                product_data['product_name'] = title_elements[0].get_text(strip=True)
        
        # Generic approach for other retailers
        if not product_data['brand'] or product_data['brand'] == brand_name:
            # Common selectors for brand info
            brand_selectors = [
                '.brand', '.product-brand', '.product_brand', 
                '[itemprop="brand"]', '.manufacturer', 
                '.vendor', '.product-vendor', 
                'meta[property="og:brand"]', 'meta[name="brand"]'
            ]
            
            for selector in brand_selectors:
                elements = soup.select(selector)
                if elements:
                    if elements[0].name == 'meta':
                        product_data['brand'] = elements[0].get('content', '')
                    else:
                        product_data['brand'] = elements[0].get_text(strip=True)
                    break
        
        # Clean up brand (remove "Brand:", "by", etc.)
        if product_data['brand']:
            for prefix in ['Brand:', 'by ', 'By ', 'Visit the ', 'From ', 'from ']:
                if product_data['brand'].startswith(prefix):
                    product_data['brand'] = product_data['brand'][len(prefix):].strip()
        
        # Generic approach for product name if not already found
        if not product_data['product_name'] or product_data['product_name'] == product_name:
            # Common selectors for product name
            name_selectors = [
                'h1.product-title', 'h1.product_title', 'h1.productName',
                'h1[itemprop="name"]', '.product-name', '.product_name',
                'meta[property="og:title"]', 'meta[name="title"]'
            ]
            
            for selector in name_selectors:
                elements = soup.select(selector)
                if elements:
                    if elements[0].name == 'meta':
                        product_data['product_name'] = elements[0].get('content', '')
                    else:
                        product_data['product_name'] = elements[0].get_text(strip=True)
                    break
        
        # If we still don't have a product name, use the page title as last resort
        if not product_data['product_name'] or product_data['product_name'] == product_name:
            title_tag = soup.find('title')
            if title_tag:
                title_text = title_tag.get_text(strip=True)
                # Some cleanup - remove store name, etc.
                for store in ['Amazon.com', 'Walmart.com', 'Target', 'GNC', 'The Vitamin Shoppe']:
                    if store in title_text:
                        title_text = title_text.split(store)[0].strip()
                product_data['product_name'] = title_text
        
        # Clean up product name (remove brand name if it appears at the beginning)
        if product_data['brand'] and product_data['product_name'].startswith(product_data['brand']):
            product_data['product_name'] = product_data['product_name'][len(product_data['brand']):].strip(' -:')
        
        logging.info(f"Extracted brand: {product_data['brand']}")
        logging.info(f"Extracted product name: {product_data['product_name']}")
        
        #---------------------------------------------------------------------------
        # 2. FIND MAIN PRODUCT IMAGE
        #---------------------------------------------------------------------------
        
        # Retailer-specific image extraction
        main_image_found = False
        
        if retailer == "target":
            # Target usually has primary image with specific data attributes
            image_elements = soup.select('[data-test="product-image"]')
            if image_elements:
                img_tag = image_elements[0].find('img')
                if img_tag and 'src' in img_tag.attrs:
                    product_data['image_url'] = img_tag['src']
                    # Sometimes the src is a small thumbnail, look for larger version
                    if 'srcset' in img_tag.attrs:
                        srcset = img_tag['srcset']
                        largest_img = srcset.split(',')[-1].strip().split(' ')[0]
                        if largest_img:
                            product_data['image_url'] = largest_img
                    main_image_found = True
        
        elif retailer == "amazon":
            # Try to find Amazon's main product image
            image_elements = soup.select('#landingImage, #imgBlkFront')
            if image_elements:
                if 'data-old-hires' in image_elements[0].attrs:
                    product_data['image_url'] = image_elements[0]['data-old-hires']
                    main_image_found = True
                elif 'src' in image_elements[0].attrs:
                    product_data['image_url'] = image_elements[0]['src']
                    main_image_found = True
        
        # Generic image finding if retailer-specific approach didn't work
        if not main_image_found:
            # Check common image selectors
            image_selectors = [
                # Common product image selectors
                'img.product-image', 'img.productImage', 'img.product_image',
                'img.main-image', 'img.mainImage', 'img.primary-image', 
                '.product-main-image img', '.product-media img',
                '.product-image-container img', '.product-image-gallery img',
                # Additional selectors for specific platforms
                '.woocommerce-product-gallery__image img',  # WooCommerce
                '.product-single__photo img',  # Shopify
                '.product-photo-container img',  # More Shopify
                '[data-component="ProductImage"] img',  # Squarespace
                '.main-product-image img',  # Generic
                '.gallery-image-container img',  # More generic
                # Open Graph image as fallback
                'meta[property="og:image"]'
            ]
            
            # Try each image selector
            for selector in image_selectors:
                img_tags = soup.select(selector)
                if img_tags:
                    if img_tags[0].name == 'meta':
                        product_data['image_url'] = img_tags[0].get('content', '')
                    elif 'src' in img_tags[0].attrs:
                        product_data['image_url'] = img_tags[0]['src']
                    
                    if product_data['image_url']:
                        main_image_found = True
                        break
        
        # If no image found with selectors, try looking for any large image that might be the product
        if not main_image_found:
            all_images = soup.find_all('img')
            product_name_parts = product_data['product_name'].lower().split()
            
            for img in all_images:
                # Check alt text
                alt_text = img.get('alt', '').lower()
                if any(part in alt_text for part in product_name_parts):
                    product_data['image_url'] = img.get('src', '')
                    break
                
                # If this is a large enough image (likely a product image)
                width = img.get('width')
                height = img.get('height')
                if width and height and int(width) > 300 and int(height) > 300:
                    product_data['image_url'] = img.get('src', '')
                    break
        
        # Handle relative URLs
        if product_data['image_url']:
            if product_data['image_url'].startswith('/'):
                product_data['image_url'] = f"{domain}{product_data['image_url']}"
            # Handle protocol-relative URLs
            elif product_data['image_url'].startswith('//'):
                product_data['image_url'] = f"https:{product_data['image_url']}"
                
            logging.info(f"Found product image: {product_data['image_url']}")
        
        #---------------------------------------------------------------------------
        # 3. FIND INGREDIENTS IN TEXT
        #---------------------------------------------------------------------------
        
        # Retailer-specific approach for ingredients
        ingredients_found = False
        
        if retailer == "target":
            # Target usually has details section
            details_tab = soup.select('[data-test="detailsTab"]')
            if details_tab:
                details_sections = details_tab[0].find_all('div', class_='h-padding-h-default')
                for section in details_sections:
                    if 'Ingredients' in section.get_text() or 'ingredients' in section.get_text().lower():
                        ingredients_text = section.get_text(strip=True)
                        # Try to extract just the ingredient part
                        if ':' in ingredients_text:
                            ingredients_text = ingredients_text.split(':', 1)[1].strip()
                        product_data['ingredients'] = ingredients_text
                        ingredients_found = True
                        break
        
        elif retailer == "amazon":
            # Amazon often has product details in a structured format
            detail_sections = soup.select('#productDetails, #detailBullets_feature_div, #detail-bullets')
            for section in detail_sections:
                if 'Ingredients' in section.get_text() or 'ingredients' in section.get_text().lower():
                    # Try to find the ingredient section
                    li_elements = section.find_all('li')
                    for li in li_elements:
                        if 'Ingredients' in li.get_text() or 'ingredients' in li.get_text().lower():
                            ingredients_text = li.get_text(strip=True)
                            # Extract just the ingredients
                            if ':' in ingredients_text:
                                ingredients_text = ingredients_text.split(':', 1)[1].strip()
                            product_data['ingredients'] = ingredients_text
                            ingredients_found = True
                            break
            
            # Amazon also sometimes has a dedicated section
            if not ingredients_found:
                ingredient_section = soup.select('#important-information .content')
                if ingredient_section:
                    product_data['ingredients'] = ingredient_section[0].get_text(strip=True)
                    ingredients_found = True
        
        # Generic approach if retailer-specific didn't work
        if not ingredients_found:
            # Look for common ingredient section identifiers
            ingredient_identifiers = [
                # Headers and section titles
                'Ingredients', 'INGREDIENTS', 'ingredients', 
                'Ingredient List', 'Supplement Facts',
                # HTML attributes
                'id="ingredients"', 'class="ingredients"',
                'data-tab="ingredients"', 'data-section="ingredients"',
                # Labels
                'Ingredients:', 'Active Ingredients:', 'Contains:',
                # More specific variations
                'Other Ingredients', 'Inactive Ingredients',
                'Supplement Facts', 'Nutrition Facts',
                'Medicinal Ingredients', 'Non-Medicinal Ingredients'
            ]
            
            # Method 1: Try to find dedicated ingredients section
            for identifier in ingredient_identifiers:
                # Try to find headers with this text
                headers = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'dt', 'strong'], 
                                      string=lambda s: s and identifier.lower() in s.lower())
                
                for header in headers:
                    # Get the next paragraph or div after this header
                    ingredient_section = header.find_next(['p', 'div', 'span', 'ul', 'li'])
                    if ingredient_section:
                        ingredients_text = ingredient_section.get_text(strip=True)
                        if ingredients_text and len(ingredients_text) > 10:
                            product_data['ingredients'] = ingredients_text
                            ingredients_found = True
                            break
                
                if ingredients_found:
                    break
                    
                # Try to find divs with matching IDs or classes
                if 'id=' in identifier or 'class=' in identifier:
                    attr_name, attr_value = identifier.split('=')
                    attr_name = attr_name.strip()
                    attr_value = attr_value.strip('"\'')
                    
                    sections = soup.find_all(attrs={attr_name: attr_value})
                    if sections:
                        ingredients_text = sections[0].get_text(strip=True)
                        if ingredients_text and len(ingredients_text) > 10:
                            product_data['ingredients'] = ingredients_text
                            ingredients_found = True
                            break
            
            # Method 2: If no dedicated section found, look for paragraphs containing ingredient keywords
            if not ingredients_found:
                ingredient_keywords = ['ingredient', 'contains', 'formulation', 'composition']
                paragraphs = soup.find_all(['p', 'div', 'span', 'li'])
                
                for p in paragraphs:
                    text = p.get_text(strip=True).lower()
                    if any(keyword in text for keyword in ingredient_keywords) and len(text) > 30:
                        ingredients_text = p.get_text(strip=True)
                        if ingredients_text and len(ingredients_text) > 10:
                            product_data['ingredients'] = ingredients_text
                            ingredients_found = True
                            break
            
            # Method 3: Try to find tables that might contain ingredients
            if not ingredients_found:
                tables = soup.find_all('table')
                for table in tables:
                    table_text = table.get_text().lower()
                    if 'ingredient' in table_text or 'supplement facts' in table_text:
                        ingredients_text = table.get_text(strip=True)
                        if ingredients_text and len(ingredients_text) > 10:
                            product_data['ingredients'] = ingredients_text
                            ingredients_found = True
                            break
        
        if ingredients_found:
            logging.info(f"Found ingredients in text: {product_data['ingredients'][:100]}...")
        
        #---------------------------------------------------------------------------
        # 4. FIND INGREDIENT IMAGES (if text ingredients not found or as backup)
        #---------------------------------------------------------------------------
        
        # Look for images that might contain ingredient lists
        ingredient_img_keywords = [
            'ingredients', 'supplement facts', 'nutrition facts', 'label', 
            'facts', 'nutritional', 'nutrition information', 'drug facts'
        ]
        
        # Retailer-specific approach
        ingredient_image_found = False
        
        if retailer == "target" and not ingredient_image_found:
            # Target often shows nutrition label in image gallery
            image_gallery = soup.select('[data-test="image-gallery"]')
            if image_gallery:
                thumbnail_row = image_gallery[0].find_all('div', {'class': 'thumbnail-row'})
                if thumbnail_row:
                    thumbnails = thumbnail_row[0].find_all('button')
                    for thumb in thumbnails[1:]:  # Skip the first one (main product image)
                        thumb_img = thumb.find('img')
                        if thumb_img:
                            for keyword in ingredient_img_keywords:
                                if keyword in thumb_img.get('alt', '').lower():
                                    # This might be an ingredient image - find the corresponding full-size image
                                    thumb_id = thumb.get('aria-labelledby', '')
                                    if thumb_id:
                                        # Extract index from thumbnail id
                                        index_match = re.search(r'thumbnail-(\d+)', thumb_id)
                                        if index_match:
                                            idx = index_match.group(1)
                                            full_image = soup.select(f'#gallery-image-{idx}')
                                            if full_image:
                                                img_tag = full_image[0].find('img')
                                                if img_tag and 'src' in img_tag.attrs:
                                                    product_data['ingredient_image_url'] = img_tag['src']
                                                    ingredient_image_found = True
                                                    break
                        if ingredient_image_found:
                            break
        
        # Generic approach - track all potential ingredient images
        if not ingredient_image_found:
            potential_ingredient_images = []
            
            # Method 1: Look for images with ingredient-related alt text
            all_images = soup.find_all('img')
            for img in all_images:
                alt_text = img.get('alt', '').lower()
                src = img.get('src', '').lower()
                
                # Skip tiny images that couldn't contain readable ingredients
                width = img.get('width', '0')
                height = img.get('height', '0')
                try:
                    if (width and int(width) < 200) or (height and int(height) < 200):
                        continue
                except:
                    pass
                
                # Check if any ingredient keyword is in alt text or image URL
                if any(keyword in alt_text for keyword in ingredient_img_keywords) or \
                   any(keyword in src for keyword in ingredient_img_keywords):
                    image_url = img.get('src', '')
                    if image_url:
                        # Handle relative URLs
                        if image_url.startswith('/'):
                            image_url = f"{domain}{image_url}"
                        # Handle protocol-relative URLs
                        elif image_url.startswith('//'):
                            image_url = f"https:{image_url}"
                        
                        score = 0
                        # Score the image based on keywords in alt text and URL
                        for keyword in ingredient_img_keywords:
                            if keyword in alt_text:
                                score += 2
                            if keyword in src:
                                score += 1
                        
                        potential_ingredient_images.append((image_url, score))
            
            # Method 2: Look for images near ingredient-related headers or sections
            for identifier in ['Ingredients', 'Supplement Facts', 'Nutrition Facts']:
                headers = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'dt', 'strong'], 
                                      string=lambda s: s and identifier.lower() in s.lower())
                
                for header in headers:
                    # Look for images after or before the header
                    img_after = header.find_next('img')
                    img_before = header.find_previous('img')
                    
                    if img_after:
                        image_url = img_after.get('src', '')
                        if image_url:
                            # Handle relative URLs
                            if image_url.startswith('/'):
                                image_url = f"{domain}{image_url}"
                            # Handle protocol-relative URLs
                            elif image_url.startswith('//'):
                                image_url = f"https:{image_url}"
                            
                            potential_ingredient_images.append((image_url, 3))  # Higher score for images near headers
                    
                    if img_before:
                        image_url = img_before.get('src', '')
                        if image_url:
                            # Handle relative URLs
                            if image_url.startswith('/'):
                                image_url = f"{domain}{image_url}"
                            # Handle protocol-relative URLs
                            elif image_url.startswith('//'):
                                image_url = f"https:{image_url}"
                            
                            potential_ingredient_images.append((image_url, 2))
            
            # Sort by score and select the highest scoring image
            if potential_ingredient_images:
                potential_ingredient_images.sort(key=lambda x: x[1], reverse=True)
                best_ingredient_image = potential_ingredient_images[0][0]
                product_data['ingredient_image_url'] = best_ingredient_image
                logging.info(f"Found potential ingredient image: {best_ingredient_image}")
                ingredient_image_found = True
        
        #---------------------------------------------------------------------------
        # 5. ADDITIONAL INFORMATION (directions, warnings, etc.)
        #---------------------------------------------------------------------------
        
        # Add code for other product details like directions, warnings, etc.
        # This would follow a similar pattern to the ingredients extraction above
        
        # Try to categorize the supplement based on extracted ingredients
        if product_data['ingredients']:
            main_category, subcategory = categorize_supplement(product_data['ingredients'])
            product_data['main_category'] = main_category
            product_data['subcategory'] = subcategory
        
        logging.info(f"Successfully scraped product data from {product_url}")
        return product_data
        
    except Exception as e:
        logging.error(f"Error scraping product from URL: {e}")
        return product_data
# Helper function to extract domain from URL
def extract_domain(url):
    """Extract domain from URL for resolving relative paths"""
    if '//' in url:
        return url.split('//', 1)[0] + '//' + url.split('//', 1)[1].split('/', 1)[0]
    return url

# Function to score ingredients quality
def score_ingredients(ingredients, allergen_free, vegan, gluten_free, non_gmo, organic):
    """
    Score the ingredients quality and safety.
    
    Parameters:
    - ingredients (str): List of ingredients
    - allergen_free, vegan, etc. (bool): Product claims
    
    Returns:
    - float: Score from 0-10
    """
    base_score = 5.0  # Start with a neutral score
    
    # Ingredient quality checks
    if ingredients:
        # Check for artificial ingredients
        artificial_ingredients = [
            'artificial flavor', 'artificial color', 'sodium benzoate',
            'potassium sorbate', 'propylene glycol', 'BHT', 'BHA',
            'hydrogenated', 'high fructose', 'aspartame', 'sucralose',
            'acesulfame', 'saccharin', 'red dye', 'yellow dye', 'blue dye'
        ]
        artificial_count = sum(1 for item in artificial_ingredients if item.lower() in ingredients.lower())
        base_score -= artificial_count * 0.5
        
        # Check for proprietary blends (reduces transparency)
        if 'proprietary blend' in ingredients.lower():
            base_score -= 1.0
        
        # Check for beneficial ingredients
        beneficial_ingredients = [
            'extract', 'natural', 'organic', 'whole', 'raw', 'fermented',
            'sprouted', 'cultured', 'pure', 'unrefined', 'cold-pressed'
        ]
        beneficial_count = sum(1 for item in beneficial_ingredients if item.lower() in ingredients.lower())
        base_score += min(beneficial_count * 0.3, 1.5)  # Cap at 1.5 points
    
    # Certifications boost
    if organic:
        base_score += 1.5
    if non_gmo:
        base_score += 1.0
    if allergen_free:
        base_score += 0.5
    if gluten_free:
        base_score += 0.5
    if vegan:
        base_score += 0.5
    
    # Ensure score is within 0-10 range
    return max(0, min(10, base_score))

# Function to score manufacturing quality
def score_manufacturing(gmp_certified, country_of_origin, brand):
    """
    Score the manufacturing quality.
    
    Parameters:
    - gmp_certified (bool): Has GMP certification
    - country_of_origin (str): Manufacturing country
    - brand (str): Brand name for reputation lookup
    
    Returns:
    - float: Score from 0-10
    """
    base_score = 5.0
    
    # GMP certification is crucial
    if gmp_certified:
        base_score += 3.0
    
    # Country of origin considerations
    high_standard_countries = [
        'usa', 'canada', 'japan', 'australia', 'new zealand',
        'switzerland', 'germany', 'france', 'uk', 'united kingdom',
        'sweden', 'norway', 'finland', 'denmark', 'netherlands'
    ]
    
    if country_of_origin and any(country.lower() in country_of_origin.lower() for country in high_standard_countries):
        base_score += 1.0
    
    # Brand reputation impact (placeholder implementation)
    # In a full system, this would query a reputation database
    reputable_brands = [
        'now foods', 'thorne', 'jarrow', 'life extension', 'nordic naturals',
        'garden of life', 'solgar', 'pure encapsulations', 'standard process',
        'designs for health', 'metagenics', 'gaia herbs', 'integrative therapeutics',
        'natural factors', 'carlson', 'nature\'s way', 'doctor\'s best', 'bluebonnet'
    ]
    
    brand_lower = brand.lower() if brand else ""
    if any(rb in brand_lower for rb in reputable_brands):
        base_score += 1.0
    
    return max(0, min(10, base_score))

# Function to score testing and verification
def score_testing(third_party_tested, certifications):
    """
    Score the testing and verification quality.
    
    Parameters:
    - third_party_tested (bool): Has independent testing
    - certifications (str): List of certifications
    
    Returns:
    - float: Score from 0-10
    """
    base_score = 4.0
    
    # Third-party testing is crucial
    if third_party_tested:
        base_score += 3.0
    
    # Valuable certifications
    valuable_certs = ['USP', 'NSF', 'Informed Choice', 'Informed Sport', 'ConsumerLab']
    
    if certifications:
        cert_count = sum(1 for cert in valuable_certs if cert.lower() in certifications.lower())
        base_score += cert_count * 1.0
    
    return max(0, min(10, base_score))

# Function to score label accuracy
def score_label_accuracy(ingredients, warnings, directions, serving_size):
    """
    Score the label accuracy and transparency.
    
    Parameters:
    - ingredients (str): Ingredient list
    - warnings (str): Warning text
    - directions (str): Usage directions
    - serving_size (str): Serving size info
    
    Returns:
    - float: Score from 0-10
    """
    base_score = 3.0
    
    # Check for comprehensive information
    if ingredients and len(ingredients) > 10:
        base_score += 2.0
    
    if warnings and len(warnings) > 10:
        base_score += 1.5
    
    if directions and len(directions) > 10:
        base_score += 1.5
    
    if serving_size and len(serving_size) > 2:
        base_score += 2.0
    
    return max(0, min(10, base_score))

# Function to score nutritional quality
def score_nutritional_quality(main_category, subcategory, ingredients):
    """
    Score the nutritional quality based on category-specific criteria.
    
    Parameters:
    - main_category (str): Main supplement category
    - subcategory (str): Supplement subcategory
    - ingredients (str): Ingredient list
    
    Returns:
    - float: Score from 0-10
    """
    base_score = 5.0
    
    if not ingredients or not main_category:
        return base_score
    
    ingredients_lower = ingredients.lower()
    
    # Category-specific scoring
    if main_category == "Vitamins & Minerals":
        # Check for bioavailable forms
        bioavailable_forms = [
            'methylcobalamin', 'pyridoxal-5-phosphate', 'methylfolate', 
            'chelated', 'glycinate', 'citrate', 'malate', 'picolinate'
        ]
        bioavailable_count = sum(1 for form in bioavailable_forms if form.lower() in ingredients_lower)
        base_score += bioavailable_count * 0.5
    
    elif main_category == "Digestive Health" and subcategory == "Probiotics":
        # Check for CFU count and strain diversity
        if "billion cfu" in ingredients_lower:
            # Try to extract CFU count
            import re
            cfu_pattern = r'(\d+)\s*billion\s*cfu'
            match = re.search(cfu_pattern, ingredients_lower)
            if match:
                cfu_count = int(match.group(1))
                if cfu_count > 30:
                    base_score += 2.0
                elif cfu_count > 10:
                    base_score += 1.0
        
        # Check strain diversity
        strain_count = ingredients_lower.count("lactobacillus") + ingredients_lower.count("bifidobacterium")
        base_score += min(strain_count * 0.5, 3.0)
    
    elif main_category == "Fitness & Performance":
        # Check for scientifically validated ingredients
        proven_ingredients = [
            'creatine monohydrate', 'whey protein isolate', 'casein protein',
            'beta-alanine', 'citrulline malate', 'bcaa', 'eaa', 'glutamine'
        ]
        proven_count = sum(1 for ing in proven_ingredients if ing in ingredients_lower)
        base_score += proven_count * 0.5
    
    elif main_category == "Cognitive & Mental Health":
        # Check for researched nootropics
        researched_nootropics = [
            'bacopa monnieri', 'lions mane', 'phosphatidylserine',
            'acetyl-l-carnitine', 'rhodiola rosea', 'ginkgo biloba',
            'ashwagandha', 'l-theanine'
        ]
        researched_count = sum(1 for noot in researched_nootropics if noot in ingredients_lower)
        base_score += researched_count * 0.5
    
    # General quality factors across all categories
    quality_terms = [
        'standardized extract', 'full spectrum', 'whole food', 'organic',
        'wild-crafted', 'fermented', 'activated', 'sprouted'
    ]
    quality_count = sum(1 for term in quality_terms if term in ingredients_lower)
    base_score += quality_count * 0.3
    
    return max(0, min(10, base_score))

# Function to score sustainability and ethics
def score_sustainability(certifications, brand):
    """
    Score the sustainability and ethics.
    
    Parameters:
    - certifications (str): List of certifications
    - brand (str): Brand name for reputation lookup
    
    Returns:
    - float: Score from 0-10
    """
    base_score = 5.0
    
    # Sustainability certifications
    sustainable_certs = [
        'B Corporation', 'Fair Trade', 'Rainforest Alliance', 
        'USDA Organic', 'Carbon Neutral', 'Non-GMO Project',
        'Certified Organic', 'Eco-Cert'
    ]
    
    if certifications:
        cert_count = sum(1 for cert in sustainable_certs if cert.lower() in certifications.lower())
        base_score += cert_count * 0.7
    
    # Sustainable packaging terms
    packaging_terms = ['recyclable', 'compostable', 'biodegradable', 'plastic-free', 'glass']
    if any(term in certifications.lower() for term in packaging_terms):
        base_score += 1.0
    
    # Brand sustainability reputation (simplified implementation)
    sustainable_brands = [
        'garden of life', 'nordic naturals', 'new chapter', 'megafood',
        'nutiva', 'gaia herbs', 'himalaya', 'traditional medicinals'
    ]
    
    brand_lower = brand.lower() if brand else ""
    if any(sb in brand_lower for sb in sustainable_brands):
        base_score += 1.0
    
    return max(0, min(10, base_score))

# Function to calculate all scores for a supplement
def calculate_scores(product_data):
    """
    Calculate supplement quality scores across multiple criteria
    
    Parameters:
    - product_data (dict): Supplement data dictionary
    
    Returns:
    - dict: Dictionary of scores for each criterion and overall score
    """
    logging.info(f"Calculating scores for {product_data.get('brand', '')} {product_data.get('product_name', '')}")
    
    # 1. Ingredients & Formulation Score (0-10)
    ingredients_score = score_ingredients(
        ingredients=product_data.get('ingredients', ''),
        allergen_free=product_data.get('allergen_free', False),
        vegan=product_data.get('vegan', False),
        gluten_free=product_data.get('gluten_free', False),
        non_gmo=product_data.get('non_gmo', False),
        organic=product_data.get('organic', False)
    )
    
    # 2. Manufacturing Quality Score (0-10)
    manufacturing_score = score_manufacturing(
        gmp_certified=product_data.get('gmp_certified', False),
        country_of_origin=product_data.get('country_of_origin', ''),
        brand=product_data.get('brand', '')
    )
    
    # 3. Testing & Verification Score (0-10)
    testing_score = score_testing(
        third_party_tested=product_data.get('third_party_tested', False),
        certifications=product_data.get('certifications', '')
    )
    
    # 4. Label Accuracy & Transparency Score (0-10)
    label_score = score_label_accuracy(
        ingredients=product_data.get('ingredients', ''),
        warnings=product_data.get('warnings', ''),
        directions=product_data.get('directions', ''),
        serving_size=product_data.get('serving_size', '')
    )
    
    # 5. Nutritional Quality Score (0-10)
    nutritional_score = score_nutritional_quality(
        main_category=product_data.get('main_category', ''),
        subcategory=product_data.get('subcategory', ''),
        ingredients=product_data.get('ingredients', '')
    )
    
    # 6. Sustainability & Ethics Score (0-10)
    sustainability_score = score_sustainability(
        certifications=product_data.get('certifications', ''),
        brand=product_data.get('brand', '')
    )
    
    # Calculate overall weighted score
    weights = {
        'ingredients_score': 0.25,
        'manufacturing_quality_score': 0.20,
        'testing_verification_score': 0.20,
        'label_accuracy_score': 0.15,
        'nutritional_quality_score': 0.15,
        'sustainability_score': 0.05
    }
    
    scores = {
        'ingredients_score': ingredients_score,
        'manufacturing_quality_score': manufacturing_score,
        'testing_verification_score': testing_score,
        'label_accuracy_score': label_score,
        'nutritional_quality_score': nutritional_score,
        'sustainability_score': sustainability_score
    }
    
    overall_score = sum(scores[key] * weights[key] for key in weights)
    scores['overall_score'] = round(overall_score, 1)
    
    logging.info(f"Calculated overall score: {scores['overall_score']}")
    return scores
