"""Add recursive merging to Pydantic models.

Use :class:`BaseModel` directly, or combine :class:`MergeableExtension` with
``pydantic.BaseModel`` when keeping Pydantic's base class import is preferred.
Nested models are merged recursively; scalar, list, and dictionary values are
replaced by override values.
"""

from __future__ import annotations

from typing import Any, Self, dataclass_transform

import pydantic

__version__ = "0.1.2.1"


class PydanticMergeError(Exception):
    """Base class for exceptions in this module."""


def make_default_dict(model: type[pydantic.BaseModel] | pydantic.BaseModel) -> dict[str, tuple[bool, Any]]:
    """Build the model values used as the base of a merge.

    The boolean in each tuple indicates whether the value came from a model
    field default. Explicitly set values are kept so subsequent merges can
    preserve them.
    """

    if isinstance(model, pydantic.BaseModel):
        org_default = make_default_dict(model.__class__)

        exp_values = model.model_dump(mode="json", exclude_unset=True)

        for name in exp_values:
            v = getattr(model, name, None)
            if isinstance(v, pydantic.BaseModel):
                org_default[name] = (False, v)
            else:
                org_default[name] = (False, exp_values[name])

        return org_default

    dct: dict[str, tuple[bool, Any]] = {}
    for name, field in model.model_fields.items():
        default = (
            field.default_factory()  # pyright: ignore[reportCallIssue]
            if field.default_factory is not None
            else field.default
        )

        if isinstance(default, pydantic.BaseModel):
            dct[name] = (True, default)
            continue
    return dct


def merge_dump(v: pydantic.BaseModel | dict[str, Any]) -> dict[str, Any]:
    """Convert a model or dictionary to the representation used for merging.

    Nested model instances are restored after serialization so they remain
    available for recursive merging.
    """

    if isinstance(v, pydantic.BaseModel):
        dct = v.model_dump(mode="json", exclude_unset=True)
        for name in dct:
            r_v = getattr(v, name, None)
            if isinstance(r_v, pydantic.BaseModel):
                dct[name] = r_v
        return dct
    if isinstance(v, dict):  # pyright: ignore[reportUnnecessaryIsInstance]
        return v
    raise PydanticMergeError(
        f"merge_dump can only be used with dict or pydantic.BaseModel subclasses, got {v.__class__}"
    )


def merge_dct(
    default: type[pydantic.BaseModel] | pydantic.BaseModel,
    override: dict[str, Any] | pydantic.BaseModel,
) -> dict[str, Any]:
    """Merge an override into a model class or instance.

    Only Pydantic model values are recursively merged. All other override
    values, including lists and dictionaries, replace the existing value.
    """

    _default = make_default_dict(default)
    override = merge_dump(override)

    names = set(override.keys()).union(set(_default.keys()))
    base: dict[str, Any] = {}

    for name in names:
        if name not in override:
            is_def, d_value = _default[name]
            if not is_def:
                base[name] = d_value
            continue
        o_value = override[name]

        # New fields have no base value, so they are passed through unchanged.
        if name not in _default:
            base[name] = o_value
            continue

        is_def, d_value = _default[name]

        if isinstance(d_value, MergeableExtension):
            base[name] = d_value.model_merge(o_value)
            continue

        # Lists, dictionaries, and scalar values are replacement values.
        if not isinstance(o_value, (dict, pydantic.BaseModel)) or not isinstance(d_value, (pydantic.BaseModel)):
            base[name] = o_value
            continue

        if isinstance(o_value, pydantic.BaseModel):
            o_value = merge_dump(o_value)

        base[name] = merge_dct(d_value, o_value)  # pyright: ignore[reportUnknownArgumentType]

    return base


class MergeableExtension:
    """Mixin that adds recursive merge validation to a Pydantic model."""

    @pydantic.model_validator(mode="before")
    @classmethod
    def _validate_base(cls, v: Any) -> Any:  # noqa: ANN401
        """Merge input with nested model defaults before Pydantic validates it."""

        if not issubclass(cls, pydantic.BaseModel):
            raise PydanticMergeError(
                f"MergeableExtension can only be used with pydantic.BaseModel subclasses, got {cls}"
            )

        return merge_dct(cls, v)

    def model_merge(self, other: Self | dict[str, Any] | Any) -> Any:  # noqa: ANN401
        """Return a validated copy with values from ``other`` merged into it.

        ``other`` may be a dictionary or another Pydantic model. Unsupported
        values are returned unchanged for compatibility with the current API.
        """

        if not isinstance(self, pydantic.BaseModel):
            raise PydanticMergeError(
                f"model_merge can only be used with pydantic.BaseModel subclasses, got {self.__class__}"
            )
        if not isinstance(other, (dict, pydantic.BaseModel)):
            # other is not a dict or BaseModel, returning other
            return other

        return self.__class__.model_validate(merge_dct(self, other))  # pyright: ignore[reportUnknownArgumentType]


@dataclass_transform(field_specifiers=(pydantic.Field,))  # type: ignore[misc]
class BaseModel(pydantic.BaseModel, MergeableExtension):
    """Pydantic model base class with recursive merge support."""


__all__ = ["BaseModel", "MergeableExtension", "PydanticMergeError"]
