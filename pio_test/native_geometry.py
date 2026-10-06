"""Flat AV Post descendants in their PIO-local document-unit coordinates.

The SDK observer supplies the real root matrix and Top/Plan state. Nested groups,
curved polylines, rotated/mirrored text and unsupported types fail explicitly in
this first adapter. No projected box is treated as an arbitrary text anchor.
"""

import math

from .errors import require


def point(value):
    require(
        type(value) in (tuple, list)
        and len(value) == 2
        and all(type(x) in (int, float) and math.isfinite(x) for x in value),
        "INVALID_NATIVE_GEOMETRY",
    )
    return list(value)


def describe(vs, child, root, native):
    require(vs.GetParent(child) == root, "NESTED_GEOMETRY_UNSUPPORTED")
    require(native["top_plan"] is True, "GEOMETRY_REQUIRES_TOP_PLAN")
    kind = vs.GetTypeN(child)
    class_name = vs.GetClass(child)
    require(class_name == "AV-MCP-TEST", "FOREIGN_CHILD_CLASS")
    base = {"class": class_name}
    if kind == 2:
        return dict(
            base,
            kind="line",
            start=point(vs.GetSegPt1(child)),
            end=point(vs.GetSegPt2(child)),
        )
    if kind == 5:
        count = vs.GetVertNum(child)
        require(type(count) is int and 2 <= count <= 64, "CHILD_VERTEX_LIMIT")
        return dict(
            base,
            kind="polyline",
            vertices=[point(vs.GetPolyPt(child, i)) for i in range(1, count + 1)],
            closed=vs.IsPolyClosed(child),
        )
    if kind == 10:
        length = vs.GetTextLength(child)
        require(type(length) is int and 0 < length <= 1024, "CHILD_TEXT_LIMIT")
        text = vs.GetText(child)
        require(type(text) is str and len(text) <= 1024, "CHILD_TEXT_LIMIT")
        origin, angle, mirrored = vs.GetTextOrientation(child)
        require(
            type(angle) in (int, float)
            and math.isfinite(angle)
            and abs(angle) < 1e-9
            and mirrored is False,
            "ROTATED_TEXT_METRICS_UNSUPPORTED",
        )
        # For this bounded first Post milestone the native root must be unrotated
        # and unreflected too. Top/Plan boxes then share the child local axes.
        require(
            native["matrix"][:4] == [1, 0, 0, 1], "TRANSFORMED_TEXT_METRICS_UNSUPPORTED"
        )
        p1, p2 = (point(p) for p in vs.GetBBox(child))
        lower = [min(p1[0], p2[0]), min(p1[1], p2[1])]
        upper = [max(p1[0], p2[0]), max(p1[1], p2[1])]
        width, height = upper[0] - lower[0], upper[1] - lower[1]
        require(width > 0 and height > 0, "INVALID_NATIVE_TEXT_METRICS")
        return dict(
            base,
            kind="text",
            text=text,
            origin=point(origin),
            baseline_direction=[1, 0],
            font_size_points=vs.GetTextSize(child, 0),
            width=width,
            height=height,
            bounds=[lower, upper],
        )
    require(False, "NATIVE_CHILD_TYPE_UNSUPPORTED")
