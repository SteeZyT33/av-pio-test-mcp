# Local PIO testing controls

The runtime is hosted only on the user's machine: external stdio MCP process,
authenticated local file IPC, and the reviewed native Vectorworks menus. Code
development elsewhere does not host the runtime. There is no network listener,
tunnel, cloud service, telemetry, Windows startup service or automatic arming.
No process-killing launcher is supplied; temporary native Disable is sufficient
to stop further PIO testing even when a client relaunches the stdio process.

## Operator commands and states

| Command | Behavior |
| --- | --- |
| Enable PIO Testing | Keep OFF during lazy observer registration and bridge initialization; enable only after successful initialization. READY requires a separate explicit arm of the exact saved scratch drawing. Repeated Enable revokes the previous session. |
| Disable PIO Testing | Revoke enabled state/control generation immediately, including old sessions and queued requests. Preserve all objects/drawings. If an operation is executing, request disable and acknowledge OFF only after it returns. |
| PIO Testing Status | Show actual native gate and current bridge authority state without dispatching a queued job or querying drawing geometry. Works without an armed drawing. Native fallback remains available if Python/IPC is unavailable. |
| AV PIO Test Supervisor | Execute one queued authenticated job through the fixed Python pump only while the native gate permits it. Does not enable or arm. |

| State | Meaning |
| --- | --- |
| OFF | Native testing authority is disabled. An earlier outcome may still be unconfirmed; OFF does not undo changes. |
| READY | Local gate is enabled, with no current armed scratch session. |
| ARMED | A current exact scratch session exists under the native control/lifecycle generation. |
| BUSY | A native operation is still executing. Disable cannot interrupt a synchronous call; a disable request waits for return. |
| UNCONFIRMED | A reset awaits later inspection, or a prior effect/startup/publication failure needs local review. This does not claim rollback or authorize retry. |

Native OFF is checked again before an IPC claim, after claim, in the in-VW
dispatcher, and throughout armed read/mutation/ownership guards. Authentication,
expiry, schema, session and document binding are validated before accepting a
claim. Changing the operator epoch revokes ownership and rotates the bridge nonce;
queued old requests cannot become valid after re-enable. No saved object is adopted.
Native callbacks also revoke document authority; local status can observe their
generation without reading a drawing. Each new Python bridge runtime forces OFF.
External server/client restart has no native enable/arm side effect.

Disable does not depend on a valid drawing, authenticated MCP request, IPC key
read, or successful IPC file write. The native menu switches OFF first. Python
revocation/publication is best effort afterwards; failures cannot reopen the
gate. An executing call can have partial effects before return, so uncertain
outcome and objects remain for inspection. Unconfirmed outcomes survive disable
and cannot be cleared by Enable or ordinary re-arm.

MCP `test_status` can return the last signed local OFF publication without queuing
a job; it labels that result `last_published: true` and
`live_status_verified: false`. This is not a live native query. Other commands
can reject from that publication as a convenience; native checks remain decisive.
The local Status menu is the independent native control. If its Python component
is missing or broken, it explicitly identifies native-gate-only status instead
of claiming a known ARMED state. The display acknowledgment never grants authority.

## Native initialization and one-time setup

Extension constructors only bind deferred callback functions. They neither
register notifications nor query a drawing. The SDK-independent
`DeferredRegistration` implementation used by the native observer is tested for
zero constructor/destructor side effects while inactive, explicit activation,
partial-failure rollback, no duplicate registration, and active teardown.
Enable is a genuine native menu handler; it holds OFF while activating the
supported SDK notification procedures. Failure rolls back and leaves OFF.

After source/build review, install only the new observer `.vlb` and `.vwr` in the
confirmed user Plug-ins folder, with Vectorworks closed by the operator first.
Do not hot-copy/load the plugin into a running instance or force-close it.
The user creates two separate unlocked Python MENU COMMAND definitions:

- `AV PIO Test Pump`: reviewed `BridgeStart_MenuCommand.py` template.
- `AV PIO Test Operator`: reviewed `Operator_MenuCommand.py` template.

Configure both templates with identical reviewed checkout/private config literals.
The native commands invoke only those fixed menu names. Add the native Enable,
Disable, Status and Supervisor entries manually to a development workspace,
preserving the original. Native credentials/enablement still require the operator.
No PIO definition, AV bootstrap, workspace, user-folder setting or security setting
is edited automatically. On the next native startup confirm Status OFF before
selecting Enable. Then explicitly arm and pump each scratch test request.

## Recovery and verification

If disabling during an operation, wait for its actual return and OFF acknowledgment.
Keep visible native errors/dialogs; do not force-kill VW, automatically undo, repeat
a timed-out mutation, delete a drawing, or assume disabling cancelled prior effects.
After an unresolved claim/crash, the next bridge starts OFF and refuses that
claimed slot. Review the scratch drawing and private evidence; use the explicit
fresh-runtime/private-IPC recovery procedure in DEPLOYMENT.md. Do not discard an
uncertainty tombstone to retry the original job. Temporary Disable and uninstall
are separate procedures.

Offline checks cover queued disable/re-enable, old sessions, client reconnect,
bridge restart, document generation, missing IPC authentication, claimed shutdown,
pending reset uncertainty and disable during a blocked operation without rollback.
The native gate and deferred-registration policy compile and run separately.
These checks do not prove actual VW menu dispatch, UI availability during a modal
native operation, notification timing, or PIO behavior; verify those locally before
claiming a working native MCP loop.
