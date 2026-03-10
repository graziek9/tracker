from portfolio import fetch_portfolio
from notifications import send_telegram_message
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def format_positions_message(user_label, user_address, portfolio):
    """
    Build a Telegram message summarizing current open positions.
    """

    lines = [
        "",
        "🔸🔸🔸🔸🔸🔸🔸🔸🔸🔸🔸🔸🔸🔸",
        "",
        f"📌 Current positions for {user_label}",
        f"Address: {user_address}",
        ""
    ]

    if not portfolio:
        lines.append("No open positions found.")
        lines.append("#####################")
        return "\n".join(lines)

    count = 0

    for pos in portfolio:

        title = pos.get("title") or pos.get("market") or pos.get("question") or "Unknown market"
        outcome = pos.get("outcome") or pos.get("side") or "Unknown outcome"
        size = pos.get("size") or pos.get("shares") or pos.get("amount") or 0
        avg_price = pos.get("avgPrice") or pos.get("averagePrice") or pos.get("price") or 0

        try:
            size_val = float(size)
        except:
            size_val = 0

        try:
            avg_price_val = float(avg_price)
        except:
            avg_price_val = 0

        if size_val == 0:
            continue

        count += 1

        lines.append(
            f"{count}. {title}\n"
            f"   Outcome: {outcome}\n"
            f"   Size: {size_val}\n"
            f"   Avg price: {avg_price_val}\n"
            f"   Cost basis: ${round(avg_price_val * size_val, 2)}\n"
            f"--------------------------"
        )

    if count == 0:
        lines.append("No open positions found.")

    

    return "\n".join(lines)


def send_positions_summary(user_label, user_address):
    """
    Fetch portfolio and send Telegram summary.
    """

    try:
        portfolio = fetch_portfolio(user_address)

        msg = format_positions_message(
            user_label,
            user_address,
            portfolio
        )

        send_telegram_message(
            TELEGRAM_BOT_TOKEN,
            TELEGRAM_CHAT_ID,
            msg
        )

    except Exception as e:
        print(f"Failed to send positions summary for {user_label}: {e}")