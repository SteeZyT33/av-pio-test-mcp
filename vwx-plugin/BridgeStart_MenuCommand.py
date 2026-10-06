# REVIEW TEMPLATE ONLY. Do not run until the native integration gates are met.
# Paste into a USER-CREATED Python MENU COMMAND in VW2026, not Run Script,
# OnIdle, a timer, a web palette or a native raw Python-engine callback.
# Exact name: AV PIO Test Pump. Invoke through the separately reviewed SDK
# AV PIO Test Supervisor menu; direct invocation fails native scope verification.
# Edit only these two local literals. Never accept paths from an MCP payload.
import sys

REVIEWED_CHECKOUT = r'C:\REPLACE_WITH_REVIEWED_CHECKOUT\av-pio-test-mcp'
PRIVATE_CONFIG = r'C:\REPLACE_WITH_PRIVATE_CONFIG\config.json'
if 'REPLACE_WITH_' in REVIEWED_CHECKOUT or 'REPLACE_WITH_' in PRIVATE_CONFIG:
    raise RuntimeError('Configure and review the local test harness before use')
sys.path.insert(0, REVIEWED_CHECKOUT)
from pio_test.menu import run_once

# Exactly one bounded job per manual invocation. No automatic module reload:
# reloading the AV PIO sources remains under the operator's existing bootstrap.
run_once(PRIVATE_CONFIG)
