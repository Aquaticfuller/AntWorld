#pragma once
#include "event_block.hpp"
#include "store_internal.hpp"

namespace antworld::storage {
struct SaveFrame {
    WorldSnapshot state;
    std::vector<std::uint8_t> checkpoint;
    HistoryCapture history;
    Observation observation;
    GeometrySnapshot geometry;
    std::vector<GeometryEdit> edits;
    std::vector<AntState> ants;
    std::vector<CommandReceipt> receipts;
};
namespace detail {
[[nodiscard]] SaveFrame capture_frame(const WorldRuntime&);

struct HistoryAnchor {
    SaveToken token;
    SimTime time;
    Digest parent,tail,digest;
    std::vector<std::uint8_t> frame;
};

struct DatabaseCloser {
    void operator()(sqlite3* db) const noexcept { sqlite3_close_v2(db); }
};
using Database = std::unique_ptr<sqlite3,DatabaseCloser>;
[[nodiscard]] Database open_readonly(const std::filesystem::path&);

class SqlEventPrefix final : public EventPrefix {
public:
    SqlEventPrefix(const std::filesystem::path&,WorldId,std::size_t,Digest);
    [[nodiscard]] std::size_t size() const noexcept override { return size_; }
    [[nodiscard]] std::vector<WorldEvent> read(EventId,std::size_t) const override;
    [[nodiscard]] bool matches(WorldId world,std::uint64_t cursor,const Digest& digest) const noexcept {
        return world==world_ && cursor==size_ && digest==tail_;
    }
private:
    Database db_;
    WorldId world_;
    std::size_t size_;
    Digest tail_;
};

// Visits an authoritative contiguous suffix ending at a published block boundary.
// Return false from the visitor to stop at a query page limit.
class BlockCursor {
public:
    BlockCursor(sqlite3*,WorldId,EventId after,EventId through);
    [[nodiscard]] std::optional<EventBlock> next();
private:
    sqlite3* db_;
    WorldId world_;
    EventId cursor_,through_;
    std::optional<Digest> previous_;
    SimTime previous_time_{};
    Statement query_;
};

[[nodiscard]] Digest column_digest(const Statement&,int);
[[nodiscard]] Digest block_tail(sqlite3*,WorldId,EventId);
[[nodiscard]] Digest append_blocks(sqlite3*,WorldId,const HistoryCapture&,EventId from,EventId through,FactSchema = FactSchema::Legacy);
[[nodiscard]] FactSchema frame_fact_schema(std::span<const std::uint8_t>);
[[nodiscard]] constexpr bool compatible_fact_schema(FactSchema a,FactSchema b) {
    // Keep the existing legacy/first-F1 compatibility and isolate both later candidates.
    return a==b || (a<FactSchema::FoundingPersistence && b<FactSchema::FoundingPersistence);
}
void verify_blocks(sqlite3*,WorldId,EventId from,EventId through,const Digest& tail,FactSchema);
void require_history_prefix(sqlite3*,WorldId,const HistoryCapture&,EventId cursor,const Digest& tail);
void put_anchor(sqlite3*,const SaveToken&,SimTime,std::span<const std::uint8_t>,const Digest& parent,const Digest& tail);
[[nodiscard]] HistoryAnchor read_anchor(sqlite3*,WorldId,std::uint64_t,std::size_t byte_limit);
} // namespace detail
} // namespace antworld::storage
