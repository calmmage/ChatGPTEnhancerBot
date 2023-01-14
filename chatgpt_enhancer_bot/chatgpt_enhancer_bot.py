# a version that combines all parts of the code. MVP
# uses 2_openai_chatbot
# and semi-smart telegram bot on a better platform that just default python api.


"""a simple bot that just forwards queries to openai and sends the response"""
import logging
import os
import time
import traceback
from typing import Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler

from openai_chatbot import ChatBot, telegram_commands_registry
from utils import get_secrets, generate_funny_reason, generate_funny_consolation

secrets = get_secrets()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

TOUCH_FILE_PATH = os.path.expanduser('~/heartbeat/chatgpt_enhancer_last_alive')
os.makedirs(os.path.dirname(TOUCH_FILE_PATH), exist_ok=True)

bots = {}  # type: Dict[str, ChatBot]

default_model = "text-ada:001"

history_dir = os.path.join(os.path.dirname(__file__), 'history')
os.makedirs(history_dir, exist_ok=True)


def get_bot(user) -> ChatBot:
    if user not in bots:
        history_path = os.path.join(history_dir, f'history_{user}.json')
        new_bot = ChatBot(conversations_history_path=history_path, model=default_model, user=user)
        bots[user] = new_bot
    return bots[user]


def chat(prompt, user):
    bot = get_bot(user)
    return bot.chat(prompt=prompt)


def chat_handler(update: Update, context: CallbackContext) -> None:
    response = chat(update.message.text, user=update.effective_user.username)
    update.message.reply_markdown_v2(response)


def build_menu(buttons, n_cols, header_buttons=None, footer_buttons=None):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, header_buttons)
    if footer_buttons:
        menu.append(footer_buttons)
    return menu


def send_menu(update, context, menu: dict, message, n_cols=2):
    button_list = [InlineKeyboardButton(k, callback_data=v) for k, v in menu.items()]
    reply_markup = InlineKeyboardMarkup(build_menu(button_list, n_cols=n_cols))
    update.message.reply_text(message, reply_markup=reply_markup)


def topics_menu_handler(update: Update, context: CallbackContext) -> None:
    user = update.effective_user.username
    bot = get_bot(user)
    send_menu(update, context, bot.get_topics_menu(), "Choose a topic to switch to:")


def button_callback(update, context):
    prompt = update.callback_query.data
    user = update.effective_user.username
    bot = get_bot(user)

    if prompt.startswith('/'):
        command, qargs, qkwargs = bot.parse_query(prompt)
        method_name = bot.command_registry.get_function(command)
        method = getattr(bot, method_name)
        result = method(*qargs, **qkwargs)
        if not result:
            result = f"Command {command} finished successfully"
    else:
        result = bot.chat(prompt)

    result = clean_markdown(result)
    response_message = update.effective_message.reply_markdown_v2(result)
    if result.startswith("Active topic"):
        response_message.pin()


# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


def error_handler(update: Update, context: CallbackContext):
    # step 1: Save the error, so that /dev command can show it
    # What I want to save: timestamp, error, traceback, prompt
    user = update.effective_user.username
    bot = get_bot(user)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    prompt = None
    if update.message:
        prompt = update.message.text
    elif update.callback_query:
        prompt = update.callback_query.data
    bot.save_error(timestamp=timestamp, error=context.error, traceback=traceback.format_exc(),
                   message_text=prompt)
    # todo: make save_error also save error to file somewhere
    logger.warning(traceback.format_exc())

    # # step 1.5: todo, retry after 1 second
    # time.sleep(1)
    # prompt = update.message.text
    # try:
    #     # todo: retrying the 'new_chat' command is stupid
    #     # do I need to process the commands differently? I have a special parser inside chat() method.. should be ok
    #     chat(prompt, user)
    # except Exception as e:
    #     bot = get_bot(user)
    #     bot.save_traceback(traceback.format_exc())
    #     update.message.reply_text(f"Nah, it's hopeless.. {generate_funny_consolation().lower()}")

    # step 2: Send a funny reason to the user, (but also an error message)
    # Give user the info? Naah, let's rather joke around
    funny_reason = generate_funny_reason().lower()
    funny_consolation = generate_funny_consolation().lower()
    error_message = f"""Sorry, seems {funny_reason}. 
There was an error: {context.error}. 
You can use /dev command to see the traceback.. or bump @petr_lavrov about it
Please, accept my sincere apologies. And.. {funny_consolation}.
If the error persists, you can also try /new_chat command to start a new conversation.
"""
    update.message.reply_text(error_message)


def clean_markdown(msg: str):
    chars = '()[]_~<>#+-=|{}.!'
    for c in chars:
        msg = msg.replace(c, '\\' + c)
    return msg


def make_command_handler(method_name):
    def command_handler(update: Update, context: CallbackContext) -> None:
        user = update.effective_user.username
        bot = get_bot(user)
        method = bot.__getattribute__(method_name)

        prompt = update.message.text
        command, qargs, qkwargs = bot.parse_query(prompt)
        result = method(*qargs, **qkwargs)  # todo: parse kwargs from the command
        if not result:
            result = f"Command {command} finished successfully"
        result = clean_markdown(result)
        response_message = update.effective_message.reply_markdown_v2(result)
        if result.startswith("Active topic"):
            response_message.pin()

    return command_handler


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

    globals()['default_model'] = "text-davinci-003" if expensive else "text-ada:001"
    # on non command i.e message - echo the message on Telegram
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, chat_handler))

    for command in telegram_commands_registry.list_commands():
        match command:
            case "/get_topics_menu":
                command_handler = topics_menu_handler
            case other:
                function_name = telegram_commands_registry.get_function(command)
                command_handler = make_command_handler(function_name)
        dispatcher.add_handler(CommandHandler(command.lstrip('/'), command_handler))

    # Add the callback handler to the dispatcher
    dispatcher.add_handler(CallbackQueryHandler(button_callback))

    # Update commands list
    commands = [BotCommand(command, telegram_commands_registry.get_description(command)) for command in
                telegram_commands_registry.list_commands()]
    dispatcher.bot.set_my_commands(commands)

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
