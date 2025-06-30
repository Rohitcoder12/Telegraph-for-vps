# login.py

from telethon.sync import TelegramClient
import config

print("Attempting to log in with Telethon to create a session file...")

# Use the config to get credentials
client = TelegramClient('bot_session', int(config.API_ID), config.API_HASH)

async def main():
    await client.start()
    me = await client.get_me()
    print(f"Login successful! Session file created for: {me.first_name}")
    await client.disconnect()

with client:
    client.loop.run_until_complete(main())