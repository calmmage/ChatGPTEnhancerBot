import pytest

from chatgpt_enhancer_bot.openai_chatbot import ChatBot


@pytest.mark.parametrize("query,expected", [
    ("/command", ("/command", [], {})),
    ("/command a", ("/command", ["a"], {})),
    ("/command\na", ("/command", ["a"], {})),
    ("/command a k1=b", ("/command", ["a"], {"k1": "b"})),
    ("/command k2=c", ("/command", [], {"k2": "c"})),
    ("/command a k1=b k2=c", ("/command", ["a"], {"k1": "b", "k2": "c"})),
    ("/command\na k3==d", ("/command", ["a k3==d"], {})),
    ("/command test\na k3==d", ("/command", ["test", "a k3==d"], {})),
    ("/command test k1=x k2=y\na k3==d", ("/command", ["test", "a k3==d"], {"k1": "x", "k2": "y"})),
])
def test_parse_query(query, expected):
    res = ChatBot.parse_query(query)
    assert res == expected
