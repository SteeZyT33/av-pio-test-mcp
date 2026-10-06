# Offline verification record

Date: 2026-10-06. Fork base: `0a2f554a15ddddf0d43dc9d251d90a42146c9363`.
Environment: Linux, CPython 3.12.14, GCC 13.3.0. No Vectorworks/SDK or private AV
PIO code was available. No installation, live MCP connection or native plugin
build/deployment was performed.

| Command/check | Result |
| --- | --- |
| `python -m unittest discover -v` | 70 tests run: **69 passed, 1 skipped**, 0 failures/errors; 0.514 s on the recorded final run |
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
correct geometry/text/grips. NativeProof is intentionally unavailable. The local
implementation and acceptance blockers are listed in NATIVE_ACCEPTANCE.md and STATUS.md.
