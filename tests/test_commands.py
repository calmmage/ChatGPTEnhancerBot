import pytest

from chatgpt_enhancer_bot.openai_chatbot import ChatBot


@pytest.fixture
def chatbot_fixture():
    return ChatBot()


def test_model(chatbot_fixture):
    bot = chatbot_fixture
    # step one - test that it works at all
    res = bot.get_active_model()
    assert res == 'text-ada:001'


def test_list_models(chatbot_fixture):
    bot = chatbot_fixture
    # step one - test that it works at all
    res = bot.get_models_ids_command()
    assert res is not None


def test_set_max_tokens(chatbot_fixture):
    bot = chatbot_fixture
    # step one - test that it works at all
    res = bot.set_max_tokens(10)
    assert bot._query_config.max_tokens == 10
    assert res == 'Response max tokens length set to 10'
