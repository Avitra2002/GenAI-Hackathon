import os
import sys
from typing import Dict, List

from dotenv import load_dotenv
from loguru import logger
from openai import AzureOpenAI

from utils.tokens import (
    DEFAULT_MODEL,
    log_usage,
    num_tokens_from_messages,
    num_tokens_from_string,
)

DEFAULT_MAX_TOKENS = 800
DEFAULT_TEMPERATURE = 0.0
DEFAULT_TOP_P = 0.95
DEFAULT_FREQUENCY_PENALTY = 0.0
DEFAULT_PRESENCE_PENALTY = 0.0

LOG_FILEPATH = "./logs/out.log"
load_dotenv()
client = AzureOpenAI()

if os.environ.get("DISABLE_LOG_TO_TERMINAL").lower() == "true":
    logger.remove()

logger.add(LOG_FILEPATH)


def get_completion(
    messages: List[Dict[str, str]],
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE,
    top_p: float = DEFAULT_TOP_P,
    frequency_penalty: float = DEFAULT_FREQUENCY_PENALTY,
    presence_penalty: float = DEFAULT_PRESENCE_PENALTY,
):
    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=messages,
        stream=False,  # https://cookbook.openai.com/examples/how_to_stream_completions
        max_tokens=max_tokens,  # max token for each response
        temperature=temperature,  # https://platform.openai.com/docs/guides/text-generation/how-should-i-set-the-temperature-parameter
        top_p=top_p,
        frequency_penalty=frequency_penalty,  # https://platform.openai.com/docs/guides/text-generation/frequency-and-presence-penalties
        presence_penalty=presence_penalty,
        seed=42,  # https://platform.openai.com/docs/guides/text-generation/reproducible-outputs
    )
    log_usage(prompt=messages, completion=response.choices[0].message.content)
    return response


class CompletionStream:
    def __init__(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
        top_p: float = DEFAULT_TOP_P,
        frequency_penalty: float = DEFAULT_FREQUENCY_PENALTY,
        presence_penalty: float = DEFAULT_PRESENCE_PENALTY,
    ):
        self.messages = messages
        self.completion = None
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.frequency_penalty = frequency_penalty
        self.presence_penalty = presence_penalty

    def __enter__(self):
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=self.messages,
            stream=True,  # https://cookbook.openai.com/examples/how_to_stream_completions
            max_tokens=self.max_tokens,  # max token for each response
            temperature=self.temperature,  # https://platform.openai.com/docs/guides/text-generation/how-should-i-set-the-temperature-parameter
            top_p=self.top_p,
            frequency_penalty=self.frequency_penalty,  # https://platform.openai.com/docs/guides/text-generation/frequency-and-presence-penalties
            presence_penalty=self.presence_penalty,
            seed=42,  # https://platform.openai.com/docs/guides/text-generation/reproducible-outputs
        )
        return response

    def __exit__(self, exc_type, exc_value, traceback):
        log_usage(prompt=self.messages, completion=self.completion)
