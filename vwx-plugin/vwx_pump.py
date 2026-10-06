"""The old broad dispatcher is retired, including direct-import callers."""


def pump_all():
    raise RuntimeError('Legacy pump disabled; use the reviewed restricted menu template')


def pump_readonly():
    raise RuntimeError('Background document access is disabled')
