import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List


class ChatType(Enum):
    PERSONAL_CHAT = 'personal_chat'  # personal chat with the bot
    TOPIC_CHAT = 'topic_chat'  # private chat with the bot, assigned to a specific topic
    GROUP_CHAT = 'group_chat'  # multi-user group chat
    CHANNEL = 'channel'  # multi-user channel


@dataclass
class Chat:
    chat_id: int
    chat_type: ChatType
    users: List[int]  # list of user_ids


class ChatRegistry:
    def __init__(self, root_dir: str = 'app_data/chats'):
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self._chats = self._load_all_chats()  # Dict[int, Chat]

    def _load_all_chats(self):
        chats = {}
        for file in self.root_dir.iterdir():
            if not file.suffix == 'json':
                continue
            chat_id = int(file.stem)
            chats[chat_id] = self._load_chat(chat_id)
        return chats

    def _save_chat(self, chat: Chat):
        file_path = self.root_dir / f'{chat.chat_id}.json'
        with open(file_path, 'w') as file:
            json.dump(chat.__dict__, file)

    def _load_chat(self, chat_id: int):
        try:
            file_path = self.root_dir / f'{chat_id}.json'
            with open(file_path, 'r') as file:
                data = json.load(file)
            return Chat(**data)
        except FileNotFoundError:
            return None

    def add_chat(self, chat_id: int, chat_type: ChatType, users: List[int]):
        if chat_id in self._chats:
            return
        chat = Chat(chat_id, chat_type, users)
        self._chats[chat_id] = chat
        self._save_chat(chat)
