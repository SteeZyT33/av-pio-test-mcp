# AV PIO test-only MCP — draft, native acceptance pending

Restricted local test harness for **Vectorworks 2026 / Windows 11**, forked from
vicquick/vwx-mcp at `0a2f554a15ddddf0d43dc9d251d90a42146c9363`. MIT attribution is
retained in [LICENSE](LICENSE). No company drawing or AV PIO implementation is included.

**This draft has not passed live PIO acceptance.** The Post adapter now implements
typed native fields, Point creation, bounded flat geometry/text inspection, and
reset submission followed by confirmation in a later supervised menu invocation.
It requires a separate SDK observer; missing functions or an unverified native
menu scope reject before document access. An internal observer was built locally
against the pinned official SDK2026; its SDK-dependent source and binaries remain
private under the SDK license. Nothing has been installed or connected to VW.
See [the Post contract](docs/NATIVE_POST_ADAPTER.md) and
[the acceptance gates](docs/NATIVE_ACCEPTANCE.md).

## What changed

The broad upstream server/commands, socket bridges, toolset restoration, live
resources, script execution, native palette/timer/hotkey/error-dismiss code,
administrator installer and runtime pip bootstrap were removed. Git history
retains their original source. The replacement has ten fixed tools:

| Tools | Scope |
| --- | --- |
| `test_status`, `test_arm`, `test_disarm` | Status and explicit ephemeral test authority |
| `test_create` | Native milestone: AV Post at origin zero, rotation zero; Linear AV Callout explicitly unsupported |
| `test_read`, `test_set_parameters`, `test_regenerate` | Owned fields and flat child metrics; mutation returns pending, later read confirms current fresh children |
| `test_transform` | Schema bounded; native transforms await calibration and reject before mutation |
| `test_case` | Schema bounded; native multi-reset cases await continuations and reject before mutation |
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
g++ -std=c++17 -Wall -Wextra -Werror -pedantic native/test_menu_lifecycle.cpp -o /tmp/av-pio-menu-test
/tmp/av-pio-menu-test
git diff --check
```

Tests use a record-store double, not the private AV implementations. They do not
establish native stability, correct geometry, grip usability, or SDK compatibility.
No VM is required for subsequent local acceptance on the undeployed VW2026 install.

- [Audit and affected files](docs/AUDIT.md)
- [Protocol and lifecycle](docs/ARCHITECTURE.md)
- [Dependency/deployment manifest and explicit removal steps](docs/DEPLOYMENT.md)
- [Local native matrix and remaining implementation](docs/NATIVE_ACCEPTANCE.md)
- [Supervised Post adapter and fixed native ABI](docs/NATIVE_POST_ADAPTER.md)
- [Recorded offline results](docs/CHECKS.md)

Do not install an old VwxBridge binary alongside this harness. This code does
not sandbox PIO code or other processes running with the same Windows identity.
