# config.py

import os
from dotenv import load_dotenv

# Load all the variables from the .env file
load_dotenv()

# --- Telegram Bot Configuration ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
OWNER_ID = int(os.environ.get("OWNER_ID", 0))

# --- Telethon Worker Configuration ---
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")

# --- External Services & Settings ---
IMAGEBB_API_KEY = os.environ.get("IMAGEBB_API_KEY")
THUMBNAIL_FILE_ID = os.environ.get("THUMBNAIL_FILE_ID")

# --- Channel Configuration ---
TARGET_CHANNELS_STR = os.environ.get("TARGET_CHANNELS", "")
PREMIUM_CHANNELS_STR = os.environ.get("PREMIUM_CHANNELS", "")

# --- A check to make sure all essential variables are loaded ---
if not all([TELEGRAM_TOKEN, API_ID, API_HASH, OWNER_ID, WEBHOOK_URL]):
    raise ValueError("One or more essential environment variables are missing! Please check your .env file.")