"""Typed PIO record values; text is never trimmed or interpreted as code.

Coordinate fields use VW's unit parser and an explicit unit mark when written.
Dimensionless reals use round-trippable decimal strings, not drawing precision.
The field's actual native type must be verified before these routines are used.
"""

import math
import re

from .errors import require
from .schema import validate

INTEGER = re.compile(r"[+-]?[0-9]+")
REAL = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")


def native_type(name, schema):
    if name == "ControlPoint01X":
        return 10
    if name == "ControlPoint01Y":
        return 11
    return {
        "boolean": 2,
        "integer": 1,
        "number": 3,
        "string": 8 if "enum" in schema else 4,
    }[schema["type"]]


def decode(vs, name, raw, schema):
    require(type(raw) is str and len(raw) <= 2048, "INVALID_NATIVE_FIELD")
    kind = schema["type"]
    if kind == "string":
        value = raw
    elif kind == "boolean":
        require(raw.lower() in ("true", "false", "1", "0"), "INVALID_NATIVE_FIELD")
        value = raw.lower() in ("true", "1")
    elif kind == "integer":
        require(INTEGER.fullmatch(raw) is not None, "INVALID_NATIVE_FIELD")
        value = int(raw)
    elif name in ("ControlPoint01X", "ControlPoint01Y"):
        ok, value = vs.ValidNumStr(raw)
        require(
            ok and type(value) in (int, float) and math.isfinite(value),
            "INVALID_NATIVE_FIELD",
        )
    else:
        require(REAL.fullmatch(raw) is not None, "INVALID_NATIVE_FIELD")
        value = float(raw)
    validate(value, schema)
    return value


def encode(vs, name, value, schema, units):
    validate(value, schema)
    if schema["type"] == "string":
        return value
    if schema["type"] == "boolean":
        return "True" if value else "False"
    if schema["type"] == "integer":
        return str(value)
    numeric = format(value, ".17g")
    if name in ("ControlPoint01X", "ControlPoint01Y"):
        require(units in ("inches", "mm"), "UNSUPPORTED_UNITS")
        numeric += '"' if units == "inches" else "mm"
        # Validate VW's interpretation before writing, including locale/units.
        decoded = decode(vs, name, numeric, schema)
        require(
            math.isclose(decoded, value, rel_tol=1e-12, abs_tol=1e-9),
            "NATIVE_FIELD_CODEC_MISMATCH",
        )
    else:
        require(
            decode(vs, name, numeric, schema) == value, "NATIVE_FIELD_CODEC_MISMATCH"
        )
    return numeric
