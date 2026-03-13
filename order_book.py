#!/usr/bin/env python3
import json
import requests

# -------------------------
# CONFIG
# -------------------------
BOT_TOKEN = "8691017421:AAH5z290vgFau1SqIBC0DkfkvTfei3obtyk"
CHAT_ID = "5449810522"

MARKET_SLUG = "us-forces-enter-iran-by-march-14-337"
POLYMARKET_URL = f"https://gamma-api.polymarket.com/markets/slug/{MARKET_SLUG}"


def parse_maybe_json_array(value):
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return json.loads(value)
    raise TypeError(f"Unexpected type: {type(value)}")


def get_no_price():
    r = requests.get(POLYMARKET_URL, timeout=20)
    r.raise_for_status()
    market = r.json()

    outcomes = parse_maybe_json_array(market["outcomes"])
    prices = parse_maybe_json_array(market["outcomePrices"])

    for outcome, price in zip(outcomes, prices):
        if str(outcome).strip().lower() == "no":
            return str(price)

    raise ValueError(f"'No' outcome not found. Outcomes returned: {outcomes}")


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
    }
    r = requests.post(url, json=payload, timeout=20)
    r.raise_for_status()


def main():
    price = get_no_price()
    send_telegram_message(price)
    print(f"Sent price: {price}")


if __name__ == "__main__":
    main()