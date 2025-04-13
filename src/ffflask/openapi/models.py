from typing import Any, TypedDict

from pydantic import AnyUrl


class Example(TypedDict, total=False):
    summary: str | None
    description: str | None
    value: Any | None
    externalValue: AnyUrl | None

    # noinspection PyTypedDict
    __pydantic_config__ = {"extra": "allow"}  # noqa: RUF012
