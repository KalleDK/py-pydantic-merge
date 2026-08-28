# Pydantic Merge

Merge configuration values with the validation and type safety of
[Pydantic](https://docs.pydantic.dev/).

`pydantic-merge` adds a `model_merge()` method to a Pydantic model. Values in
nested `BaseModel` fields are merged recursively; ordinary values are
overwritten by the new value.

## Installation

```sh
pip install pydantic-merge pydantic
```

The package supports Python 3.13 and later.

## Usage

Import `BaseModel` from `pydantic_merge` instead of directly from Pydantic:

```python
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
```

`model_merge()` accepts either another compatible model or a dictionary:

```python
patch = AppConfig(database={"port": 5434})
merged = base.model_merge(patch)
```

The result is a new instance. The original model is not modified, and the
merged values are validated by Pydantic.

### Using the mixin with Pydantic

If you want to keep importing `BaseModel` from Pydantic, add
`MergeableExtension` as a second base class:

```python
import pydantic

from pydantic_merge import MergeableExtension


class DatabaseConfig(pydantic.BaseModel):
    host: str = "localhost"
    port: int = 5432


class AppConfig(pydantic.BaseModel, MergeableExtension):
    database: DatabaseConfig = DatabaseConfig()


config = AppConfig.model_validate({"database": {"port": 5433}})

assert config.database.host == "localhost"
assert config.database.port == 5433
```

Place `pydantic.BaseModel` before `MergeableExtension` in the class
definition. This form provides the same recursive validation and
`model_merge()` behavior as importing `BaseModel` from `pydantic_merge`.

## Merge behavior

- Nested `pydantic_merge.BaseModel` fields are merged recursively.
- Fields supplied by the override replace the corresponding base value.
- Fields omitted from the override retain the base value or model default.
- Lists are replaced as a whole; their items are not merged.
- Plain dictionaries are replaced as a whole; their keys are not merged.
- A nested model can be overridden with a dictionary containing only the
  fields that should change.

The top-level model must either inherit from `pydantic_merge.BaseModel` or use
`MergeableExtension` alongside `pydantic.BaseModel` to provide the
`model_merge()` method. Nested Pydantic `BaseModel` fields are recognized and
can be merged recursively; lists and dictionaries remain replacement values.

## Errors

`PydanticMergeError` is raised when `MergeableExtension` is used with an
unsupported type. Normal validation failures are raised by Pydantic as
`ValidationError`.

## Development

Install the development environment and run the tests with [uv](https://docs.astral.sh/uv/):

```sh
uv sync --group test --group stubs
uv run pytest -v
```

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
