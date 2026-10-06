// MIT; portable POLICY MODEL ONLY. No VW SDK entry points or plugin exports.
// A local SDK integration must deliver complete lifecycle notifications and a
// CSPRNG nonce. A sampled document pointer alone cannot implement this contract.
#pragma once
#include <cstdint>
#include <map>
#include <stdexcept>
#include <string>

namespace av_pio_test {
struct Identity {
    std::uintptr_t handle = 0;
    std::uint64_t generation = 0;
    std::string process_nonce;
    bool operator==(const Identity& b) const {
        return handle == b.handle && generation == b.generation && process_nonce == b.process_nonce;
    }
};

class DocumentLifetime {
    std::map<std::uintptr_t, bool> open_;
    std::uintptr_t active_ = 0;
    std::uint64_t epoch_ = 0;
    std::string nonce_;
public:
    explicit DocumentLifetime(std::string cryptographic_nonce) : nonce_(cryptographic_nonce) {
        if (nonce_.size() != 64 || nonce_.find_first_not_of("0123456789abcdef") != std::string::npos)
            throw std::invalid_argument("missing process nonce");
    }
    void opened(std::uintptr_t handle) {
        invalidate();
        if (!handle || open_.count(handle)) { open_.clear(); return; }
        open_[handle] = true;
    }
    void activated(std::uintptr_t handle) {
        invalidate(); // switching away and back invalidates old authority
        if (open_.count(handle)) active_ = handle;
    }
    void closed(std::uintptr_t handle) {
        invalidate();
        open_.erase(handle);
    }
    void invalidate() { ++epoch_; active_ = 0; }
    // Call on undo/redo, missed/uncertain lifecycle events, listener teardown,
    // save-as and document replacement. Only a known activation restores it.
    Identity snapshot() const {
        if (!active_ || !open_.count(active_)) throw std::runtime_error("unknown document lifetime");
        return {active_, epoch_, nonce_};
    }
};
} // namespace av_pio_test
