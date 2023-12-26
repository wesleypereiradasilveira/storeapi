import os
os.environ["ENV_STATE"] = "test"

import pytest
from typing import AsyncGenerator, Dict, Generator
from fastapi.testclient import TestClient
from httpx import AsyncClient, Request, Response
from unittest.mock import AsyncMock, Mock
from storeapi.main import app
from storeapi.database import database, user_table

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture()
def client() -> Generator:
    yield TestClient(app)

@pytest.fixture(autouse=True)
async def db() -> AsyncGenerator:
    await database.connect()
    yield database
    await database.disconnect()
    
@pytest.fixture()
async def async_client(client) -> AsyncGenerator:
    async with AsyncClient(app=app, base_url=client.base_url) as ac:
        yield ac

@pytest.fixture()
async def registered_user(async_client: AsyncClient) -> Dict:
    user_details = {"email": "test@example.net", "password": "1234"}
    await async_client.post("/register", json=user_details)
    query = user_table.select().where(user_table.c.email == user_details["email"])
    user = await database.fetch_one(query)
    user_details["id"] = user.id
    return user_details

@pytest.fixture()
async def confirmed_user(registered_user: Dict) -> Dict:
    query = user_table.update().where(user_table.c.email == registered_user["email"]).values(confirmed=True)
    await database.execute(query)
    return registered_user

@pytest.fixture()
async def logged_in_token(async_client: AsyncClient, confirmed_user: Dict) -> str:
    response = await async_client.post("/token", json=confirmed_user)
    return response.json()["access_token"]

@pytest.fixture(autouse=True)
async def mock_httpx_client(mocker):
    mocked_client = mocker.patch("storeapi.tasks.httpx.AsyncClient")
    mocked_async_client = Mock()
    response = Response(status_code=200, content="", request=Request("POST", "//"))
    mocked_async_client.post = AsyncMock(return_value=response)
    mocked_client.return_value.__aenter__.return_value = mocked_async_client

    return mocked_async_client

@pytest.fixture()
def mock_generate_cute_creature_api(mocker):
    return mocker.patch(
        "storeapi.tasks._generate_cute_creature_api",
        return_value={"output_url": "http://example.net"},
    )
