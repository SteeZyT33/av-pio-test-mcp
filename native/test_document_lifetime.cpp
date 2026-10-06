#include "document_lifetime.hpp"
#include <cassert>

int main() {
    using namespace av_pio_test;
    DocumentLifetime state(std::string(64, 'a'));
    bool rejected = false;
    try { state.snapshot(); } catch (...) { rejected = true; }
    assert(rejected);
    state.opened(100); state.activated(100);
    const auto first = state.snapshot();
    state.closed(100); state.opened(100); state.activated(100);
    assert(!(first == state.snapshot())); // even if pointer is reused
    const auto reopened = state.snapshot();
    state.opened(200); state.activated(200); state.activated(100);
    assert(!(reopened == state.snapshot()));
    state.invalidate();
    rejected = false;
    try { state.snapshot(); } catch (...) { rejected = true; }
    assert(rejected);
    DocumentLifetime restart(std::string(64, 'b'));
    restart.opened(100); restart.activated(100);
    assert(!(first == restart.snapshot()));
}
