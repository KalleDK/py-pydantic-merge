from typing import Any, Self

import pydantic

__version__ = "0.1.0"


class PydanticMergeError(Exception):
    """Base class for exceptions in this module."""


def make_default_dict(model: type[pydantic.BaseModel] | pydantic.BaseModel) -> dict[str, tuple[bool, Any]]:

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
        if isinstance(field.default, pydantic.BaseModel):
            dct[name] = (True, field.default)
            continue
    return dct


def merge_dump(v: pydantic.BaseModel | dict[str, Any]) -> dict[str, Any]:
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

        # If the field is not present in the base
        # We will just override the base value with the override value
        if name not in _default:
            base[name] = o_value
            continue

        is_def, d_value = _default[name]

        if isinstance(d_value, MergeableExtension):
            base[name] = d_value.model_merge(o_value)
            continue

        # We don't merge basic dict's for now as it feels more like it should be an override than a merge, but we can add this later if needed

        # If the override value is not a dict or BaseModel
        # If the base value is not a BaseModel
        # We will just override the base value with the override value
        if not isinstance(o_value, (dict, pydantic.BaseModel)) or not isinstance(d_value, (pydantic.BaseModel)):
            base[name] = o_value
            continue

        if isinstance(o_value, pydantic.BaseModel):
            o_value = merge_dump(o_value)

        base[name] = merge_dct(d_value, o_value)  # pyright: ignore[reportUnknownArgumentType]

    return base


class MergeableExtension:
    @pydantic.model_validator(mode="before")
    @classmethod
    def _validate_base(cls, v: Any) -> Any:
        if not issubclass(cls, pydantic.BaseModel):
            raise PydanticMergeError(
                f"MergeableExtension can only be used with pydantic.BaseModel subclasses, got {cls}"
            )

        return merge_dct(cls, v)

    def model_merge(self: Self, other: Self | dict[str, Any] | Any) -> Any:

        if not isinstance(self, pydantic.BaseModel):
            raise PydanticMergeError(
                f"model_merge can only be used with pydantic.BaseModel subclasses, got {self.__class__}"
            )
        if not isinstance(other, (dict, pydantic.BaseModel)):
            print(f"other is not a dict or BaseModel, returning other: {other}")
            return other

        obj = self.__class__.model_validate(merge_dct(self, other))  # pyright: ignore[reportUnknownArgumentType]

        return obj


class BaseModel(pydantic.BaseModel, MergeableExtension):
    pass


__all__ = ["BaseModel", "MergeableExtension", "PydanticMergeError"]
