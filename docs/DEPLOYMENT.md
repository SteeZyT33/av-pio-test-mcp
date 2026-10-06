# Dependency and deployment manifest

**This cloud task performs no installation, connection to local VW, workspace
editing, settings changes or native deployment. Native arming is blocked.**
The following is a reviewable local procedure after the source gates are resolved,
not a claim that this draft is deployable today.

## Dependency closure and outputs

| Component | Dependencies / supplied files | Writes |
| --- | --- | --- |
| External stdio server | Reviewed CPython + `mcp-server/vwx_mcp_server.py` and `pio_test/*.py`; standard library only | Fixed private IPC files |
| VW Python menu template | Vendor embedded Python (3.9 syntax), vendor `vs`, reviewed checkout; no FastMCP/pip | Fixed IPC files and allowed session-owned PIO operations, once native gates exist |
| Windows path/DACL validation | Windows system `kernel32`/`advapi32` via stdlib ctypes | None |
| Offline tests | CPython stdlib unittest; C++17 compiler for policy test | Temporary disposable mock files and portable test executable |
| Native runtime plugin | **None provided or buildable in this draft** | None |
| Lock | `requirements.lock` = complete empty third-party closure | No downloads |

Cloud checks used CPython 3.12.14 and GCC 13.3.0 on Linux. Record exact Windows
CPython, VW2026 build/embedded-Python version, SDK distribution/hash and MSVC/Windows
SDK versions when validating locally. Pin that evidence before permitting native
operation; no automatic interpreter, SDK or dependency upgrades. The old vcxproj
is removed and must not be used to build/deploy the broad bridge from git history.

## Explicit file preparation, without installing VW components

Use a dedicated **local fixed NTFS drive**, with separate directories such as
`C:\Users\you\AV-PIO-Lab\drawings` and `C:\Users\you\AV-PIO-Lab\ipc`.
No production folders, OneDrive/cloud-sync paths, UNC/mapped drives, junctions,
symlinks, hardlinked files or shared network storage. Only saved disposable `.vwx`
files belong under `drawings`. The code never saves them automatically.

Create the two directories manually. Before generating a key, make the **empty
IPC directory** owned by your current Windows SID, protect its DACL from inherited
permissions, and grant FullControl only to that SID and optionally LocalSystem
(`S-1-5-18`), inheritable by files/subdirectories. Remove broad Users,
Authenticated Users, Everyone and Administrators allow entries from this specific
directory. The runtime rejects null/broad/unsupported DACLs; do not disable checks
to accommodate a failure. Use the Windows Security > Advanced UI on this new
directory; no admin elevation or changes to parent/user/VW folders are needed.
Inspect child-file ACL inheritance locally. Other accounts must be denied access.

On POSIX for offline work use owner-only `0700` directory and `0600` files. This
does not prove Windows ACL behavior. Same-identity processes remain trusted.

Review `POST_SIZES` in `pio_test/schema.py` against the operator/native catalog.
The supplied corrected strings are exact. Then, from the reviewed checkout:

```powershell
python -m pio_test.prepare --test-root 'C:\Users\you\AV-PIO-Lab\drawings' --ipc-root 'C:\Users\you\AV-PIO-Lab\ipc' --confirm-post-catalog
```

This explicitly writes only `ipc\config.json` and a cryptographic `ipc\key.bin`.
It requires an existing empty private directory, refuses overwrites and performs
no VW installation. Do not print/upload the key, configuration or IPC contents.
If preparation partially fails, inspect only those two named files; retain
evidence as needed and use a new empty private directory instead of overwriting.

Run the stdio entry with an explicit trusted interpreter/config path:

```powershell
& 'C:\path\to\python.exe' -I 'C:\reviewed\av-pio-test-mcp\mcp-server\vwx_mcp_server.py' --config 'C:\Users\you\AV-PIO-Lab\ipc\config.json'
```

`bridge\vwx-mcp.bat` accepts those same two paths as positional arguments. It
does not create a venv, pip install, elevate, auto-update or honor legacy network
variables. Initially only MCP enumeration is meaningful without a pump. Do not
connect it to real VW until the native implementation and acceptance gates pass.

## Local menu/fixture setup after gate implementation and review

1. The user creates/maintains **AV Post and AV Callout native definitions locally**
   with the existing private AV bootstrap/hot reload. Nothing here installs,
   edits, copies, renames or recreates those definitions. AV Beam/AV Beam Tool
   stay excluded. Confirm ordinary regeneration, Event-Based OFF and Reset on
   Move/Rotate ON without changing the private implementation in this repository.
2. The user creates a new disposable design-layer drawing, saves it at the exact
   intended path under the test root, and manually creates an empty synthetic
   `AV-MCP-TEST` design layer and synthetic `AV-MCP-TEST` class. The future native
   preflight must verify them, supported units and scale. This interface exposes
   no layer/class/scale creation or editing: those setup actions remain manual.
3. Create a separate user-owned **Python MENU COMMAND** named `AV PIO Test Pump`;
   paste the reviewed `vwx-plugin/BridgeStart_MenuCommand.py` after editing its two
   local path literals. Add it manually to a development workspace. Do not use a
   document script, timer, OnIdle, raw native Python engine, socket thread or
   web-palette callback. Do not add automatic hotkeys/triggers.
4. Run the menu once to initialize the bridge descriptor, then request
   `test_arm` for e.g. `disposable.vwx` and manually run the menu again. Each
   subsequent queued job needs one manual invocation before its TTL expires.
   Client default is 30 seconds, requests can never exceed 60 seconds.
5. Keep all test-created PIOs on the synthetic layer. Scale/class experiments are
   manual and must be observed by the native proof. No broad document queries,
   hidden saves, selections, production modeling or PIO definitions are exposed.

The tradeoff is deliberate: one small manual pump, visible errors, and bounded
jobs instead of a persistent palette/timer/keyboard automation system.

## User-folder versus machine-wide locations

The default VW2026 **user** Plug-ins location on Windows is typically
`%APPDATA%\Nemetschek\Vectorworks\2026\Plug-ins`; the user may configure another
user folder. Confirm the actual location in VW locally; do not edit that setting.
A later reviewed custom Python menu command (`.vsm`) belongs in that user folder,
not in a company workgroup location. The old installer used the **machine-wide**
`C:\Program Files\Vectorworks 2026\Plug-ins` directory for `VwxBridge.vlb/.vwr`.
This fork has no installer and copies nothing to either location.

Any future required native lifecycle observer must be built from reviewed source
against the local 2026 SDK, without post-build deployment. Review its exact output
names/credential files separately. No native binary is included in this draft,
and no existing upstream binary should be downloaded or reused.

## Explicit recovery and removal — preserve user files/settings

- On an ambiguous timeout, **do not retry**. Stop the MCP process, wait for VW to
  return (or review its crash), and inspect the disposable drawing manually. Do
  not assume cancellation or an error undid the operation. Keep the private IPC
  evidence if needed. Close VW before clearing any residual native context.
- To start again, create a **new** empty private IPC directory/key/config and
  deliberately edit the menu's config literal with VW stopped. New runtime and
  bridge/session nonces revoke old jobs. Never copy `claimed.json`, ownership or
  uncertainty state to the new directory. Saved objects are not adopted.
- To remove this harness, stop the MCP process and close VW. Remove only the
  manually created `AV PIO Test Pump` workspace entry and its specifically named
  user `.vsm` file, if you created them. Remove only this reviewed harness checkout
  if desired. Do not remove the user's AV definitions/bootstrap or workspace file.
- Remove the exact dedicated private IPC directory only after reviewing it for
  unexpected user files; its expected files are listed above/in ARCHITECTURE.
  Do not recursively delete a Plug-ins folder, user folder, drawings root, class,
  layer or document. Delete/discard disposable drawings manually if desired;
  cleanup through the test interface is limited to explicitly listed owned UUIDs.
- If an old upstream bridge was independently installed, this PR does not remove
  it. With VW closed, inspect the exact user/machine-wide locations and provenance
  of `VwxBridge.vlb` and `VwxBridge.vwr`. Remove only confirmed old bridge files and
  their workspace entries manually. Never wildcard-delete `Credentials*.vst` or
  other plug-ins: credentials may cover multiple tools. Preserve all user settings.
