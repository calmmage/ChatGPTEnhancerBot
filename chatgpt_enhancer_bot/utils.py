import os
import random


def try_guess_topic_name(name, candidates):
    matches = [c for c in candidates if name in c]
    if len(matches) == 1:
        return matches[0]
    matches = [c for c in candidates if name.lower() in c.lower()]
    if len(matches) == 1:
        return matches[0]
    return None


reasons_path = os.path.join(os.path.dirname(__file__), 'resources/reasons.txt')
reasons = open(reasons_path).read().splitlines()
consolations_path = os.path.join(os.path.dirname(__file__),
                                 'resources/consolations.txt')
consolations = open(consolations_path).read().splitlines()


def generate_funny_reason():
    return random.choice(reasons)


def generate_funny_consolation():
    return random.choice(consolations)


def split_to_code_blocks(text):
    is_code_block = False
    blocks = []
    for block in text.split("```"):
        if block:
            blocks.append(

                {"text": block,
                 "is_code_block": is_code_block}
            )
        is_code_block = not is_code_block
    return blocks


def parse_query(query: str):
    """format: "/command arg text key1=arg1 key2=arg2\n Long text arg" """
    args = []
    kwargs = {}
    query = query.strip()

    if '\n' in query:
        query, text = query.split('\n', 1)
        if text.strip():
            args.append(text.strip())

    if query.startswith('/'):
        if len(query.split()) == 1:
            return query, args, kwargs
        command, query = query.split(maxsplit=1)
    else:
        raise RuntimeError(f"command not included? {query}")

    if '=' not in query:
        args = [query] + args
        return command, args, kwargs

    parts = query.strip().split('=')

    # parse arg
    part = parts[0].strip()
    if ' ' in part:
        arg, key = part.rsplit(maxsplit=1)
        arg = arg.strip()
        if arg:
            args = [arg] + args
    else:
        key = part

    # todo: rework all this. What if someone uses commands for code?
    #  Let's only allow kwargs in the first line of the message
    # parse kwargs
    for part in parts[1:-1]:
        if len(part.split()) > 1:
            value, next_key = part.rsplit(maxsplit=1)
            kwargs[key] = value.strip()
            key = next_key
        else:
            raise RuntimeError(f"Invalid query: {query}")
    kwargs[key] = parts[-1].strip()

    return command, args, kwargs
