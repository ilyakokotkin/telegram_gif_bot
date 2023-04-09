import os
import random
import requests
import logging
from telegram import Update, error
from telegram.ext import Updater, CommandHandler, CallbackContext
from concurrent.futures import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor as APSchedulerThreadPoolExecutor

TOKEN = "YOUR_TELEGRAM_TOKEN"
GIPHY_API_KEY = "YOUR_GIPHY_API_KEY"

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

chat_ids = set()
paused_chat_ids = set()

def start(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id

    if chat_id not in chat_ids:
        chat_ids.add(chat_id)
        context.bot.send_message(chat_id=chat_id, text="Hey! I am a bot that sends you cute cat GIFs at random times to surprise & cheer you up. Type /pause to pause & /resume to resume")
        send_cat_gif(update, context)
    else:
        context.bot.send_message(chat_id=chat_id, text="You have already started the bot.")

def pause(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    if chat_id in chat_ids:
        paused_chat_ids.add(chat_id)
        context.bot.send_message(chat_id=chat_id, text="Bot paused. You will not receive GIFs until you resume.")
    else:
        context.bot.send_message(chat_id=chat_id, text="You have not started the bot yet. Use /start to start the bot.")

def resume(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    if chat_id in paused_chat_ids:
        paused_chat_ids.remove(chat_id)
        context.bot.send_message(chat_id=chat_id, text="Bot resumed. You will receive GIFs again.")
    else:
        context.bot.send_message(chat_id=chat_id, text="The bot is not paused. Use /pause to pause the bot.")

def get_cat_gif_url():
    giphy_url = f'https://api.giphy.com/v1/gifs/search?api_key={GIPHY_API_KEY}&q=cat&limit=10&offset={random.randint(1, 100)}&rating=g&lang=en'
    response = requests.get(giphy_url)
    data = response.json()
    gif_url = data['data'][random.randint(0, len(data['data']) - 1)]['images']['fixed_height']['url']
    return gif_url

def send_cat_gif(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    gif_url = get_cat_gif_url()
    context.bot.send_animation(chat_id=chat_id, animation=gif_url)

def send_random_cat_gif(context: CallbackContext):
    try:
        gif_url = get_cat_gif_url()
    except Exception as e:
        logger.error(f"Error getting cat GIF from GIPHY API: {e}")
        return

    for chat_id in chat_ids:
        if chat_id not in paused_chat_ids:
            try:
                context.bot.send_animation(chat_id=chat_id, animation=gif_url)
            except Exception as e:
                logger.error(f"Error sending cat GIF to chat_id {chat_id}: {e}")
                continue

    # Schedule the next cat GIF
    random_interval = random.randint(900, 3600)  # Set the min and max interval values
    context.job_queue.run_once(send_random_cat_gif, random_interval, context=context)

def error_handler(update: Update, context: CallbackContext):
    """Handle any errors encountered while running the bot."""
    logger.error(f"Update {update} caused error: {context.error}")

    # If the error is related to a network issue, log it and continue running the bot.
    if isinstance(context.error, error.NetworkError):
        logger.warning(f"NetworkError encountered: {context.error}")
    else:
        # For other types of errors, log them and re-raise the error to stop the bot.
        logger.error(f"Error not handled: {context.error}")
        raise context.error


def main():
    custom_executor = APSchedulerThreadPoolExecutor(max_workers=20)
    custom_scheduler = BackgroundScheduler(executors={'default': custom_executor})
    
    updater = Updater(TOKEN, use_context=True)
    
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("pause", pause))
    dp.add_handler(CommandHandler("resume", resume))

    # Register the custom error handler
    dp.add_error_handler(error_handler)

    job_queue = updater.job_queue
    job_queue.scheduler = custom_scheduler
    job_queue.run_once(send_random_cat_gif, 1, context=None)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()