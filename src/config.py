from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import (
    BaseSettings,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

BASE_DIR = Path(__file__).parent.parent
TOML_PATH = BASE_DIR / "config.toml"


class Kwork(BaseModel):
    base_url: str = Field(default="https://kwork.ru")
    request_delay: float = Field(default=1.5)
    user_agent: str = Field(
        default=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
    )
    cookies: str = Field(default="")


class Logging(BaseModel):
    level: str = Field(default="INFO")


class RabbitMQ(BaseModel):
    url: str = Field(default="amqp://guest:guest@localhost/")


class Dragonfly(BaseModel):
    url: str = Field(default="redis://localhost:6379")
    dedup_ttl_days: int = Field(default=7)

    @property
    def dedup_ttl_seconds(self) -> int:
        return self.dedup_ttl_days * 86400


class Parser(BaseModel):
    interval: int = Field(default=60)


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore",
        toml_file=TOML_PATH,
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    kwork: Kwork = Kwork()
    logging: Logging = Logging()
    rabbitmq: RabbitMQ = RabbitMQ()
    dragonfly: Dragonfly = Dragonfly()
    parser: Parser = Parser()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,  # noqa: ARG003
        env_settings: PydanticBaseSettingsSource,  # noqa: ARG003
        dotenv_settings: PydanticBaseSettingsSource,  # noqa: ARG003
        file_secret_settings: PydanticBaseSettingsSource,  # noqa: ARG003
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        sources: list[PydanticBaseSettingsSource] = [
            EnvSettingsSource(settings_cls),
        ]
        if TOML_PATH.exists():
            sources.append(TomlConfigSettingsSource(settings_cls))
        return tuple(sources)


cfg = Config()
