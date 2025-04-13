import pytest
from flask import Flask


@pytest.fixture
def app() -> Flask:
    app = Flask(__name__)
    app.debug = True
    return app


@pytest.fixture
def client(app: Flask) -> Flask.test_client:
    return app.test_client()
