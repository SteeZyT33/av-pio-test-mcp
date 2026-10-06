#include "menu_lifecycle.hpp"
#include <cassert>

int main() {
    using namespace av_pio_test;
    MenuLifecycle state;
    const auto first = state.generation();
    state.notification(Event::edit, 7);
    assert(state.generation() == first + 1);
    state.enter(7);
    assert(state.invocation(7) == 1 && state.in_menu(7) && !state.in_menu(8));
    const auto inside = state.generation();
    state.notification(Event::undo, 7);
    state.notification(Event::edit, 7);
    assert(state.generation() == inside);
    state.notification(Event::edit, 8); // a different thread cannot borrow scope
    assert(state.generation() == inside + 1);
    state.notification(Event::document, 7); // even own nested document events revoke
    assert(state.generation() == inside + 2);
    bool rejected = false;
    try { state.enter(7); } catch (const std::runtime_error&) { rejected = true; }
    assert(rejected && state.invocation(7) == 1);
    rejected = false;
    try { state.leave(8); } catch (const std::runtime_error&) { rejected = true; }
    assert(rejected && state.in_menu(7));
    state.leave(7);
    state.notification(Event::undo, 7); // delayed own notification fails closed
    assert(state.generation() == inside + 3);
    state.enter(7);
    assert(state.invocation(7) == 2);
    state.leave(7);
    rejected = false;
    try { state.invocation(7); } catch (const std::runtime_error&) { rejected = true; }
    assert(rejected);
    return 0;
}
