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

load_dotenv()
client = AzureOpenAI()

LOG_FILEPATH = "./logs/out.log"
LOG_FORMAT = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
logger.add(sys.stderr, format=LOG_FORMAT)

if os.environ.get("DISABLE_LOG_TO_TERMINAL").lower() == "true":
    logger.remove()
logger.add(LOG_FILEPATH)


def get_completion(messages: List[Dict[str, str]]):
    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=messages,
        stream=False,  # https://cookbook.openai.com/examples/how_to_stream_completions
        temperature=0,  # https://platform.openai.com/docs/guides/text-generation/how-should-i-set-the-temperature-parameter
        seed=42,  # https://platform.openai.com/docs/guides/text-generation/reproducible-outputs
        max_tokens=1000,  # max token for each response
    )
    log_usage(prompt=messages, completion=response.choices[0].message.content)
    return response


class CompletionStream:
    def __init__(self, messages: List[Dict[str, str]]):
        self.messages = messages
        self.completion = None

    def __enter__(self):
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=self.messages,
            stream=True,  # https://cookbook.openai.com/examples/how_to_stream_completions
            max_tokens=1000,  # max token for each response
            temperature=0,  # https://platform.openai.com/docs/guides/text-generation/how-should-i-set-the-temperature-parameter
            seed=42,  # https://platform.openai.com/docs/guides/text-generation/reproducible-outputs
        )
        return response

    def __exit__(self, exc_type, exc_value, traceback):
        log_usage(prompt=self.messages, completion=self.completion)
