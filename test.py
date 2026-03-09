import requests
'''
def fetch_portfolio(user_address):
    url = "https://data-api.polymarket.com/positions"
    params = {"user": user_address}

    response = requests.get(url, params=params)
    response.raise_for_status()

    return response.json()


def display_portfolio(positions):
    if not positions:
        print("No portfolio data.")
        return

    # Filter only open positions
    open_positions = [p for p in positions if float(p.get("curPrice", 0)) > 0]

    if not open_positions:
        print("No open positions.")
        return

    print("\n" + "="*60)
    print("📊 POLYMARKET OPEN POSITIONS")
    print("="*60)

    total_value = 0
    total_pnl = 0

    for p in open_positions:
        title = p.get("title")
        outcome = p.get("outcome")
        shares = float(p.get("size", 0))
        avg_price = float(p.get("avgPrice", 0))
        cur_price = float(p.get("curPrice", 0))
        pnl = float(p.get("cashPnl", 0))

        total_value += float(p.get("currentValue", 0))
        total_pnl += pnl

        print(f"\nMarket: {title}")
        print(f"Outcome: {outcome}")
        print(f"Shares: {shares}")
        print(f"Avg price: {avg_price}")
        print(f"Current price: {cur_price}")
        print(f"PnL: ${pnl:.2f}")

    print("\n" + "-"*60)
    print(f"Total value: ${total_value:.2f}")
    print(f"Total PnL: ${total_pnl:.2f}")


portfolio = fetch_portfolio("0x121785324CCa3fcf5a60D12ED8a96B93583C690a")
display_portfolio(portfolio)


import requests
import csv
from datetime import datetime
import os

LOG_FILE = "polymarket_logbook.csv"


def fetch_portfolio(user_address):
    url = "https://data-api.polymarket.com/positions"
    params = {"user": user_address}

    response = requests.get(url, params=params)
    response.raise_for_status()

    return response.json()


def log_positions(positions):
    """Save positions to a CSV logbook."""
    
    file_exists = os.path.exists(LOG_FILE)

    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Write header if file doesn't exist yet
        if not file_exists:
            writer.writerow([
                "timestamp",
                "market",
                "outcome",
                "shares",
                "avg_price",
                "current_price",
                "pnl",
                "status"
            ])

        for p in positions:
            shares = float(p.get("size", 0))
            status = "OPEN" if shares > 0 else "CLOSED"

            writer.writerow([
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                p.get("title"),
                p.get("outcome"),
                shares,
                p.get("avgPrice"),
                p.get("curPrice"),
                p.get("cashPnl"),
                status
            ])


def display_portfolio(positions):
    if not positions:
        print("No portfolio data.")
        return

    open_positions = [p for p in positions if float(p.get("size", 0)) > 0]
    closed_positions = [p for p in positions if float(p.get("size", 0)) == 0]

    print("\n" + "="*60)
    print("📊 POLYMARKET OPEN POSITIONS")
    print("="*60)

    total_value = 0
    total_pnl = 0

    for p in open_positions:
        title = p.get("title")
        outcome = p.get("outcome")
        shares = float(p.get("size", 0))
        avg_price = float(p.get("avgPrice", 0))
        cur_price = float(p.get("curPrice", 0))
        pnl = float(p.get("cashPnl", 0))

        total_value += float(p.get("currentValue", 0))
        total_pnl += pnl

        print(f"\nMarket: {title}")
        print(f"Outcome: {outcome}")
        print(f"Shares: {shares}")
        print(f"Avg price: {avg_price}")
        print(f"Current price: {cur_price}")
        print(f"PnL: ${pnl:.2f}")

    print("\n" + "-"*60)
    print(f"Total value: ${total_value:.2f}")
    print(f"Total PnL: ${total_pnl:.2f}")

    print("\nClosed positions:", len(closed_positions))


portfolio = fetch_portfolio("0x121785324CCa3fcf5a60D12ED8a96B93583C690a")

display_portfolio(portfolio)

# Save to logbook
log_positions(portfolio)
'''

import requests
import csv
from datetime import datetime
import os

LOG_FILE = "polymarket_logbook.csv"


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
    """
    Build dictionary of earliest trade timestamp for each market/outcome.
    """
    first_trade = {}

    for t in trades:
        key = (t.get("title"), t.get("outcome"))
        ts = t.get("timestamp")

        if key not in first_trade:
            first_trade[key] = ts
        else:
            first_trade[key] = min(first_trade[key], ts)

    return first_trade


def log_positions(positions, first_trade_times):

    file_exists = os.path.exists(LOG_FILE)

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

    # Sort chronologically by first trade
    rows.sort(key=lambda x: x[0] if x[0] else datetime.max)

    with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
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


def display_portfolio(positions, first_trade_times):

    if not positions:
        print("No portfolio data.")
        return

    open_positions = [p for p in positions if float(p.get("size", 0)) > 0]

    print("\n" + "=" * 60)
    print("📊 POLYMARKET OPEN POSITIONS")
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


user = "0x121785324CCa3fcf5a60D12ED8a96B93583C690a"

portfolio = fetch_portfolio(user)
trades = fetch_trades(user)

first_trade_times = get_first_trade_times(trades)

display_portfolio(portfolio, first_trade_times)

log_positions(portfolio, first_trade_times)