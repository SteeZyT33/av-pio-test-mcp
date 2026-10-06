# Native policy and resource build support

This public directory contains portable policies and our own menu resource
catalog/packager. The SDK-dependent native implementation and binary remain
private; this directory alone is not a deployable native plug-in.

Build a menu resource archive with:

```text
python native/package_resources.py <output>/AVPIOTestObserver.vwr
python native/package_resources.py --check <output>/AVPIOTestObserver.vwr
python -m unittest native.test_package_resources -v
```

Menu `.vwstrings` use UTF-16LE with an FF FE byte-order mark. The archive uses
ZIP_STORED and the exact path `Strings/Supervisor.vwstrings`; it has no extra
plug-in-name directory. This matches the actual SDK2026 Windows BuildVWR output
and shipping VW2026 resources. The checker also accepts the SDK builder's
optional `Strings/` directory entry. Plain ASCII/UTF-8 resources are rejected.
The previous ASCII resource package could prevent native menu titles/category
from loading; corrected live menu visibility still needs operator verification.
The packager performs no native calls or installation and exposes no MCP route.

Official format and SDK examples:
[SDKExamples](https://github.com/VectorworksDeveloper/SDKExamples) and
[UTF-16 resource strings](https://github.com/Vectorworks/developer-scripting/blob/main/Marionette/pages/Implement%20a%20Node.md).

## Earlier draft boundary

The previous palette, error-dialog dismissal, timers, keystroke synthesis,
callbacks and vcxproj were removed. Do not reuse the upstream binary.

`document_lifetime.hpp` is a portable policy model and
`test_document_lifetime.cpp` its test. Neither includes VW SDK headers, registers
a plugin, observes real documents, calls Python, or dismisses dialogs. Compile
and run the portable test as documented in the root README.

The real SDK lifetime/completion integration is missing. See
`docs/NATIVE_ACCEPTANCE.md` before implementing it locally. No native build or
deployment is authorized by this cloud task.
