# AV PIO testing fork

Work only in `SteeZyT33/av-pio-test-mcp`. User restrictions override historical
upstream instructions. Do not restore upstream escape tools, dispatchers,
installers, callbacks, presets or live-document resources.

- Only AV Post and AV Callout are allowed. AV Beam is production and forbidden;
  AV Beam Tool is excluded too. No AV PIO source/definitions belong in this repo.
- The supported entry is `mcp-server/vwx_mcp_server.py` (stdio). The in-VW
  boundary is `pio_test/engine.py`; schemas are in `pio_test/schema.py`.
- Document path plus native runtime lifetime/generation must be proven before
  any operation. Markers, handles, filenames and UUIDs alone are insufficient.
- `NativeProof` is intentionally unavailable. Do not replace it with an
  operator checkbox, fake `vs`, basename check or optimistic reset completion.
- All VW mutations belong in VW's own Python MENU-COMMAND runner, initiated
  manually. Native notifications may only invalidate identity. No automatic
  clicks, timers, raw Python-engine execution, sockets, or dialog dismissal.
- Do not modify the operator's AV bootstrap, hot reload, settings or drawing
  files. No installation/deployment is authorized by this PR.
- Python inside VW must parse as 3.9. Standard library only. Never log secrets,
  paths, parameter text, full envelopes or native exception strings.
- Run `python -m unittest discover -v`, portable C++ check in README, and
  `git diff --check`. These verify restrictions, not native safety/stability.
- Keep local evidence private. Before committing, inspect all staged paths;
  never add `.vwx`, `.vso`, `.vsm`, `.vlb`, `.vwr`, `.vst`, private config or keys.
