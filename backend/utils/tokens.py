from typing import List

import tiktoken

enc = tiktoken.encoding_for_model("gpt-4o")


def get_tokens(value: str) -> List[int]:
    return enc.encode(value)
