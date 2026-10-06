#include "deferred_registration.hpp"
#include <cassert>
#include <stdexcept>

int main() {
    using namespace av_pio_test;
    int starts = 0, stops = 0;
    {
        DeferredRegistration metadata([&] { ++starts; return true; }, [&] { ++stops; });
        assert(!metadata.active() && starts == 0 && stops == 0);
    }
    assert(starts == 0 && stops == 0); // Metadata construction/destruction has no callback side effect.
    {
        DeferredRegistration observer([&] { ++starts; return true; }, [&] { ++stops; });
        assert(observer.activate());
        assert(observer.active() && starts == 1);
        assert(observer.activate() && starts == 1); // no duplicate listeners
        observer.deactivate();
        observer.deactivate();
        assert(!observer.active() && stops == 1);
    }
    assert(stops == 1);
    {
        DeferredRegistration failed([&] { ++starts; return false; }, [&] { ++stops; });
        assert(!failed.activate() && !failed.active());
        assert(stops == 2); // cleanup even after partial registration failure
    }
    assert(stops == 2);
    {
        DeferredRegistration failed([&]() -> bool { ++starts; throw std::runtime_error("failed"); },
                                    [&] { ++stops; });
        bool rejected = false;
        try { failed.activate(); } catch (...) { rejected = true; }
        assert(rejected && !failed.active() && stops == 3);
    }
    {
        DeferredRegistration active([&] { ++starts; return true; }, [&] { ++stops; });
        assert(active.activate());
    }
    assert(stops == 4); // active teardown unregisters exactly once
}
