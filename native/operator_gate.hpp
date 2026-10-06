// MIT. Local native operator control; no drawing, IPC or SDK dependency.
#pragma once
#include <cstdint>
#include <mutex>
#include <stdexcept>

namespace av_pio_test {
struct GateSnapshot {
    bool enabled;
    bool busy;
    bool disable_pending;
    bool unconfirmed;
    std::uint64_t epoch;
};
class OperatorGate {
    mutable std::mutex mutex_;
    bool enabled_ = false;
    bool busy_ = false;
    bool disable_pending_ = false;
    bool unconfirmed_ = false;
    std::uint64_t epoch_ = 1;
public:
    GateSnapshot snapshot() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return {enabled_, busy_, disable_pending_, unconfirmed_, epoch_};
    }
    void enable() {
        std::lock_guard<std::mutex> lock(mutex_);
        if (busy_) throw std::runtime_error("operation still executing");
        if (unconfirmed_) throw std::runtime_error("local outcome review required");
        ++epoch_; // Even repeated Enable requires fresh explicit arm.
        enabled_ = true;
        disable_pending_ = false;
    }
    void disable() {
        std::lock_guard<std::mutex> lock(mutex_);
        enabled_ = false;
        ++epoch_; // Invalidates authority immediately, including queued work.
        disable_pending_ = busy_;
    }
    void start() {
        std::lock_guard<std::mutex> lock(mutex_);
        if (!enabled_ || disable_pending_ || unconfirmed_)
            throw std::runtime_error("testing off or unconfirmed");
        if (busy_) throw std::runtime_error("recursive operation");
        busy_ = true;
    }
    bool can_execute() const {
        auto value = snapshot();
        return value.enabled && value.busy && !value.disable_pending && !value.unconfirmed;
    }
    void uncertain() {
        std::lock_guard<std::mutex> lock(mutex_);
        unconfirmed_ = true;
    }
    void finish() {
        std::lock_guard<std::mutex> lock(mutex_);
        busy_ = false;
        disable_pending_ = false; // OFF acknowledgment only after actual return.
    }
};
} // namespace av_pio_test
