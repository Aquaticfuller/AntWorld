#pragma once
#include "antworld/core/history.hpp"
#include <algorithm>
#include <cassert>
#include <iterator>
#include <limits>
#include <stdexcept>

namespace antworld::detail {
class EventJournal {
public:
    static constexpr std::size_t page_size = 4096;
    [[nodiscard]] std::size_t size() const noexcept { return sealed_end_ + active_.size(); }
    [[nodiscard]] bool empty() const noexcept { return !size(); }
    [[nodiscard]] bool has_prefix() const noexcept { return static_cast<bool>(prefix_); }
    [[nodiscard]] std::size_t first_cursor() const noexcept { return first_cursor_; }
    void start_at(std::size_t cursor) noexcept {
        assert(empty() && !prefix_);
        first_cursor_=sealed_end_=cursor;
    }
    [[nodiscard]] std::size_t unpublished() const noexcept { return size() - cold_size(); }
    [[nodiscard]] std::size_t resident_bytes() const;
    void limit(std::size_t value) {
        if (!value || unpublished() > value) throw std::length_error("unpublished history budget exceeded");
        limit_ = value;
    }
    void check_append() const {
        if (unpublished() >= limit_) throw std::length_error("unpublished history backpressure");
    }
    void push_back(const WorldEvent& event) { active_.push_back(event); }
    void resize(std::size_t value) noexcept {
        assert(value >= sealed_end_ && value <= size());
        active_.resize(value - sealed_end_);
    }
    [[nodiscard]] WorldEvent at(std::size_t index) const;
    [[nodiscard]] WorldEvent front() const { return at(first_cursor_); }
    [[nodiscard]] std::vector<WorldEvent> read(EventId after,std::size_t limit) const;
    [[nodiscard]] HistoryCapture capture() const;
    void acknowledge(const HistoryCapture&,std::shared_ptr<const EventPrefix>);
    void attach(std::shared_ptr<const EventPrefix>);

    struct Iterator {
        const EventJournal* journal;
        std::size_t index;
        [[nodiscard]] WorldEvent operator*() const { return journal->at(index); }
        void operator++() { ++index; }
        bool operator==(const Iterator&) const = default;
    };
    [[nodiscard]] Iterator begin() const noexcept { return {this,first_cursor_}; }
    [[nodiscard]] Iterator end() const noexcept { return {this,size()}; }

private:
    [[nodiscard]] std::size_t cold_size() const noexcept { return prefix_ ? prefix_->size() : first_cursor_; }
    std::shared_ptr<const EventPrefix> prefix_;
    mutable std::vector<HistoryCapture::Chunk> sealed_ = std::vector<HistoryCapture::Chunk>(0);
    mutable std::vector<WorldEvent> active_ = std::vector<WorldEvent>(0);
    mutable std::size_t sealed_end_{};
    std::size_t first_cursor_{};
    std::size_t limit_{std::numeric_limits<std::size_t>::max()};
    mutable std::size_t cache_begin_{};
    mutable std::vector<WorldEvent> cache_ = std::vector<WorldEvent>(0);
};
} // namespace antworld::detail
