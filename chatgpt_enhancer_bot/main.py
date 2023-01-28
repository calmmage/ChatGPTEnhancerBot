# a version that combines all parts of the code. MVP
# uses 2_openai_chatbot
# and semi-smart telegram bot on a better platform that just default python api.


"""a simple bot that just forwards queries to openai and sends the response"""
import logging
import os
import time
import traceback
from pathlib import Path
from typing import Dict, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
from telegram.utils.helpers import escape_markdown

from chatgpt_enhancer_bot.bot.chat_registry import ChatType
from chatgpt_enhancer_bot.bot.user_registry import UserRegistry
from chatgpt_enhancer_bot.command_registry import CommandRegistry
from .openai_chatbot import ChatBot, gpt_commands_registry, WELCOME_MESSAGE
from .utils import get_secrets, generate_funny_reason, generate_funny_consolation, split_to_code_blocks, parse_query

secrets = get_secrets()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

TOUCH_FILE_PATH = Path('~/heartbeat/chatgpt_enhancer_last_alive').expanduser()
TOUCH_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

bot_registry = {}  # type: Dict[str, ChatBot]

default_model = "text-ada:001"

history_dir = Path('app_data/history')
history_dir.mkdir(parents=True, exist_ok=True)


def get_bot(user) -> ChatBot:
    if user not in bot_registry.keys():
        history_path = os.path.join(history_dir, f'history_{user}.json')
        new_bot = ChatBot(conversations_history_path=history_path, model=default_model, user=user)
        bot_registry[user] = new_bot
    return bot_registry[user]


def send_message_with_markdown(message_to_reply_to, message, enable_markdown=False, escape_markdown_flag=False):
    if enable_markdown:
        if escape_markdown_flag:
            message = escape_markdown(message, version=2)
        try:
            return message_to_reply_to.reply_markdown_v2(message)
        except:  # can't parse entities
            error_message = "Unable to parse markdown in this response. Here's the raw text:\n\n" + message
            return message_to_reply_to.reply_text(error_message)
    else:
        return message_to_reply_to.reply_text(message)


def send_message_to_user(message_to_reply_to, message):
    # just always send as plain text for now
    # step 1: tell the bot to always use ``` for the code
    # step 2: parse the code blocks in text
    blocks = split_to_code_blocks(message)
    sent_messages = []
    for block in blocks:
        if block['is_code_block']:
            text = f"```{block['text']}```"
        else:
            text = block['text']
        msg = send_message_with_markdown(message_to_reply_to, text, enable_markdown=block['is_code_block'])
        sent_messages.append(msg)

    if len(sent_messages) == 1:
        # todo: add support for multiple messages everywhere where this is used
        return sent_messages[0]
    return sent_messages


def chat_handler(update: Update, context: CallbackContext) -> None:
    user = update.effective_user.username
    bot = get_bot(user)
    reply = bot.chat(prompt=update.message.text)
    # send_message_to_user(update.message, reply, enable_markdown=bot.markdown_enabled, escape_markdown_flag=False)
    send_message_to_user(update.message, reply)


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


def topics_menu_command(update: Update, context: CallbackContext) -> None:
    user = update.effective_user.username
    bot = get_bot(user)
    send_menu(update, context, bot.get_topics_menu(), "Choose a topic to switch to:")


def button_callback(update, context):
    prompt = update.callback_query.data
    user = update.effective_user.username
    bot = get_bot(user)

    if prompt.startswith('/'):
        command, qargs, qkwargs = parse_query(prompt)
        method_name = bot.command_registry.get_function(command)
        method = getattr(bot, method_name)
        result = method(*qargs, **qkwargs)
        if not result:
            result = f"Command {command} finished successfully"
    else:
        result = bot.chat(prompt)

    # markdown_safe =
    # escape_markdown_flag = not markdown_safe
    # response_message = send_message_to_user(update.effective_message, result, enable_markdown=bot.markdown_enabled,
    #                                         escape_markdown_flag=escape_markdown_flag)
    response_message = send_message_to_user(update.effective_message, result)
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
You can use /error command to see the traceback.. or bump @petr_lavrov about it
Please, accept my sincere apologies. And.. {funny_consolation}.
If the error persists, you can also try /new_chat command to start a new conversation.
"""
    # if bot.markdown_enabled:
    #     error_message += "\n Or /disable_markdown to disable markdown in this chat"
    update.message.reply_text(error_message)


ANNOUNCEMENT_TEMPLATE = """
Hey, this is an announcement from @petr_lavrov.

{message}

P.s. yes, I am shamelessly abusing my powers to send you this message.
Please use /stop_announcements command to stop receiving these messages.
"""


# ANNOUNCEMENT_TEMPLATE += "Please use /stop command to stop EVERYTHING."


def make_command_handler(method_name):
    def command_handler(update: Update, context: CallbackContext) -> None:
        user = update.effective_user.username
        bot = get_bot(user)
        method = bot.__getattribute__(method_name)

        prompt = update.message.text
        command, qargs, qkwargs = parse_query(prompt)
        # todo: if necessary args are missing, ask for them or at least handle the exception gracefully
        result = method(*qargs, **qkwargs)  # todo: parse kwargs from the command
        if not result:
            result = f"Command {command} finished successfully"
        # escape_markdown_flag = not bot.command_registry.is_markdown_safe(command)
        # response_message = send_message_to_user(update.effective_message, result, enable_markdown=bot.markdown_enabled,
        #                                         escape_markdown_flag=escape_markdown_flag)
        response_message = send_message_to_user(update.effective_message, result)
        if result.startswith("Active topic"):
            response_message.pin()

    return command_handler


telegram_commands_registry = CommandRegistry()


class TelegramBot:
    def __init__(self, token=None, root_dir=None, user_registry: Optional[UserRegistry] = None):
        if token is None:
            # get token from env variables
            token = os.getenv("TELEGRAM_BOT_TOKEN")
        self._updater = Updater(token=token, use_context=True)
        if root_dir is None:
            root_dir = 'app_data'
        root_dir = Path(root_dir)
        self._root_dir = root_dir
        if user_registry is None:
            user_registry_path = root_dir / 'users'
            user_registry = UserRegistry(user_registry_path)
        self.user_registry = user_registry
        # todo: add chat registry

        self._commands_names = []

        # configs
        self._heartbeat = True

    @property
    def _dispatcher(self):
        return self._updater.dispatcher

    def _add_handler(self, handler):
        self._dispatcher.add_handler(handler)

    def setup(self, expensive=False):
        # todo: make this univesal for all commands, support Logic module
        globals()['default_model'] = "text-davinci-003" if expensive else "text-ada:001"
        # on non command i.e message - echo the message on Telegram
        self._add_handler(MessageHandler(Filters.text & ~Filters.command, chat_handler))

        self._register_commands(telegram_commands_registry, self.__getattribute__)
        self._register_commands(gpt_commands_registry, make_command_handler)

        # Add the callback handler to the dispatcher
        self._add_handler(CommandHandler("get_topics_menu", topics_menu_command))
        self._add_handler(CallbackQueryHandler(button_callback))

        self._dispatcher.bot.set_my_commands(self._commands_names)

        # Add the error handler to the dispatcher
        self._dispatcher.add_error_handler(error_handler)

        # order important - this must be after /start command
        self._dispatcher.add_handler(MessageHandler(Filters.update, self.auto_register_new_chats))

    def _register_commands(self, command_registry, command_factory):
        for command in command_registry.list_commands():
            if not command_registry.is_active(command):
                continue
            function_name = command_registry.get_function(command)
            command_handler = command_factory(function_name)
            self._dispatcher.add_handler(CommandHandler(command.lstrip('/'), command_handler))

        # Update commands list
        self._commands_names += [
            BotCommand(command, command_registry.get_description(command))
            for command in command_registry.list_commands()
        ]

    def run(self):
        # Start the Bot
        self._updater.start_polling()
        self._updater.idle()

        # Run the bot until you press Ctrl-C or the process receives SIGINT,
        # SIGTERM or SIGABRT. This should be used most of the time, since
        # start_polling() is non-blocking and will stop the bot gracefully.
        count = 0
        while True:
            time.sleep(1)

            # heartbeat
            if self._heartbeat:
                count += 1
                if count % 60 == 0:
                    # touch the touch file
                    with open(TOUCH_FILE_PATH, 'w'):
                        pass

    def auto_register_new_chats(self, update: Update, context: CallbackContext):
        """
        Automatically register new chats from all updates, except for the ones from the bot itself
        :param update:
        :param context:
        :return:
        """
        if update.effective_user.id == self.bot.id:
            return
        self.update_chat_id(update, context)

    # on each chat message and command update chat_id
    def update_chat_id(self, update: Update, context: CallbackContext) -> None:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        chat_type = update.effective_chat.type
        match chat_type:
            case "private":
                user_chat_type = ChatType.PERSONAL_CHAT
            case "group":
                user_count = context.bot.get_chat_members_count(chat_id)
                if user_count == 2:
                    user_chat_type = ChatType.TOPIC_CHAT
                else:
                    user_chat_type = ChatType.GROUP_CHAT
            case "supergroup":
                user_chat_type = ChatType.GROUP_CHAT
            case "channel":
                user_chat_type = ChatType.CHANNEL
            case other:
                raise ValueError(f"Unknown chat type {chat_type}")
        self.update_user_chat(user_id, chat_id, user_chat_type)

    @telegram_commands_registry.register(group='basic')
    def start(self, update: Update, context: CallbackContext):
        # register user
        username = update.effective_user.username
        user_id = update.effective_user.id

        if self.have_user(user_id):
            message = f"Welcome back, {username}!\n"
            message += WELCOME_MESSAGE  # todo: find a way to extract this to Logic plugin
            self.activate_user(user_id)
            update.effective_message.reply_text(message)
        else:
            message = f"Welcome, {username}!\n"
            message += WELCOME_MESSAGE  # todo: find a way to extract this to Logic plugin
            self.add_user(user_id=user_id, username=username)
            update.effective_message.reply_text(message)

    # @telegram_commands_registry.register(group='basic')
    def stop(self, update: Update, context: CallbackContext):
        # find user
        user_id = update.effective_user.id
        # update user
        self.deactivate_user(user_id)

    @telegram_commands_registry.register(group='basic')
    def stop_announcements(self, update: Update, context: CallbackContext):
        # find user
        user_id = update.effective_user.id
        # update user
        self.stop_user_announcements(user_id)

    @telegram_commands_registry.register(group='basic')
    def start_announcements(self, update: Update, context: CallbackContext):
        # find user
        user_id = update.effective_user.id
        # update user
        self.start_user_announcements(user_id)

    @property
    def bot(self) -> Bot:
        return self._updater.bot

    def send_message(self, message, user_id: int = None, username: str = None):
        if user_id is None:
            if username is not None:
                user_id = self.find_user(username)
            else:
                raise ValueError("Either username or user_id must be provided")
        self.bot.send_message(user_id, text=message)

    # user registry
    def add_user(self, user_id, username):
        self.user_registry.add_user(user_id, username)

    def have_user(self, user_id):
        return self.user_registry.have_user(user_id)

    def activate_user(self, user_id):
        self.user_registry.activate_user(user_id)

    def deactivate_user(self, user_id):
        self.user_registry.stop_user(user_id)

    def stop_user_announcements(self, user_id):
        self.user_registry.stop_user_announcements(user_id)

    def start_user_announcements(self, user_id):
        self.user_registry.start_user_announcements(user_id)

    def update_user_chat(self, user_id, chat_id, user_chat_type):
        self.user_registry.update_user_chat(user_id, chat_id, user_chat_type)

    def find_user(self, username):
        return self.user_registry.find_user(username)

    def get_user(self, user_id):
        return self.user_registry.get_user(user_id)

    # admin commnads
    @telegram_commands_registry.register('/announce', group='admin')
    def announce(self, update: Update, context: CallbackContext):
        """Send a message to all users"""
        user = update.effective_user.username
        if user == "petr_lavrov":
            message = update.message.text
            message = message.replace("/announce", "").strip()
            if not message:
                update.message.reply_text("Please provide a message")
                return
            message = ANNOUNCEMENT_TEMPLATE.format(message=message)
            for user in self.user_registry.get_active_users():
                if user.announcements_enabled:
                    self.send_message(message, user.user_id)
        else:
            update.message.reply_text("Haaa, you sneaky! You can't do that!")


def main(expensive: bool) -> None:
    """
    Start the bot
    :param expensive: Use 'text-davinci-003' model instead of 'text-ada:001'
    :return:
    """
    # Create the Updater and pass it your bot's token.
    token = secrets["telegram_api_token"]
    bot = TelegramBot(token=token)
    bot.setup(expensive=expensive)
    bot.run()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--expensive", action="store_true",
                        help="use expensive calculation - 'text-davinci-003' model instead of 'text-ada:001' ")
    args = parser.parse_args()

    main(expensive=args.expensive)
