import os
from datetime import datetime
import pandas as pd
import requests
from bs4 import BeautifulSoup

# Target URL for SIH Problem Statements
URL = "https://www.sih.gov.in/sih2026PS" # Update path if necessary

def scrape_sih_data():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(URL, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching the portal: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    scraped_data = []
    
    # NOTE: Inspect the actual DOM elements on the live site to match your CSS selectors.
    # This loop assumes rows are contained in a table or structured grid blocks.
    # Example logic matching typical table rows:
    rows = soup.find_all('tr') # Or whatever container holds the problem items
    
    for row in rows:
        # Example extraction: adjust tags based on the site's exact table structure
        cols = row.find_all('td')
        if len(cols) > 3:
            ps_id = cols[0].text.strip()
            title = cols[1].text.strip()
            # Assuming a column or text string containing ideas count like "120/500"
            ideas_text = cols[2].text.strip() 
            
            scraped_data.append({
                "Timestamp": timestamp,
                "PS_ID": ps_id,
                "Title": title,
                "Submissions": ideas_text
            })
            
    return scraped_data

def update_history(new_data):
    if not new_data:
        print("No data collected during this run.")
        return

    os.makedirs("data", exist_ok=True)
    csv_file = "data/sih_history.csv"
    
    df_new = pd.DataFrame(new_data)
    
    if os.path.exists(csv_file):
        df_old = pd.read_csv(csv_file)
        df_combined = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df_combined = df_new
        
    df_combined.to_csv(csv_file, index=False)
    print(f"Successfully appended {len(new_data)} rows to history at {datetime.now()}")

if __name__ == "__main__":
    data = scrape_sih_data()
    update_history(data)