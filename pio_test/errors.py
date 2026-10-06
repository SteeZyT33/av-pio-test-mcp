"""Stable error codes: never interpolate untrusted text or exception messages."""


class Rejected(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def require(condition, code):
    if not condition:
        raise Rejected(code)
