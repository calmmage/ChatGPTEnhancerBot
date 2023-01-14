from dataclasses import dataclass
from typing import Optional

import openai


@dataclass
class QueryConfig:
    model: str = "text-davinci:003"
    max_tokens: int = 512
    temperature: float = 0.9
    top_p: float = 1.0
    n: int = 1
    stream: bool = False
    stop: str = "\n"
    user: Optional[str] = None

    def update(self, **kwargs):
        self.__dict__.update(kwargs)


DEFAULT_QUERY_CONFIG = QueryConfig()


# todo: add the ability to override specific config values
def query_openai(prompt: str, config: QueryConfig = DEFAULT_QUERY_CONFIG, **kwargs) -> str:
    config.update(**kwargs)
    response = openai.Completion.create(
        model=config.model,
        prompt=prompt,
        max_tokens=config.max_tokens,
        temperature=config.temperature,
        top_p=config.top_p,
        n=config.n,
        stream=config.stream,
        stop=config.stop,
        user=config.user,
    )
    return response.choices[0].text
