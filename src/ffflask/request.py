import dataclasses as dc
from collections.abc import Callable, Generator
from contextlib import contextmanager
from functools import wraps
from typing import Any, ParamSpec, TypeVar, get_origin, get_type_hints

from flask import Request as FlaskRequest
from flask import Response as FlaskResponse
from flask import request as current_request
from pydantic import BaseModel, RootModel, ValidationError, create_model
from werkzeug.datastructures import MultiDict

from ffflask.params import Body, Cookie, File, Form, Header, Param, Path, Query

P = ParamSpec("P")
Response = TypeVar("Response")


@dc.dataclass()
class _ValidationErrorHandler:
    _errors: list[ValidationError] = dc.field(default_factory=list)

    @contextmanager
    def catch_errors(self) -> Generator[None, Any, None]:
        try:
            yield
        except ValidationError as e:
            self._errors.append(e)

    def has_errors(self) -> bool:
        return bool(self._errors)

    def format_errors(self) -> str:
        lines: list[str] = []
        for error in self._errors:
            for details in error.errors(
                include_input=False, include_context=False, include_url=False
            ):
                parts = [error.title]
                parts.extend(str(l) for l in details["loc"])
                parts.append(details["msg"])
                lines.append(": ".join(parts))
        return "\n".join(lines)


@dc.dataclass
class _RequestHandler:
    func: Callable[P, Response]

    path_params: dict[str, tuple[type, Path]] = dc.field(
        default_factory=dict, init=False
    )
    query_params: dict[str, tuple[type, Query]] = dc.field(
        default_factory=dict, init=False
    )
    headers_params: dict[str, tuple[type, Header]] = dc.field(
        default_factory=dict, init=False
    )
    cookies_params: dict[str, tuple[type, Cookie]] = dc.field(
        default_factory=dict, init=False
    )
    form_params: dict[str, tuple[type, Form]] = dc.field(
        default_factory=dict, init=False
    )
    files_params: dict[str, tuple[type, File]] = dc.field(
        default_factory=dict, init=False
    )
    body_param: tuple[str, type, Body] | None = dc.field(default=None, init=False)

    path_model: type[BaseModel] | None = dc.field(default=None, init=False)
    query_model: type[BaseModel] | None = dc.field(default=None, init=False)
    headers_model: type[BaseModel] | None = dc.field(default=None, init=False)
    cookies_model: type[BaseModel] | None = dc.field(default=None, init=False)
    form_model: type[BaseModel] | None = dc.field(default=None, init=False)
    files_model: type[BaseModel] | None = dc.field(default=None, init=False)
    body_model: type[RootModel] | None = dc.field(default=None, init=False)

    def __post_init__(self) -> None:
        for arg_name, arg_hint in get_type_hints(
            self.func, include_extras=True
        ).items():
            arg_type = getattr(arg_hint, "__origin__", None)
            if not arg_type:
                continue
            metadata = getattr(arg_hint, "__metadata__", None)
            if not metadata:
                continue
            param = metadata[0]
            match param:
                case Path():
                    self.path_params[arg_name] = (arg_type, param)
                case Query():
                    self.query_params[arg_name] = (arg_type, param)
                case Header():
                    self.headers_params[arg_name] = (arg_type, param)
                case Cookie():
                    self.cookies_params[arg_name] = (arg_type, param)
                case Body():
                    assert self.body_param is None, "Only one body fragment is allowed"
                    self.body_param = (arg_name, arg_type, param)
                case Form():
                    self.form_params[arg_name] = (arg_type, param)
                case File():
                    self.files_params[arg_name] = (arg_type, param)
                case _:
                    pass
        self.path_model = self.build_model_from_params("path", self.path_params)
        self.query_model = self.build_model_from_params("query", self.query_params)
        self.headers_model = self.build_model_from_params(
            "headers", self.headers_params
        )
        self.cookies_model = self.build_model_from_params(
            "cookies", self.cookies_params
        )
        self.form_model = self.build_model_from_params("form", self.form_params)
        self.files_model = self.build_model_from_params("files", self.files_params)
        if self.body_param:
            body_type = self.body_param[1]
            body_model_field = self.body_param[2].to_field()

            class body(RootModel):
                root: body_type = body_model_field

            self.body_model = body

    @staticmethod
    def build_model_from_params(
        name: str, params: dict[str, tuple[type, Param]]
    ) -> type[BaseModel] | None:
        if not params:
            return None
        return create_model(
            name,
            **{
                param_name: (param_type, param.to_field())
                for param_name, (param_type, param) in params.items()
            },
        )

    def process_args(
        self,
        args: dict[str, Any],
        flask_request: FlaskRequest,
        error_handler: _ValidationErrorHandler,
    ) -> dict[str, Any]:
        with error_handler.catch_errors():
            args = self.process_path(args)
        with error_handler.catch_errors():
            args = self.process_query(args, flask_request.args)
        with error_handler.catch_errors():
            args = self.process_body(args, flask_request.data)
        with error_handler.catch_errors():
            args = self.process_cookies(args, flask_request.cookies.to_dict())
        with error_handler.catch_errors():
            args = self.process_headers(args, dict(flask_request.headers))
        return args

    def process_path(self, args: dict[str, Any]) -> dict[str, Any]:
        if not self.path_model:
            return args

        path = self.path_model(**args)
        args.update(path.model_dump())

        for field_name, field in self.path_model.model_fields.items():
            if field.alias and field.alias != field_name and field.alias in args:
                del args[field.alias]
        return args

    def process_query(
        self, args: dict[str, Any], request_args: MultiDict[str, str]
    ) -> dict[str, Any]:
        if not self.query_model:
            return args

        query_args = {}
        for field_name, field in self.query_model.model_fields.items():
            if field_name in request_args:
                query_arg_name = field_name
            elif field.alias and field.alias in request_args:
                query_arg_name = field.alias
            else:
                continue
            if get_origin(field.annotation) in (list, tuple, set):
                query_args[query_arg_name] = request_args.getlist(query_arg_name)
            else:
                query_args[query_arg_name] = request_args.get(query_arg_name)
        query = self.query_model(**query_args)
        args.update(query.model_dump())
        return args

    def process_body(self, args: dict[str, Any], request_data: bytes) -> dict[str, Any]:
        if not self.body_model:
            return args
        assert self.body_param is not None
        args[self.body_param[0]] = self.body_model.model_validate_json(
            request_data
        ).root
        return args

    def process_cookies(
        self, args: dict[str, Any], request_cookies: dict[str, str]
    ) -> dict[str, Any]:
        if not self.cookies_model:
            return args
        cookies = self.cookies_model(**request_cookies)
        args.update(cookies.model_dump())
        return args

    def process_headers(
        self, args: dict[str, Any], request_headers: dict[str, str]
    ) -> dict[str, Any]:
        if not self.headers_model:
            return args
        headers = self.headers_model(**request_headers)
        args.update(headers.model_dump())
        return args

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> FlaskResponse:
        error_handler = _ValidationErrorHandler()
        kwargs = self.process_args(kwargs, current_request, error_handler)
        if error_handler.has_errors():
            return FlaskResponse(status=400, response=error_handler.format_errors())
        response = self.func(*args, **kwargs)
        if isinstance(response, BaseModel):
            return FlaskResponse(
                status=200,
                response=response.model_dump_json(),
                content_type="application/json",
            )
        return response


def request_handler(func: Callable[P, Response]) -> Callable[P, Response]:
    handler = _RequestHandler(func)

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> FlaskResponse:
        return handler(*args, **kwargs)

    return wrapper
