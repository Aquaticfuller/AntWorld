#pragma once
#include "antworld/core/event.hpp"
#include <memory>
#include <vector>

namespace antworld {
// An immutable committed prefix. The application owns its storage and verifies
// the bytes before exposing them. The Core has no dependency on that storage.
class EventPrefix {
public:
    virtual ~EventPrefix() = default;
    [[nodiscard]] virtual std::size_t size() const noexcept = 0;
    [[nodiscard]] virtual std::vector<WorldEvent> read(EventId after,std::size_t limit) const = 0;
};

namespace detail { class EventJournal; }

class HistoryCapture {
public:
    [[nodiscard]] std::size_t size() const noexcept { return size_; }
    [[nodiscard]] std::size_t resident_bytes() const;
    [[nodiscard]] const std::shared_ptr<const EventPrefix>& prefix() const noexcept { return prefix_; }
    [[nodiscard]] std::vector<WorldEvent> read(EventId after,std::size_t limit) const;

private:
    friend class detail::EventJournal;
    struct Chunk {
        std::size_t begin;
        std::shared_ptr<const std::vector<WorldEvent>> events;
        bool operator==(const Chunk&) const = default;
    };
    std::shared_ptr<const EventPrefix> prefix_;
    std::vector<Chunk> chunks_ = std::vector<Chunk>(0);
    std::size_t size_{};
};
} // namespace antworld
