# idea: the "openai" part of the bot. API. A functionality
import datetime
import json
import logging
import os.path
import pprint

import openai
from random_word import RandomWords

from command_registry import CommandRegistry
from openai_wrapper import DEFAULT_QUERY_CONFIG, query_openai
from utils import get_secrets

secrets = get_secrets()

openai.api_key = secrets["openai_api_key"]

CONVERSATIONS_HISTORY_PATH = 'conversations_history.json'
HISTORY_WORD_LIMIT = 1000

HUMAN_TOKEN = '[H]'
BOT_TOKEN = '[B]'
CHATBOT_INTRO_MESSAGE = f"The following is a conversation of human {HUMAN_TOKEN} with an AI assistant {BOT_TOKEN}. " \
                        "The assistant is helpful, creative, clever, and very friendly. " \
                        "All code must be in ```{lang} code ```. " \
                        "The bot was created by OpenAI team and enhanced by Petr Lavrov. \n"

WELCOME_MESSAGE = """This is an alpha version of the Petr Lavrov's ChatGPT enhancer.
This message is last updated on 03.01.2023. Please ping t.me/petr_lavrov if I forgot to update it :)
Please play around, but don't abuse too much. I run this for my own money... It's ok if you send ~100 messages
"""

ERROR_MESSAGE_TEMPLATE = """
Error: *{error}*
*Timestamp:* {timestamp}
*Original message:* {message_text}
*Traceback:* {traceback}
"""

RW = RandomWords()

MAX_HISTORY_WORD_LIMIT = 4096

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

telegram_commands_registry = CommandRegistry()


def try_guess_topic_name(name, candidates):
    matches = [c for c in candidates if name in c]
    if len(matches) == 1:
        return matches[0]
    matches = [c for c in candidates if name.lower() in c.lower()]
    if len(matches) == 1:
        return matches[0]
    return None


class ChatBot:  # todo: rename to OpenAIChatbot
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

        self.topic_count = 0
        self._session_name = RW.get_random_word()  # random-word
        self._history_word_limit = history_word_limit

        self._active_topic = self.DEFAULT_TOPIC_NAME
        self._conversations_history_path = conversations_history_path
        self._conversations_history = self._load_conversations_history()  # attempt to make 'new chat' a thing
        # self._start_new_topic()
        self._traceback = []

    @property
    @telegram_commands_registry.register('/model', group='models')
    def active_model(self):
        """ Get active model """
        # todo: figure out how to handle multpile configs
        return self._query_config.model

    @telegram_commands_registry.register(group='configs')
    def set_temperature(self, temperature: float):
        """ Set temperature for the model """
        if not 0 <= temperature <= 1:
            raise ValueError("Temperature must be in [0, 1]")
        self._query_config.temperature = temperature
        return f"Temperature set to {temperature}"

    @telegram_commands_registry.register(['/set_max_tokens', '/set_response_length'], group='configs')
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

    @telegram_commands_registry.register(['/set_history_depth', '/set_history_word_limit'], group='configs')
    def set_history_word_limit(self, limit: int):
        """Set history word limit - how many words to include for chatbot for context"""
        if limit > MAX_HISTORY_WORD_LIMIT - self._query_config.max_tokens:
            raise ValueError(f"Limit must be less than {MAX_HISTORY_WORD_LIMIT}")
        self._history_word_limit = limit
        return f"History word limit set to {limit}"

    @property
    def command_registry(self):
        return telegram_commands_registry

    # commands = {
    #     # todo: group commands by meaning
    #
    #     # Chat management
    #     # todo: default = everytime new chat (and sometimes go back), or default = everytime same chat (and sometimes go to threads)
    #     # todo: map discussions, summary. Group by topic. Depth Navigation.
    #
    #     # model configuration and preset
    #     # todo: presets, menu
    #
    #     # todo: rewrite all commands as a separate wrapper methods, starting with _command
    # }

    @telegram_commands_registry.register('/topics_menu', group='topics')
    def get_topics_menu(self):
        """
        Display topics menu with most recent topics
        :return:
        """
        # todo: pass max topics number, adapt rows number. Get most recent topics
        return {f"*{topic}*" if topic == self._active_topic else topic: f"/switch_topic {topic}" for topic in
                self.list_topics()}

    def _load_conversations_history(self):
        if os.path.exists(self._conversations_history_path):
            return json.load(open(self._conversations_history_path))
        else:
            return {self.DEFAULT_TOPIC_NAME: []}

    def _save_conversations_history(self):
        json.dump(self._conversations_history, open(self._conversations_history_path, 'w'), indent=' ')
        # todo: Implement saving to database

    def get_history(self, topic=None, limit=10):
        """
        Get conversation history for a particular topic
        :param topic: what context/thread to use. By default - current
        :param limit: Max messages from history
        :return: List[Tuple(prompt, response)]
        """
        if limit is not None:
            limit = int(limit)
        if topic is None:
            topic = self._active_topic
        return self._conversations_history[topic][-limit:]

    @telegram_commands_registry.register('/history', group='topics')
    def get_history_command(self, topic=None, limit=10):
        """
        Get conversation history for a particular topic. Use limit=5 if getting 'message too long' error
        Or ping @petr_lavrov to add pagination or buffer
        :param topic:
        :param limit: messages to include
        :return:
        """
        if limit is not None:
            limit = int(limit)
        history = self.get_history(topic, limit)
        # todo: figure out telegram message lenght limit - split into multiple messages
        return '\n'.join(
            f"{timestamp}\n"
            f"[Human]: {prompt}\n[Bot]: {response}"
            for prompt, response, timestamp in history)

    # def get_summary(self):
    # todo: get summary of the conversation from ChatGPT until this point..

    def _record_history(self, prompt, response_text, topic=None):  # todo: save to proper database
        if topic is None:
            topic = self._active_topic

        timestamp = datetime.datetime.now()
        self._conversations_history[topic].append((prompt, response_text, timestamp.isoformat()))
        self._save_conversations_history()

    @telegram_commands_registry.register('/new_topic', group='topics')
    def add_new_topic(self, name=None):
        """
        Start a new conversation thread with clean context. Saves up the token quota.
        :param name: Name for a new topic (don't repeat yourself!)
        :return:
        """
        if name is None:
            name = self._generate_new_topic_name()
        if name in self._conversations_history:
            # todo: process properly? Switch instead?
            raise RuntimeError("Topic already exists")
        self._active_topic = name
        self._conversations_history[self._active_topic] = []
        self.topic_count += 1
        # todo: name a topic accordingly, after a few messages
        return f"Active topic: *{self._active_topic}*"

    def _generate_new_topic_name(self):
        # todo: rename topic according to its history - get the syntactic analysis
        #  (from chatgpt, some lightweight model)
        today = datetime.datetime.now().strftime('%Y%b%d')
        new_topic_name = f'{today}-{self._session_name}-{self.topic_count}'
        return new_topic_name

    def list_topics(self, limit=10):
        """ List 10 most recent topics. Use /list_topics 0 to list all topics

        :param limit: Num topics to list. Default - 10. To get all topics - set to 0
        :return:
        """
        if limit is not None:
            limit = int(limit)
        return list(self._conversations_history.keys())[-limit:]

    @telegram_commands_registry.register(['/topics', '/t'], group='topics')
    def list_topics_command(self, limit=10):
        """
        List 10 most recent topics. Use /list_topics 0 to list all topics
        """
        return '\n'.join(f"*{t}*" if t == self._active_topic else t for t in self.list_topics(limit))

    @telegram_commands_registry.register(['/switch_topic', '/st'], group='topics')
    def switch_topic(self, name=None, index=None):
        """
        Switch ChatGPT context to another thread of discussion. Provide name or index of the chat to switch
        :param name:
        :param index:
        :return:
        """
        if name is not None:
            if name in self._conversations_history:  # todo: fuzzy matching, especially using our random words
                self._active_topic = name
                return f"Active topic: {name}"  # todo - log instead? And then send logs to user
            guess = try_guess_topic_name(name, self._conversations_history.keys())
            if guess is not None:
                self._active_topic = guess
                return f"Active topic: {guess}"
            try:
                index = int(name)
            except:
                raise RuntimeError(f"Missing topic with name {name}")
        if index is not None:
            name = list(self._conversations_history.keys())[-index]
            self._active_topic = name
            return f"Active topic: {name}"  # todo - log instead? And then send logs to user
        raise RuntimeError("Both name and index are missing")

    @telegram_commands_registry.register(group='topics')
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
            topic = self._active_topic
            self._active_topic = new_name
        elif topic not in self._conversations_history:
            raise RuntimeError(f"Topic {topic} not found")

        # update conversation history
        self._conversations_history[new_name] = self._conversations_history[topic]
        del self._conversations_history[topic]

        if new_name == self._active_topic:
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
        """format: "/command arg text key1=arg1 key2=arg2" """
        args = []
        kwargs = {}
        query = query.strip()

        if query.startswith('/'):
            if ' ' not in query:
                return query, args, kwargs
            command, query = query.split(' ', 1)
        else:
            raise RuntimeError(f"command not included? {query}")

        if '=' not in query:
            return command, [query], kwargs

        parts = query.strip().split('=')

        # parse arg
        arg, key = parts[0].rsplit(' ', 1)
        arg = arg.strip()
        if arg:
            args.append(arg)

        # parse kwargs
        for part in parts[1:-1]:
            value, next_key = part.rsplit(' ', 1)
            kwargs[key] = value.strip()
            key = next_key
        kwargs[key] = parts[-1].strip()

        return command, args, kwargs

    @telegram_commands_registry.register('/start', group='basic')
    def start(self):
        """Send a message when the command /start is issued, initiate the bot"""
        # todo: register user - once the User data model is ready and database is set up
        # user = update.effective_user
        # welcome_message = f'Hi {user.username}!\n'
        return WELCOME_MESSAGE

    @telegram_commands_registry.register('/help', group='basic')
    def help(self, command=None):
        """Auto-generated from docstrings. Use /help {command} for full docstrings
        *CONGRATULATIONS* You used /help help!!
        """
        if command is None:
            help_message = "Available commands:\n"
            for command in self.command_registry.list_commands():
                # todo: add command groups
                help_message += f'{command}: {self.command_registry.get_description(command)}\n'
            return help_message
        else:
            return self.command_registry.get_docstring(command)

    models_data = {m.id: m for m in openai.Model.list().data}

    def get_models_ids(self):
        """
        Get available openai models ids
        :return: List[str]
        """
        return sorted(self.models_data.keys())

    @telegram_commands_registry.register('/list_models', group='models')
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

    @telegram_commands_registry.register('/get_model_info', group='models')
    def get_model_info_command(self, model_id):
        """
        Get model info
        :param model_id: str
        :return: str
        """
        return pprint.pformat(self.get_model_info(model_id))

    @telegram_commands_registry.register(group='models')
    def switch_model(self, model=None):
        """Switch under-the-hood model that this bot uses
        Most notable models:
        'text-davinci-003' - strongest and most expensive
        Others make pretty mush no sense for Chat
        'davinci-instruct' - predecessor for official ChatGPT
        'codex' - for code generation, model under the hood of Github Copilot
        Probably only makes sense use /query command if you decide to explore
        """
        # check model is valid
        # todo: if model is missing - show user a menu with available models..
        if model not in self.models_data:
            raise RuntimeError(f"Model {model} is not in the list, use /list_models to see available models")
        self._query_config.model = model
        return f"Active model: {model}"

    def save_error(self, timestamp, error, traceback, message_text):
        self._traceback.append((timestamp, error, traceback, message_text))

    def get_errors(self, limit=1):
        if limit is not None:
            limit = int(limit)
        return self._traceback[-limit:]

    @telegram_commands_registry.register(['/error', '/describe_error'], group='dev')
    def describe_errors(self, limit=1):
        """
        Get last errors
        :param limit: int, number of errors to return
        :return: str
        """
        if limit is not None:
            limit = int(limit)
        errors = self.get_errors(limit)
        res = []
        for timestamp, error, traceback, message_text in errors:
            res.append(ERROR_MESSAGE_TEMPLATE.format(
                error=error,
                timestamp=timestamp,
                message_text=message_text,
                traceback=traceback
            ))
        return '\n'.join(res)

    @telegram_commands_registry.register(['/raw_query', '/query'], group='dev')
    def raw_query(self, prompt, **kwargs):
        """
        Send query to openai model "as is", without any extra context
        :param prompt:
        :param kwargs: additional parameters to pass to openai.Completion.create
        Description https://beta.openai.com/docs/api-reference/completions/create
        :return:
        """
        return query_openai(prompt, config=self._query_config, **kwargs)

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
            raise NotImplementedError("There was an update to command handling, this part of code is not updated yet")
            # todo: update, add tests
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
            past_prompt, past_response, timestamp = history[i]
            # if self._query_config['history_include_timestamp']:
            # augmented_prompt += f"{timestamp}\n"
            augmented_prompt += f"{HUMAN_TOKEN}: {past_prompt}\n{BOT_TOKEN}: {past_response}\n"

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
