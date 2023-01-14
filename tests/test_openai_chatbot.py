import pytest

from openai_chatbot import ChatBot


@pytest.fixture
def chatbot_fixture():
    return ChatBot()


def test_help(chatbot_fixture):
    # step one - test that it works at all
    res = chatbot_fixture.help()

    # todo: step two - test that it returns the right thing
    # assert chatbot_fixture.help() ==

    # check for specific method
    res = chatbot_fixture.help('/help')
    expected_result = ChatBot.help.__doc__
    assert expected_result == res
