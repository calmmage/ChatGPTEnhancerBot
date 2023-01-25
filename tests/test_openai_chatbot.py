import pytest

from chatgpt_enhancer_bot.openai_chatbot import ChatBot


@pytest.fixture
def chatbot_fixture():
    return ChatBot()


def test_help(chatbot_fixture):
    bot = chatbot_fixture
    # step one - test that it works at all
    res = bot.help()

    # todo: step two - test that it returns the right thing
    # assert chatbot_fixture.help() ==

    # check for specific method
    res = bot.help('/help')
    expected_result = ChatBot.help.__doc__
    assert expected_result == res
