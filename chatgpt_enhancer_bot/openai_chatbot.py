# idea: the "openai" part of the bot. API. A functionality
import datetime
import json
import logging
import os.path
import pprint

import openai
from random_word import RandomWords

from chatgpt_enhancer_bot.chatgpt_enhancer_bot import WELCOME_MESSAGE
from chatgpt_enhancer_bot.command_registry import CommandRegistry
from utils import get_secrets

secrets = get_secrets()

openai.api_key = secrets["openai_api_key"]

CONVERSATIONS_HISTORY_PATH = 'conversations_history.json'
HISTORY_WORD_LIMIT = 1000

CHATBOT_INTRO_MESSAGE = "The following is a conversation with an AI assistant [Bot]. " \
                        "The assistant is helpful, creative, clever, and very friendly. " \
                        "The bot was created by OpenAI team and enhanced by Petr Lavrov \n"
RW = RandomWords()

HUMAN_TOKEN = '[HUMAN]'
BOT_TOKEN = '[BOT]'
MAX_HISTORY_WORD_LIMIT = 4096

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

telegram_commands_registry = CommandRegistry()


class ChatBot:
    DEFAULT_TOPIC_NAME = 'General'

    def __init__(self, model=None, history_word_limit=HISTORY_WORD_LIMIT,  # history_path=HISTORY_PATH,
                 conversations_history_path=CONVERSATIONS_HISTORY_PATH, query_config=DEFAULT_QUERY_CONFIG, user=None,
                 **kwargs):
        # set up query config
        self._query_config = query_config
        self._query_config.update(**kwargs)
        if user is not None:
            self._query_config.user = user
        if model is not None:
            self._query_config.model = model

        self.chat_count = 0
        self._session_name = RW.get_random_word()  # random-word
        self._history_word_limit = history_word_limit

        self._active_chat = self.DEFAULT_TOPIC_NAME
        self._conversations_history_path = conversations_history_path
        self._conversations_history = self._load_conversations_history()  # attempt to make 'new chat' a thing
        # self._start_new_topic()
        self._traceback = []

    @property
    @telegram_commands_registry.register('model')
    def active_model(self):
        # todo: figure out how to handle multpile configs
        return self._query_config.model

    @telegram_commands_registry.register()
    def set_temperature(self, temperature: float):
        if not 0 <= temperature <= 1:
            raise ValueError("Temperature must be in [0, 1]")
        self._query_config.temperature = temperature
        return f"Temperature set to {temperature}"

    @telegram_commands_registry.register(['set_max_tokens', 'set_response_length'])
    def set_max_tokens(self, max_tokens: int):
        """
        Set max tokens for the response
        Total number of tokens (including prompt) should not exceed the limit for the model - 4096 for text-davinci
        :param max_tokens:
        :return:
        """
        model_token_limit = self.get_model_info(self.active_model)['max_tokens']
        if max_tokens > model_token_limit - self._history_word_limit:
            raise ValueError(
                f"Max tokens combined with history word limit ({self._history_word_limit}) should not exceed {model_token_limit}")
        self._query_config.update(max_tokens=max_tokens)
        return f"Response max tokens length set to {max_tokens}"

    @telegram_commands_registry.register(['set_history_depth', 'set_history_word_limit'])
    def set_history_word_limit(self, limit: int):
        if limit > MAX_HISTORY_WORD_LIMIT - self._query_config.max_tokens:
            raise ValueError(f"Limit must be less than {MAX_HISTORY_WORD_LIMIT}")
        self._history_word_limit = limit
        return f"History word limit set to {limit}"

    commands = {
        # todo: group commands by meaning

        # Chat management
        "/history": "get_history",
        # todo: default = everytime new chat (and sometimes go back), or default = everytime same chat (and sometimes go to threads)
        # todo: map discussions, summary. Group by topic. Depth Navigation.

        # model configuration and preset
        "/list_models": "list_models",
        "/switch_model": "switch_model",
        # todo: presets, menu

        # dev
        "/dev": "get_traceback",

        # todo: rewrite all commands as a separate wrapper methods, starting with _command
    }
    telegram_commands_registry.update(commands)

    def _load_conversations_history(self):
        if os.path.exists(self._conversations_history_path):
            return json.load(open(self._conversations_history_path))
        else:
            return {self.DEFAULT_TOPIC_NAME: []}

    def _save_conversations_history(self):
        json.dump(self._conversations_history, open(self._conversations_history_path, 'w'), indent=' ')
        # todo: Implement saving to database

    def get_history(self, chat=None, limit=10):
        """
        Get conversation history for a particular chat
        :param chat: what context/thread to use. By default - current
        :param limit: Max messages from history
        :return: List[Tuple(prompt, response)]
        """
        if chat is None:
            chat = self._active_chat
        return self._conversations_history[chat][-limit:]

    def _record_history(self, prompt, response_text, chat=None):  # todo: save to proper database
        if chat is None:
            chat = self._active_chat

        timestamp = datetime.datetime.now()
        self._conversations_history[chat].append((prompt, response_text, timestamp.isoformat()))
        self._save_conversations_history()

    @telegram_commands_registry.register('/new_topic')
    def add_new_topic(self, name=None):
        """
        Start a new conversation thread with clean context. Saves up the token quota.
        :param name: Name for a new chat (don't repeat yourself!)
        :return:
        """
        if name is None:
            name = self._generate_new_topic_name()
        if name in self._conversations_history:
            # todo: process properly? Switch instead?
            raise RuntimeError("Chat already exists")
        self._active_chat = name
        self._conversations_history[self._active_chat] = []
        self.chat_count += 1
        # todo: name a chat accordingly, after a few messages

    def _generate_new_topic_name(self):
        # todo: rename chat according to its history - get the syntactic analysis (from chatgpt, some lightweight model)
        today = datetime.datetime.now().strftime('%Y%b%d')
        new_topic_name = f'{today}-{self._session_name}-{self.chat_count}'
        return new_topic_name

    @telegram_commands_registry.register('/topics')
    def list_topics(self, limit=10):
        """ List 10 most recent topics. Use /list_topics 0 to list all topics

        :param limit: Num topics to list. Default - 10. To get all topics - set to 0
        :return:
        """
        return list(self._conversations_history.keys())[-limit:]

    @telegram_commands_registry.register()
    def switch_topic(self, name=None, index=None):
        """
        Switch ChatGPT context to another thread of discussion. Provide name or index of the chat to switch
        :param name:
        :param index:
        :return:
        """
        if name is not None:
            if name in self._conversations_history:  # todo: fuzzy matching, especially using our random words
                self._active_chat = name
                return f"Switched chat to {name} successfully"  # todo - log instead? And then send logs to user
            else:
                try:
                    index = int(name)
                except:
                    raise RuntimeError(f"Missing chat with name {name}")
        if index is not None:
            name = list(self._conversations_history.keys())[-index]
            self._active_chat = name
            return f"Active topic: {name}"  # todo - log instead? And then send logs to user
        raise RuntimeError("Both name and index are missing")

    @telegram_commands_registry.register()
    def rename_topic(self, new_name, topic=None):
        """
        Rename conversation thread for more convenience and future reference

        :param new_name: new name
        :param topic: topic to be renamed, by default - current one.
        :return:
        """
        # check if new name is already taken
        if new_name in self._conversations_history:
            raise RuntimeError(f"Name {new_name} already taken")
        if topic is None:
            topic = self._active_chat
            self._active_chat = new_name
        elif topic not in self._conversations_history:
            raise RuntimeError(f"Topic {topic} not found")

        # update conversation history
        self._conversations_history[new_name] = self._conversations_history[topic]
        del self._conversations_history[topic]

        if new_name == self._active_chat:
            return f"Active topic: {new_name}"
        else:
            return f"Renamed {topic} to {new_name}"

    @staticmethod
    def calculate_history_depth(history, word_limit):
        num_items = 0
        num_words = 0
        while num_words <= word_limit and num_items < len(history):
            num_words += len(history[-(num_items + 1)][0]) + len(history[-(num_items + 1)][1])
            num_items += 1
        return num_items

    @staticmethod
    def parse_query(query):
        """format: "/command arg1 arg2 key3=arg3" """
        parts = query.strip().split()
        if parts[0].startswith('/'):
            command = parts[0]
            parts = parts[1:]
        else:
            raise RuntimeError(f"command not included? {query}")
        args = []
        kwargs = {}
        for p in parts:
            if '=' in p:
                k, v = p.split('=')
                kwargs[k] = v
            else:
                args.append(p)
        return command, args, kwargs

    def help(self, command=None):
        """Auto-generated from docstrings. Use /help {command} for full docstrings
        *CONGRATULATIONS* You used /help help!!
        """

        if command is None:
            help_message = "Available commands:\n"
            for command in self.commands:
                func_name = self.commands[command]
                func = self.__getattribute__(func_name)
                docstring = func.__doc__ or "This docstring is missing!! Abuse @petr_lavrov until he writes it!!"
                first_line = docstring.strip().split('\n')[0]
                help_message += f'{command}: {first_line}\n'
            return help_message
        else:
            func_name = self.commands[command]
            func = self.__getattribute__(func_name)
            docstring = func.__doc__
            return docstring

    models_data = {m.id: m for m in openai.Model.list().data}

    def get_models_ids(self):
        """
        Get available openai models ids
        :return: List[str]
        """
        return sorted(self.models_data.keys())

    @telegram_commands_registry.register('/list_models')
    def get_models_ids_command(self):
        """
        Get available openai models ids. Pricing: https://openai.com/api/pricing/
        Play at your own peril - using /switch_model command
        Mostly old, useless, cheaper versions
        Most notable models:
        'text-davinci-003' - strongest and most expensive
        Others make pretty mush no sense for Chat
        'davinci-instruct' - predecessor for official ChatGPT
        'codex' - for code generation, model under the hood of Github Copilot
        Probably only makes sense use /query command if you decide to explore
        :return: str
        """
        #  todo: sort meaningfully, highlight most interesting models first
        return "\n".join(self.get_models_ids())

    def get_model_info(self, model_id):
        """
        Get model info
        :param model_id: str
        :return: dict
        """
        return self.models_data[model_id]

    @telegram_commands_registry.register('/get_model_info')
    def get_model_info_command(self, model_id):
        """
        Get model info
        :param model_id: str
        :return: str
        """
        return pprint.pformat(self.get_model_info(model_id))

    def switch_model(self, model):
        """Switch under-the-hood model that this bot uses
        Most notable models:
        'text-davinci-003' - strongest and most expensive
        Others make pretty mush no sense for Chat
        'davinci-instruct' - predecessor for official ChatGPT
        'codex' - for code generation, model under the hood of Github Copilot
        Probably only makes sense use /query command if you decide to explore
        """
        # check model is valid
        if model not in self.models_data:
            raise RuntimeError(f"Model {model} is not in the list")
        self.model = model
        return f"Active model: {model}"

    def save_traceback(self, msg):
        self._traceback.append(msg)

    def get_traceback(self, limit=1):
        return self._traceback[-limit:]

    # ------------------------------
    # Main chat method

    def chat(self, prompt, **kwargs):
        """
        https://beta.openai.com/docs/api-reference/completions/create

        :param prompt:
        :param kwargs:
        :return:
        """
        # todo: Commands. Extract this into a separate method
        if prompt.startswith('/'):
            command, qargs, qkwargs = self.parse_query(prompt)
            if command in self.commands:
                func = self.__getattribute__(self.commands[command])
                return func(*qargs, **qkwargs)
            else:
                raise RuntimeError(f"Unknown Command! {prompt}")
            #         # todo: log / reply instead? Telegram bot handler?
            #     return f"Unknown Command! {prompt}"

        # intro message for model
        augmented_prompt = CHATBOT_INTRO_MESSAGE

        # history - for context
        full_history = self.get_history(limit=0)
        history_depth = self.calculate_history_depth(full_history, word_limit=self._history_word_limit)
        history = full_history[-history_depth:]
        for i in range(len(history)):
            augmented_prompt += f"{HUMAN_TOKEN}: {history[i][0]}\n{BOT_TOKEN}: {history[i][1]}\n"

        # include the latest prompt
        augmented_prompt += f"{HUMAN_TOKEN}: {prompt}\n"
        logger.debug(augmented_prompt)  # print(augmented_prompt)

        response_text = query_openai(augmented_prompt, self._query_config, **kwargs)  # todo: pass hash of user

        # Extract the response from the API response
        response_text = response_text.strip()
        if response_text.startswith(BOT_TOKEN):
            response_text = response_text[len(BOT_TOKEN) + 1:]

        # Update the conversation history
        self._record_history(prompt, response_text)

        # Return the response to the user
        return response_text


def main(expensive: bool = False):
    model = "text-davinci-003" if expensive else "text-ada:001"
    b = ChatBot()
    while True:
        prompt = input(f"{HUMAN_TOKEN}: ")
        response = b.chat(prompt, model=model)
        print(f"{BOT_TOKEN}: ", response)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--expensive", action="store_true",
                        help="use expensive calculation - 'text-davinci-003' model instead of 'text-ada:001' ")
    args = parser.parse_args()

    main(expensive=args.expensive)
