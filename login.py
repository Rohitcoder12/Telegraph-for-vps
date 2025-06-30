import os
from telethon.sync import TelegramClient

# Get the API credentials from the user
api_id = input("27073191")
api_hash = input("1a32be9bed70c354d9ffc4c83034d641")
phone = input("+919369765536")

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