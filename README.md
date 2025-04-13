# ffflask - FastAPI-flavored Flask

Add some FastAPI flavor to your Flask.

> [!CAUTION]
> THIS IS A WORK IN PROGRESS. DO NOT USE IT. YOU'VE BEEN WARNED.

## TL;DR

```python
from flask import Flask
from ffflask import Body, Path, request_handler
from typing import Annotated as A
from pydantic import BaseModel, Field

app = Flask(__name__)


class User(BaseModel):
    name: str = Field(min_length=1)
    age: int = Field(gt=0)


class UpdateUserResponse(BaseModel):
    ok: bool
    errors: list[str] | None = None


@app.route("/user/<user_id>")
@request_handler
def update_user(
    user_id: A[int, Path(gt=0)],
    user: A[User, Body()],
) -> UpdateUserResponse:
    ...
    return UpdateUserResponse(ok=True)
```

## Goals

- Provide a FastAPI-like experience in Flask
  -
- Co-exist with existing Flask API frameworks (Blueprints, Flask-RESTX, etc.)
- Generate OpenAPI documentation

## Non-goals

- Support all FastAPI features, such as dependency injection or background tasks
- Be 100% compatible with FastAPI

## Differences from FastAPI

- Using `typing.Annotated` for request parameters (`Path`, `Query`, etc.) is mandatory
- Embedded `Body` models are not supported. A request may only contain at most one body `Body` model
- Header names are not auto-converted to the underscore style. Use `user_agent: Annotated[str, Header(alias="User-Agent")]` instead.
