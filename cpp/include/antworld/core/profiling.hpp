#pragma once
#include <array>
#include <chrono>
#include <cstdint>
#include <string_view>

// Optional host-only attribution. No profiler value is simulation state,
// evidence, randomness or a checkpoint field. Normal builds compile scopes out.
namespace antworld::profiling {
enum class Category : unsigned { Advance, Index, Sampling, Spatial, Scheduler,
                                 Transaction, History, Physiology, Policy, Count };
inline constexpr std::array<std::string_view, 9> names{
    "advance", "contact_index", "candidate_sampling", "spatial_validation",
    "event_scheduler", "transaction_journal", "fact_history", "physiology", "policy"};
struct Counter {
    std::uint64_t calls{}, inclusive_ns{}, exclusive_ns{};
};
using Counters = std::array<Counter, names.size()>;
#ifdef ANTWORLD_PROFILE
inline constexpr bool enabled = true;
inline thread_local Counters counters;
class Scope;
inline thread_local Scope* current{};
class Scope {
    using Clock = std::chrono::steady_clock;
    Category category;
    Scope* parent;
    Clock::time_point start;
    std::uint64_t children{};
public:
    explicit Scope(Category c) noexcept : category(c), parent(current), start(Clock::now()) { current=this; }
    ~Scope() noexcept {
        const auto duration=static_cast<std::uint64_t>(
            std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now()-start).count());
        auto& item=counters[static_cast<unsigned>(category)];
        ++item.calls; item.inclusive_ns+=duration; item.exclusive_ns+=duration-children;
        current=parent;
        if (parent) parent->children+=duration;
    }
    Scope(const Scope&)=delete;
    Scope& operator=(const Scope&)=delete;
};
inline void reset() noexcept { counters={}; }
inline Counters snapshot() noexcept { return counters; }
#else
inline constexpr bool enabled = false;
struct Scope { explicit Scope(Category) noexcept {} };
inline void reset() noexcept {}
inline Counters snapshot() noexcept { return {}; }
#endif
} // namespace antworld::profiling
