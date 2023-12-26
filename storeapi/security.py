import logging
from typing import Annotated, Literal
from datetime import datetime, timedelta, UTC
from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from storeapi.database import database, user_table
from storeapi.config import config

logger = logging.getLogger(__name__)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
pwd_context = CryptContext(schemes=["bcrypt"])

def create_credentials_exception(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"www-Authenticate": "Bearer"}
    )

def access_token_expire_minutes() -> int:
    return config.EXPIRATION

def confirm_token_expire_minutes() -> int:
    return config.CONFIRM_EXPIRATION

def create_access_token(email: str):
    logger.debug("Creating access token", extra={"email": email})
    expire = datetime.now(UTC.utc) + timedelta(minutes=access_token_expire_minutes())
    jwt_data = {"sub": email, "exp": expire, "access_type": "access"}
    encoded_jwt = jwt.encode(jwt_data, key=config.SECRET_KEY, algorithm=config.ALGORITHM)
    return encoded_jwt

def create_confirmation_token(email: str):
    logger.debug("Creating confirmation token", extra={"email": email})
    expire = datetime.now(UTC.utc) + timedelta(minutes=confirm_token_expire_minutes())
    jwt_data = {"sub": email, "exp": expire, "access_type": "confirmation"}
    encoded_jwt = jwt.encode(jwt_data, key=config.SECRET_KEY, algorithm=config.ALGORITHM)
    return encoded_jwt

def get_subject_for_token_type(token: str, access_type: Literal["access", "confirmation"]) -> str:
    try:
        payload = jwt.decode(token, key=config.SECRET_KEY, algorithms=[config.ALGORITHM])
    
    except ExpiredSignatureError as exception:
        raise create_credentials_exception("Token has expired") from exception
    
    except JWTError as exception:
        raise create_credentials_exception("Invalid token here") from exception
    
    email = payload.get("sub")
    if email is None:
        raise create_credentials_exception("Token is missing 'sub' field")
    
    token_type = payload.get("access_type")
    if token_type is None or token_type != access_type:
        raise create_credentials_exception(f"Token has incorrect type, expected '{access_type}")
    
    return email

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

async def get_user(email: str):
    logger.debug("Fetching user from the database", extra={"email", email})
    query = user_table.select().where(user_table.c.email == email)
    result = await database.fetch_one(query)
    
    if result:
        return result

async def authenticate_user(email: str, password: str):
    logger.debug("Authenticating user", extra={"email": email})
    user = await get_user(email)
    if not user:
        raise create_credentials_exception("Invalid email or password")

    if not verify_password(password, user.password):
        raise create_credentials_exception("Invalid email or password")
    
    if not user.confirmed:
        raise create_credentials_exception("User has not confirmed email")

    return user

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    email = get_subject_for_token_type(token, "access")
    user = await get_user(email=email)
    if user is None:
        raise create_credentials_exception("Could not find 'user' for this token")
    
    return user
