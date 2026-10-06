# Offline verification record

## MCP request metadata compatibility (2026-10-06)

`python -m unittest tests.test_mcp -v` passed all **11 checks** on Windows
CPython 3.12.7. This includes metadata-bearing discovery and real subprocess
initialize/initialized/tools-list/resource-list frames, exactly ten restricted
tools and empty resources, malformed metadata/progress-token rejection, strict
extra command/method argument rejection, metadata isolation from client calls
and results, unchanged oversized-frame closure, and Python 3.9/source-boundary
checks. The optional reserved `_meta` object is normalized only in the external
MCP envelope; no native/Pump/gate, IPC, installed file or tool schema changed.
The installed Codex app's actual discovery must be repeated separately by the
lead after review. These offline tests submit no Vectorworks jobs.

## Manual request window follow-up (2026-10-06)

The external Client now defaults to a 60-second request window, matching the
existing wire maximum. On Windows CPython 3.12.7, all **19 transport tests**
passed, including the two new checks: an actual signed default request validates
just before 60 seconds and expires just after it; invalid/nonfinite timeouts and
timeouts above 60 seconds remain rejected. The Python 3.9 grammar/source-boundary
check also passed. Tests use disposable offline fixtures and do not wait a real
minute or dispatch any native operation. Native Pump/menu/gates, installed files,
claim rules and no-retry behavior are unchanged.

Separate follow-up: `VwAdapter.blockers` remains a static list containing
`NATIVE_OBSERVER_REQUIRED`, even when a local native gate reports READY. This
list is not a dynamic observer probe. Its reporting needs separate review;
this timing correction does not remove blockers or claim native acceptance.

## Earlier verification provenance

Date: 2026-10-06. Fork base: `0a2f554a15ddddf0d43dc9d251d90a42146c9363`.
Environment: Linux, CPython 3.12.14, GCC 13.3.0. No Vectorworks/SDK or private AV
PIO code was available. No installation, live MCP connection or native plugin
build/deployment was performed.

| Command/check | Result |
| --- | --- |
| `python -m unittest discover -v` | 70 tests run: **69 passed, 1 skipped**, 0 failures/errors; 1.439 s on the recorded test-fixture follow-up run |
| Python 3.9 grammar gate in `SourceBoundaryTests` | Passed for all supported runtime/menu/entrypoint Python modules; not an execution test on VW's embedded Python |
| Real subprocess stdio handshake/tools/resources check | Passed under legacy HTTP/TCP/full-toolset/telemetry environment variables; exactly 10 tools, empty resource/template/prompt lists |
| `g++ -std=c++17 -Wall -Wextra -Werror -pedantic native/test_document_lifetime.cpp -o /tmp/av-pio-lifetime-test` | Compiled successfully with exit 0 |
| `/tmp/av-pio-lifetime-test` | Exit 0; portable lifecycle policy only, not SDK behavior |
| `git diff --check` | Exit 0, no whitespace errors |
| Tracked file inventory/source review | All 41 baseline files inventoried; broad native/plugin/deployment surface retired; MIT license unchanged |

The skipped test is actual Windows NTFS junction creation/rejection. Linux tests
reject symlink/hardlink escapes and simulate the Windows reparse attribute, but
do not establish Win11 filesystem/DACL behavior. Windows tests prepare only their
own new temporary directories with owner/SYSTEM ACLs; no user/VW folders are changed.

Full unittest output is [offline-checks.txt](offline-checks.txt). Restrictions
covered include unknown/production tools; typed values and exact dev5 catalogs;
read-only/unknown fields; foreign objects/records/fixtures; document switches,
same-name paths/reopen/copied identity; wrong auth/session/binding; fixed result
filenames; traversal/UNC/drive/ADS/reparse attacks; NaN/Infinity; replay/stale jobs;
claimed/unclaimed timeouts and durable no-retry behavior; partial failure/readback;
secret-free audit logs; exact MCP exposure; direct IPC bypass attempts; bounded
owned-child traversal, cycles/parent leaks/text/metric limits; safe explicit
preparation; and disabled legacy execution paths.

These tests use record stores, synthetic geometry and fake lifecycle/completion
signals. They do not recreate the private PIO implementation, establish native
stability, prove menu context/scheduling, measure native performance, or establish
correct geometry/text/grips. NativeProof was unavailable in that cloud baseline. The local
implementation and acceptance blockers are listed in NATIVE_ACCEPTANCE.md and STATUS.md.


## Windows test-fixture review follow-up

The independent local reviewer found that Python 3.12 `mkdir(0700)` can leave
explicit Administrators (`S-1-5-32-544`) and OWNER RIGHTS (`S-1-3-4`) grants on
new fixture directories. Removing inheritance and granting the current SID and
SYSTEM did not remove those explicit grants. `tests/support.py` now removes
those two grants, without recursion, only from freshly created disposable
fixture directories after granting the current SID and SYSTEM. Runtime ACL
validation and permissions are unchanged.

The claimed-mutation timeout test now arms with a 1-second budget, then uses a
0.5-second mutation budget and a 1-second fake create delay. This keeps Windows
permission-validation time out of the intended mutation-timeout scenario. The
ambiguous-timeout, exactly-one-mutation and no-retry assertions are unchanged.
The separate deliberately unclaimed-expiry test retains its original timing.

Validation provenance:

- Complete suite rerun in this Linux environment: **70 run, 69 passed, 1 Windows
  junction test skipped**, including all MCP enumeration/subprocess exposure
  tests. Full output above is refreshed for this run.
- User-relayed independent **private Windows trial** of the two fixes: **63
  selected tests, 62 passed, 1 POSIX-only skip**. The local agent did **not** run
  enumeration tests. This report was not independently reproduced on Windows
  here and must not be described as a complete Windows-suite pass.
- The new `icacls /remove:g` execution path cannot run on Linux. Windows fixture
  behavior beyond that reported trial, full Windows enumeration, and real
  VW2026/native/SDK behavior remain local validation work. No runtime permission
  check or native failure gate was weakened to obtain a test pass.

## Local native Post adapter verification (2026-10-06)

On `codex/native-post-adapter`, based on `f0444e5`, the Windows local agent ran
the complete suite with CPython 3.12.7: **88 run, 87 passed, 1 POSIX-only skip**.
This includes the real Windows junction check, native ABI/codec/flat-text contract
tests and an isolated offline stdio enumeration subprocess. Every disposable
fixture was contained under a dedicated temporary test directory; cleanup checked
that its resolved target stayed inside that directory. No Vectorworks connection
was used. Runtime files also parse under Python 3.9 grammar.

Both `native/test_document_lifetime.cpp` and `native/test_menu_lifecycle.cpp`
compiled and ran under MSVC v143 with C++17, `/W4 /WX`, and assertions enabled.
The separately maintained private observer compiled as x64 against the pinned
official SDK2026, using MSVC 14.44.35207 and Windows SDK 10.0.22621.0. Build output
and exact source/library/resource hashes are retained privately. No SDK files,
native artifacts, private PIO code, drawing, credentials or local configuration
are committed here. No observer install/load or native acceptance occurred.

Synthetic host-contract tests prove rejection and two-phase response behavior;
they do not prove SDK callback delivery, nested menu execution, native regeneration,
geometry semantics, performance or grip behavior. Those remain explicit live gates.

## Local OFF-control and lazy-observer follow-up

The complete Windows suite now runs **98 tests: 97 pass, one POSIX-only skip**
under the machine's actual default TEMP directory, with resolved containment
checked before recursive temporary cleanup. The test-only fixture base resolves
short Windows path aliases; the test-created `result.json` symlink is unlinked in
`finally` after the same REPARSE rejection assertion. Runtime path/DACL protection
is unchanged. Python 3.9 grammar still passes; no native VW was used.

Coverage includes default OFF, READY versus explicit ARMED, queued disable before
claim, epoch invalidation after re-enable, client/server reconnect, bridge restart,
document generation, broken IPC authentication, unresolved claimed-job shutdown,
pending reset uncertainty and disable during a blocked operation without rollback.
Last-published OFF status is explicitly distinguished from live native verification.

All four C++17 policy tests compile/run under MSVC /W4 /WX with assertions enabled:
document lifetime, menu lifecycle, native operator gate, and deferred registration.
The actual private observer uses those gate/deferred-registration classes and
compiles against the pinned official SDK2026. Extension construction does not
start callbacks; explicit local Enable activates them while OFF, with rollback
and active teardown. Private source assertions/build/resource hashes are retained
in the local manifest. No observer install/load or PIO acceptance is claimed.
