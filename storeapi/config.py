from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class BaseConfig(BaseSettings):
    ENV_STATE: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

class GlobalConfig(BaseConfig):
    DATABASE_URL: Optional[str] = None
    DB_FORCE_ROLL_BACK: bool = False
    LOGTAIL_APIKEY: Optional[str] = None
    SECRET_KEY: Optional[str] = None
    ALGORITHM: Optional[str] = "HS256"
    EXPIRATION: Optional[int] = 30
    CONFIRM_EXPIRATION: Optional[int] = 1440
    MAILGUN_API_KEY: Optional[str] = None
    MAILGUN_API_DOMAIN: Optional[str] = None
    B2_KEY_ID: Optional[str] = None
    B2_APPLICATION_KEY: Optional[str] = None
    B2_BUCKET_NAME: Optional[str] = None
    DEEPAI_API_KEY: Optional[str] = None

class DevConfig(GlobalConfig):
    model_config = SettingsConfigDict(env_prefix="DEV_", extra="ignore")

class ProdConfig(GlobalConfig):
    model_config = SettingsConfigDict(env_prefix="PROD_", extra="ignore")

class TestConfig(GlobalConfig):
    DATABASE_URL: Optional[str] = "sqlite:///test.db"
    DB_FORCE_ROLL_BACK: bool = True
    LOGTAIL_APIKEY: Optional[str] = "d4be6f25342a41cd0aaf93e89241b96ef8584e93e994ec12d16d885cd075e78a"
    SECRET_KEY: Optional[str] = "a7e578dcf76240a4a742ce94512c988bf6eedab930fed7b03c1588f8798d0cdf"
    ALGORITHM: Optional[str] = "HS256"
    EXPIRATION: Optional[int] = 30
    CONFIRM_EXPIRATION: Optional[int] = 1440

    model_config = SettingsConfigDict(env_prefix="TEST_", extra="allow")

@lru_cache()
def get_config(env_state: str):
    configs = {"dev": DevConfig, "prod": ProdConfig, "test": TestConfig}
    return configs[env_state]()

config = get_config(BaseConfig().ENV_STATE)
