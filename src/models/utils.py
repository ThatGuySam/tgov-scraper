import json
from typing import Sequence, Type, TypeVar


from pydantic import BaseModel


T = TypeVar("T", bound=BaseModel)


def to_jsonl(models: Sequence[T]) -> str:
    """
    Serialize a list of Pydantic models to a JSONL (JSON Lines) formatted string.

    Each model is serialized to a single line of JSON using `model_dump_json()`.

    Args:
        models: A list of Pydantic BaseModel instances.

    Returns:
        A JSONL-formatted string with one model per line.
    """
    return "\n".join(model.model_dump_json() for model in models)


def from_jsonl(jsonl_str: str, model_class: Type[T]) -> Sequence[T]:
    """
    Deserialize a JSONL string into a list of Pydantic model instances.

    Args:
        jsonl_str: The JSON Lines string to parse.
        model_class: The Pydantic model class to use for validation.

    Returns:
        A list of instances of the specified Pydantic model class.
    """
    return [
        model_class.model_validate(json.loads(line))
        for line in jsonl_str.strip().splitlines()
    ]
