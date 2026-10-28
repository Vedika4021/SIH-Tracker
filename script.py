import os
from datetime import datetime
import pandas as pd
import requests
from bs4 import BeautifulSoup

# Target URL for SIH Problem Statements
URL = "https://www.sih.gov.in/sih2026PS"

# Your specific Problem Statement ID
TARGET_PS_ID = "SIH26264"

def scrape_sih_data():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
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
    rows = soup.find_all('tr')
    
    for row in rows:
        cols = row.find_all('td')
        if len(cols) >= 4:
            try:
                ps_id = cols[3].text.strip() if len(cols) > 3 else "N/A"
                
                # Filter specifically for your target ID
                if ps_id == TARGET_PS_ID:
                    title = cols[2].text.strip() if len(cols) > 2 else "N/A"
                    ideas_text = cols[4].text.strip() if len(cols) > 4 else "0/500"
                    
                    scraped_data.append({
                        "Timestamp": timestamp,
                        "PS_ID": ps_id,
                        "Title": title,
                        "Submissions": ideas_text
                    })
                    break 
            except Exception as inner_err:
                continue
                
    return scraped_data

def update_history(new_data):
    if not new_data:
        print(f"Target Problem Statement {TARGET_PS_ID} not found in this run.")
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
    print(f"Successfully recorded update for {TARGET_PS_ID} at {datetime.now()}")

if __name__ == "__main__":
    data = scrape_sih_data()
    update_history(data)