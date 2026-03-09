import requests
import csv
from datetime import datetime
import os



def fetch_portfolio(user_address):
    url = "https://data-api.polymarket.com/positions"
    params = {"user": user_address}

    response = requests.get(url, params=params)
    response.raise_for_status()

    return response.json()


def fetch_trades(user_address):
    url = "https://data-api.polymarket.com/trades"
    params = {
        "user": user_address,
        "limit": 1000
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    return response.json()


def get_first_trade_times(trades):

    first_trade = {}

    for t in trades:
        key = (t.get("title"), t.get("outcome"))
        ts = t.get("timestamp")

        if key not in first_trade:
            first_trade[key] = ts
        else:
            first_trade[key] = min(first_trade[key], ts)

    return first_trade


def log_positions(user_address, positions, first_trade_times):

    log_file = f"polymarket_logbook_{user_address}.csv"

    rows = []

    for p in positions:

        title = p.get("title")
        outcome = p.get("outcome")
        shares = float(p.get("size", 0))
        avg_price = p.get("avgPrice")
        cur_price = p.get("curPrice")
        pnl = p.get("cashPnl")

        status = "OPEN" if shares > 0 else "CLOSED"

        ts = first_trade_times.get((title, outcome))

        if ts:
            ts = datetime.fromtimestamp(ts)
        else:
            ts = None

        rows.append([
            ts,
            title,
            outcome,
            shares,
            avg_price,
            cur_price,
            pnl,
            status
        ])

    rows.sort(key=lambda x: x[0] if x[0] else datetime.max)

    with open(log_file, "w", newline="", encoding="utf-8") as f:

        writer = csv.writer(f)

        writer.writerow([
            "first_trade_time",
            "market",
            "outcome",
            "shares",
            "avg_price",
            "current_price",
            "pnl",
            "status"
        ])

        for r in rows:
            if r[0]:
                r[0] = r[0].strftime("%Y-%m-%d %H:%M:%S")
            writer.writerow(r)


def display_portfolio(user_address, positions, first_trade_times):

    if not positions:
        print("No portfolio data.")
        return

    open_positions = [p for p in positions if float(p.get("size", 0)) > 0]

    print("\n" + "=" * 60)
    print(f"📊 POLYMARKET OPEN POSITIONS FOR {user_address}")
    print("=" * 60)

    total_value = 0
    total_pnl = 0

    for p in open_positions:

        title = p.get("title")
        outcome = p.get("outcome")
        shares = float(p.get("size", 0))
        avg_price = float(p.get("avgPrice", 0))
        cur_price = float(p.get("curPrice", 0))
        pnl = float(p.get("cashPnl", 0))

        first_trade_ts = first_trade_times.get((title, outcome))

        if first_trade_ts:
            first_trade_ts = datetime.fromtimestamp(first_trade_ts).strftime("%Y-%m-%d %H:%M:%S")
        else:
            first_trade_ts = "Unknown"

        total_value += float(p.get("currentValue", 0))
        total_pnl += pnl

        print(f"\nMarket: {title}")
        print(f"Outcome: {outcome}")
        print(f"First trade: {first_trade_ts}")
        print(f"Shares: {shares}")
        print(f"Avg price: {avg_price}")
        print(f"Current price: {cur_price}")
        print(f"PnL: ${pnl:.2f}")

    print("\n" + "-" * 60)
    print(f"Total value: ${total_value:.2f}")
    print(f"Total PnL: ${total_pnl:.2f}")