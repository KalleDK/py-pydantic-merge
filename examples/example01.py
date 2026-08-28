import pydantic

from pydantic_merge import BaseModel


class DatabaseConfig(BaseModel):
    host: str = "localhost"
    port: int = 5432


class AppConfig(BaseModel):
    debug: bool = False
    db01: DatabaseConfig = DatabaseConfig()
    db02: DatabaseConfig = pydantic.Field(default_factory=lambda: DatabaseConfig(host="db02.example.com"))
    tags: list[str] = pydantic.Field(default_factory=list)
    labels: dict[str, str] = pydantic.Field(default_factory=dict)


base = AppConfig(
    debug=False,
    db01=DatabaseConfig(host="db.example.com"),
    tags=["production"],
    labels={"team": "platform"},
)

merged = base.model_merge(
    {
        "debug": True,
        "db01": {"port": 5433},
        "db02": {"port": 5434},
        "tags": ["canary"],
        "labels": {"region": "eu-west-1"},
    }
)

assert merged.debug is True
assert merged.db01.host == "db.example.com"
assert merged.db01.port == 5433
assert merged.tags == ["canary"]
assert merged.labels == {"region": "eu-west-1"}
assert merged.db02.host == "db02.example.com"
assert merged.db02.port == 5434
