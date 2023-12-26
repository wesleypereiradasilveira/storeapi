import pytest
from typing import Dict
from jose import jwt
from storeapi import security
from storeapi.config import config

@pytest.mark.anyio
class TestSecurity:

    async def test_get_user(self, registered_user: Dict):
        user = await security.get_user(registered_user["email"])
        assert user.email == registered_user["email"]

    async def test_get_user_not_found(self):
        user = await security.get_user("test@example.com")
        assert user is None

    def test_password_hashes(self):
        password = "password"
        assert security.verify_password(password, security.get_password_hash(password))

    def test_create_access_token(self):
        token = security.create_access_token("123")
        assert {"sub": "123", "access_type": "access"}.items() <= jwt.decode(
            token=token,
            key=config.SECRET_KEY,
            algorithms=[config.ALGORITHM]
        ).items()

    def test_create_confirmation_token(self):
        token = security.create_confirmation_token("123")
        assert {"sub": "123", "access_type": "confirmation"}.items() <= jwt.decode(
            token=token,
            key=config.SECRET_KEY,
            algorithms=[config.ALGORITHM]
        ).items()

    def test_get_subject_for_token_valid_confirmation(self):
        email = "test@example.com"
        token = security.create_confirmation_token(email)

        assert email == security.get_subject_for_token_type(token, "confirmation")

    def test_get_subject_for_token_valid_access(self):
        email = "test@example.com"
        token = security.create_access_token(email)

        assert email == security.get_subject_for_token_type(token, "access")

    def test_get_subject_for_token_type_expired(self, mocker):
        mocker.patch("storeapi.security.access_token_expire_minutes", return_value=-1)
        email = "test@example.com"
        token = security.create_access_token(email)

        with pytest.raises(security.HTTPException) as exception:
            security.get_subject_for_token_type(token, "access")
        
        assert "Token has expired" == exception.value.detail

    def test_get_subject_for_token_type_invalid(self):
        token = "Invalid token"

        with pytest.raises(security.HTTPException) as exception:
            security.get_subject_for_token_type(token, "access")
        
        assert "Invalid token here" == exception.value.detail

    def test_get_subject_for_token_type_missing_sub(self):
        email = "test@example.com"
        token = security.create_access_token(email)
        payload = jwt.decode(token, key=config.SECRET_KEY, algorithms=[config.ALGORITHM])
        del payload["sub"]
        token = jwt.encode(payload, key=config.SECRET_KEY, algorithm=config.ALGORITHM)

        with pytest.raises(security.HTTPException) as exception:
            security.get_subject_for_token_type(token, "access")

        assert "Token is missing 'sub' field" == exception.value.detail

    def test_get_subject_for_token_type_wrong(self):
        email = "test@example.com"
        token = security.create_confirmation_token(email)

        with pytest.raises(security.HTTPException) as exception:
            security.get_subject_for_token_type(token, "access")

        assert "Token has incorrect type, expected 'access" == exception.value.detail

    async def test_authenticate_user(self, confirmed_user: Dict):
        user = await security.authenticate_user(confirmed_user["email"], confirmed_user["password"])
        
        assert user.email == confirmed_user["email"]

    async def test_authenticate_user_not_found(self):
        with pytest.raises(security.HTTPException):
            await security.authenticate_user("test@example.net", "1234")

    async def test_authenticate_user_wrong_password(self, registered_user: Dict):
        with pytest.raises(security.HTTPException):
            await security.authenticate_user(registered_user["email"], "wrong password")

    async def test_get_current_user(self, registered_user: Dict):
        token = security.create_access_token(registered_user["email"])
        user = await security.get_current_user(token)
        assert user.email == registered_user["email"]

    async def test_get_current_user_invalid_token(self):
        with pytest.raises(security.HTTPException):
            await security.get_current_user("Invalid token")

    async def test_get_current_user_wrong_type_token(self, registered_user: Dict):
        token = security.create_confirmation_token(registered_user["email"])

        with pytest.raises(security.HTTPException):
            await security.get_current_user(token)
