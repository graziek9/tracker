'''
python3 -m venv .venv
source .venv/bin/activate
'''

from portfolio import (
    fetch_portfolio,
    fetch_trades,
    get_first_trade_times,
    display_portfolio,
    log_positions,
)

from config import (
    TARGET_USERS,
    LIMIT,
    PORTFOLIO_USER_ADDRESS,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
)

from trade_utils import (
    track_user_trades, 
    send_telegram_message
)

from notifications import send_telegram_message




##########################################################

import json
import requests

MARKET_SLUG = "us-forces-enter-iran-by-march-14-337"
POLYMARKET_API = f"https://gamma-api.polymarket.com/markets/slug/{MARKET_SLUG}"


def parse_maybe_json_array(value):
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return json.loads(value)
    return value


def get_no_price():
    r = requests.get(POLYMARKET_API, timeout=20)
    r.raise_for_status()
    market = r.json()

    outcomes = parse_maybe_json_array(market["outcomes"])
    prices = parse_maybe_json_array(market["outcomePrices"])

    for outcome, price in zip(outcomes, prices):
        if str(outcome).lower() == "no":
            return float(price)

    raise ValueError("NO outcome not found")


##########################################################

if __name__ == "__main__":
    send_telegram_message(
        TELEGRAM_BOT_TOKEN,
        TELEGRAM_CHAT_ID,
        "✅ Code processing ..."
    )

    for user_label, user_address in TARGET_USERS.items():
        print("\n" + "#" * 70)
        print(f"Tracking trades for: {user_label}")
        print("#" * 70)
        track_user_trades(user_label, user_address, LIMIT)

    portfolio = fetch_portfolio(PORTFOLIO_USER_ADDRESS)
    trades = fetch_trades(PORTFOLIO_USER_ADDRESS)
    first_trade_times = get_first_trade_times(trades)
    display_portfolio(PORTFOLIO_USER_ADDRESS, portfolio, first_trade_times)
    log_positions(PORTFOLIO_USER_ADDRESS, portfolio, first_trade_times)

    # Fetch NO price
    no_price = get_no_price()
    send_telegram_message(
        "8691017421:AAH5z290vgFau1SqIBC0DkfkvTfei3obtyk",
        "5449810522",
        f" ------------------ \n NO price PM: {no_price}"
    )

    