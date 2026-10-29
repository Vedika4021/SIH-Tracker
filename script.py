import os
from datetime import datetime
import pandas as pd
import requests
from bs4 import BeautifulSoup

URL = "https://www.sih.gov.in/sih2026PS"
TARGET_PS_ID = "26264" # Or "SIH26264"

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
        row_text = row.text
        # Look specifically for your problem statement number
        if TARGET_PS_ID in row_text:
            cols = row.find_all('td')
            if len(cols) >= 3:
                try:
                    # Extract text from all columns to find the one with the submission count (e.g., contains "/")
                    title = "N/A"
                    ideas_text = "0/500"
                    
                    for col in cols:
                        text = col.text.strip()
                        if "/" in text and ("500" in text or "Ideas" in text or text.replace("/", "").isdigit()):
                            ideas_text = text
                        elif len(text) > 15: # Likely the title description
                            title = text

                    scraped_data.append({
                        "Timestamp": timestamp,
                        "PS_ID": f"SIH{TARGET_PS_ID}",
                        "Title": title,
                        "Submissions": ideas_text
                    })
                    print(f"Found target {TARGET_PS_ID} with submissions: {ideas_text}")
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
    print(f"Successfully recorded update for SIH{TARGET_PS_ID} at {datetime.now()}")

if __name__ == "__main__":
    data = scrape_sih_data()
    update_history(data)