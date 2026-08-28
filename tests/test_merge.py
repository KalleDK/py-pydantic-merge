from typing import Any, cast

import pytest
from pydantic import BaseModel as PydanticBaseModel
from pydantic import Field, ValidationError

from pydantic_merge import BaseModel, MergeableExtension, PydanticMergeError, merge_dump


class DatabaseConfig(BaseModel):
    host: str = "localhost"
    port: int = 5432


class PlainDatabaseConfig(PydanticBaseModel):
    host: str = "localhost"
    port: int = 5432


class AppConfig(BaseModel):
    debug: bool = False
    database: DatabaseConfig = DatabaseConfig()
    tags: list[str] = Field(default_factory=list)
    labels: dict[str, str] = Field(default_factory=dict)


class AppWithPlainDatabase(BaseModel):
    database: PlainDatabaseConfig = PlainDatabaseConfig()


def test_model_merge_recursively_merges_nested_models() -> None:
    base = AppConfig(database=DatabaseConfig(host="db.example.com"))

    merged = base.model_merge({"database": {"port": 5433}})

    assert merged.database.host == "db.example.com"
    assert merged.database.port == 5433
    assert base.database.port == 5432


def test_model_merge_replaces_scalar_list_and_dict_values() -> None:
    base = AppConfig(
        debug=False,
        tags=["production"],
        labels={"team": "platform"},
    )

    merged = base.model_merge(
        {
            "debug": True,
            "tags": ["canary"],
            "labels": {"region": "eu-west-1"},
        }
    )

    assert merged.debug is True
    assert merged.tags == ["canary"]
    assert merged.labels == {"region": "eu-west-1"}


def test_model_merge_accepts_another_model() -> None:
    base = AppConfig(database=DatabaseConfig(host="db.example.com"))
    override = AppConfig(database=DatabaseConfig(port=5434))

    merged = base.model_merge(override)

    assert merged.database.host == "db.example.com"
    assert merged.database.port == 5434


def test_model_merge_recursively_merges_plain_pydantic_models() -> None:
    base = AppWithPlainDatabase(database=PlainDatabaseConfig(host="db.example.com"))
    override = AppWithPlainDatabase(database=PlainDatabaseConfig(port=5433))

    merged = base.model_merge(override)

    assert merged.database.host == "db.example.com"
    assert merged.database.port == 5433


def test_model_validate_recursively_merges_nested_models() -> None:
    config = AppConfig.model_validate({"database": {"host": "db.example.com"}})

    assert config.database.host == "db.example.com"
    assert config.database.port == 5432


def test_model_validate_json_recursively_merges_nested_models() -> None:
    config = AppConfig.model_validate_json('{"database": {"port": 5433}}')

    assert config.database.host == "localhost"
    assert config.database.port == 5433


def test_model_merge_validates_merged_values() -> None:
    config = AppConfig()

    with pytest.raises(ValidationError):
        config.model_merge({"database": {"port": "not-a-port"}})


def test_mergeable_extension_rejects_non_model_instances() -> None:
    with pytest.raises(PydanticMergeError):
        MergeableExtension().model_merge({})


def test_merge_dump_rejects_unsupported_values() -> None:
    with pytest.raises(PydanticMergeError):
        merge_dump(cast(Any, object()))


def test_mergeable_extension_validator_rejects_non_model_classes() -> None:
    with pytest.raises(PydanticMergeError):
        MergeableExtension._validate_base({})  # pyright: ignore[reportPrivateUsage, reportCallIssue]


def test_model_merge_returns_unsupported_values(capsys: pytest.CaptureFixture[str]) -> None:
    result = AppConfig().model_merge(None)

    assert result is None
    assert "other is not a dict or BaseModel, returning other: None" in capsys.readouterr().out
