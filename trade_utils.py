import os
import json
from datetime import datetime

import pandas as pd
import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, DATA_DIR
from notifications import send_telegram_message


def fetch_user_activity(user_address, limit):
    base_url = "https://data-api.polymarket.com/trades"
    params = {
        "user": user_address,
        "limit": limit,
    }

    try:
        print(f"Fetching up to {limit} trades for user: {user_address}")
        response = requests.get(base_url, params=params, timeout=15)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"An error occurred during the API request: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding the JSON response: {e}")
        return None


def process_and_display_trades(trade_data, user_label, user_address):
    if not trade_data:
        print("No trade data to process.")
        return None

    print(f"\nSuccessfully retrieved {len(trade_data)} trades for {user_label} ({user_address}).")

    print("\nSample trade data (first record):")
    print(json.dumps(trade_data[0], indent=2))

    df = pd.DataFrame(trade_data)
    df["user"] = user_label
    df["user_address"] = user_address

    summary_columns = [
        "user",
        "user_address",
        "timestamp",
        "title",
        "side",
        "outcome",
        "price",
        "size",
        "slug",
        "eventSlug",
        "proxyWallet",
        "asset",
        "conditionId",
        "transactionHash",
    ]

    existing_columns = [col for col in summary_columns if col in df.columns]
    df_summary = df[existing_columns].copy()

    if "timestamp" in df_summary.columns:
        df_summary["timestamp"] = pd.to_datetime(
            df_summary["timestamp"], unit="s"
        ).dt.strftime("%d/%m/%Y %H:%M:%S")

    print("\n" + "=" * 60)
    print(f"SUMMARY DATAFRAME - {user_label}")
    print("=" * 60)
    print(df_summary)

    return df_summary


def load_previous_trades(user_label):
    filename = os.path.join(DATA_DIR, f"seen_trades_{user_label}.json")
    try:
        with open(filename, "r") as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()


def save_seen_trades(user_label, trade_hashes):
    filename = os.path.join(DATA_DIR, f"seen_trades_{user_label}.json")
    with open(filename, "w") as f:
        json.dump(list(trade_hashes), f, indent=2)


def update_trade_log(df_new_summary, user_label):
    log_filename = os.path.join(DATA_DIR, f"trade_log_{user_label}.csv")

    if df_new_summary is not None and not df_new_summary.empty:
        df_new_summary = df_new_summary.copy()
        df_new_summary["timestamp_dt"] = pd.to_datetime(
            df_new_summary["timestamp"],
            format="%d/%m/%Y %H:%M:%S",
        )

        if os.path.exists(log_filename):
            df_existing = pd.read_csv(log_filename)
            df_existing["timestamp_dt"] = pd.to_datetime(
                df_existing["timestamp"],
                format="%d/%m/%Y %H:%M:%S",
            )
            df_combined = pd.concat([df_existing, df_new_summary], ignore_index=True)
        else:
            df_combined = df_new_summary.copy()

        if "transactionHash" in df_combined.columns:
            df_combined = df_combined.drop_duplicates(subset=["transactionHash"], keep="last")
        else:
            df_combined = df_combined.drop_duplicates()

        df_combined = df_combined.sort_values("timestamp_dt", ascending=False)
        df_combined = df_combined.drop(columns=["timestamp_dt"])

        df_combined.to_csv(log_filename, index=False)
        print(f"✅ Trade log updated: {log_filename} (newest trades at top)")
        return df_combined

    print("No new trades to add to log.")
    return None


def send_telegram_message(bot_token, chat_id, message):
    if not bot_token or not chat_id:
        print("Telegram credentials are missing; skipping alert.")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
    }
    try:
        response = requests.post(url, data=payload, timeout=10)
        response.raise_for_status()
        print("📩 Telegram alert sent.")
    except requests.exceptions.RequestException as e:
        print(f"Failed to send Telegram message: {e}")


def format_trade_message(trade, user_label, user_address):
    ts = trade.get("timestamp")
    if ts:
        ts = datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M:%S")
    else:
        ts = "Unknown time"

    title = trade.get("title", "Unknown market")
    side = trade.get("side", "Unknown side")
    outcome = trade.get("outcome", "Unknown outcome")
    price = trade.get("price", "N/A")
    size = trade.get("size", "N/A")
    tx = trade.get("transactionHash", "N/A")

    return (
        f"🎉 New trade detected\n"
        f"User: {user_label}\n"
        f"Time: {ts}\n"
        f"Market: {title}\n"
        f"Side: {side}\n"
        f"Outcome: {outcome}\n"
        f"Price: {price}\n"
        f"Size: {size}\n"
        f"Tx: {tx}"
    )


def track_user_trades(user_label, user_address, limit):
    previous_tx_set = load_previous_trades(user_label)
    print(f"Loaded {len(previous_tx_set)} previously seen transactions for {user_label}.")

    trade_data = fetch_user_activity(user_address, limit=limit)

    if not trade_data:
        print("Failed to retrieve trade data.")
        return

    current_tx_set = {t["transactionHash"] for t in trade_data if "transactionHash" in t}
    new_tx_hashes = current_tx_set - previous_tx_set

    if new_tx_hashes:
        print(f"\n🎉 Found {len(new_tx_hashes)} NEW trades for {user_label}!")

        new_trades = [t for t in trade_data if t.get("transactionHash") in new_tx_hashes]

        new_trades_terminal = sorted(
            new_trades,
            key=lambda t: t.get("timestamp", 0),
            reverse=True,
        )

        new_trades_telegram = sorted(
            new_trades,
            key=lambda t: t.get("timestamp", 0),
        )

        df_new = process_and_display_trades(new_trades_terminal, user_label, user_address)
        if df_new is not None:
            update_trade_log(df_new, user_label)

        # Send positions FIRST
            from portfolio_utils import send_positions_summary
            send_positions_summary(user_label, user_address)

        # Then send trade alerts
        for trade in new_trades_telegram:
            msg = format_trade_message(trade, user_label, user_address)
            send_telegram_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, msg)

    else:
        print(f"✅ No new trades found for {user_label}.")

    save_seen_trades(user_label, current_tx_set)

    log_file = os.path.join(DATA_DIR, f"trade_log_{user_label}.csv")
    if os.path.exists(log_file):
        print("\n" + "=" * 60)
        print(f"📊 TOP 10 MOST RECENT TRADES - {user_label}")
        print("=" * 60)
        df_log = pd.read_csv(log_file)

        cols_to_show = [
            c for c in ["user", "timestamp", "title", "side", "outcome", "price", "size"]
            if c in df_log.columns
        ]
        print(df_log[cols_to_show].head(10).to_string(index=False))
        print(f"\n📈 Total trades in log: {len(df_log)} (showing top 10)")
    else:
        print("\n📁 No trade log file found yet.")

 
    