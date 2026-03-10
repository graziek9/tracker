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