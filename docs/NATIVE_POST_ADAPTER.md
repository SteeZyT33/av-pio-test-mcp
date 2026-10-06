# First supervised native Post milestone

Implemented on `codex/native-post-adapter`, based on Windows fixture-fix commit
`f0444e5492e49516ce9d12fb235e47b7dd9689ff`. No live Vectorworks acceptance or
deployment is claimed. Public changes contain our Python adapter and our
SDK-independent menu/lifecycle policy. The SDK integration source, build project,
resources and binaries are internal; the bundled SDK license requires separate
review before redistribution. No private AV implementation is included here.

## Supported initial scope

Windows Vectorworks 2026 Update 7, actual `GetVersionEx()` build 879357;
saved disposable local drawing under the configured test root; active empty
`AV-MCP-TEST` design layer and existing `AV-MCP-TEST` class; Top/Plan; inches or
mm; scales 1:24, 1:48 or 1:96. AV Post must be an operator-created Point PIO with
the exact 20 public universal fields and popup catalogs in `schema.py`.
Event-Based OFF and Reset on Move/Rotate ON require native manager verification.
Neither definition creation nor manager settings are changed by the adapter.

Only Post placement at `[0, 0]` with rotation zero is accepted. Object matrix
must be the native identity matrix. Allowed field writes remain schema-bounded;
diagnostics stay read-only. CP X/Y use native dimensional parsing with explicit
document units; physical-inch saved-control diagnostics remain Real values.
Strings and popup values round-trip exactly, without trimming or coercion.

Flat direct children must belong to the fixture class. The adapter reads lines,
straight polygons (maximum 64 vertices) and unrotated/unmirrored text (maximum
1024 characters). Text origin comes from native text orientation; bounds and
width/height come from its actual native box under the verified local axes.
Traversal retains lifecycle/ownership guards and the existing 128-child and
response limits. Parent leaks, cycles, foreign classes, nested groups, curved
objects and unsupported types fail explicitly. No drawing-wide scan exists.

Linear Callout creation, nonzero placement, rotations/reflections, transform
operations, named multi-reset cases and automatic pumping reject before their
first mutation. They are remaining implementation/calibration work.

## Fixed internal observer ABI

The private SDK observer must supply exactly these three Python `vs` functions.
There is no configuration-selected provider, import path, DLL loader, script,
function name, caller-selected menu or generic native execution payload.
Each result is bounded JSON (at most 8192 UTF-8 bytes) with `abi: 1` and `ok`.
Failure contains no native exception text, private path or parameter content.

| Function | Required evidence |
| --- | --- |
| `AVPIOTestSnapshot()` | Saved full path, random process instance, lifecycle generation, random current fixture identity, actual supervised menu scope/invocation, native Top/Plan, fixture class and Post plugin availability |
| `AVPIOTestObject(handle)` | Actual Post record/type/direct fixture parent/class, native object-lifetime token and planar matrix, current invocation, last reset ticket and immediate-reset-return evidence |
| `AVPIOTestReset(handle)` | Only the verified owned Post scope; real synchronous SDK reset call, returned ticket/invocation and measured native call duration |

The native **AV PIO Test Supervisor** is a genuine SDK menu event sink. It enters
a bounded scope and invokes exactly **AV PIO Test Pump** once through the native
menu API. The Python side verifies `GetPluginInfo()` reports that exact menu and
that it is not executing within a PIO. Scope exits even after failure.
Reentrant entry and observer calls during a reset reject. A callback never runs
Python or reads/mutates the drawing.

The observer registers supported lifecycle, save/open/close, edit/undo and
environment callbacks and unregisters them before teardown. Identity combines
random instance/fixture tokens, callback generation, actual drawing/layer identity
and saved path. A path or handle alone is never sufficient. Document/environment
events always revoke. Edit/record/PIO-update/undo events inside the observer's own
menu scope retain continuity; foreign or delayed events revoke it. This policy is
tested offline but actual event ordering must be calibrated. If own delayed events
revoke every job, retain the gate and revise the supported continuation design;
do not suppress arbitrary future notifications.

## Submission and confirmation are separate

1. Queue `test_create`, `test_set_parameters` or `test_regenerate`; invoke the
   supervisor once before expiry. The observer performs the immediate reset.
   Python compares bounded direct-child UUID sets before and after the call.
   Empty output or any reused pre-reset child prevents a fresh-reset claim and
   quarantines the partially changed session.
2. A successful submission returns `completed: false`, `pending: true`,
   `next_action: test_read_in_later_menu_invocation`, `rollback: false` and
   `retry_safe: false`. `vw_reset_call_ms` measures the actual synchronous call;
   it excludes manual waiting and does not assert semantic geometry correctness.
3. Queue `test_read` for that owned UUID and invoke the supervisor again. It must
   be a later native invocation under unchanged identity. The reset ticket,
   synchronous-return evidence and fresh generated-child UUID set must still
   match. Fields must read back, one-shot ResetLeader must clear, and the actual
   polygon/label constituents must be present when required.
4. Success adds `regeneration.completed: true` with boundary
   `immediate_reset_and_later_menu_readback`. It explicitly reports
   `semantic_geometry_validation: false`. Compare measured geometry with the
   private tool specification and native visual result during acceptance.

A read in the same invocation reports `REGENERATION_PENDING` without resetting
again or quarantining solely for that early read. A later failed confirmation
quarantines prior uncertain mutation. No automatic retry, undo, sleep, dialog
dismissal, timer, keyboard invocation or raw Python-engine call is used.

## Required native acceptance before claiming working MCP

Review the exact internal source/build/file manifest first. The operator must
confirm the effective user Plug-ins folder, native plugin credentials or manual
enablement, both menu definitions and Point PIO settings. Do not overwrite any
existing plugin, bootstrap, workspace or drawing. Install only reviewed new files.
The internal build has no post-build copy step.

On a disposable saved fixture, initialize/arm through the supervisor, then prove
create → later read → field change/reset → later read → owned cleanup. Verify
Reference/Notes and 8.5-point text, native control points, fresh child UUIDs and
class inheritance. Run inches/mm and each supported scale before extending scope.
Manually switch/save/reopen/undo outside the menu and verify authority is revoked.
Keep native errors visible. Record source/build identifiers, timing and measured
geometry privately; compiling or offline test success is not live acceptance.

Supported native script context and host version APIs are documented in the
official [GetPluginInfo reference](https://github.com/Vectorworks/developer-scripting/blob/main/Function%20Reference/Functions/GetPluginInfo.md)
and [GetVersionEx reference](https://github.com/Vectorworks/developer-scripting/blob/main/Function%20Reference/Functions/GetVersionEx.md).
The official [2026 plugin credentials guidance](https://github.com/Vectorworks/developer-scripting/blob/main/Common/Tasks/Info/PluginCredentials.md)
describes the operator/developer enablement prerequisite. SDK-dependent evidence
and license review remain in the private local handoff.
