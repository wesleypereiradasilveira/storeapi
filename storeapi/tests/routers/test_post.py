import pytest
from pydantic.types import Dict, List
from httpx import AsyncClient
from storeapi import security

@pytest.mark.anyio
class TestPost:

    async def create_post(self, body: str, async_client: AsyncClient, logged_in_token: str) -> Dict:
        response = await async_client.post(
            "/post", 
            json={"body": body}, 
            headers={"Authorization": f"Bearer {logged_in_token}"}
        )
        return response.json()

    async def create_comment(self, body: str, post_id: int, async_client: AsyncClient, logged_in_token: str) -> Dict:
        response = await async_client.post(
            "/comment", 
            json={"body": body, "post_id": post_id}, 
            headers={"Authorization": f"Bearer {logged_in_token}"}
        )
        return response.json()
    
    async def like_post(self, post_id: int, async_client: AsyncClient, logged_in_token: str) -> Dict:
        response = await async_client.post(
            "/like",
            json={"post_id": post_id},
            headers={"Authorization": f"Bearer {logged_in_token}"}
        )
        return response.json()

    @pytest.fixture()
    async def created_post(self, async_client: AsyncClient, logged_in_token: str):
        return await self.create_post("Test Post", async_client, logged_in_token)

    @pytest.fixture()
    async def created_comment(self, async_client: AsyncClient, created_post: Dict, logged_in_token: str):
        return await self.create_comment("Test Comment", created_post["id"], async_client, logged_in_token)
    
    async def test_create_post_expired_token(self, async_client: AsyncClient, confirmed_user: Dict, mocker):
        mocker.patch("storeapi.security.access_token_expire_minutes", return_value=-1)
        token = security.create_access_token(confirmed_user["email"])
        response = await async_client.post(
            "/post", 
            json={"body": "Test Post"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401
        assert "Token has expired" in response.json()["detail"]

    async def test_create_post(self, async_client: AsyncClient, confirmed_user: Dict, logged_in_token: str):
        body = "Test post"
        response = await async_client.post(
            "/post", 
            json={"body": body},
            headers={"Authorization": f"Bearer {logged_in_token}"}
        )

        assert response.status_code == 201
        assert {
            "id": 1, 
            "body": body, 
            "user_id": confirmed_user["id"],
            "image_url": None,
        }.items() <= response.json().items()

    async def test_create_post_with_prompt(async_client: AsyncClient, logged_in_token: str, mock_generate_cute_creature_api):
        response = await async_client.post(
            "/post?prompt=A cat",
            json={"body": "Test Post"},
            headers={"Authorization": f"Bearer {logged_in_token}"},
        )
        
        assert response.status_code == 201
        assert {
            "id": 1,
            "body": "Test Post",
            "image_url": None,
        }.items() <= response.json().items()

        mock_generate_cute_creature_api.assert_called()

    async def test_create_post_missing_data(self, async_client: AsyncClient, logged_in_token: str):
        response = await async_client.post(
            "/post", 
            json={},
            headers={"Authorization": f"Bearer {logged_in_token}"}
        )

        assert response.status_code == 422
        assert {}.items() <= response.json().items()

    async def test_get_posts(self, async_client: AsyncClient, created_post: Dict):
        response = await async_client.get("/post")

        assert response.status_code == 200
        assert response.json() == [{**created_post, "likes": 0}]

    @pytest.mark.parametrize(
            "sorting, expected_order",
            [
                ("new", [2,1]),
                ("old", [1,2]),
            ]
    )
    async def test_get_posts_sorting(self, async_client: AsyncClient, logged_in_token: str, sorting: str, expected_order: List[int]):
        await self.create_post("Test Post 1", async_client, logged_in_token)
        await self.create_post("Test Post 2", async_client, logged_in_token)
        response = await async_client.get("/post", params={"sorting": sorting})
        data = response.json()
        post_ids = [post["id"] for post in data]

        assert response.status_code == 200
        assert post_ids == expected_order

    async def test_get_posts_most_likes(self, async_client: AsyncClient, logged_in_token: str):
        await self.create_post("Test Post 1", async_client, logged_in_token)
        await self.create_post("Test Post 2", async_client, logged_in_token)
        await self.like_post(1, async_client, logged_in_token)
        response = await async_client.get("/post", params={"sorting": "most_likes"})
        data = response.json()
        post_ids = [post["id"] for post in data]
        expected_order = [1, 2]

        assert response.status_code == 200
        assert post_ids == expected_order

    async def test_get_posts_wrong_sorting(self, async_client: AsyncClient):
        response = await async_client.get("/post", params={"sorting": "wrong"})
        
        assert response.status_code == 422

    async def test_create_comment(self, async_client: AsyncClient, created_post: Dict, confirmed_user: Dict, logged_in_token: str):
        body = "Test Comment"
        response = await async_client.post(
            "/comment", 
            json={"body": body, "post_id": created_post["id"]},
            headers={"Authorization": f"Bearer {logged_in_token}"}
        )

        assert response.status_code == 201
        assert {
            "id": 1,
            "body": body,
            "post_id": created_post["id"],
            "user_id": confirmed_user["id"]
        }.items() <= response.json().items()

    async def test_get_comments(self, async_client: AsyncClient, created_post: Dict, created_comment: Dict):
        response = await async_client.get(f"/post/{created_post['id']}/comment")

        assert response.status_code == 200
        assert response.json() == [created_comment]

    async def test_get_comments_with_missing_data(self, async_client: AsyncClient, created_post: Dict):
        response = await async_client.get(f"/post/{created_post['id']}/comment")

        assert response.status_code == 200
        assert response.json() == []

    async def test_get_post_comments(self, async_client: AsyncClient, created_post: Dict, created_comment: Dict):
        response = await async_client.get(f"/post/{created_post['id']}")

        assert response.status_code == 200
        assert response.json() == {"post": {**created_post, "likes": 0}, "comments": [created_comment],}

    async def test_get_post_comments_with_missing_data(self, async_client: AsyncClient, created_post: Dict, created_comment: Dict):
        response = await async_client.get("/post/2")

        assert response.status_code == 404
    
    async def test_like_post(self, async_client: AsyncClient, created_post: Dict, logged_in_token: str):
        response = await async_client.post(
            "/like",
            json={"post_id": created_post["id"]},
            headers={"Authorization": f"Bearer {logged_in_token}"}
        )

        assert response.status_code == 201
