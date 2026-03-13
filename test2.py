import json
import time
import ssl
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, Tuple, Optional

import certifi
import requests
import websocket

GAMMA_BASE = "https://gamma-api.polymarket.com"
WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"


def now_str() -> str:
    return datetime.now().strftime("%H:%M:%S")


def fmt_num(value, places: int = 3) -> str:
    if value is None:
        return "-"
    try:
        d = Decimal(str(value))
        return f"{d:.{places}f}"
    except (InvalidOperation, ValueError):
        return str(value)


def fmt_size(value) -> str:
    if value is None:
        return "-"
    try:
        d = Decimal(str(value))
        if abs(d) >= 1000000:
            return f"{d / Decimal('1000000'):.2f}M"
        if abs(d) >= 1000:
            return f"{d / Decimal('1000'):.2f}K"
        return f"{d:.2f}"
    except (InvalidOperation, ValueError):
        return str(value)


def fmt_ts(ms_value) -> str:
    if ms_value is None:
        return "-"
    try:
        ts = int(ms_value) / 1000
        return datetime.fromtimestamp(ts).strftime("%H:%M:%S")
    except Exception:
        return str(ms_value)


def get_market_by_slug(slug: str) -> dict:
    url = f"{GAMMA_BASE}/markets/slug/{slug}"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return r.json()


def extract_token_ids(market: dict) -> Tuple[str, str]:
    raw = market.get("clobTokenIds")

    if raw is None:
        raise ValueError("No clobTokenIds found in market response")

    if isinstance(raw, list):
        token_ids = [str(x) for x in raw if x]
    elif isinstance(raw, str):
        parsed = json.loads(raw)
        if not isinstance(parsed, list):
            raise ValueError("clobTokenIds string did not parse to a list")
        token_ids = [str(x) for x in parsed if x]
    else:
        raise ValueError(f"Unexpected clobTokenIds type: {type(raw)}")

    if len(token_ids) < 2:
        raise ValueError(f"Expected at least 2 token ids, got: {token_ids}")

    return token_ids[0], token_ids[1]


def extract_best_price(levels) -> Optional[str]:
    if not levels:
        return None

    top = levels[0]
    if isinstance(top, dict):
        return top.get("price")
    return top


def print_separator():
    print("-" * 110)


def print_book_snapshot(book_state: Dict[str, Dict[str, Optional[str]]]):
    print_separator()
    print(f"{'TIME':<10} {'TOKEN':<6} {'BEST_BID':>10} {'BEST_ASK':>10}")
    print_separator()
    for label in ("YES", "NO"):
        row = book_state.get(label, {})
        print(
            f"{now_str():<10} "
            f"{label:<6} "
            f"{fmt_num(row.get('best_bid')):>10} "
            f"{fmt_num(row.get('best_ask')):>10}"
        )
    print_separator()


def print_trade_header():
    print_separator()
    print(
        f"{'LOCAL':<10} {'EVENT_TS':<10} {'TOKEN':<6} {'SIDE':<6} "
        f"{'PRICE':>8} {'SIZE':>10} {'BID':>8} {'ASK':>8} {'HASH':<10}"
    )
    print_separator()


def print_trade_row(
    event_ts,
    label: str,
    side,
    price,
    size,
    best_bid,
    best_ask,
    trade_hash,
):
    short_hash = str(trade_hash)[:10] if trade_hash else "-"
    print(
        f"{now_str():<10} "
        f"{fmt_ts(event_ts):<10} "
        f"{label:<6} "
        f"{str(side or '-'): <6} "
        f"{fmt_num(price):>8} "
        f"{fmt_size(size):>10} "
        f"{fmt_num(best_bid):>8} "
        f"{fmt_num(best_ask):>8} "
        f"{short_hash:<10}"
    )


def build_handlers(token_labels: Dict[str, str]):
    book_state = {
        "YES": {"best_bid": None, "best_ask": None},
        "NO": {"best_bid": None, "best_ask": None},
    }
    printed_trade_header = False

    def label_for_asset(asset_id) -> str:
        if asset_id is None:
            return "UNKNOWN"
        return token_labels.get(str(asset_id), "UNKNOWN")

    def on_open(ws):
        sub = {
            "assets_ids": list(token_labels.keys()),
            "type": "market",
        }
        ws.send(json.dumps(sub))

        print()
        print("=" * 110)
        print("POLYMARKET LIVE MARKET FEED")
        print("=" * 110)
        print("Streaming structured updates for YES and NO")
        print_separator()

    def on_message(ws, message):
        nonlocal printed_trade_header

        try:
            payload = json.loads(message)
        except json.JSONDecodeError:
            print(f"[{now_str()}] RAW {message}")
            return

        if isinstance(payload, list):
            for event in payload:
                handle_event(event)
        else:
            handle_event(payload)

    def handle_event(event: dict):
        nonlocal printed_trade_header

        if not isinstance(event, dict):
            return

        event_type = event.get("event_type") or event.get("type") or "unknown"

        if event_type == "book":
            asset_id = event.get("asset_id") or event.get("assetId") or event.get("asset")
            label = label_for_asset(asset_id)

            bids = event.get("bids", [])
            asks = event.get("asks", [])
            best_bid = extract_best_price(bids)
            best_ask = extract_best_price(asks)

            if label in book_state:
                book_state[label]["best_bid"] = best_bid
                book_state[label]["best_ask"] = best_ask

            print_book_snapshot(book_state)
            return

        if event_type == "price_change":
            changes = event.get("price_changes", [])
            event_ts = event.get("timestamp")

            if changes and not printed_trade_header:
                print_trade_header()
                printed_trade_header = True

            for change in changes:
                asset_id = change.get("asset_id")
                label = label_for_asset(asset_id)

                best_bid = change.get("best_bid")
                best_ask = change.get("best_ask")

                if label in book_state:
                    if best_bid is not None:
                        book_state[label]["best_bid"] = best_bid
                    if best_ask is not None:
                        book_state[label]["best_ask"] = best_ask

                print_trade_row(
                    event_ts=event_ts,
                    label=label,
                    side=change.get("side"),
                    price=change.get("price"),
                    size=change.get("size"),
                    best_bid=change.get("best_bid"),
                    best_ask=change.get("best_ask"),
                    trade_hash=change.get("hash"),
                )
            return

        if event_type == "last_trade_price":
            asset_id = event.get("asset_id") or event.get("assetId") or event.get("asset")
            label = label_for_asset(asset_id)

            if not printed_trade_header:
                print_trade_header()
                printed_trade_header = True

            print_trade_row(
                event_ts=event.get("timestamp"),
                label=label,
                side=event.get("side"),
                price=event.get("price") or event.get("last_trade_price"),
                size=event.get("size"),
                best_bid=book_state.get(label, {}).get("best_bid"),
                best_ask=book_state.get(label, {}).get("best_ask"),
                trade_hash=event.get("hash"),
            )
            return

        if event_type in {"best_bid_ask", "tick_size_change", "market_resolved", "new_market"}:
            print(f"[{now_str()}] {event_type.upper()} {json.dumps(event, separators=(',', ':'))}")
            return

        # Ignore noisy unknowns unless you want full debug:
        # print(f"[{now_str()}] UNKNOWN_EVENT {json.dumps(event, separators=(',', ':'))}")

    def on_error(ws, error):
        print(f"[{now_str()}] WebSocket error: {error}")

    def on_close(ws, close_status_code, close_msg):
        print(f"[{now_str()}] Closed: code={close_status_code}, reason={close_msg}")

    return on_open, on_message, on_error, on_close


def stream_market(slug: str):
    market = get_market_by_slug(slug)

    question = market.get("question")
    condition_id = market.get("conditionId")
    yes_token, no_token = extract_token_ids(market)

    print("=" * 110)
    print("MARKET INFO")
    print("=" * 110)
    print(f"Slug         : {slug}")
    print(f"Question     : {question}")
    print(f"Condition ID : {condition_id}")
    print(f"YES token    : {yes_token}")
    print(f"NO token     : {no_token}")

    token_labels = {
        yes_token: "YES",
        no_token: "NO",
    }

    on_open, on_message, on_error, on_close = build_handlers(token_labels)

    while True:
        try:
            ws = websocket.WebSocketApp(
                WS_URL,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
            )

            ws.run_forever(
                ping_interval=20,
                ping_timeout=10,
                sslopt={
                    "ca_certs": certifi.where(),
                    "cert_reqs": ssl.CERT_REQUIRED,
                },
            )

        except KeyboardInterrupt:
            print(f"\n[{now_str()}] Stopped by user.")
            break
        except Exception as e:
            print(f"[{now_str()}] Reconnect after error: {e}")
            time.sleep(3)


if __name__ == "__main__":
    stream_market("us-forces-enter-iran-by-march-14-337")