import streamlit as st
import pandas as pd
from io import StringIO # To handle uploaded file in memory
import scraper_module # Import the scraping functions

# --- Streamlit App Configuration ---
st.set_page_config(page_title="Supplement Scraper", layout="wide")
st.title("💊 Supplement Ingredient & Directions Scraper")

st.markdown("""
Upload a CSV file with a column named `ProductURL` containing the links to supplement product pages.
The tool will attempt to scrape the Ingredients and Directions text directly from the HTML.

**Important Notes:**
*   **Accuracy:** Scraping depends heavily on website structure. Results may be incomplete or missing, especially if data is in images (like nutrition labels) or loaded dynamically. Target.com is known to use images.
*   **Anti-Scraping:** Major retailers (Amazon, Walmart) actively block scrapers. Success isn't guaranteed and may require more advanced techniques (proxies, etc.) not included here. Be respectful and use moderate delays.
*   **Terms of Service:** Ensure you comply with the website's terms of service regarding scraping.
*   **Images/OCR:** This version **does not** analyze images (OCR).
""")

# --- File Upload ---
uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

if uploaded_file is not None:
    # Read the uploaded CSV file
    try:
        # Use StringIO to read the uploaded file object as a string
        stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
        df_input = pd.read_csv(stringio)

        if 'ProductURL' not in df_input.columns:
            st.error("CSV file must contain a column named 'ProductURL'.")
        else:
            st.success(f"Successfully loaded {len(df_input)} URLs from {uploaded_file.name}")
            st.dataframe(df_input.head()) # Show preview

            # --- Scraping Execution ---
            if st.button("✨ Start Scraping"):
                results = []
                total_urls = len(df_input)
                progress_bar = st.progress(0)
                status_text = st.empty() # Placeholder for status updates

                st.info("Scraping started... This may take a while depending on the number of URLs and delays.")
                st.warning(f"A delay of {scraper_module.REQUEST_DELAY_SECONDS} seconds is applied between requests.")

                # Use st.expander for detailed logs if needed
                # log_expander = st.expander("Show Detailed Logs")

                for index, row in df_input.iterrows():
                    url = row['ProductURL']
                    status_text.text(f"Processing URL {index + 1}/{total_urls}: {url}")

                    # Call the scraping function from the imported module
                    result = scraper_module.scrape_single_url(url)
                    results.append(result)

                    # Update progress bar
                    progress_bar.progress((index + 1) / total_urls)

                    # Optional: Log detailed status within the app
                    # with log_expander:
                    #     st.text(f"URL: {result['URL']}")
                    #     st.text(f" Status: {result['Status']}")
                    #     st.text(f" Ingredients Found: {'Yes' if not result['Ingredients'].startswith(('Ingredient','Invalid','Parsing','Fetch')) else 'No'}")
                    #     st.text(f" Directions Found: {'Yes' if not result['Directions'].startswith(('Direction','Invalid','Parsing','Fetch')) else 'No'}")
                    #     st.divider()

                status_text.success("Scraping complete!")

                # --- Display Results ---
                st.subheader("📊 Scraping Results")
                df_output = pd.DataFrame(results)

                # Display the DataFrame (allow scrolling)
                st.dataframe(df_output)

                # --- Download Results ---
                st.subheader("💾 Download Results")

                @st.cache_data # Cache the conversion to prevent re-running on interaction
                def convert_df_to_csv(df):
                    # IMPORTANT: Cache the conversion to prevent computation on every rerun
                    return df.to_csv(index=False).encode('utf-8')

                csv_data = convert_df_to_csv(df_output)

                st.download_button(
                    label="Download results as CSV",
                    data=csv_data,
                    file_name='supplement_scrape_results.csv',
                    mime='text/csv',
                )

    except Exception as e:
        st.error(f"An error occurred processing the CSV file: {e}")
else:
    st.info("Awaiting CSV file upload.")

# --- Footer/Info ---
st.markdown("---")
st.markdown("Developed with Python, Streamlit, Requests, and BeautifulSoup.")
