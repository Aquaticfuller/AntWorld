#pragma once

#include "antworld/core/world_runtime.hpp"

#include <filesystem>
#include <memory>

namespace antworld::rm02 {
inline constexpr std::size_t fact_page = 256;
inline constexpr std::size_t cut_limit = 3 * 1024 * 1024;
inline constexpr std::size_t database_limit = 64 * 1024 * 1024;
inline constexpr std::size_t pending_limit = 512;
inline constexpr std::size_t focal_limit = 64;

enum class Record : std::uint8_t { Fact = 1, State, Ledger, Pending, Neighbor };
enum class Coverage : std::uint8_t { NotRequested, Complete, Limit, Missing };

struct Plan {
    std::string lineage;
    std::vector<EntityId> focal;
    EntityId neighbor_actor;
    bool all_relevant{}, pending{}, start_at_current{};
    std::size_t payload_limit{cut_limit};
    bool activity_care{};
    bool foraging{};
};

struct Boundary {
    SimTime time;
    std::uint64_t revision{}, cursor{}, rng{};
    bool operator==(const Boundary&) const = default;
};

struct Cut {
    WorldId world;
    Boundary end;
    std::uint64_t from{}, examined{}, selected{}, records{}, dropped{};
    Coverage pending{}, neighbors{};
    std::vector<std::uint8_t> payload;
};

enum class Publish { Committed, Staged, Duplicate };
enum class PublicationMode { Immediate, Buffered };
enum class PublicationFault { None, BeforeCommit };
struct BackgroundStats {
    double write_ms{};
    std::size_t peak_payload_bytes{};
};

// A live instance is bound to one owner-thread continuation. After restoring
// the runtime, reopen against the exact paired checkpoint on a new instance.
// Checkpoint arguments are caller-owned authoritative exports of that runtime.
class Observer {
public:
    Observer(const std::filesystem::path&, const WorldRuntime&, Plan);
    Observer(const std::filesystem::path&, const WorldRuntime&, Plan,
             std::span<const std::uint8_t> restored_checkpoint);
    ~Observer();
    Observer(const Observer&) = delete;
    Observer& operator=(const Observer&) = delete;

    [[nodiscard]] Cut capture() const;
    Publish publish(const Cut&, PublicationFault = PublicationFault::None,
                    PublicationMode = PublicationMode::Immediate);
    void start_background();
    void submit(Cut&&, PublicationFault = PublicationFault::None);
    void flush();
    [[nodiscard]] BackgroundStats background_stats() const;
    void anchor(std::span<const std::uint8_t> checkpoint);
    [[nodiscard]] std::uint64_t committed_cuts() const;
    [[nodiscard]] std::uint64_t cursor() const;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};
} // namespace antworld::rm02
