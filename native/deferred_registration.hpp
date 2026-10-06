// MIT. Construction binds functions; only explicit activation registers them.
#pragma once
#include <functional>
#include <utility>

namespace av_pio_test {
class DeferredRegistration {
    std::function<bool()> start_;
    std::function<void()> stop_;
    bool active_ = false;
public:
    DeferredRegistration(std::function<bool()> start, std::function<void()> stop)
        : start_(std::move(start)), stop_(std::move(stop)) {}
    DeferredRegistration(const DeferredRegistration&) = delete;
    DeferredRegistration& operator=(const DeferredRegistration&) = delete;
    ~DeferredRegistration() { deactivate(); }
    bool activate() {
        if (active_) return true;
        try {
            if (start_()) { active_ = true; return true; }
        }
        catch (...) { stop_(); throw; }
        stop_(); // Also rolls back partial failed registrations.
        return false;
    }
    void deactivate() {
        if (!active_) return;
        active_ = false;
        stop_();
    }
    bool active() const { return active_; }
};
} // namespace av_pio_test
