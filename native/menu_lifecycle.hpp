// MIT. SDK-independent state used by the private native observer.
// Callbacks may invalidate; they cannot acquire menu authority or run a job.
#pragma once
#include <atomic>
#include <cstdint>
#include <stdexcept>

namespace av_pio_test {
enum class Event { document, edit, undo, environment };

class MenuLifecycle {
    std::atomic<std::uint64_t> epoch_{1};
    std::atomic<std::uint64_t> owner_{0};
    std::uint64_t invocation_ = 0; // accessed only by the menu owner
public:
    void enter(std::uint64_t thread) {
        std::uint64_t no_owner = 0;
        if (!thread || !owner_.compare_exchange_strong(no_owner, thread))
            throw std::runtime_error("recursive or invalid menu context");
        ++invocation_;
    }
    void leave(std::uint64_t thread) {
        if (!in_menu(thread)) throw std::runtime_error("wrong menu owner");
        owner_.store(0);
    }
    bool in_menu(std::uint64_t thread) const { return thread && owner_.load() == thread; }
    std::uint64_t generation() const { return epoch_.load(); }
    std::uint64_t invocation(std::uint64_t thread) const {
        if (!in_menu(thread)) throw std::runtime_error("not a menu invocation");
        return invocation_;
    }
    void invalidate() noexcept { epoch_.fetch_add(1); }
    void notification(Event event, std::uint64_t thread) noexcept {
        if ((event == Event::edit || event == Event::undo) && in_menu(thread)) return;
        invalidate();
    }
};
} // namespace av_pio_test
