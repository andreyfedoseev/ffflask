import datetime
from http import HTTPStatus
from typing import Annotated as A

from flask import Flask
from flask.testing import FlaskClient
from pydantic import BaseModel
from pytest_mock import MockerFixture

from ffflask import Body, Cookie, Header, Path, Query, request_handler


def test_path(app: Flask, client: FlaskClient, mocker: MockerFixture) -> None:
    callee = mocker.Mock()

    @app.get("/test/<id>/<published_on>")
    @request_handler
    def my_view(
        *, id_: A[int, Path(alias="id")], published_on: A[datetime.date, Path()]
    ) -> str:
        callee(id_=id_, published_on=published_on)

        return "success"

    response = client.get("/test/123/2025-01-01")
    assert response.status_code == HTTPStatus.OK
    callee.assert_called_once_with(id_=123, published_on=datetime.date(2025, 1, 1))

    callee.reset_mock()
    response = client.get("/test/123/abc")
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert (
        response.text
        == "path: published_on: Input should be a valid date or datetime, input is too short"
    )
    assert callee.call_count == 0


def test_query(app: Flask, client: FlaskClient, mocker: MockerFixture) -> None:
    callee = mocker.Mock()

    @app.get("/test/")
    @request_handler
    def my_view(
        *,
        id_: A[int, Query(alias="id")],
        published_on: A[datetime.date, Query()],
        items: A[list[int], Query()],
    ) -> str:
        callee(
            id_=id_,
            published_on=published_on,
            items=items,
        )
        return "success"

    response = client.get("/test/?id=123&published_on=2025-01-01&items=1&items=2")
    assert response.status_code == HTTPStatus.OK
    callee.assert_called_once_with(
        id_=123, published_on=datetime.date(2025, 1, 1), items=[1, 2]
    )

    callee.reset_mock()
    response = client.get("/test/?id=123&published_on=abc")
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.text == (
        "query: published_on: Input should be a valid date or datetime, input is too short\n"
        "query: items: Field required"
    )
    assert callee.call_count == 0


def test_body(app: Flask, client: FlaskClient, mocker: MockerFixture) -> None:
    callee = mocker.Mock()

    class User(BaseModel):
        id: int
        name: str
        age: int

    @app.post("/test/")
    @request_handler
    def my_view(
        *,
        user: A[User, Body()],
    ) -> str:
        callee(user=user)
        return "success"

    response = client.post("/test/", json={"id": "123", "name": "John", "age": 30})
    assert response.status_code == HTTPStatus.OK
    callee.assert_called_once_with(user=User(id=123, name="John", age=30))

    callee.reset_mock()
    response = client.post("/test/", json={"id": "abc", "name": "John", "age": 30})
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert (
        response.text
        == "body: id: Input should be a valid integer, unable to parse string as an integer"
    )
    assert callee.call_count == 0


def test_body__list(app: Flask, client: FlaskClient, mocker: MockerFixture) -> None:
    callee = mocker.Mock()

    class User(BaseModel):
        id: int
        name: str
        age: int

    @app.post("/test/")
    @request_handler
    def my_view(
        *,
        users: A[list[User], Body()],
    ) -> str:
        callee(users=users)
        return "success"

    response = client.post("/test/", json=[{"id": "123", "name": "John", "age": 30}])
    assert response.status_code == HTTPStatus.OK
    callee.assert_called_once_with(users=[User(id=123, name="John", age=30)])

    callee.reset_mock()
    response = client.post("/test/", json=[{"id": "abc", "name": "John", "age": 30}])
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert (
        response.text
        == "body: 0: id: Input should be a valid integer, unable to parse string as an integer"
    )
    assert callee.call_count == 0


def test_body__int_validation(
    app: Flask, client: FlaskClient, mocker: MockerFixture
) -> None:
    callee = mocker.Mock()

    @app.post("/test/")
    @request_handler
    def my_view(
        *,
        id_: A[int, Body(gt=10)],
    ) -> str:
        callee(id_=id_)
        return "success"

    response = client.post("/test/", data="20")
    assert response.status_code == HTTPStatus.OK
    callee.assert_called_once_with(id_=20)

    callee.reset_mock()
    response = client.post("/test/", data="5")
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.text == "body: Input should be greater than 10"
    assert callee.call_count == 0


def test_cookies(app: Flask, client: FlaskClient, mocker: MockerFixture) -> None:
    callee = mocker.Mock()

    @app.get("/test/")
    @request_handler
    def my_view(
        *,
        a_cookie: A[int, Cookie()],
    ) -> str:
        callee(a_cookie=a_cookie)
        return "success"

    client.set_cookie("a_cookie", "123")
    response = client.get("/test/")
    assert response.status_code == HTTPStatus.OK
    callee.assert_called_once_with(a_cookie=123)

    client.set_cookie("a_cookie", "value")
    callee.reset_mock()
    response = client.get("/test/")
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert (
        response.text
        == "cookies: a_cookie: Input should be a valid integer, unable to parse string as an integer"
    )
    assert callee.call_count == 0


def test_headers(app: Flask, client: FlaskClient, mocker: MockerFixture) -> None:
    callee = mocker.Mock()

    @app.get("/test/")
    @request_handler
    def my_view(
        *,
        header: A[str, Header(alias="X-Header")],
    ) -> str:
        callee(header=header)
        return "success"

    response = client.get("/test/", headers={"X-Header": "value"})
    assert response.status_code == HTTPStatus.OK
    callee.assert_called_once_with(header="value")

    callee.reset_mock()
    response = client.get("/test/")
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.text == "headers: X-Header: Field required"
    assert callee.call_count == 0


# TODO: test files
# TODO: test model in response is returned as JSON
