# idea: the "openai" part of the bot. API. A functionality
import datetime
import json
import logging
import os.path
from functools import lru_cache

import openai
from random_word import RandomWords

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

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)


class ChatBot:
    DEFAULT_CHAT_NAME = 'General'

    def __init__(self, model="text-ada:001", history_word_limit=HISTORY_WORD_LIMIT,  # history_path=HISTORY_PATH,
                 conversations_history_path=CONVERSATIONS_HISTORY_PATH):
        self.model = model
        self.chat_count = 0
        self._session_name = RW.get_random_word()  # random-word
        self._history_word_limit = history_word_limit

        self._active_chat = self.DEFAULT_CHAT_NAME
        self._conversations_history_path = conversations_history_path
        self._conversations_history = self._load_conversations_history()  # attempt to make 'new chat' a thing
        # self._start_new_chat()
        self._traceback = []

    commands = {
        # todo: group commands by meaning
        "/help": "help",
        # todo: register user (/start)
        # todo:

        # Chat management
        "/new_chat": "start_new_chat",
        "/chats": "list_chats",
        "/switch_chat": "switch_chat",
        "/rename_chat": "rename_chat",
        "/history": "get_history",
        # todo: default = everytime new chat (and sometimes go back), or default = everytime same chat (and sometimes go to threads)
        # todo: map discussions, summary. Group by topic. Depth Navigation.

        # model configuration and preset
        # todo: history tokens limit
        # todo: temperature
        # todo: response tokens limit
        "/list_models": "list_models",
        "/switch_model": "switch_model",
        # todo: presets, menu

        # dev
        "/dev": "get_traceback",

        # todo: rewrite all commands as a separate wrapper methods, starting with _command
    }

    def _load_conversations_history(self):
        if os.path.exists(self._conversations_history_path):
            return json.load(open(self._conversations_history_path))
        else:
            return {self.DEFAULT_CHAT_NAME: []}

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

    def start_new_chat(self, name=None):
        """
        Start a new conversation thread with clean context. Saves up the token quota.
        :param name: Name for a new chat (don't repeat yourself!)
        :return:
        """
        if name is None:
            name = self._generate_new_chat_name()
        if name in self._conversations_history:
            # todo: process properly? Switch instead?
            raise RuntimeError("Chat already exists")
        self._active_chat = name
        self._conversations_history[self._active_chat] = []
        self.chat_count += 1
        # todo: name a chat accordingly, after a few messages

    def _generate_new_chat_name(self):
        # todo: rename chat according to its history - get the syntactic analysis (from chatgpt, some lightweight model)
        today = datetime.datetime.now().strftime('%y%b%d')
        new_chat_name = f'{today}-{self._session_name}-{self.chat_count}'
        return new_chat_name

    def list_chats(self, limit=10):
        """ List 10 most recent chats. Use /list_chats 0 to list all chats

        :param limit: Num chats to list. Default - 10. To get all chats - set to 0
        :return:
        """
        return list(self._conversations_history.keys())[-limit:]

    def switch_chat(self, name=None, index=None):
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
            return f"Switched chat to {name} successfully"  # todo - log instead? And then send logs to user
        raise RuntimeError("Both name and index are missing")

    def rename_chat(self, new_name, target_chat=None):
        """
        Rename conversation thread for more convenience and future reference

        :param new_name: new name
        :param target_chat: chat to be renamed, by default - current one.
        :return:
        """
        # check if new name is already taken
        if new_name in self._conversations_history:
            raise RuntimeError(f"Name {new_name} already taken")
        if target_chat is None:
            target_chat = self._active_chat
            self._active_chat = new_name
        self._conversations_history[new_name] = self._conversations_history[target_chat]
        del self._conversations_history[target_chat]

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

    def switch_model(self, model):
        """Switch under-the-hood model that ChatGPT uses
        Most notable models:
        'text-davinci-003' - strongest and most expensive
        Others make pretty mush no sense
        there w
        """
        # check model is valid
        if model not in self.list_models():
            raise RuntimeError(f"Model {model} is not in the list")
        self.model = model

    @staticmethod
    @lru_cache()
    def list_models():
        """List available openai models. Play at your own peril - using /switch_model command
        Mostly old, useless, cheaper versions
        But also some alternative / experimental ones - most notably codex (for coding) and
        """
        models_list = openai.Model.list()  # todo: pretty print
        return [m.id for m in models_list]

    def save_traceback(self, msg):
        self._traceback.append(msg)

    def get_traceback(self, limit=1):
        return self._traceback[-limit:]

    # ------------------------------
    # Main chat method

    def chat(self, prompt, model=None, max_tokens=512,
             # temperature=0.5, top_p=1, n=1, stream=False, stop="\n",
             **kwargs):
        """
        https://beta.openai.com/docs/api-reference/completions/create

        :param prompt:
        :param model: For testing purposes - cheap - 'text-ada:001'. For real purposes - "text-davinci-003" - expensive!
        :param temperature: 0-1
        :param max_tokens: 16-4096
        :param kwargs:
        :return:
        """
        # todo: Commands. Extract this into a separate method
        if prompt.startswith('/'):
            command, qargs, qkwargs = self.parse_query(prompt)
            if command in self.commands:
                func = self.__getattribute__(self.commands[command])
                return func(*qargs, qkwargs)
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

        # Send the message to the OpenAI API
        if model is None:
            model = self.model
        response = openai.Completion.create(model=model, prompt=augmented_prompt, max_tokens=max_tokens
                                            # todo: pass hash of user
                                            # , temperature=temperature,
                                            # top_p=top_p, n=n, stream=stream, stop=stop
                                            , **kwargs)

        # Extract the response from the API response
        response_text = response['choices'][0]['text'].strip()
        if response_text.startswith(BOT_TOKEN):
            response_text = response_text[len(BOT_TOKEN) + 2:]

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
