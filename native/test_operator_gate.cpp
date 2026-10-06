#include "operator_gate.hpp"
#include <cassert>

int main() {
    using namespace av_pio_test;
    OperatorGate gate;
    auto initial = gate.snapshot();
    assert(!initial.enabled && !initial.busy && initial.epoch == 1);
    bool rejected = false;
    try { gate.start(); } catch (...) { rejected = true; }
    assert(rejected); // External startup cannot enter while OFF.
    gate.enable();
    auto ready = gate.snapshot();
    assert(ready.enabled && ready.epoch > initial.epoch);
    gate.start();
    assert(gate.can_execute());
    rejected = false;
    try { gate.start(); } catch (...) { rejected = true; }
    assert(rejected);
    rejected = false;
    try { gate.enable(); } catch (...) { rejected = true; }
    assert(rejected);
    gate.disable();
    auto pending = gate.snapshot();
    assert(!pending.enabled && pending.busy && pending.disable_pending);
    assert(pending.epoch > ready.epoch && !gate.can_execute());
    gate.uncertain(); // Return does not fabricate rollback of in-flight effects.
    gate.finish();
    auto off = gate.snapshot();
    assert(!off.enabled && !off.busy && !off.disable_pending && off.unconfirmed);
    rejected = false;
    try { gate.enable(); } catch (...) { rejected = true; }
    assert(rejected);
    OperatorGate restarted;
    assert(!restarted.snapshot().enabled); // New native process always OFF.
    restarted.enable();
    auto before_disable = restarted.snapshot().epoch;
    restarted.disable();
    restarted.enable();
    assert(restarted.snapshot().epoch > before_disable);
}
