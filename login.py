import os
from telethon.sync import TelegramClient

# Get the API credentials from the user
api_id = input("Please enter your API ID: ")
api_hash = input("Please enter your API HASH: ")
phone = input("Please enter your phone number with country code: ")

# Create the client and connect
print("Connecting to Telegram...")
client = TelegramClient('bot_session', int(api_id), api_hash)

async def main():
    await client.start(phone)
    print("Login successful! You are connected.")
    # Get your own user info to confirm it's working
    me = await client.get_me()
    print(f"Logged in as: {me.first_name}")
    await client.disconnect()
    print("Disconnected. The 'bot_session.session' file has been created.")

with client:
    client.loop.run_until_complete(main())