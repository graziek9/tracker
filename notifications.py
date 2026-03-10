import requests


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