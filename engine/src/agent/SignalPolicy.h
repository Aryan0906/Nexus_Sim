#pragma once
#include <string>
#include <cstdint>

namespace nexussim {

class SignalPolicy {
public:
    virtual ~SignalPolicy() = default;
    // Demand observation for adaptive policies (queue length in vehicles,
    // mean wait time in seconds on the current green approaches).
    virtual void set_inputs(double /*queue_len*/, double /*wait_time*/) {}
    virtual void tick(double dt) = 0;
    virtual bool is_green(int64_t incoming_edge_id) const = 0;
    virtual int current_phase_index() const = 0;
    virtual std::string policy_name() const = 0;
};

} // namespace nexussim
