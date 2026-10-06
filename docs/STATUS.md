# Implementation status and local handoff

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
