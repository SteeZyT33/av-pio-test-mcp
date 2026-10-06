"""Enforce the native operator switch; no client/configuration can enable it."""

from .errors import require


def snapshot(adapter):
    return validate_snapshot(adapter.operator_control())


def validate_snapshot(value):
    require(
        type(value) is dict
        and set(value)
        == {"enabled", "epoch", "generation", "busy", "disable_pending", "unconfirmed"},
        "INVALID_OPERATOR_CONTROL",
    )
    for name in ("enabled", "busy", "disable_pending", "unconfirmed"):
        require(type(value[name]) is bool, "INVALID_OPERATOR_CONTROL")
    for name in ("epoch", "generation"):
        require(
            type(value[name]) is int and value[name] > 0, "INVALID_OPERATOR_CONTROL"
        )
    require(
        not value["disable_pending"] or (value["busy"] and not value["enabled"]),
        "INVALID_OPERATOR_CONTROL",
    )
    return value


def state(value, armed=False, uncertain=False, pending=False):
    if value["busy"]:
        return "BUSY"
    if not value["enabled"]:
        return "OFF"
    if value["unconfirmed"] or uncertain or pending:
        return "UNCONFIRMED"
    return "ARMED" if armed else "READY"
