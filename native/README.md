# No deployable native plugin in this draft

The previous palette, error-dialog dismissal, timers, keystroke synthesis,
callbacks, resources and vcxproj were removed. Do not reuse the upstream binary.

`document_lifetime.hpp` is a portable policy model and
`test_document_lifetime.cpp` its test. Neither includes VW SDK headers, registers
a plugin, observes real documents, calls Python, or dismisses dialogs. Compile
and run the portable test as documented in the root README.

The real SDK lifetime/completion integration is missing. See
`docs/NATIVE_ACCEPTANCE.md` before implementing it locally. No native build or
deployment is authorized by this cloud task.
