from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic.aliases import AliasChoices, AliasPath
from pydantic.fields import Field, FieldInfo, _Unset
from pydantic_core import PydanticUndefined as Undefined
from typing_extensions import deprecated

from ffflask.openapi.models import Example


@dataclass
class Param:
    default: Any = Undefined
    default_factory: Callable[[], Any] | None = _Unset
    annotation: Any | None = None
    alias: str | None = None
    alias_priority: int | None = _Unset
    validation_alias: str | AliasPath | AliasChoices | None = None
    serialization_alias: str | None = None
    title: str | None = None
    description: str | None = None
    gt: float | None = None
    ge: float | None = None
    lt: float | None = None
    le: float | None = None
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None
    discriminator: str | None = None
    strict: bool | None = _Unset
    multiple_of: float | None = _Unset
    allow_inf_nan: bool | None = _Unset
    max_digits: int | None = _Unset
    decimal_places: int | None = _Unset
    examples: list[Any] | None = None
    openapi_examples: dict[str, Example] | None = None
    deprecated: deprecated | str | bool | None = None
    include_in_schema: bool = True
    json_schema_extra: dict[str, Any] | None = None

    def to_field(self) -> FieldInfo:
        # TODO: fix parameters based on the actual param spec of `Field`
        return Field(
            default=self.default,
            default_factory=self.default_factory,
            annotation=self.annotation,
            alias=self.alias,
            alias_priority=self.alias_priority,
            validation_alias=self.validation_alias,
            serialization_alias=self.serialization_alias,
            title=self.title,
            description=self.description,
            gt=self.gt,
            ge=self.ge,
            lt=self.lt,
            le=self.le,
            min_length=self.min_length,
            max_length=self.max_length,
            pattern=self.pattern,
            discriminator=self.discriminator,
            strict=self.strict,
            multiple_of=self.multiple_of,
            allow_inf_nan=self.allow_inf_nan,
            max_digits=self.max_digits,
            decimal_places=self.decimal_places,
            examples=self.examples,
            deprecated=self.deprecated,
            include_in_schema=self.include_in_schema,
            json_schema_extra=self.json_schema_extra,
        )


@dataclass
class Path(Param):
    def __post_init__(self) -> None:
        assert self.default is Undefined, "Path parameters cannot have a default value."


@dataclass
class Query(Param):
    pass


@dataclass
class Header(Param):
    pass


@dataclass
class Cookie(Param):
    pass


@dataclass
class Body(Param):
    pass


@dataclass
class Form(Param):
    pass


@dataclass
class File(Param):
    pass
