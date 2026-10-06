# Restricted protocol and lifecycle

The external server uses newline-delimited MCP JSON-RPC over stdio (the explicit
2025-06-18 subset), with ten tools and no resources, prompts, tasks, HTTP server,
socket bridge, transport fallback, tunneling or telemetry. Legacy environment
variables cannot expand its exposure. It does not use FastMCP inside or outside VW.
Client interoperability beyond the exercised handshake still needs a local check.

## Modules and authority

| Files | Responsibility |
| --- | --- |
| `schema.py` | One schema for tool exposure, command allowlist, writable fields, diagnostics and bounds |
| `wire.py`, `paths.py`, `windows_acl.py`, `transport.py`, `mcp_stdio.py` | Strict parsing, authenticated transport, confinement, stdio |
| `authorization.py`, `engine.py` | Session binding, native document lifetime and object ownership |
| `operations.py` | Explicit bounded PIO operations, partial failure, completed-reset readback |
| `inspection.py` | Bounded traversal of owned PIO descendants, typed geometry/text snapshot |
| `vw_adapter.py`, `menu.py` | VW API boundary and manual Python menu-command lifecycle |
| `audit_log.py` | Bounded metadata-only audit log |

An arm request carries a relative saved `.vwx` path under an operator-configured
test root. No drawing is created, opened, activated, saved, imported or exported
by this interface. Canonical full-path equality is necessary, and insufficient:
authority also binds a native process/document-lifetime token, invalidation
generation and runtime synthetic fixture identity. The native observer must
invalidate on switch-away even if the user switches back before the next pump,
close/reopen, save-as, undo/redo, listener loss or uncertain lifecycle events.
The core checks identity on every armed command, including status/read/disarm,
and before/after individual operation stages. Uncertainty revokes authority.

No drawing marker is currently used. A future marker could identify the intended
fixture, but must never serve as the lifetime proof: copies preserve markers and
UUIDs, and native handles can be reused. `native/document_lifetime.hpp` models
invalidation only; it has no SDK hooks and supplies no evidence about real VW.
`NativeProof.identity()` therefore fails closed today. Configuration cannot
turn that failure into success. A native provider is a reviewed source change,
never a payload/import/module-name setting.

Owned UUIDs are recorded only after test creation, with actual allowed parametric
record and native object-lifetime identity. Each operation must resolve the UUID,
verify the actual record and lifetime and verify direct membership in the bound
synthetic design layer. Arbitrary handles and preexisting PIOs are never adopted.
Disarm/restart loses ownership; old objects are left for operator review. Cleanup
deletes only an explicit owned UUID list, no selection/criteria/delete-all calls.

## File IPC

The configured private directory contains only fixed names: `key.bin`,
`bridge.json`, `request.json`, `claimed.json`, `result.json`, `client.lock`,
`pump.lock`, `uncertain.json`, `audit.jsonl` and corresponding temporary files.
Operator-only preparation also writes `config.json`. Correlation IDs are checked
as 32 lowercase hex characters and never become filenames. Keys are 32 random
bytes; bridge/session nonces are independently generated 32-byte tokens. They
are not logged or returned in MCP tool content.

Canonical JSON is signed with HMAC-SHA256. Kind-specific exact field sets and
MAC domains distinguish descriptors, requests, results and uncertainty records.
Both ends verify response/request authentication and bridge/correlation/sequence
binding. Requests also bind session/document fingerprint, issue time and expiry
(at most 60 seconds; client default 60). Duplicated JSON keys, NaN/Infinity,
unknown fields and invalid types are rejected. No prefix/getattr command dispatch.

The MCP stdio envelope accepts the standard optional `_meta` object. Its
request `progressToken`, when present, must be a string or finite number.
Metadata is discarded before the existing method/command parameter checks;
it is never forwarded to IPC/tool arguments, used as authority, logged or
echoed in results. The 64 KiB frame limit and exact tool allowlist remain intact.
See the [MCP 2025-06-18 request schema](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/schema/2025-06-18/schema.ts).

The in-VW pump claims one fixed request slot by rename. Before executing it,
it reserves increasing sequence and correlation ID in runtime memory. Each runtime
has a fresh bridge nonce. Claimed jobs left by a crash block further operation;
they are never replayed. A new bridge rejects envelopes from the previous nonce.
Only one client slot and one pump invocation can hold their exclusive lock.
Residual locks fail closed; there is no automatic stale-lock removal.

The client writes an authenticated uncertainty tombstone **before** publishing a
job. It removes that tombstone only after an authenticated result. A timeout or
client crash leaves it in place across client restarts. Subsequent mutations are
refused. `test_status` may collect a late result, but cannot clear uncertainty or
retry the mutation. Local review and an explicitly fresh IPC directory/session
are required. Cancellation cannot interrupt an in-flight PIO and is not rollback.
There is no automatic mutation retry, including after ambiguous transport errors.

The pump is invoked manually from VW's own Python MENU-COMMAND runner, one job
per invocation. There is no background read pump either. VW may display errors;
nothing dismisses dialogs or presses keys. A hung/resetting PIO may block the
menu invocation. Timeout quarantines external automation; it does not stop VW.

## Parameter and workload rules

- Exactly the supplied AV universal names. Correct catalog begins `(2) 2x4`,
  `(2) 2x6`, `(2) 2x8`, `(3) 2x6`; no trimming or alias rewriting.
- AV Post 0.1.0.dev5 adds only `KingSize` (default `2x6`), with exact choices
  `2x4, 2x6, 2x8, 4x4, 4x6, 4x8, 6x6, 6x8, 6x10, 6x12, 8x8, 8x10, 8x12,
  10x10, 10x12, 12x12`. `StudSize` displays “Trimmer size”; `KingStuds`
  displays “King members per side” and counts individual selected-size members
  per side. Built-up kings use KingSize=`2x6`, KingStuds=2, never a built-up
  KingSize string. Definitions must be updated locally and test objects created
  fresh; the bridge does not migrate or edit definitions.
- Trimmers/KingStuds integers 1–20; text at most 512 characters; TextSize
  0.1–144 points; finite coordinates within ±100,000 document units; rotation
  within ±360°. Native preflight must also bound final extents after transforms.
- Read-only initialization/automatic flags and PlacementScale/SavedControlX/Y
  cannot be set by clients. SavedControl values are **physical inches in Real
  fields**. ControlPoint coordinates are **document units**; no shared conversion.
- Callout creation requires distinct native linear endpoints; elbow CP fields
  are separate. Native endpoint creation/length/readback remain unimplemented.
- At most 500 owned objects; 25 UUIDs per case/cleanup; 4 iterations, maximum
  100 object-iterations. No client scripts or list of arbitrary commands.
- Reset completion requires native evidence before readback. `ResetObject`
  returning, identical parameter values and elapsed waiting time are insufficient.
  ResetLeader/ResetElbow must be false after the proven successful redraw.
- Results preserve stage, command, created IDs and completed count after partial
  failures. Raw exception strings, paths, credentials and payload text are never
  logged. The log stops growing near 60 KB; it is not automatically rotated.

Named cases are `regenerate_owned`, `text_roundtrip` (fixed two-line test text,
does not restore original text), and `placement_reset`. They return per-reset
timing supplied **inside VW by the native completion observer**, not bridge wall
latency. Fake timings in tests are deliberately synthetic. Actual grip dragging,
scale-preserved manual offsets and native geometry require local acceptance.


## Owned geometry/text inspection and autonomous workflow

`test_read` and completed mutation readback include `geometry` from
`inspection.py`: a complete bounded snapshot or an explicit failure, never a
silently truncated success. Limits are 128 descendants, depth 4, 64 vertices per
polyline, 1024 characters per text item, 4096 total text characters, and 32 KiB
serialized geometry. It traverses only the owned PIO's children. Every direct
parent is checked before describing or advancing a handle; cycles and foreign
handles leaked by an empty-group iterator reject. No document-wide traversal,
selection, arbitrary criteria, record enumeration or export is introduced.

Snapshots contain group, line, polyline/polygon, ellipse/arc and text primitives,
snapshot-local ordinal paths, the owned children's actual class names, and text
content, origin, baseline direction, size in points, measured width/height and
bounds. The native adapter must normalize nested group/text geometry into the
root PIO's local document-unit frame. `frame.pio_to_document` is the six affine
coefficients `[a,b,c,d,tx,ty]`, where `(x,y)` maps to
`(a*x+c*y+tx, b*x+d*y+ty)`. Frame includes inches/mm, layer scale and actual native
Callout linear endpoints separately from elbow CP fields. Unsupported primitives,
nonfinite metrics or incomplete native observations fail rather than create a
false assertion pass. Native extraction/metrics are still a hard implementation
gate; the portable reader tests do not prove real text metrics or transforms.

These data permit a local agent to assert landing endpoints, text widths and
paper gaps without unrelated document queries. For physical spacing, convert a
paper-inch distance to local model units as `inches * layer_scale`, then multiply
by 25.4 for mm. Compare with an explicitly chosen local tolerance; do not treat a
rotated screen bounding box as a text width. Derive the upper/lower text roles
from content/placement, not unverified child order or a persistent child UUID.

The target loop is local private-source edit → restricted scratch creation/update
→ proven completed regeneration → owned geometry/text inspection → report/iterate.
Private source editing stays with the local agent's filesystem capabilities and
existing AV bootstrap, outside this public bridge; no arbitrary source-file write
or code execution tool is added. The user creates/updates the one-time native
PIO definitions. A manual menu invocation per operation is only an interim
milestone. Autonomous scheduling requires a separately reviewed supported way to
enter the valid native execution context with lifecycle identity; no scheduling
API is invented and no automatic keystroke/timer workaround is supplied.
