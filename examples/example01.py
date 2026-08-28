import pydantic

from pydantic_merge import BaseModel


class DatabaseConfig(BaseModel):
    host: str = "localhost"
    port: int = 5432


class AppConfig(BaseModel):
    debug: bool = False
    database: DatabaseConfig = DatabaseConfig()
    tags: list[str] = pydantic.Field(default_factory=list)
    labels: dict[str, str] = pydantic.Field(default_factory=dict)


base = AppConfig(
    debug=False,
    database=DatabaseConfig(host="db.example.com"),
    tags=["production"],
    labels={"team": "platform"},
)

merged = base.model_merge(
    {
        "debug": True,
        "database": {"port": 5433},
        "tags": ["canary"],
        "labels": {"region": "eu-west-1"},
    }
)

assert merged.debug is True
assert merged.database.host == "db.example.com"
assert merged.database.port == 5433
assert merged.tags == ["canary"]
assert merged.labels == {"region": "eu-west-1"}
