#pragma once
#include "antworld/storage/store.hpp"

namespace antworld::storage {
struct LiveHistoryLimits {
    std::size_t unpublished_facts{600000};
    std::size_t capture_bytes{256*1024*1024};
};
struct Publication {
    SaveToken token;
    double checkpoint_ms{}, capture_ms{}, background_ms{};
    std::size_t frame_bytes{}, captured_bytes{};
};

// One in-flight immutable capture. Submission, finish and all runtime calls
// belong to the application simulation thread. The worker owns its SQLite
// connection. Its completion alone never changes live Core memory.
class LiveHistoryWriter {
public:
    explicit LiveHistoryWriter(const std::filesystem::path&,RuntimeLimits = {},LiveHistoryLimits = {});
    ~LiveHistoryWriter();
    LiveHistoryWriter(const LiveHistoryWriter&)=delete;
    LiveHistoryWriter& operator=(const LiveHistoryWriter&)=delete;
    void bind(WorldRuntime&) const;
    [[nodiscard]] bool try_submit(WorldRuntime&,std::optional<SaveToken> expected = {},const SaveOptions& = {});
    [[nodiscard]] bool pending() const noexcept;
    [[nodiscard]] bool ready() const;
    Publication finish(WorldRuntime&);

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};
} // namespace antworld::storage
