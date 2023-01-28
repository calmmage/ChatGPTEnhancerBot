from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from chatgpt_enhancer_bot.bot.chat_registry import ChatType
from chatgpt_enhancer_bot.bot.user_registry import UserRegistry


@pytest.fixture
def temp_dir():
    with TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


def test_add_user(temp_dir):
    user_registry = UserRegistry(root_dir=temp_dir)
    user_id = 1
    username = 'testuser'
    user_registry.add_user(user_id, username)
    assert user_registry.have_user(user_id) == True
    assert temp_dir.joinpath(f'{user_id}.json').exists() == True


def test_get_user(temp_dir):
    user_registry = UserRegistry(root_dir=temp_dir)
    user_id = 1
    username = 'testuser'
    user_registry.add_user(user_id, username)
    assert user_registry.get_user(user_id).username == username


def test_update_user(temp_dir):
    user_registry = UserRegistry(root_dir=temp_dir)
    user_id = 1
    username = 'testuser'
    user_registry.add_user(user_id, username)
    new_username = 'newusername'
    user_registry._update_user(user_id, username=new_username)
    assert user_registry.get_user(user_id).username == new_username
    assert temp_dir.joinpath(f'{user_id}.json').exists() == True


def test_load_users(temp_dir):
    user_registry = UserRegistry(root_dir=temp_dir)
    user_id = 1
    username = 'testuser'
    user_registry.add_user(user_id, username)
    user_registry = UserRegistry(root_dir=temp_dir)
    assert user_registry.have_user(user_id) == True
    assert user_registry.get_user(user_id).username == username


def test_update_chat_id(temp_dir):
    user_registry = UserRegistry(root_dir=temp_dir)
    user_id = 1
    username = 'testuser'
    user_registry.add_user(user_id, username)
    chat_id_1 = 1
    chat_type = ChatType.PERSONAL_CHAT
    user_registry.update_user_chat(user_id, chat_id_1, chat_type)

    chat_id_2 = 2
    chat_type = ChatType.TOPIC_CHAT
    user_registry.update_user_chat(user_id, chat_id_2, chat_type)
    assert user_registry.get_user(user_id).topic_chats == {chat_id_2}

    chat_id_3 = 3
    chat_type = ChatType.TOPIC_CHAT
    user_registry.update_user_chat(user_id, chat_id_3, chat_type)
    assert user_registry.get_user(user_id).topic_chats == {chat_id_2, chat_id_3}

    chat_id_4 = 4
    chat_type = ChatType.GROUP_CHAT
    user_registry.update_user_chat(user_id, chat_id_4, chat_type)
    assert user_registry.get_user(user_id).group_chats == {chat_id_4}

    chat_id_5 = 5
    chat_type = ChatType.GROUP_CHAT
    user_registry.update_user_chat(user_id, chat_id_5, chat_type)
    assert user_registry.get_user(user_id).group_chats == {chat_id_4, chat_id_5}

    chat_id_6 = 6
    chat_type = ChatType.PERSONAL_CHAT
    with pytest.raises(Exception):
        user_registry.update_user_chat(user_id, chat_id_6, chat_type)
