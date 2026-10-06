# Native implementation gates and local acceptance

**Not executed in cloud. Not ready to arm natively.** The AV development package
is private/unavailable here and must not be uploaded or recreated. Windows 11
with the undeployed VW2026 installation is the target; no VM is required. Tests
must use disposable saved drawings under a dedicated test root and the user's
locally created definitions. Keep all evidence free of production drawings/code.

## Required source work before enabling native operations

The narrow Post adapter is implemented in `pio_test/native_proof.py`; its
separate internal SDK observer has compiled offline. This does not complete the
matrix below. Review [the Post contract](NATIVE_POST_ADAPTER.md), then verify
native notification delivery, menu nesting, reset/child freshness and coordinates
before accepting that milestone. Callout, transformations and automatic pumping
remain unsupported. Never bypass evidence with configuration switches.

| Gate | Required evidence / implementation |
| --- | --- |
| Exact saved full path | Verify `vs.GetFPathName()` in the actual VW build, including unsaved documents, same-name documents and save-as. Match OS-canonical path exactly, not basename/suffix. Reject uncertain/network/escaped paths. |
| Runtime document lifetime | Locate/document supported SDK document identity and complete open/close/activation/change notifications. Maintain a CSPRNG process/session lifetime token and invalidation generation; no persisted marker/UUID/handle alone. Detect close/reopen with pointer reuse, switches away and back between pumps, listener teardown, undo/redo and save-as. Unknown/missed events revoke. Use native notifications only for state invalidation, never for Python/document mutation. |
| Object lifetime and fixture | Verify actual parametric record universal name and UUID resolution in the bound document, live instance ownership and direct synthetic design-layer parent, never wall/container/reference/sheet objects. Prevent replacement/undo/reuse from adopting foreign objects. Preflight the empty initial `AV-MCP-TEST` layer/class; reject missing/ambiguous metadata, unsupported units/scale or wrong active layer. |
| Menu context | Independently confirm that only VW's own Python MENU-COMMAND runner reaches operations. Demonstrate no native raw Python-engine, timer, OnIdle, socket thread or palette path. The chosen template follows the locally investigated boundary but cloud mocks do not prove its native behavior. |
| Definitions/fields | Check exact universal names/types/catalog from native metadata and operator configuration. AV Post is Point PIO; AV Callout is Linear PIO. Event-Based OFF, Reset on Move/Rotate ON; no init/widget/button/state-change notifications. Fail before mutation on metadata mismatch. Do not modify/install definitions. |
| Typed native field codec | Validate booleans, integers, finite Reals, coordinate-unit parsing/serialization and exact text/enum roundtrip in inches and mm. `SavedControlX/Y` are physical inches stored as Real, not coordinate fields. Use separate conversion paths. No eval/exec or payload imports. |
| Creation/endpoints | Prove returned handle/UUID is newly created by this operation; post uses a candidate `CreateCustomObjectN` call. Implement supported **Linear** Callout creation with distinct start/end/length and verify native readback. Never treat elbow `ControlPoint01X/Y` as the linear endpoints. No guessed `LineLength` field writes. |
| Regeneration completion | Implement `regenerate_completed` using evidence that ordinary regeneration actually finished. Readback only afterwards; a queued `ResetObject` return is insufficient. Preserve errors and record completed/partial state. Measure `vw_ms` inside VW around the actual native regeneration interval. If completion is deferred until the menu returns, add a bounded two-phase continuation with retained identity/ownership and a fresh menu invocation—no repeated reset, sleeps, timer mutation or fake proof. |
| Owned child geometry/text | Implement NativeProof.geometry_frame/describe_child using supported native APIs, including nested transforms and real text placement/metrics. Validate FInGroup/NextObj/GetParent behavior and empty-group parent leaks. Return only bounded owned descendants and actual native Callout endpoints. No broad document queries or export. |
| Autonomous scheduling | Identify a documented/supported mechanism that actually enters the VW Python menu-command execution context with current lifetime identity. Manual pumping is interim; no claim of a completed autonomous loop. Never infer safe scheduling from fake vs, a main-thread callback or a guessed SDK method. |
| Geometry/transform extent | Verify candidate HMove/HRotate/MirrorN semantics locally, including reflection, returned handle and no replacement. Bound resulting model extents, not just input offsets; return/record native placement/endpoints for acceptance. Do not silently create duplicates. |
| SDK/compiler | Build any new observer from source with the operator's licensed VW2026 SDK and MSVC/Windows SDK. Record versions/hashes, enable buffer-security checks, review notification lifetime/reentrancy and ABI signatures. No downloaded opaque binaries or post-build copy/install steps. |
| Filesystem | Verify ctypes ACL inspection and failure modes on Win11, current-SID ownership, protected DACL and child inheritance; reject other users, null/unsupported DACLs, real junctions/symlinks, hardlinks, ADS/UNC/mapped drives and filename tricks. No ACL change is automatic. |

`native/document_lifetime.hpp` is a portable lifecycle policy model, not an SDK
adapter. The C++ test checks invalidation, reused pointer IDs and process-token
changes only. A provider that just returns that model's state without reliable
SDK events is **not** acceptable.

## Local matrix after the gates above are implemented

Record VW build, Python, OS/SDK versions, PIO source revision (private identifier
only), units, layer scale, native operation/reset timing, observed geometry,
returned fields and visible errors. Never publish private source or screenshots
containing company work. Mark each row PASS/FAIL/BLOCKED with local evidence.

Run the geometry/placement rows for **inches and mm**, at design-layer scales
**1:24, 1:48 and 1:96**. Include rotations 0°, 30°, 90°, 180° and 270°, reflected
across horizontal, vertical and diagonal axes, then rotated after reflection.

| Scenario | Actions and required observations |
| --- | --- |
| Positive/negative identity | Arm exact saved test path; reject unsaved doc, no doc, other path with same basename, different active doc, copied drawing/marker and same-path reopen. Queue a job, switch away/back or close/reopen, then pump: zero new effects. Replay old jobs after restart: zero effects. All reads/status use the same checks. |
| AV Post physical geometry | Each exact PostSize catalog value; ShowMode `Post` and `Trmr + King`; StudSize 2x4/2x6/2x8; counts 1, typical, 20; KingSide Left/Right/Both; Rotate90 both. Geometry remains model-sized across layer scales. Invalid sizes/spaces, 0/negative counts and production tools reject before creation. |
| AV Post dev5 mixed assemblies | Fresh operator-updated definitions/objects with KingSize present. Test StudSize 2x4/2x6/2x8 independently against small/large KingSize choices; built-up KingSize=2x6, KingStuds=2; large KingSize=6x6, KingStuds=1; counts 1/2/20 per side and Left/Right/Both. Kings flank centered trimmers with touching side faces and a common depth centerline, with independent width/depth. Rotate90 rotates the whole assembly. Leader attaches to central trimmers and clears surrounding kings under all tested rotations/reflections. No built-up KingSize strings. |
| AV Post two-block landing | Universal Reference/Notes stay unchanged, displayed as Note above leader / Note below leader. Post description plus Reference above, Notes below. Horizontal landing fits the maximum measured text width, with 0.06 paper-inch gaps. Control point is the sloping-leader/landing junction. After a real mouse drag and separately after programmatic CP edits, change either text block, text size, scale and source revision: manual junction stays fixed while landing resizes. Check upper/lower text metrics and gaps through owned-child snapshots and native UI at all rotations/reflections. |
| AV Callout native line | Circle/Square/Hexagon/Diamond; UseElbow both. Create differing native line lengths/directions, inspect true start/end/length and orientation in native UI; move the endpoint and verify separately from elbow. Zero-length endpoints reject. Reflection/rotation must preserve intended endpoint/elbow relationships. |
| Text | Empty, typical and 512-character fields; long text and real two-line Callout/Line2; Reference/Notes, ShowLabel both, TextSize at bounds and typical. Confirm printed text points, no clipping or accidental text-as-code behavior; visible native errors remain visible. |
| Automatic placement | New instances, ordinary redraw, text edits and each scale. Read LabelInitialized/LeaderAutomatic or ElbowInitialized and PlacementScale without writing them. One-shot ResetLeader/ResetElbow clears only after successful redraw. |
| Programmatic control points | Set allowed CP X/Y explicitly in document units, regenerate, edit text, regenerate and hot reload source. Confirm CPs and physical-inch SavedControl snapshots behave as intended. These are parameter-edit tests, **not evidence of mouse-grip usability**. |
| Actual mouse-grip dragging | Manually drag leader/elbow handles in the VW UI at multiple rotations/reflections/scales. Check grip selection, cursor feedback, axis behavior and placement. Ordinary redraw, text edits and source reload must preserve the manually chosen offset. For Callout distinguish endpoint grips from the elbow grip. |
| Scale preservation | Start with genuinely manually dragged placement, change synthetic layer scale 24→48→96→24 manually, redraw. Printed/manual offsets persist; SavedControlX/Y physical inches stay consistent; CP values convert in document units; actual post geometry stays model-sized. Check automatic placement separately. |
| One-shot placement reset | Manually move a handle, set only ResetLeader/ResetElbow true, complete redraw, observe expected automatic reposition and Boolean clearing. Next redraw must not reset again. Do not write initialization flags/internal snapshots. |
| Class inheritance | Synthetic fixture class, changed attributes manually, inherit-by-class behavior of PIO/children, ShowLabel variations. No production classes/layers touched. No class/layer deletion or document-wide scans in test interface. |
| Source hot reload | Use existing private bootstrap unchanged. Reload sources with manually positioned instances and long/two-line text present; ordinary regeneration must preserve user placement. No Event-Based/widget/init/button/state-change dependence. The bridge modules/ownership are not reloaded automatically. |
| Undo/redo/save/reopen | Manual undo/redo must invalidate session authority; saved/reopened same path requires fresh arm and must not adopt old UUIDs. Inspect PIO persistence manually after save/reopen, including manually dragged handles and reset flags. The interface does not save or invoke Undo/Redo by menu name. |
| Owned cleanup/foreign objects | Mix session-created PIOs with manually created allowed PIOs. Cleanup explicit owned list only; other objects unchanged. Modify actual record/layer/lifetime and verify rejection. Production AV Beam/AV Beam Tool always reject. |
| Error/timeout | Native PIO errors, failed readback, modal dialog and slow regeneration: retain visible dialog, report partial/uncertain state, no mutation retry or claimed-job replay. Cancellation never reports rollback. Verify client-crash uncertainty survives restart. |
| Hundreds of objects and timings | Build 100, 250, then up to 500 owned objects in bounded operations, and reset/read in batches ≤25 objects × ≤4 iterations. Measure p50/p95/max and total **inside-VW completed regeneration durations** separately from IPC/manual wait. Report object count, memory/UI responsiveness and errors. Adjust a suite downward if 30-second job TTL is exceeded; never raise bounds silently or auto-repeat timed-out batches. |

There is no pass threshold invented for native speed or stability. Establish a
baseline on the local build and compare changes. A passing matrix does not make
arbitrary native PIO code safe or isolate it from other files/processes.
