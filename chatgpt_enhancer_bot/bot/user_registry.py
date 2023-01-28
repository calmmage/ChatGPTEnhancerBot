import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Union, Set

from .chat_registry import ChatType


@dataclass
class User:
    username: str
    user_id: int
    announcements_enabled: bool = True
    active: bool = True
    # personal_chat_id: int = None  # todo: mandatory for personal chats,
    topic_chats: Set[int] = field(default_factory=set)  # list of chat_ids of chats with TOPIC_CHAT type
    group_chats: Set[int] = field(default_factory=set)  # list of chat_ids of chats with GROUP_CHAT type

    def to_json(self):
        return json.dumps({
            "username": self.username,
            "user_id": self.user_id,
            "announcements_enabled": self.announcements_enabled,
            "active": self.active,
            "topic_chats": list(self.topic_chats),
            "group_chats": list(self.group_chats)
        })


class UserRegistry:
    def __init__(self, root_dir: Union[str, Path] = 'app_data/users'):
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self._users = self._load_all_users()  # Dict[int, User]
        self._usernames_map = {user.username: user.user_id for user in self._users.values()}  # Dict[str, User]

    def _load_all_users(self):
        # todo: create and store a separate user list file to track all users
        users = {}
        for file in self.root_dir.iterdir():
            if not file.suffix == '.json':
                continue
            user_id = int(file.stem)
            users[user_id] = self._load_user(user_id)
        return users

    def _save_user(self, user: User):
        file_path = self.root_dir / f'{user.user_id}.json'
        with open(file_path, 'w') as file:
            file.write(user.to_json())

    def _load_user(self, user_id: int):
        try:
            file_path = self.root_dir / f'{user_id}.json'
            with open(file_path, 'r') as file:
                data = json.load(file)
            return User(**data)
        except FileNotFoundError:
            # todo: add logging
            raise ValueError(f'User with id {user_id} not found')

    def add_user(
            self,
            user_id: int,
            username: str,
            chat_id: int = None,
            chat_type: ChatType = None,
    ):
        if user_id in self._users:
            return
        user = User(username, user_id)
        self._users[user_id] = user
        self._usernames_map[username] = user_id
        if chat_id is not None and chat_type is not None:
            self.update_user_chat(user_id, chat_id, chat_type)
        self._save_user(user)

    def get_user(self, user_id: int):
        user_id = int(user_id)
        return self._users.get(user_id)

    def have_user(self, user_id: int):
        user_id = int(user_id)
        return user_id in self._users

    def find_user(self, username: str):
        user_id = self._usernames_map.get(username)
        return user_id

    def _update_user(
            self,
            user_id,
            active: bool = None,
            announcements_enabled: bool = None,
            personal_chat_id: int = None,
            topic_chats: List[int] = None,
            group_chats: List[int] = None,
            remove_chats: bool = False,
            **kwargs):
        """
        Updates user data. If a field is not specified, it will not be updated.
        :param user_id:
        :param active:
        :param announcements_enabled:
        :param personal_chat_id:
        :param topic_chats:
        :param group_chats:
        :param remove_chats: whether to remove chats from the list or add them
        :param kwargs:
        :return:
        """
        user = self._users[user_id]
        if active is not None:
            user.active = active
        if announcements_enabled is not None:
            user.announcements_enabled = announcements_enabled
        if personal_chat_id is not None:
            user.personal_chat_id = personal_chat_id
        if topic_chats is not None:
            if remove_chats:
                user.topic_chats -= set(topic_chats)
            else:
                user.topic_chats.update(topic_chats)
        if group_chats is not None:
            if remove_chats:
                user.group_chats -= set(group_chats)
            else:
                user.group_chats.update(group_chats)

        for key, value in kwargs.items():
            setattr(user, key, value)
        self._save_user(user)

    def activate_user(self, user_id):
        self._update_user(user_id, active=True)

    def stop_user(self, user_id):
        self._update_user(user_id, active=False)

    def start_user_announcements(self, user_id):
        self._update_user(user_id, announcements_enabled=True)

    def stop_user_announcements(self, user_id):
        self._update_user(user_id, announcements_enabled=False)

    def update_user_chat(self, user_id, chat_id, chat_type):
        user = self.get_user(user_id)
        match chat_type:
            case ChatType.PERSONAL_CHAT:
                if user.user_id != chat_id:
                    raise ValueError(
                        f'Please report to @petr_lavrov: Your user id {user_id} does not match chat id {chat_id}')
            case ChatType.TOPIC_CHAT:
                if chat_id not in user.topic_chats:
                    self._update_user(user_id, topic_chats=[chat_id])
            case ChatType.GROUP_CHAT:
                if chat_id not in user.group_chats:
                    self._update_user(user_id, group_chats=[chat_id])
            case _:
                raise ValueError('Invalid chat type')

    def get_active_users(self):
        return [user for user in self._users.values() if user.active]
