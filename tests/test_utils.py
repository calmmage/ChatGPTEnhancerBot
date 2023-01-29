import pytest

from chatgpt_enhancer_bot.utils import split_to_code_blocks


@pytest.mark.parametrize("text,expected", [
    ("some text ```some code``` some more text",
     [
         {'text': 'some text', 'is_code_block': False},
         {'text': 'some code', 'is_code_block': True},
         {'text': 'some more text', 'is_code_block': False}
     ]),
    ("", []),
    ("```some code```", [{'text': 'some code', 'is_code_block': True}]),
    ("```some code```some text",
     [{'text': 'some code', 'is_code_block': True}, {'text': 'some text', 'is_code_block': False}]),
    ("some text```some code```",
     [{'text': 'some text', 'is_code_block': False}, {'text': 'some code', 'is_code_block': True}]),
])
def test_split_to_code_blocks(text, expected):
    """test that the text is split into code blocks"""
    res = split_to_code_blocks(text)
    assert res == expected


# todo: change the behavior and update the test
#  expected behavior - if the code block is not closed, it should be closed
@pytest.mark.parametrize("text,expected", [
    ("```", []),
    ("```some code", [{'text': 'some code', 'is_code_block': True}]),
    ("some text```", [{'text': 'some text', 'is_code_block': False}]),
])
def test_undefined_behaviour(text, expected):
    """test that the text is split into code blocks"""
    res = split_to_code_blocks(text)
    assert expected == res
