# a version that combines all parts of the code. MVP
# uses 2_openai_chatbot
# and semi-smart telegram bot on a better platform that just default python api.


"""a simple bot that just forwards queries to openai and sends the response"""
import logging
import os
import time
import traceback

from telegram import Update
from telegram.error import NetworkError
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

from openai_chatbot import ChatBot
from utils import get_secrets

secrets = get_secrets()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

WELCOME_MESSAGE = """This is an alpha version of the Petr Lavrov's ChatGPT enhancer.
This message is last updated on 03.01.2023. Please ping t.me/petr_lavrov if I forgot to update it :)
Please play around, but don't abuse too much. I run this for my own money... It's ok if you send ~100 messages
"""

TOUCH_FILE_PATH = os.path.expanduser('~/heartbeat/chatgpt_enhancer_last_alive')
os.makedirs(os.path.dirname(TOUCH_FILE_PATH), exist_ok=True)


# Define a few command handlers. These usually take the two arguments update and
# context.
def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    welcome_message = f'Hi {user.username}!\n'
    welcome_message += WELCOME_MESSAGE
    update.message.reply_text(
        welcome_message,
        # reply_markup=ForceReply(selective=True),
    )


# def help_command(update: Update, context: CallbackContext) -> None:
#     """Send a message when the command /help is issued."""
#     update.message.reply_text('Help!')


bots = {}  # Dict[str, ChatBot]

default_model = "text-ada:001"

history_dir = os.path.join(os.path.dirname(__file__), 'history')
os.makedirs(history_dir, exist_ok=True)


def chat(prompt, user):
    if user not in bots:
        history_path = os.path.join(history_dir, f'history_{user}.json')
        new_bot = ChatBot(conversations_history_path=history_path, model=default_model)
        bots[user] = new_bot
    bot = bots[user]
    return bot.chat(prompt=prompt)


def chat_handler(update: Update, context: CallbackContext) -> None:
    response = chat(update.message.text, user=update.effective_user.username)
    update.message.reply_text(response)


# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


# Define the error handler function
def error_handler(update: Update, context: CallbackContext):
    if isinstance(context.error, NetworkError):
        # Do something when the "Bad Gateway" error occurs
        logger.info('NetworkError occurred')
        time.sleep(1)
    else:
        # todo: send error to admin - petrlavrov
        # for now: just log
        logger.warning(traceback.format_exc())


def main(expensive: bool) -> None:
    """
    Start the bot
    :param expensive: Use 'text-davinci-003' model instead of 'text-ada:001'
    :return:
    """
    # Create the Updater and pass it your bot's token.
    token = secrets["telegram_api_token"]
    updater = Updater(token)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("start", start))
    # dispatcher.add_handler(CommandHandler("help", help_command))

    # b = ChatBot()
    globals()['default_model'] = "text-davinci-003" if expensive else "text-ada:001"
    # on non command i.e message - echo the message on Telegram
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, chat_handler
                                          # telegram_user_decorator(b.chat, model=model)
                                          ))

    # Add the error handler to the dispatcher
    dispatcher.add_error_handler(error_handler)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    count = 0
    while True:
        time.sleep(1)

        # heartbeat
        count += 1
        if count % 60 == 0:
            # touch the touch file
            with open(TOUCH_FILE_PATH, 'w'):
                pass


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--expensive", action="store_true",
                        help="use expensive calculation - 'text-davinci-003' model instead of 'text-ada:001' ")
    args = parser.parse_args()

    main(expensive=args.expensive)
