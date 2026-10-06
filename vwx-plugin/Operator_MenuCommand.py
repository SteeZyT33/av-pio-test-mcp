# REVIEW TEMPLATE: user-created Python MENU COMMAND named AV PIO Test Operator.
# Invoked only by the fixed native Enable/Disable/Status/Supervisor commands.
# It never dispatches an IPC job or changes a drawing. Preserve existing plugins.
import sys

REVIEWED_CHECKOUT = r"C:\REPLACE_WITH_REVIEWED_CHECKOUT\av-pio-test-mcp"
PRIVATE_CONFIG = r"C:\REPLACE_WITH_PRIVATE_CONFIG\config.json"
if "REPLACE_WITH_" in REVIEWED_CHECKOUT or "REPLACE_WITH_" in PRIVATE_CONFIG:
    raise RuntimeError("Configure and review the local test harness before use")
sys.path.insert(0, REVIEWED_CHECKOUT)
from pio_test.menu import operator_sync

operator_sync(PRIVATE_CONFIG)
