'''
python3 -m venv .venv
source .venv/bin/activate
'''

import os
import requests
import pandas as pd
import json
from datetime import datetime

gamma_api = "https://gamma-api.polymarket.com"
data_api = "https://data-api.polymarket.com"
clob_api = "https://clob.polymarket.com"

def fetch_user_activity(user_address, limit):
    base_url = "https://data-api.polymarket.com/trades"
    params = {
        'user': user_address,
        'limit': limit
    }

    try:
        print(f"Fetching up to {limit} trades for user: {user_address}")
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        
        trades = response.json()
        return trades

    except requests.exceptions.RequestException as e:
        print(f"An error occurred during the API request: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding the JSON response: {e}")
        return None

def process_and_display_trades(trade_data):

    if not trade_data:
        print("No trade data to process.")
        return None
    
    print(f"\nSuccessfully retrieved {len(trade_data)} trades.")
    
    # Show sample of first record
    print("\nSample trade data (first record):")
    print(json.dumps(trade_data[0], indent=2))
    
    # Create the main DataFrame
    df = pd.DataFrame(trade_data)
    
    # Create summary DataFrame with only the columns you want
    summary_columns = [
        'timestamp', 
        'title', 
        'side', 
        'outcome', 
        'price', 
        'size', 
        'slug', 
        'eventSlug', 
        'proxyWallet', 
        'asset', 
        'conditionId'
    ]
    
    # Filter data col
    existing_columns = [col for col in summary_columns if col in df.columns]
    df_summary = df[existing_columns].copy()
    
    # time convertion
    if 'timestamp' in df_summary.columns:
        df_summary['timestamp'] = pd.to_datetime(df_summary['timestamp'], unit='s').dt.strftime('%d/%m/%Y %H:%M:%S')
    
    print("\n" + "="*60)
    print("SUMMARY DATAFRAME")
    print("="*60)
    print(df_summary)

    return df_summary

def load_previous_trades(user_address):
    """Loads previously seen transaction hashes from a file."""
    filename = f"seen_trades_{user_address[:10]}.json"
    try:
        with open(filename, 'r') as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()

def save_seen_trades(user_address, trade_hashes):
    """Saves seen transaction hashes to a file."""
    filename = f"seen_trades_{user_address[:10]}.json"
    with open(filename, 'w') as f:
        json.dump(list(trade_hashes), f, indent=2)

def update_trade_log(df_new_summary, target_user, all_trade_data):
    """
    Updates the trade log CSV with new trades and ensures newest trades are at the top.
    """
    log_filename = f"trade_log_{target_user[:10]}.csv"
    
    if df_new_summary is not None and not df_new_summary.empty:
        # Convert timestamp strings back to datetime for proper sorting
        df_new_summary['timestamp_dt'] = pd.to_datetime(df_new_summary['timestamp'], format='%d/%m/%Y %H:%M:%S')
        
        # Check if log file already exists
        if os.path.exists(log_filename):
            # Read existing log
            df_existing = pd.read_csv(log_filename)
            
            # Convert existing timestamps to datetime for sorting
            df_existing['timestamp_dt'] = pd.to_datetime(df_existing['timestamp'], format='%d/%m/%Y %H:%M:%S')
            
            # Combine new and existing data
            df_combined = pd.concat([df_existing, df_new_summary], ignore_index=True)
        else:
            # First time - just use new data
            df_combined = df_new_summary.copy()
            df_combined['timestamp_dt'] = pd.to_datetime(df_combined['timestamp'], format='%d/%m/%Y %H:%M:%S')
        
        # Remove duplicates based on transactionHash (if available) or all columns
        if 'transactionHash' in df_combined.columns:
            df_combined = df_combined.drop_duplicates(subset=['transactionHash'], keep='last')
        else:
            df_combined = df_combined.drop_duplicates()
        
        # Sort by timestamp (newest first) - this is the key fix!
        df_combined = df_combined.sort_values('timestamp_dt', ascending=False)
        
        # Drop the temporary datetime column before saving
        df_combined = df_combined.drop(columns=['timestamp_dt'])
        
        # Save back to CSV with newest at top
        df_combined.to_csv(log_filename, index=False)
        print(f"✅ Trade log updated: {log_filename} (newest trades at top)")
        
        return df_combined
    else:
        print("No new trades to add to log.")
        return None

def track_user_trades(user_address, limit):
    """
    Complete workflow to track new trades for a specific user.
    """
    # Load previous state
    previous_tx_set = load_previous_trades(user_address)
    print(f"Loaded {len(previous_tx_set)} previously seen transactions.")

    # Fetch current data
    trade_data = fetch_user_activity(user_address, limit=limit)
    
    if not trade_data:
        print("Failed to retrieve trade data.")
        return

    # Process trades
    current_tx_set = {t['transactionHash'] for t in trade_data if 'transactionHash' in t}
    new_tx_hashes = current_tx_set - previous_tx_set

    if new_tx_hashes:
        print(f"\n🎉 Found {len(new_tx_hashes)} NEW trades!")
        new_trades = [t for t in trade_data if t['transactionHash'] in new_tx_hashes]
        
        df_new = process_and_display_trades(new_trades)
        if df_new is not None:
            update_trade_log(df_new, user_address, trade_data)
    else:
        print("✅ No new trades found.")

    # Update state
    save_seen_trades(user_address, current_tx_set)
    
    # Show top 10 rows from CSV
    log_file = f"trade_log_{user_address[:10]}.csv"
    if os.path.exists(log_file):
        print("\n" + "="*60)
        print("📊 TOP 10 MOST RECENT TRADES")
        print("="*60)
        df_log = pd.read_csv(log_file)
        print(df_log[['timestamp', 'title', 'side', 'outcome', 'price', 'size']].head(10).to_string())
        print(f"\n📈 Total trades in log: {len(df_log)} (showing top 10)")
    else:
        print("\n📁 No trade log file found yet.")


###################################################################
#                                                                 #
#                     Main Execution                              #
#                                                                 #
###################################################################

if __name__ == "__main__":
    # Configuration
    target_user = "0xde7be6d489bce070a959e0cb813128ae659b5f4b"  
    limit = 100
    
    # Run the tracker
    track_user_trades(target_user, limit)