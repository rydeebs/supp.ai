import streamlit as st
import pandas as pd
import requests
import os
import time
import matplotlib.pyplot as plt
import seaborn as sns
from PIL import Image
from io import BytesIO, StringIO
import re
import hashlib
import base64
import json
from datetime import datetime
import uuid
import csv

# Import our supplement data collection module
from supplement_collector import (
    fetch_from_off,
    download_image,
    fetch_supplement_image,
    categorize_supplement,
    calculate_scores,
    ingredient_category_map,
    scrape_product_from_url
)

# Configure page settings
st.set_page_config(
    page_title="Supplement Data Collector",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# App title and description
st.title("🧪 Supplement Data Collection Dashboard")
st.markdown("""
This application helps you collect and organize supplement data for your barcode scanning app.
You can search for supplements, view their details, categorize them, and export the data to CSV for Firebase.
""")

# Initialize session state variables
if 'supplements_df' not in st.session_state:
    # Create empty DataFrame with our structure
    st.session_state.supplements_df = pd.DataFrame(columns=[
        'id', 'barcode', 'brand', 'product_name', 'main_category', 'subcategory',
        'ingredients', 'manufacturing_quality_score', 'testing_verification_score',
        'label_accuracy_score', 'nutritional_quality_score', 'certifications',
        'sustainability_score', 'overall_score', 'gmp_certified', 'third_party_tested',
        'allergen_free', 'vegan', 'gluten_free', 'non_gmo', 'organic',
        'country_of_origin', 'manufacture_date', 'serving_size', 'directions',
        'warnings', 'storage_instructions', 'image_url', 'local_image_path', 'website', 'last_updated'
    ])

if 'images_dir' not in st.session_state:
    # Create directory for storing images
    IMAGES_DIR = "supplement_images"
    os.makedirs(IMAGES_DIR, exist_ok=True)
    st.session_state.images_dir = IMAGES_DIR

if 'batch_results' not in st.session_state:
    st.session_state.batch_results = []

# Display image function
def display_image(image_path=None, image_url=None):
    if image_path and os.path.exists(image_path):
        return Image.open(image_path)
    elif image_url:
        try:
            response = requests.get(image_url)
            return Image.open(BytesIO(response.content))
        except:
            return None
    return None

# Function to search supplement by barcode
def search_by_barcode(barcode):
    st.write(f"Searching for barcode: {barcode}")
    
    # Check if we already have this barcode
    if st.session_state.supplements_df['barcode'].astype(str).isin([str(barcode)]).any():
        st.success("This supplement is already in your database!")
        return st.session_state.supplements_df[st.session_state.supplements_df['barcode'].astype(str) == str(barcode)].iloc[0].to_dict()
    
    with st.spinner("Fetching data from Open Food Facts..."):
        # Try to get from Open Food Facts
        product_data = fetch_from_off(barcode)
        
    if not product_data:
        st.warning("No data found in Open Food Facts for this barcode.")
        # Create empty data with just the barcode
        product_data = {
            'barcode': barcode,
            'brand': '',
            'product_name': '',
            'ingredients': '',
            'image_url': ''
        }
    
    # Determine category based on ingredients
    if product_data.get('ingredients'):
        with st.spinner("Categorizing supplement..."):
            main_category, subcategory = categorize_supplement(product_data['ingredients'])
            product_data['main_category'] = main_category
            product_data['subcategory'] = subcategory
    
    # Try to get an image if not already present
    if not product_data.get('image_url'):
        with st.spinner("Searching for product image..."):
            image_url = fetch_supplement_image(
                product_data.get('brand', ''),
                product_data.get('product_name', ''),
                barcode
            )
            if image_url:
                product_data['image_url'] = image_url
    
    # Download image if URL exists
    if product_data.get('image_url'):
        with st.spinner("Downloading product image..."):
            local_path = download_image(
                product_data['image_url'],
                barcode,
                product_data.get('brand', ''),
                product_data.get('product_name', '')
            )
            product_data['local_image_path'] = local_path
    
    return product_data

# Function to add new supplement to the database
def add_supplement(product_data):
    # Generate a unique ID
    product_id = f"SUPP{str(uuid.uuid4())[:8].upper()}"
    product_data['id'] = product_id
    
    # Set timestamp
    product_data['last_updated'] = datetime.now().strftime('%Y-%m-%d')
    
    # Calculate initial scores if ingredients are available
    if product_data.get('ingredients'):
        scores = calculate_scores(product_data)
        product_data.update(scores)
    
    # Add to DataFrame
    st.session_state.supplements_df = pd.concat([
        st.session_state.supplements_df, 
        pd.DataFrame([product_data])
    ], ignore_index=True)
    
    st.success(f"Added {product_data.get('product_name', 'New Supplement')} to your database!")
    return product_id

# Function to parse URL batch file
def parse_url_file(file):
    urls = []
    
    # Determine file format
    if file.name.endswith('.csv'):
        df = pd.read_csv(file)
        
        # Try to find URL column
        url_column = None
        for col in df.columns:
            if 'url' in col.lower() or 'link' in col.lower():
                url_column = col
                break
        
        if url_column:
            urls = df[url_column].tolist()
        else:
            # If no obvious URL column, take the first column
            urls = df.iloc[:, 0].tolist()
    
    elif file.name.endswith('.txt'):
        content = file.getvalue().decode('utf-8')
        urls = [line.strip() for line in content.split('\n') if line.strip()]
    
    # Filter out non-URL entries
    valid_urls = []
    for url in urls:
        if isinstance(url, str) and (url.startswith('http://') or url.startswith('https://')):
            valid_urls.append(url)
    
    return valid_urls

# Function to extract brand and product name from URL
def extract_info_from_url(url):
    try:
        # Remove http://, https://, and www.
        clean_url = re.sub(r'^https?://(www\.)?', '', url)
        
        # Split by domain and path
        parts = clean_url.split('/', 1)
        domain = parts[0]
        
        # Extract brand from domain
        brand_match = re.search(r'^(?:www\.)?([^.]+)', domain)
        brand = brand_match.group(1).replace('-', ' ').title() if brand_match else "Unknown Brand"
        
        # Try to extract product name from path
        product_name = "Unknown Product"
        if len(parts) > 1:
            path = parts[1]
            
            # Look for common product URL patterns
            # Pattern 1: words separated by hyphens or underscores
            product_match = re.search(r'[\w-]+/([\w-]+)/?$', path)
            if product_match:
                product_name = product_match.group(1).replace('-', ' ').replace('_', ' ').title()
            
            # If product_name still looks like a slug or is too short, try different approach
            if len(product_name.split()) < 2 or len(product_name) < 10:
                # Try looking for a longer segment
                segments = path.split('/')
                for segment in segments:
                    if len(segment) > len(product_name) and '-' in segment:
                        product_name = segment.replace('-', ' ').replace('_', ' ').title()
        
        return brand, product_name
    except:
        return "Unknown Brand", "Unknown Product"

# Function to batch scrape URLs
def batch_scrape_urls(urls, auto_add=False, progress_bar=None):
    results = []
    total_urls = len(urls)
    
    for i, url in enumerate(urls):
        try:
            # Extract brand and product name from URL
            brand, product_name = extract_info_from_url(url)
            
            # Update progress
            if progress_bar:
                progress_bar.progress((i + 1) / total_urls)
            
            # Scrape the URL
            product_data = scrape_product_from_url(brand, product_name, url)
            
            # Generate a pseudo-barcode if not provided
            if not product_data.get('barcode'):
                product_data['barcode'] = f"GEN{int(time.time()) + i}"
            
            # Download image if URL exists
            if product_data.get('image_url'):
                local_path = download_image(
                    product_data['image_url'],
                    product_data['barcode'],
                    product_data.get('brand', ''),
                    product_data.get('product_name', '')
                )
                if local_path:
                    product_data['local_image_path'] = local_path
            
            # Calculate scores
            scores = calculate_scores(product_data)
            product_data.update(scores)
            
            # Add to database if auto_add is enabled
            if auto_add:
                add_supplement(product_data)
                results.append({
                    'url': url,
                    'status': 'Success - Added to database',
                    'brand': product_data.get('brand', ''),
                    'product_name': product_data.get('product_name', ''),
                    'overall_score': product_data.get('overall_score', 0)
                })
            else:
                results.append({
                    'url': url,
                    'status': 'Success',
                    'brand': product_data.get('brand', ''),
                    'product_name': product_data.get('product_name', ''),
                    'product_data': product_data,
                    'overall_score': product_data.get('overall_score', 0)
                })
                
        except Exception as e:
            results.append({
                'url': url,
                'status': f'Error: {str(e)}',
                'brand': '',
                'product_name': '',
                'overall_score': 0
            })
    
    return results

# Sidebar navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Search & Add", "Batch Processing", "View Database", "Export Data", "Settings"])

if page == "Search & Add":
    st.header("Search & Add Supplements")
    
    search_col1, search_col2 = st.columns([3, 1])
    
    with search_col1:
        search_method = st.radio("Search Method", ["Barcode", "Product Name", "Direct URL"], horizontal=True)
        
        if search_method == "Barcode":
            barcode = st.text_input("Enter Barcode", value="")
            search_button = st.button("Search")
            
            if search_button and barcode:
                product_data = search_by_barcode(barcode)
                
                if product_data:
                    # Display product info
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        image = None
                        if product_data.get('local_image_path'):
                            image = display_image(image_path=product_data['local_image_path'])
                        elif product_data.get('image_url'):
                            image = display_image(image_url=product_data['image_url'])
                            
                        if image:
                            st.image(image, caption="Product Image", width=250)
                        else:
                            st.info("No image available")
                    
                    with col2:
                        # Allow editing of product data
                        edited_data = {}
                        edited_data['brand'] = st.text_input("Brand", value=product_data.get('brand', ''))
                        edited_data['product_name'] = st.text_input("Product Name", value=product_data.get('product_name', ''))
                        
                        # Category/subcategory selector
                        categories = {
                            "Cognitive & Mental Health": ["Nootropics", "Memory & Focus", "Mood Support", "Stress & Anxiety Relief"],
                            "Fitness & Performance": ["Pre-Workout", "Post-Workout / Recovery", "Muscle Building", "Endurance & Energy"],
                            "Joint & Bone Health": ["Joint Support", "Bone Strength"],
                            "Heart & Circulatory Health": ["Cholesterol Support", "Blood Pressure Support", "Circulation Enhancers"],
                            "Immune Support": ["General Immune Boosters", "Antivirals", "Adaptogens"],
                            "Cellular Health & Longevity": ["Antioxidants", "Mitochondrial Support", "Telomere/Anti-aging"],
                            "Hormonal Support": ["Testosterone Boosters", "Estrogen Balance", "Thyroid Support", "Menopause & PMS"],
                            "Digestive Health": ["Probiotics", "Prebiotics", "Digestive Enzymes", "Gut Lining Support"],
                            "Vitamins & Minerals": ["Multivitamins", "Individual Vitamins", "Individual Minerals"],
                            "Greens & Superfoods": ["Greens Powders", "Algae & Sea Vegetables", "Reds/Berries Powders"],
                            "Sleep & Relaxation": ["Sleep Aids", "Relaxation Support"],
                            "Weight Management": ["Appetite Suppressants", "Fat Burners", "Metabolism Boosters"],
                            "Detox & Cleanse": ["Liver Support", "Heavy Metal Detox", "Colon Cleanses"]
                        }
                        
                        edited_data['main_category'] = st.selectbox(
                            "Main Category", 
                            list(categories.keys()),
                            index=list(categories.keys()).index(product_data.get('main_category', 'Vitamins & Minerals')) if product_data.get('main_category') in categories.keys() else 0
                        )
                        
                        edited_data['subcategory'] = st.selectbox(
                            "Subcategory", 
                            categories[edited_data['main_category']],
                            index=categories[edited_data['main_category']].index(product_data.get('subcategory', categories[edited_data['main_category']][0])) if product_data.get('subcategory') in categories[edited_data['main_category']] else 0
                        )
                        
                        edited_data['ingredients'] = st.text_area("Ingredients", value=product_data.get('ingredients', ''))
                        
                        # Certifications and claims
                        st.markdown("### Certifications & Claims")
                        cert_col1, cert_col2 = st.columns(2)
                        
                        with cert_col1:
                            edited_data['gmp_certified'] = st.checkbox("GMP Certified", value=product_data.get('gmp_certified', False))
                            edited_data['third_party_tested'] = st.checkbox("Third-Party Tested", value=product_data.get('third_party_tested', False))
                            edited_data['allergen_free'] = st.checkbox("Allergen Free", value=product_data.get('allergen_free', False))
                        
                        with cert_col2:
                            edited_data['vegan'] = st.checkbox("Vegan", value=product_data.get('vegan', False))
                            edited_data['gluten_free'] = st.checkbox("Gluten Free", value=product_data.get('gluten_free', False))
                            edited_data['non_gmo'] = st.checkbox("Non-GMO", value=product_data.get('non_gmo', False))
                            edited_data['organic'] = st.checkbox("Organic", value=product_data.get('organic', False))
                        
                        # Additional information
                        with st.expander("Additional Information"):
                            edited_data['country_of_origin'] = st.text_input("Country of Origin", value=product_data.get('country_of_origin', 'USA'))
                            edited_data['serving_size'] = st.text_input("Serving Size", value=product_data.get('serving_size', ''))
                            edited_data['directions'] = st.text_area("Directions", value=product_data.get('directions', ''))
                            edited_data['warnings'] = st.text_area("Warnings", value=product_data.get('warnings', ''))
                            edited_data['website'] = st.text_input("Website", value=product_data.get('website', ''))
                        
                        # Merge the original data with edited data
                        merged_data = {**product_data, **edited_data}
                        
                        # Add button
                        if st.button("Add to Database"):
                            product_id = add_supplement(merged_data)
                            st.success(f"Added supplement with ID: {product_id}")
        
        elif search_method == "Product Name":
            brand = st.text_input("Brand (optional)")
            product_name = st.text_input("Product Name")
            
            if st.button("Search") and product_name:
                st.info("This feature will search for supplements by name across various sources. Not implemented in this demo.")
                # This would require additional API implementations
        
        elif search_method == "Direct URL":
            with st.form("direct_url_form"):
                brand = st.text_input("Brand Name", help="Enter the supplement brand name")
                product_name = st.text_input("Product Name", help="Enter the supplement product name")
                barcode = st.text_input("Barcode (optional)", help="Enter the product barcode if available")
                product_url = st.text_input("Product URL", help="Enter the full URL to the product page on the brand's website")
                
                submitted = st.form_submit_button("Scrape Product Data")
                
                if submitted and product_url:
                    if not brand or not product_name:
                        st.error("Brand name and product name are required")
                    else:
                        with st.spinner("Scraping product data from URL..."):
                            # Call the scraper function
                            product_data = scrape_product_from_url(brand, product_name, product_url)
                            
                            # Add barcode if provided
                            if barcode:
                                product_data['barcode'] = barcode
                            
                            # Download image if URL exists
                            if product_data.get('image_url'):
                                local_path = download_image(
                                    product_data['image_url'],
                                    barcode if barcode else "nobarcode",
                                    product_data.get('brand', ''),
                                    product_data.get('product_name', '')
                                )
                                if local_path:
                                    product_data['local_image_path'] = local_path
                            
                            # Display the scraped data
                            col1, col2 = st.columns([1, 2])
                            
                            with col1:
                                if product_data.get('image_url'):
                                    image = display_image(image_url=product_data['image_url'])
                                    if image:
                                        st.image(image, caption="Product Image", width=250)
                                    else:
                                        st.info("Image could not be displayed")
                                        st.text(product_data['image_url'])
                                else:
                                    st.info("No image found on product page")
                            
                            with col2:
                                # Allow editing of product data
                                edited_data = {}
                                # Brand and product name are already set
                                edited_data['brand'] = st.text_input("Brand", value=product_data.get('brand', ''), key="url_brand")
                                edited_data['product_name'] = st.text_input("Product Name", value=product_data.get('product_name', ''), key="url_product")
                                
                                # Category/subcategory selector
                                categories = {
                                    "Cognitive & Mental Health": ["Nootropics", "Memory & Focus", "Mood Support", "Stress & Anxiety Relief"],
                                    "Fitness & Performance": ["Pre-Workout", "Post-Workout / Recovery", "Muscle Building", "Endurance & Energy"],
                                    "Joint & Bone Health": ["Joint Support", "Bone Strength"],
                                    "Heart & Circulatory Health": ["Cholesterol Support", "Blood Pressure Support", "Circulation Enhancers"],
                                    "Immune Support": ["General Immune Boosters", "Antivirals", "Adaptogens"],
                                    "Cellular Health & Longevity": ["Antioxidants", "Mitochondrial Support", "Telomere/Anti-aging"],
                                    "Hormonal Support": ["Testosterone Boosters", "Estrogen Balance", "Thyroid Support", "Menopause & PMS"],
                                    "Digestive Health": ["Probiotics", "Prebiotics", "Digestive Enzymes", "Gut Lining Support"],
                                    "Vitamins & Minerals": ["Multivitamins", "Individual Vitamins", "Individual Minerals"],
                                    "Greens & Superfoods": ["Greens Powders", "Algae & Sea Vegetables", "Reds/Berries Powders"],
                                    "Sleep & Relaxation": ["Sleep Aids", "Relaxation Support"],
                                    "Weight Management": ["Appetite Suppressants", "Fat Burners", "Metabolism Boosters"],
                                    "Detox & Cleanse": ["Liver Support", "Heavy Metal Detox", "Colon Cleanses"]
                                }
                                
                                edited_data['main_category'] = st.selectbox(
                                    "Main Category", 
                                    list(categories.keys()),
                                    index=list(categories.keys()).index(product_data.get('main_category', 'Vitamins & Minerals')) if product_data.get('main_category') in categories.keys() else 0,
                                    key="url_category"
                                )
                                
                                edited_data['subcategory'] = st.selectbox(
                                    "Subcategory", 
                                    categories[edited_data['main_category']],
                                    index=categories[edited_data['main_category']].index(product_data.get('subcategory', categories[edited_data['main_category']][0])) if product_data.get('subcategory') in categories[edited_data['main_category']] else 0,
                                    key="url_subcategory"
                                )
                                
                                # Show scraped ingredients and allow editing
                                edited_data['ingredients'] = st.text_area("Ingredients", value=product_data.get('ingredients', ''), key="url_ingredients")
                                
                                # Display and allow editing of other scraped data
                                if product_data.get('directions'):
                                    st.success("✓ Directions successfully scraped")
                                    edited_data['directions'] = st.text_area("Directions", value=product_data.get('directions', ''), key="url_directions")
                                else:
                                    edited_data['directions'] = st.text_area("Directions (not found - add manually)", value="", key="url_directions_manual")
                                
                                if product_data.get('warnings'):
                                    st.success("✓ Warnings successfully scraped")
                                    edited_data['warnings'] = st.text_area("Warnings", value=product_data.get('warnings', ''), key="url_warnings")
                                else:
                                    edited_data['warnings'] = st.text_area("Warnings (not found - add manually)", value="", key="url_warnings_manual")
                                
                                if product_data.get('serving_size'):
                                    st.success("✓ Serving size successfully scraped")
                                    edited_data['serving_size'] = st.text_input("Serving Size", value=product_data.get('serving_size', ''), key="url_serving")
                                else:
                                    edited_data['serving_size'] = st.text_input("Serving Size (not found - add manually)", value="", key="url_serving_manual")
                                
                                # Certifications
                                st.markdown("### Certifications & Claims")
                                if product_data.get('certifications'):
                                    st.success(f"✓ Certifications found: {product_data.get('certifications', '')}")
                                
                                cert_col1, cert_col2 = st.columns(2)
                                
                                with cert_col1:
                                    edited_data['gmp_certified'] = st.checkbox("GMP Certified", value=product_data.get('gmp_certified', False), key="url_gmp")
                                    edited_data['third_party_tested'] = st.checkbox("Third-Party Tested", value=product_data.get('third_party_tested', False), key="url_third_party")
                                    edited_data['allergen_free'] = st.checkbox("Allergen Free", value=product_data.get('allergen_free', False), key="url_allergen")
                                
                                with cert_col2:
                                    edited_data['vegan'] = st.checkbox("Vegan", value=product_data.get('vegan', False), key="url_vegan")
                                    edited_data['gluten_free'] = st.checkbox("Gluten Free", value=product_data.get('gluten_free', False), key="url_gluten")
                                    edited_data['non_gmo'] = st.checkbox("Non-GMO", value=product_data.get('non_gmo', False), key="url_nongmo")
                                    edited_data['organic'] = st.checkbox("Organic", value=product_data.get('organic', False), key="url_organic")
                                
                                # Additional information
                                with st.expander("Additional Information"):
                                    if product_data.get('country_of_origin'):
                                        st.success(f"✓ Country of origin detected: {product_data.get('country_of_origin')}")
                                    
                                    edited_data['country_of_origin'] = st.text_input(
                                        "Country of Origin", 
                                        value=product_data.get('country_of_origin', 'USA'),
                                        key="url_country"
                                    )
                                    
                                    # Website should already be filled with the provided URL
                                    edited_data['website'] = product_url
                                
                                # Merge the original data with edited data
                                merged_data = {**product_data, **edited_data}
                                
                                # Calculate scores based on the scraped data
                                with st.spinner("Calculating supplement scores..."):
                                    scores = calculate_scores(merged_data)
                                    merged_data.update(scores)
                                
                                # Display preliminary scores
                                st.subheader("Calculated Scores")
                                score_df = pd.DataFrame({
                                    'Metric': [
                                        'Overall Score',
                                        'Ingredients Quality',
                                        'Manufacturing Quality',
                                        'Testing & Verification',
                                        'Label Accuracy',
                                        'Nutritional Quality',
                                        'Sustainability'
                                    ],
                                    'Score': [
                                        scores.get('overall_score', 0),
                                        scores.get('ingredients_score', 0),
                                        scores.get('manufacturing_quality_score', 0),
                                        scores.get('testing_verification_score', 0),
                                        scores.get('label_accuracy_score', 0),
                                        scores.get('nutritional_quality_score', 0),
                                        scores.get('sustainability_score', 0)
                                    ]
                                })
                                
                                fig, ax = plt.subplots(figsize=(10, 3))
                                bars = sns.barplot(x='Score', y='Metric', data=score_df, orient='h', palette='viridis')
                                ax.set_xlim(0, 10)
                                ax.set_title('Supplement Scores')
                                st.pyplot(fig)
                                
                                # Add button
                                if st.button("Add to Database", key="url_add_button"):
                                    if not merged_data.get('barcode'):
                                        # Generate a pseudo-barcode if not provided
                                        merged_data['barcode'] = f"GEN{int(time.time())}"
                                        
                                    product_id = add_supplement(merged_data)
                                    st.success(f"Added supplement with ID: {product_id}")
                                    
                                    # Display image download link if available
                                    if merged_data.get('local_image_path') and os.path.exists(merged_data['local_image_path']):
                                        with open(merged_data['local_image_path'], "rb") as img_file:
                                            img_bytes = img_file.read()
                                            b64 = base64.b64encode(img_bytes).decode()
                                            href = f'<a href="data:image/jpeg;base64,{b64}" download="{os.path.basename(merged_data["local_image_path"])}">Download Product Image</a>'
                                            st.markdown(href, unsafe_allow_html=True)

elif page == "Batch Processing":
    st.header("Batch URL Processing")
    
    st.markdown("""
    This page allows you to upload a file containing multiple URLs and process them all at once.
    You can upload either:
    - A CSV file with a column containing URLs
    - A TXT file with one URL per line
    """)
    
    # File uploader
    uploaded_file = st.file_uploader("Upload URL List", type=["csv", "txt"])
    
    if uploaded_file is not None:
        # Parse the uploaded file
        urls = parse_url_file(uploaded_file)
        
        st.write(f"Found {len(urls)} valid URLs in the uploaded file.")
        
        # Show a preview of the URLs
        if urls:
            with st.expander("Preview URLs"):
                for i, url in enumerate(urls[:10]):
                    st.write(f"{i+1}. {url}")
                if len(urls) > 10:
                    st.write(f"... and {len(urls) - 10} more")
            
            # Batch processing options
            st.subheader("Processing Options")
            
            col1, col2 = st.columns(2)
            with col1:
                auto_add = st.checkbox("Automatically add to database", value=True, 
                                      help="When enabled, all successfully scraped supplements will be automatically added to the database")
            
            with col2:
                delay = st.number_input("Delay between requests (seconds)", 
                                       min_value=0.0, max_value=10.0, value=1.0, step=0.5,
                                       help="Add a delay between requests to avoid overloading the server")
            
            # Process button
            if st.button("Process All URLs"):
                # Create a progress bar
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Process the URLs in batches
                with st.spinner("Scraping URLs..."):
                    status_text.text("Starting batch processing...")
                    
                    # Batch process all URLs
                    results = batch_scrape_urls(urls, auto_add=auto_add, progress_bar=progress_bar)
                    st.session_state.batch_results = results
                    
                    # Show summary
                    status_text.text(f"Completed processing {len(urls)} URLs.")
                
                # Show results summary
                success_count = sum(1 for r in results if 'Success' in r['status'])
                error_count = len(results) - success_count
                
                st.subheader("Processing Results")
                st.write(f"Successfully processed: {success_count} URLs")
                st.write(f"Failed to process: {error_count} URLs")
                
                # Display results in a table
                result_df = pd.DataFrame([
                    {
                        'URL': r['url'],
                        'Status': r['status'],
                        'Brand': r['brand'],
                        'Product': r['product_name'],
                        'Score': r['overall_score']
                    } for r in results
                ])
                
                st.dataframe(result_df)
                
                # Option to download results as CSV
                csv = result_df.to_csv(index=False)
                b64 = base64.b64encode(csv.encode()).decode()
                href = f'<a href="data:file/csv;base64,{b64}" download="batch_processing_results.csv">Download Results as CSV</a>'
                st.markdown(href, unsafe_allow_html=True)
                
                # If not auto-adding, show interface to review and add manually
                if not auto_add and success_count > 0:
                    st.subheader("Review and Add to Database")
                    st.write("The following supplements were successfully scraped but not added to the database. Select the ones you want to add:")
                    
                    # Create a list of success items with product data
                    success_items = [r for r in results if 'Success' in r['status'] and 'product_data' in r]
                    
                    # Create multiselect for choosing which to add
                    selected_indices = st.multiselect(
                        "Select supplements to add",
                        options=list(range(len(success_items))),
                        format_func=lambda i: f"{success_items[i]['brand']} - {success_items[i]['product_name']}"
                    )
                    
                    if selected_indices and st.button("Add Selected to Database"):
                        for i in selected_indices:
                            add_supplement(success_items[i]['product_data'])
                        
                        st.success(f"Added {len(selected_indices)} supplements to database")
        else:
            st.error("No valid URLs found in the uploaded file. Please make sure your file contains URLs starting with http:// or https://")
    
    # Example template
    st.subheader("Download Template")
    st.write("Download a template file to see the expected format:")
    
    # Generate example CSV
    example_urls = [
        "https://www.nowfoods.com/products/double-strength-l-theanine-200-mg",
        "https://www.jarrow.com/products/ashwagandha-300-mg",
        "https://www.naturemade.com/products/vitamin-d3-2000-iu",
        "https://www.gardenoflife.com/products/raw-probiotics-ultimate-care-100-billion"
    ]
    
    example_df = pd.DataFrame({"product_url": example_urls})
    csv = example_df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="example_urls.csv">Download Example CSV</a>'
    st.markdown(href, unsafe_allow_html=True)
    
    # Generate example TXT
    txt = "\n".join(example_urls)
    b64 = base64.b64encode(txt.encode()).decode()
    href = f'<a href="data:file/txt;base64,{b64}" download="example_urls.txt">Download Example TXT</a>'
    st.markdown(href, unsafe_allow_html=True)

elif page == "View Database":
    st.header("View Supplement Database")
    
    # Show database statistics
    if not st.session_state.supplements_df.empty:
        st.subheader("Database Statistics")
        stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
        
        with stat_col1:
            st.metric("Total Supplements", len(st.session_state.supplements_df))
        
        with stat_col2:
            categories_count = st.session_state.supplements_df['main_category'].nunique()
            st.metric("Categories", categories_count)
        
        with stat_col3:
            brands_count = st.session_state.supplements_df['brand'].nunique()
            st.metric("Unique Brands", brands_count)
        
        with stat_col4:
            avg_score = st.session_state.supplements_df['overall_score'].mean()
            if pd.isna(avg_score):
                avg_score = 0
            st.metric("Avg. Score", f"{avg_score:.1f}/10")
        
        # Filter options
        filter_col1, filter_col2 = st.columns(2)
        
        with filter_col1:
            filter_category = st.multiselect(
                "Filter by Category",
                options=st.session_state.supplements_df['main_category'].dropna().unique()
            )
        
        with filter_col2:
            filter_brand = st.multiselect(
                "Filter by Brand",
                options=st.session_state.supplements_df['brand'].dropna().unique()
            )
        
        # Apply filters
        filtered_df = st.session_state.supplements_df.copy()
        
        if filter_category:
            filtered_df = filtered_df[filtered_df['main_category'].isin(filter_category)]
        
        if filter_brand:
            filtered_df = filtered_df[filtered_df['brand'].isin(filter_brand)]
        
        # Show the data
        st.subheader("Supplement Data")
        st.dataframe(filtered_df[['id', 'barcode', 'brand', 'product_name', 'main_category', 'subcategory', 'overall_score']])
        
        # Display a single supplement details
        st.subheader("View Supplement Details")
        selected_id = st.selectbox("Select Supplement", options=filtered_df['id'].tolist())
        
        if selected_id:
            selected_supp = filtered_df[filtered_df['id'] == selected_id].iloc[0]
            
            detail_col1, detail_col2 = st.columns([1, 2])
            
            with detail_col1:
                image = None
                if selected_supp.get('local_image_path') and os.path.exists(selected_supp.get('local_image_path')):
                    image = display_image(image_path=selected_supp['local_image_path'])
                elif selected_supp.get('image_url'):
                    image = display_image(image_url=selected_supp['image_url'])
                    
                if image:
                    st.image(image, caption=f"{selected_supp['brand']} {selected_supp['product_name']}", width=250)
                else:
                    st.info("No image available")
            
            with detail_col2:
                st.markdown(f"### {selected_supp['brand']} {selected_supp['product_name']}")
                st.markdown(f"**Category:** {selected_supp['main_category']} - {selected_supp['subcategory']}")
                st.markdown(f"**Barcode:** {selected_supp['barcode']}")
                
                # Show scores in a horizontal bar
                scores = {
                    'Overall Score': selected_supp.get('overall_score', 0),
                    'Ingredients': selected_supp.get('ingredients_score', 0),
                    'Manufacturing': selected_supp.get('manufacturing_quality_score', 0),
                    'Testing': selected_supp.get('testing_verification_score', 0),
                    'Label Accuracy': selected_supp.get('label_accuracy_score', 0),
                    'Nutritional Quality': selected_supp.get('nutritional_quality_score', 0)
                }
                
                score_df = pd.DataFrame(list(scores.items()), columns=['Metric', 'Score'])
                if not score_df['Score'].isna().all():
                    fig, ax = plt.subplots(figsize=(10, 3))
                    bars = sns.barplot(x='Score', y='Metric', data=score_df, orient='h', palette='viridis')
                    ax.set_xlim(0, 10)
                    ax.set_title('Supplement Scores')
                    st.pyplot(fig)
                
                # Show certification badges
                cert_col1, cert_col2, cert_col3, cert_col4 = st.columns(4)
                
                with cert_col1:
                    if selected_supp.get('gmp_certified'):
                        st.success("✓ GMP Certified")
                
                with cert_col2:
                    if selected_supp.get('third_party_tested'):
                        st.success("✓ Third-Party Tested")
                
                with cert_col3:
                    if selected_supp.get('non_gmo'):
                        st.success("✓ Non-GMO")
                
                with cert_col4:
                    if selected_supp.get('organic'):
                        st.success("✓ Organic")
                
                # Ingredients
                st.markdown("#### Ingredients")
                st.markdown(selected_supp.get('ingredients', 'No ingredient data available'))
                
                # Other details
                with st.expander("Additional Details"):
                    st.markdown(f"**Serving Size:** {selected_supp.get('serving_size', 'N/A')}")
                    st.markdown(f"**Directions:** {selected_supp.get('directions', 'N/A')}")
                    st.markdown(f"**Warnings:** {selected_supp.get('warnings', 'N/A')}")
                    st.markdown(f"**Country of Origin:** {selected_supp.get('country_of_origin', 'N/A')}")
                    st.markdown(f"**Website:** {selected_supp.get('website', 'N/A')}")
            
            # Edit button
            if st.button("Edit this Supplement"):
                st.session_state.editing_supplement = selected_id
                st.info("Editing functionality would be implemented here")
    else:
        st.info("Your database is empty. Go to the 'Search & Add' page to add supplements.")

elif page == "Export Data":
    st.header("Export Data")
    
    if not st.session_state.supplements_df.empty:
        # Export options
        export_format = st.radio("Export Format", ["CSV", "JSON", "Firebase JSON"], horizontal=True)
        
        # Generate download link
        if export_format == "CSV":
            csv = st.session_state.supplements_df.to_csv(index=False)
            b64 = base64.b64encode(csv.encode()).decode()
            href = f'<a href="data:file/csv;base64,{b64}" download="supplements_database.csv">Download CSV File</a>'
            st.markdown(href, unsafe_allow_html=True)
        
        elif export_format == "JSON":
            json_str = st.session_state.supplements_df.to_json(orient='records')
            b64 = base64.b64encode(json_str.encode()).decode()
            href = f'<a href="data:file/json;base64,{b64}" download="supplements_database.json">Download JSON File</a>'
            st.markdown(href, unsafe_allow_html=True)
        
        elif export_format == "Firebase JSON":
            # Convert to Firebase format (each document keyed by ID)
            firebase_data = {}
            for _, row in st.session_state.supplements_df.iterrows():
                supplement_id = row['id']
                firebase_data[supplement_id] = row.to_dict()
            
            json_str = json.dumps(firebase_data)
            b64 = base64.b64encode(json_str.encode()).decode()
            href = f'<a href="data:file/json;base64,{b64}" download="supplements_firebase.json">Download Firebase JSON</a>'
            st.markdown(href, unsafe_allow_html=True)
        
        # Firebase direct upload option (would need implementation)
        st.subheader("Upload to Firebase")
        st.info("Direct Firebase upload would be implemented here, requiring Firebase credentials.")
        
        # Mock Firebase upload interface
        with st.expander("Firebase Upload Configuration"):
            st.text_input("Firebase Project ID")
            st.text_input("Storage Bucket")
            st.file_uploader("Upload Service Account JSON")
            st.checkbox("Upload Images to Storage")
            st.button("Upload to Firebase")
    else:
        st.info("Your database is empty. Go to the 'Search & Add' page to add supplements.")

elif page == "Settings":
    st.header("Settings")
    
    # Database management
    st.subheader("Database Management")
    db_action = st.radio("Database Action", ["Clear Database", "Import Data"], horizontal=True)
    
    if db_action == "Clear Database":
        if st.button("Clear All Data"):
            st.session_state.supplements_df = pd.DataFrame(columns=st.session_state.supplements_df.columns)
            st.success("Database cleared successfully")
    
    elif db_action == "Import Data":
        uploaded_file = st.file_uploader("Upload CSV or JSON", type=["csv", "json"])
        
        if uploaded_file is not None:
            if uploaded_file.name.endswith('.csv'):
                imported_df = pd.read_csv(uploaded_file)
                st.session_state.supplements_df = imported_df
                st.success(f"Successfully imported {len(imported_df)} supplements")
            elif uploaded_file.name.endswith('.json'):
                try:
                    imported_data = json.load(uploaded_file)
                    
                    # Check if it's Firebase format or regular JSON array
                    if isinstance(imported_data, dict):
                        # Firebase format - convert to DataFrame
                        records = []
                        for supp_id, supp_data in imported_data.items():
                            if 'id' not in supp_data:
                                supp_data['id'] = supp_id
                            records.append(supp_data)
                        imported_df = pd.DataFrame(records)
                    else:
                        # Regular JSON array
                        imported_df = pd.DataFrame(imported_data)
                    
                    st.session_state.supplements_df = imported_df
                    st.success(f"Successfully imported {len(imported_df)} supplements")
                except Exception as e:
                    st.error(f"Error importing JSON: {e}")
    
    # Configuration
    st.subheader("App Configuration")
    
    with st.expander("Image Settings"):
        st.selectbox("Default Image Size", ["800x800", "600x600", "400x400"])
        st.checkbox("Save Images Locally", value=True)
        st.text_input("Image Directory", value=st.session_state.images_dir)
    
    with st.expander("API Configuration"):
        st.text_input("Open Food Facts API Rate Limit", value="1 request per second")
        st.text_input("Google API Key (for image search)")
        st.checkbox("Enable Web Scraping", value=True)
        st.multiselect("Retailer Sources for Scraping", ["Amazon", "iHerb", "Walmart", "GNC", "Vitamin Shoppe"])
    
    with st.expander("Batch Processing Settings"):
        st.number_input("Default Delay Between Requests (seconds)", min_value=0.0, max_value=5.0, value=1.0, step=0.1)
        st.checkbox("Skip Failed URLs in Batch Processing", value=True)
        st.number_input("Maximum URLs to Process in One Batch", min_value=1, max_value=1000, value=100)

# Place a progress bar at the bottom to show database size
st.sidebar.markdown("---")
st.sidebar.subheader("Database Status")
total_supplements = len(st.session_state.supplements_df)
st.sidebar.progress(min(total_supplements / 100, 1.0))
st.sidebar.text(f"{total_supplements} supplements collected")

# Footer
st.sidebar.markdown("---")
st.sidebar.info("© 2025 Supplement Scanner App")
