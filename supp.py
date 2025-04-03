import streamlit as st
import pandas as pd
import requests
import os
import time
import matplotlib.pyplot as plt
import seaborn as sns
from PIL import Image
from io import BytesIO
import re
import hashlib
import base64
import json
from datetime import datetime
import uuid

# Import our supplement data collection module
from supplement_collector import (
    fetch_from_off,
    download_image,
    fetch_supplement_image,
    categorize_supplement,
    calculate_scores,
    ingredient_category_map
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

# Sidebar navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Search & Add", "View Database", "Export Data", "Settings"])

if page == "Search & Add":
    st.header("Search & Add Supplements")
    
    search_col1, search_col2 = st.columns([3, 1])
    
    with search_col1:
        search_method = st.radio("Search Method", ["Barcode", "Product Name"], horizontal=True)
        
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

# Place a progress bar at the bottom to show database size
st.sidebar.markdown("---")
st.sidebar.subheader("Database Status")
total_supplements = len(st.session_state.supplements_df)
st.sidebar.progress(min(total_supplements / 100, 1.0))
st.sidebar.text(f"{total_supplements} supplements collected")

# Footer
st.sidebar.markdown("---")
st.sidebar.info("© 2025 Supplement Scanner App")
