# AV PIO test-only MCP — draft, native arming blocked

Restricted local test harness for **Vectorworks 2026 / Windows 11**, forked from
vicquick/vwx-mcp at `0a2f554a15ddddf0d43dc9d251d90a42146c9363`. MIT attribution is
retained in [LICENSE](LICENSE). No company drawing or AV PIO implementation is included.

**This draft is not ready for live PIO testing.** The stdio server, authenticated
IPC, schemas, authorization and test operations are implemented and exercised
offline. `NativeProof` deliberately rejects native arming until full-path/runtime
document identity, completed regeneration, typed VW field conversion and Linear
PIO creation and owned-child geometry/text metrics are implemented through supported VW2026 APIs and verified locally.
The portable C++ lifecycle model is not an SDK plugin. No native binary is built
or deployed. See [the acceptance gates](docs/NATIVE_ACCEPTANCE.md).

## What changed

The broad upstream server/commands, socket bridges, toolset restoration, live
resources, script execution, native palette/timer/hotkey/error-dismiss code,
administrator installer and runtime pip bootstrap were removed. Git history
retains their original source. The replacement has ten fixed tools:

| Tools | Scope |
| --- | --- |
| `test_status`, `test_arm`, `test_disarm` | Status and explicit ephemeral test authority |
| `test_create` | AV Post or Linear AV Callout only |
| `test_read`, `test_set_parameters`, `test_regenerate` | Owned fields plus bounded child geometry/text metrics; completed regeneration/readback |
| `test_transform` | Bounded move/rotate/mirror in place |
| `test_case` | Three fixed cases, maximum 100 object-iterations |
| `test_cleanup` | Explicit list of at most 25 session-created UUIDs |

AV Beam and AV Beam Tool are rejected at both entry and in-VW boundaries.
There are no MCP resources, arbitrary batch/scripting tools, exports, saves,
document switches, layer/class setters or PIO-definition editing routes.

## Development workflow and current milestone

The end goal is a complete local edit → create/change scratch PIO → regenerate →
inspect owned geometry/text → assert/report → iterate loop. Local source edits
stay in the private AV checkout using the local agent's filesystem tools and
existing bootstrap; this restricted MCP does not accept or write source code.
The user creates the native definitions and updates them for new fields, including
AV Post 0.1.0.dev5 `KingSize`, then creates fresh test objects. Definition creation
and migration are not automated here.

**Manual pumping is an interim milestone, not the completed autonomous workflow.**
The current design requires a human menu invocation for every queued operation.
Autonomous scheduling remains blocked on defensible supported native execution
context/lifecycle APIs. No unsupported scheduling API or hotkey workaround is
substituted. The independent local agent “Stand by for directions” is preparing
prerequisites/native acceptance; no cloud installation or cross-agent transfer of
private tool sources has been performed.

## Offline verification

No package installation is needed; the complete third-party dependency lock is
empty. Run from the checkout:

```sh
python -m unittest discover -v
g++ -std=c++17 -Wall -Wextra -Werror -pedantic native/test_document_lifetime.cpp -o /tmp/av-pio-lifetime-test
/tmp/av-pio-lifetime-test
git diff --check
```

Tests use a record-store double, not the private AV implementations. They do not
establish native stability, correct geometry, grip usability, or SDK compatibility.
No VM is required for subsequent local acceptance on the undeployed VW2026 install.

- [Audit and affected files](docs/AUDIT.md)
- [Protocol and lifecycle](docs/ARCHITECTURE.md)
- [Dependency/deployment manifest and explicit removal steps](docs/DEPLOYMENT.md)
- [Local native matrix and remaining implementation](docs/NATIVE_ACCEPTANCE.md)
- [Recorded offline results](docs/CHECKS.md)

Do not install an old VwxBridge binary alongside this harness. This code does
not sandbox PIO code or other processes running with the same Windows identity.
