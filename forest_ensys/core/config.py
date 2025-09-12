import pathlib
import secrets
from typing import Optional, Dict, Any

from pydantic import validator, PostgresDsn
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Settings for this application.

    You can override the variables with a .env file.
    You can override the variables (and .env file) by environment variables.
    """

    SERVER_NAME: str = "FOREST Energy System Model"

    # Secret key for hashing passwords
    SECRET_KEY: str = secrets.token_urlsafe(32)

    # Expire duration for access tokens
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8

    # Database access
    POSTGRES_SERVER: Optional[str] = None
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_DB: Optional[str] = None
    SQLALCHEMY_DATABASE_URI: Optional[str] = None

    @validator("SQLALCHEMY_DATABASE_URI", pre=True)
    def assemble_db_connection(cls, v: Optional[str], values: Dict[str, Any]) -> str:
        if isinstance(v, str):
            return v
        if all(
            isinstance(values[key], str)
            for key in ("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_SERVER")
        ):
            return PostgresDsn.build(
                scheme="postgresql",
                user=values.get("POSTGRES_USER"),
                password=values.get("POSTGRES_PASSWORD"),
                host=values.get("POSTGRES_SERVER"),
                path=f"/{values.get('POSTGRES_DB') or ''}",
            )

        config_folder = pathlib.Path(__file__).parent.resolve()
        return f"sqlite:///{config_folder}/../local.db"

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()
