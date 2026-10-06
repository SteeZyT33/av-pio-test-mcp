# Audit and change report

Scope: all 41 tracked files at fork revision
`0a2f554a15ddddf0d43dc9d251d90a42146c9363`, including AGENTS, Python entrypoints,
launch/install scripts, native C++/project/resources, requirements, legacy paths
and maintenance tools. No installed machine, drawing, SDK binary or company PIO
package was accessed. Static review and AST/file inventory are not a guarantee
of absence of every defect. `upstream-inventory.json` records each exact baseline
path, byte count, SHA-256, Python imports/function count and change disposition.
There were 424 top-level functions in upstream `commands.py`.

## Findings and disposition

| Finding | Exact original files | Change |
| --- | --- | --- |
| Arbitrary Python, generic dispatch/batch, menu invocation and restoring all tools; presets were exposure filters, not authorization | `mcp-server/vwx_mcp_server.py`, `mcp-server/tool_tags.py`, `vwx-plugin/commands.py`, `AGENTS.md` | Broad implementation/tags removed; restricted server replaces entrypoint; shared schema plus explicit in-VW dispatch |
| Dynamic `getattr(commands, cmd)` and module reload; unauthenticated file jobs lacked exact document/session binding; `_cid` influenced output paths | `vwx-plugin/vwx_pump.py`, `vwx-plugin/commands.py` | Legacy pump rejects calls; new authenticated fixed-slot IPC + runtime authority; no payload-selected files |
| Unauthenticated TCP/timer alternatives, permissive async/poll and legacy routes | `vwx-plugin/vwx_mcp_bridge.py`, `legacy/vwx_mcp_bridge_dialog.py`, `legacy/README.md` | Removed entirely; no TCP fallback |
| Standalone HTTP default `0.0.0.0`; broad live-document/layer/class/unit/georef/command resources; optional telemetry/tasks/cache | `mcp-server/vwx_mcp_server.py` | Replaced by minimal stdio-only server; no live resources/cache/telemetry/tasks |
| Launcher performed automatic pip upgrade/install; FastMCP pin plus unbounded Pillow dependency lacked full transitive lock | `bridge/vwx-mcp.bat`, `mcp-server/requirements.txt` | Explicit interpreter/config stdio launcher; zero third-party runtime dependencies; complete empty `requirements.lock` |
| Self-elevation, machine-wide overwrite and wildcard credential deployment | `bridge/deploy_native_bridge.bat`, `native/CredentialsVwxMcp.json`, `docs/PLUGIN_CREDENTIALS.md` | Removed installer/credential packaging; documented manual, reversible local preparation only |
| Error-dialog dismissal, timer/hotkey synthesis, raw Python-engine/background callbacks; stale comments claimed broad context safety | `native/Source/Bridge/VwxBridgePalette.cpp`, `native/Source/Bridge/VwxBridgePalette.h`, `native/Source/ModuleMain.cpp`, `native/VwxBridge.vwr/html/main.js`, `native/VwxBridge.vwr/html/index.html` | Removed the native palette and trigger path, including dismissal implementation. Only manual Python menu template remains; no automatic native execution |
| Native build disabled buffer-security checking, inherited local SDK build props, bundled broad palette resources; not reproducible in cloud without licensed SDK/toolchain | `native/VwxBridge2026.vcxproj`, `native/Source/Prefix/*`, `native/Source/Module-Info.plist`, `native/VwxBridge.vwr/Strings/*`, `native/.gitignore` | Old build/resources removed rather than ship an unsafe/incomplete binary. New C++ lifecycle policy is portable and not deployable |
| Bootstrap auto-discovered installed VW versions/paths and reloaded bridge modules | `vwx-plugin/BridgeStart_MenuCommand.py` | Fixed operator-edited local paths; one manual bounded pump; bridge state is not hot reloaded |
| Broad discovery index and consistency/index-generation tools retained the former surface | `vwx-plugin/vs_index.json`, `tools/build_vs_index.py`, `tools/pruefe_konsistenz.py`, `tools/pruefe_vs_aufrufe.py` | Removed from current deployment; replaced by focused offline restriction tests |
| Guidance recommended unrestricted use and overstated native crash safety | `README.md`, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, `docs/TOOL_COVERAGE.md`, `docs/MIGRATION_fastmcp3.md`, `AGENTS.md` | Replaced current guidance; obsolete broad-roadmap/migration/coverage docs removed |

The original MIT `LICENSE` is unchanged. Original SDK-derived prefix-file notices
remain in git history with their source; those files are not shipped in the new
runtime. No existing AV PIO definition is modified, generated, renamed or copied.

## New/replacement implementation files

`pio_test/{schema,wire,paths,windows_acl,transport,mcp_stdio}.py` handles exact
schema/transport. `pio_test/{authorization,engine}.py` enforces authority.
`pio_test/{operations,inspection}.py` contains bounded operations and owned-child geometry/text inspection. `pio_test/{vw_adapter,menu}.py`
provides the gated VW boundary. `pio_test/audit_log.py` records metadata only.
`pio_test/{__init__,errors,prepare}.py` contains shared support and explicit
non-installing file preparation. `mcp-server/vwx_mcp_server.py`,
`vwx-plugin/{BridgeStart_MenuCommand,vwx_pump}.py`, `bridge/vwx-mcp.bat` are the
replacement/disabled entrypoints. `native/document_lifetime.hpp` and
`native/test_document_lifetime.cpp` are portable policy source/tests only.
`tests/{support,test_restrictions,test_transport,test_paths,test_mcp,test_inspection,test_prepare}.py` plus
`tests/__init__.py` implement offline checks. `.gitignore`, `requirements.lock`,
`mcp-server/requirements.txt` and the current documentation complete the manifest.

## Unresolved limitations — review blockers

1. **Native arming intentionally fails.** `pio_test/vw_adapter.py:NativeProof`
   has no VW2026 document lifecycle listener, supported regeneration-completion
   observer, validated field codec, Linear creation adapter or verified transform
   extent checks, owned-child geometry/text metrics or autonomous scheduling. This is remaining implementation, not merely a checkbox/test.
   Neither `GetFPathName` nor a marker establishes lifetime. `native/` tests do not
   prove SDK notification delivery or active-document behavior.
2. **Windows DACL code and real junction handling require Windows validation.**
   `windows_acl.py` is a read-only ctypes implementation; Linux tests cover POSIX
   modes and simulate the reparse attribute. Actual NTFS/Win11 checks are pending.
3. **No synchronous-reset assumption.** If VW only provides queued reset in this
   context, local integration must implement a bounded pending/completion phase
   across genuine menu invocations, with the same identity and no repeated reset.
   Do not use sleep, a fake completion flag, timer or PIO event-mode changes.
4. **Untrusted local code still runs with user privileges.** Allowed PIO scripts
   themselves can execute arbitrary code and affect the document/files/settings.
   Names/parameter schemas do not sandbox them. Same-user processes can read keys,
   alter code and race path checks. Administrators can override ACLs. The root
   must actually contain disposable drawings; the bridge cannot infer business
   importance from bytes. No production directories belong in configuration.
5. **No rollback or crash containment.** A failed/slow native PIO can crash/hang
   VW or leave untracked/partial effects before returning a UUID. Automation
   quarantines and stops; the operator reviews the drawing. No silent retries.
6. **MCP subset/interpreter coverage.** New stdio implementation is intentionally
   small, not the full SDK. Standard framing/handshake/exposure tests pass; the
   chosen local MCP host must be checked. Python 3.9 grammar is checked, but the
   vendor's embedded interpreter has not executed this code in cloud.
7. **UI/geometry not demonstrated.** Private AV implementations are unavailable.
   Fake tests assert restriction logic, not geometry, label placement, physical
   offsets, class inheritance, grip usability, source hot reload or native timing.

## Evidence sources

Primary implementation evidence is the exact base revision and its full recorded
inventory. The baseline `vs_index.json` records `GetFPathName`, GetRField/SetRField,
UUID/parametric record APIs, CreateCustomObjectN and MirrorN; that is an upstream
SDK-derived index, not independent proof of VW2026 behavior. Treat candidate
adapter calls as local-review targets. Public official reference consulted:
[MCP 2025-06-18 stdio transport](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports).
The official Vectorworks scripting repository was identified, but individual
function-page retrieval failed in this environment; no invented SDK API is used
to fill the missing lifetime/completion proof.
