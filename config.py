import os

gamma_api = "https://gamma-api.polymarket.com"
data_api = "https://data-api.polymarket.com"
clob_api = "https://clob.polymarket.com"

TELEGRAM_BOT_TOKEN = "8652673090:AAHIQX1wJCKcCzLYb-tPI-q-sHPSyUudwyA"
TELEGRAM_CHAT_ID = "5449810522"

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

LOG_FILE = "polymarket_logbook.csv"

TARGET_USERS = {
    "user_P1": "0xde7be6d489bce070a959e0cb813128ae659b5f4b",
    "user_P2": "0xa39c488ea8269609aea27f5f8486044d839908bc",
    "user_S1": "0x9ea10c9f5eeadf149da34117a7882f2275c9df66",
    "user_P3": "0xc6dd722558dbfbd8fa780efcbe819ed8c6604b9f",
    "user_P4": "0x9ec7da81a2da3d47a47dd281b1ecf2cf2b3a35c0",
    "user_P5": "0x56ebe2a8eb1b9bccfd3059f981f9c987e45e076a",
}

LIMIT = 100

PORTFOLIO_USER_ADDRESS = "0x121785324CCa3fcf5a60D12ED8a96B93583C690a"