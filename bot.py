# bot.py

import logging
import requests
import base64
import os
import json
import html
import asyncio
from typing import List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
)
from telethon.sync import TelegramClient
import config # Import our new config file

# --- LOGGING SETUP ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- HELPER FUNCTIONS ---
def get_telegraph_token(bot_author_name="Dailynewswalla"):
    logger.info("No Telegraph token found, creating a new one...");
    try:
        response = requests.get("https://api.telegra.ph/createAccount", params={"short_name": bot_author_name, "author_name": bot_author_name}); response.raise_for_status(); data = response.json()
        if data.get("ok"): token = data["result"]["access_token"]; logger.info(f"Created Telegraph account: {token[:8]}..."); return token
    except Exception as e: logger.error(f"Failed to create Telegraph account: {e}", exc_info=True)
    return None
def upload_to_imagebb(file_path: str) -> str | None:
    url = "https://api.imgbb.com/1/upload"
    try:
        with open(file_path, "rb") as file: payload = {"key": config.IMAGEBB_API_KEY, "image": base64.b64encode(file.read())}
        response = requests.post(url, payload); response.raise_for_status(); data = response.json()
        if data.get('success'): return data['data']['url']
    except Exception as e: logger.error(f"Error INSIDE upload_to_imagebb: {e}", exc_info=True)
    finally:
        if os.path.exists(file_path): os.remove(file_path)
    return None
def create_telegraph_page(access_token: str, title: str, image_urls: List[str], author_name="Dailynewswalla") -> str | None:
    api_url = "https://api.telegra.ph/createPage"
    public_channel_url = "https://t.me/dailynewswalla"; premium_channel_url = "https://t.me/+Lp-38ITvDzJhYWRl"
    content = [{"tag": "img", "attrs": {"src": url}} for url in image_urls]
    note_text = "Note: Videos of this exclusive collections only available for premium users."
    note_node = {"tag": "p", "children": [{"tag": "a", "attrs": {"href": premium_channel_url}, "children": [note_text]}]}
    content.append(note_node)
    payload = {'access_token': access_token, 'title': title, 'author_name': author_name, 'author_url': public_channel_url, 'content': json.dumps(content)}
    try:
        response = requests.post(api_url, data=payload); response.raise_for_status(); data = response.json()
        if data.get('ok'): return data['result']['url']
        else: logger.error(f"Telegraph API returned an error: {data.get('error')}")
    except Exception as e: logger.error(f"Error INSIDE create_telegraph_page: {e}", exc_info=True)
    return None

# --- BOT COMMANDS & CONVERSATION ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Hello! 👋 I'm the Telegraph Maker bot.\n\nPlease send me a photo or multiple photos (as an album) to begin.")

GETTING_PHOTOS, GETTING_CAPTION, AWAITING_SEND, GETTING_VIDEOS, CONFIRM_VIDEOS = range(5)
async def handle_photos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message
    if not context.user_data.get('photos'): context.user_data['photos'] = []
    context.user_data['photos'].append(message)
    await message.reply_text(f"✅ Photo added ({len(context.user_data['photos'])} total). Send more photos or send /done.")
    return GETTING_PHOTOS
async def done_photos_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not context.user_data.get('photos'):
        await update.message.reply_text("You haven't sent any photos yet. Please send a photo first."); return GETTING_PHOTOS
    await update.message.reply_text("✅ All photos received! Now, please send me the caption you want to use.")
    return GETTING_CAPTION
async def process_caption(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_caption = update.message.text
    photo_messages = context.user_data.pop('photos', [])
    if not photo_messages: await update.message.reply_text("Something went wrong. Please start over."); return ConversationHandler.END
    if 'telegraph_token' not in context.bot_data:
        token = get_telegraph_token();
        if not token: await update.message.reply_text("Error: Could not create Telegraph author account."); return ConversationHandler.END
        context.bot_data['telegraph_token'] = token
    telegraph_access_token = context.bot_data['telegraph_token']
    await update.message.reply_text(f"Processing {len(photo_messages)} photo(s), please wait...")
    image_urls = []; photo_ids = [msg.photo[-1].file_id for msg in photo_messages]
    for msg in photo_messages:
        try:
            photo_file = await context.bot.get_file(msg.photo[-1].file_id); temp_path = f"temp_{msg.photo[-1].file_id}.jpg"; await photo_file.download_to_drive(temp_path)
            url = upload_to_imagebb(temp_path)
            if url: image_urls.append(url)
        except Exception as e: logger.error(f"Failed to process file_id {msg.photo[-1].file_id}: {e}")
    if not image_urls:
        await update.message.reply_text("Sorry, I couldn't upload any images."); return ConversationHandler.END
    page_url = create_telegraph_page(telegraph_access_token, user_caption, image_urls)
    if page_url:
        first_photo_id = photo_ids[0]; safe_user_caption = html.escape(user_caption)
        context.user_data['post_caption'] = safe_user_caption
        final_caption = (f"<b>{safe_user_caption}</b>\n\n" f"<b>Preview Photo👇</b>\n<b>{page_url}</b>")
        sent_message = await update.message.reply_photo(photo=first_photo_id, caption=final_caption, parse_mode=ParseMode.HTML)
        if update.effective_user.id == config.OWNER_ID and config.TARGET_CHANNELS_STR:
            keyboard = [[InlineKeyboardButton("🚀 Send to Channels", callback_data="send_channels")]]
            await sent_message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))
            return AWAITING_SEND
    else:
        await update.message.reply_text("Sorry, I failed to create the Telegraph page.")
    return ConversationHandler.END
async def send_to_channels_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query; await query.answer()
    channels = [c.strip() for c in config.TARGET_CHANNELS_STR.split(',') if c.strip()]
    original_message = query.message
    photo_to_send = original_message.photo[-1].file_id; caption_to_send = original_message.caption
    success_count = 0; failure_count = 0
    for channel in channels:
        try:
            await context.bot.send_photo(chat_id=channel, photo=photo_to_send, caption=caption_to_send, parse_mode=ParseMode.HTML)
            success_count += 1
        except Exception as e: failure_count += 1; logger.error(f"Failed to send photo to channel {channel}: {e}")
    result_text = f"🚀 Post sent to {success_count}/{len(channels)} channels."
    if failure_count > 0: result_text += f"\n(Failed for {failure_count} channels. Check logs.)"
    await query.edit_message_reply_markup(reply_markup=None); await original_message.reply_text(result_text)
    context.user_data['video_messages'] = []
    await original_message.reply_text("Now, send me the videos for this post. Send /donevideos when you are finished.")
    return GETTING_VIDEOS
async def handle_videos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.setdefault('video_messages', []).append(update.message)
    await update.message.reply_text(f"✅ Video {len(context.user_data['video_messages'])} added. Send more or /donevideos.")
    return GETTING_VIDEOS
async def done_videos_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not context.user_data.get('video_messages'):
        await update.message.reply_text("No videos were sent. Process finished."); return ConversationHandler.END
    keyboard = [[InlineKeyboardButton("✅ Yes, Send Videos", callback_data="send_premium_videos")]]
    await update.message.reply_text("Do you want to send these videos to the premium channels?", reply_markup=InlineKeyboardMarkup(keyboard))
    return CONFIRM_VIDEOS
async def send_premium_videos_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query; await query.answer()
    video_messages = context.user_data.pop('video_messages', []); post_caption = context.user_data.pop('post_caption', "New premium content")
    premium_channels = [c.strip() for c in config.PREMIUM_CHANNELS_STR.split(',') if c.strip()]
    if not premium_channels:
        await query.edit_message_text(text="Error: No premium channels configured."); return ConversationHandler.END
    await query.edit_message_text(text=f"Sending {len(video_messages)} videos to premium channels...")
    async with TelegramClient('bot_session', int(config.API_ID), config.API_HASH) as client:
        success_count = 0; failure_count = 0;
        for channel in premium_channels:
            channel_success = True
            for message in video_messages:
                temp_video_path = None
                try:
                    logger.info(f"Downloading video via Telethon worker...")
                    temp_video_path = await client.download_media(message, file="temp_video/")
                    logger.info(f"Downloaded video to {temp_video_path}")
                    with open(temp_video_path, 'rb') as video_data:
                        video_params = {
                            "chat_id": channel, "video": video_data, "caption": f"<b>{post_caption}</b>",
                            "parse_mode": ParseMode.HTML, "filename": "premium video by @Dailynewswalla.mp4"
                        }
                        if config.THUMBNAIL_FILE_ID:
                            thumb_file_obj = await context.bot.get_file(config.THUMBNAIL_FILE_ID)
                            temp_thumb_path = "temp_thumb.jpg"; await thumb_file_obj.download_to_drive(temp_thumb_path)
                            with open(temp_thumb_path, 'rb') as thumb_data:
                                video_params["thumbnail"] = thumb_data
                                await context.bot.send_video(**video_params)
                            if os.path.exists(temp_thumb_path): os.remove(temp_thumb_path)
                        else:
                            await context.bot.send_video(**video_params)
                except Exception as e:
                    channel_success = False; failure_count += 1
                    logger.error(f"Failed to send video {message.id} to premium channel {channel}: {e}")
                finally:
                    if temp_video_path and os.path.exists(temp_video_path): os.remove(temp_video_path)
            if channel_success: success_count += 1
    result_text = f"✅ Videos sent to {success_count} / {len(premium_channels)} premium channels."
    if failure_count > 0: result_text += f"\n({failure_count} individual videos failed to send. Check logs.)"
    await context.bot.send_message(chat_id=query.message.chat_id, text=result_text)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear(); await update.message.reply_text("Process canceled."); return ConversationHandler.END

# The main application object, needed for Gunicorn
application = Application.builder().token(config.TELEGRAM_TOKEN).build()

def main() -> None:
    """Sets up the bot handlers."""
    full_workflow_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.PHOTO, handle_photos)],
        states={
            GETTING_PHOTOS: [MessageHandler(filters.PHOTO, handle_photos), CommandHandler('done', done_photos_command)],
            GETTING_CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_caption)],
            AWAITING_SEND: [CallbackQueryHandler(send_to_channels_callback, pattern=r"^send_channels$")],
            GETTING_VIDEOS: [MessageHandler(filters.VIDEO, handle_videos), CommandHandler('donevideos', done_videos_command)],
            CONFIRM_VIDEOS: [CallbackQueryHandler(send_premium_videos_callback, pattern=r"^send_premium_videos$")]
        },
        fallbacks=[CommandHandler('cancel', cancel)], conversation_timeout=600
    )
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(full_workflow_handler)

if __name__ == '__main__':
    # This part is for local testing, not for the server
    logger.info("Starting bot locally in polling mode...")
    main() # Set up handlers
    application.run_polling()