# Implementation status and local handoff

The latest local follow-up adds default-OFF native operator controls, local-only
Enable/Disable/Status commands, control-epoch enforcement before IPC claim and
throughout armed operations, and lazy notification registration from explicit
Enable rather than extension construction. It adds no cloud runtime, listener,
automatic arming, startup service or process killer. See OPERATOR_CONTROLS.md.
Complete Windows verification under default TEMP: 98 run / 97 pass / one POSIX
skip; all four C++ policy tests and the internal SDK observer build pass. The
two Windows fixture-only fixes preserve runtime restrictions. Native installation
is coordinated separately; actual menu/PIO acceptance remains pending.

## Native Post branch update

`codex/native-post-adapter` is based on the cloud Windows fixture fixes at
`f0444e5492e49516ce9d12fb235e47b7dd9689ff`. The table below records the original
cloud handoff; this update supersedes its unimplemented-Post statements.

Implemented: fixed native observer ABI, real Python menu-context checks, exact
field types/catalogs and codecs, Point Post creation, bounded flat child/text
readback, native reset submission with fresh child identities and later-menu
confirmation. Failed later confirmation quarantines prior uncertain mutation.
The SDK-independent menu/lifecycle policy is shared by the tested policy and the
internal observer. The internal observer compiled against official SDK2026 commit
`0b3ec438558c264d54b190879ff86049b0e697de`; SDK-dependent source/builds remain
private for licensing review. No native plugin was installed or loaded.

Windows offline verification: 88 tests run, 87 pass, one POSIX-only skip;
Python 3.9 grammar passes. Both C++17 policy tests compile/run under MSVC with
warnings treated as errors and assertions enabled. These checks include an
isolated stdio exposure subprocess and a real Windows junction rejection, but
no connection to VW. See CHECKS.md for provenance.

Still required: source/file-manifest review, effective user-folder/credentials
and menu/Point definition setup, then real VW2026 create/change/reset/later-read
calibration. Notification ordering, nested native menu context and actual geometry
coordinates are not proven by offline tests. Linear Callout, transforms,
nonzero placement, multi-reset named cases and automatic pumping remain blocked.
The concrete first milestone is documented in NATIVE_POST_ADAPTER.md. A running
process or desktop drawing operation would not prove this MCP path works.

Cloud branch: `codex/pio-testing-only`, based exactly on
`0a2f554a15ddddf0d43dc9d251d90a42146c9363`, fork only.

| Item | State |
| --- | --- |
| Broad escape routes/resources/native auto-dismiss/installers removed | Implemented; audit and complete baseline file inventory recorded |
| Stdio, shared schema, authenticated file IPC, replay/expiry, private paths/ACLs, uncertainty tombstone | Implemented; offline adversarial checks recorded in CHECKS.md |
| Exact saved-path + runtime lifetime/generation + bridge/session binding | Core enforcement implemented/tested with fake identities; supported native identity provider remains unimplemented |
| Created-UUID ownership, actual record/lifetime checks, typed fields, partial-failure quarantine | Core implemented; native preflight/type codecs/completion remain blocked |
| Owned-child geometry/text/placement snapshots | Bounded traversal/schema implemented; native extraction/metrics/transform evidence remains blocked |
| AV Post dev5 KingSize and corrected PostSize strings | Implemented; no private definitions or PIO implementation copied |
| Native ABI, full-path/lifecycle events, completed regeneration, Linear creation, Win11 ACL/junction behavior | Must be implemented/reviewed and accepted locally against supported VW2026 APIs |
| Manual per-job menu pump | Review template supplied; no installation; interim milestone only |
| Complete autonomous private edit→test→inspect→iterate loop | Not complete; supported scheduling and native integration are blockers |

The independent local prerequisite/acceptance agent should review this draft's
gates before installing anything. Nothing in cloud changes VW settings, native
definitions, private source, company files or the user's existing hot reload.
No live MCP connection or native deployment was performed here.

Native definitions are created/updated by the user, including the dev5 KingSize
field, and fresh scratch PIOs must be used. Source edits stay with the local
agent in the private checkout. This restricted bridge never writes source,
generates definitions, exposes generic scripting or exports arbitrary files.

Start local follow-up at `docs/NATIVE_ACCEPTANCE.md`. In particular, do not replace
NativeProof with a flag acknowledging risk: it must implement actual supported
runtime evidence. If a supported completion/scheduling/lifetime mechanism cannot
be established, leave the corresponding operation blocked and report it.


The local agent “Stand by for directions” now owns native adapter/SDK
implementation on the separate `codex/native-post-adapter` branch. This cloud
follow-up changes only test fixtures and documentation on `codex/pio-testing-only`;
it does not duplicate or incorporate that native work. Native failure gates
remain in place until actual supported implementation and calibration. The
Windows reviewer trial and complete Linux rerun are distinguished in CHECKS.md.
