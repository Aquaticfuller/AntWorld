#pragma once
#include <array>
#include <chrono>
#include <cstdint>
#include <string_view>

namespace antworld::storage::timing {
enum class Phase : unsigned {
    CaptureFrame, SealBlocks, DeriveIndexes, WriteIndexes, Commit,
    VerifyBlocks, RestoreFrame, CheckIndexes, DecodeBlock, Count
};
inline constexpr std::array<std::string_view, static_cast<unsigned>(Phase::Count)> names{
    "capture_frame", "seal_blocks", "derive_indexes", "write_indexes", "commit",
    "verify_blocks", "restore_frame", "check_indexes", "decode_block"};
struct Counter { std::uint64_t calls{}, ns{}; };
using Counts = std::array<Counter, names.size()>;

#ifdef ANTWORLD_STORAGE_TIMING
inline thread_local Counts* active{};
class Scope {
public:
    explicit Scope(Phase phase) : counter(active ? &(*active)[static_cast<unsigned>(phase)] : nullptr),
                                 start(counter ? Clock::now() : Clock::time_point{}) {}
    ~Scope() {
        if (counter) {
            ++counter->calls;
            counter->ns += static_cast<std::uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(
                Clock::now()-start).count());
        }
    }
    Scope(const Scope&) = delete;
    Scope& operator=(const Scope&) = delete;
private:
    using Clock = std::chrono::steady_clock;
    Counter* counter;
    Clock::time_point start;
};
#else
struct Scope { explicit Scope(Phase) {} };
#endif
} // namespace antworld::storage::timing
