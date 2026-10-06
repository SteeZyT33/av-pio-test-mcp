"""Compatibility filename; ONLY the restricted stdio entry point remains."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pio_test.mcp_stdio import main

if __name__ == '__main__':
    sys.exit(main())
