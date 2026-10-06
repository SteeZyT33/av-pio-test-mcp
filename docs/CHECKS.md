# Offline verification record

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
