#pragma once

#include "antworld/core/world_runtime.hpp"
#include "event_block.hpp"
#include <algorithm>

namespace antworld::r0 {
// The lab retains lossless canonical history in RAM, using the same blocks as
// the SQLite store. The interactive service still uses its existing save path.
class DiagnosticHistory final : public EventPrefix {
public:
    [[nodiscard]] std::size_t size() const noexcept override { return size_; }
    [[nodiscard]] std::size_t encoded_bytes() const noexcept { return bytes_; }

    static std::shared_ptr<const DiagnosticHistory> publish(WorldRuntime& world,
                                                           const std::shared_ptr<const DiagnosticHistory>& former) {
        using namespace storage::detail;
        const auto capture=world.capture_history();
        auto next=std::make_shared<DiagnosticHistory>();
        if (former) {
            next->blocks_=former->blocks_;
            next->size_=former->size_;
            next->bytes_=former->bytes_;
        }
        auto previous=next->blocks_.empty() ? Digest{} : next->blocks_.back()->header.digest;
        while (next->size_<capture.size()) {
            const auto facts=capture.read({next->size_},block_records);
            auto block=std::make_shared<const EventBlock>(seal_block(facts,previous,FactSchema::EcologicalClosure));
            previous=block->header.digest;
            next->size_+=facts.size();
            next->bytes_+=block->bytes.capacity();
            next->blocks_.push_back(std::move(block));
        }
        world.acknowledge_history(capture,next);
        return next;
    }

    [[nodiscard]] std::vector<WorldEvent> read(EventId after,std::size_t limit) const override {
        std::vector<WorldEvent> result(0);
        if (after.value>=size_ || !limit) return result;
        result.reserve(std::min(limit,size_-static_cast<std::size_t>(after.value)));
        auto it=std::upper_bound(blocks_.begin(),blocks_.end(),after.value,
            [](auto cursor,const auto& block) { return cursor<block->header.last.value; });
        while (it!=blocks_.end() && result.size()<limit) {
            const auto& block=**it;
            if (cache_first_!=block.header.first) {
                const auto header=storage::detail::inspect_block(block.bytes);
                cache_=storage::detail::read_block(block.bytes,header);
                cache_first_=header.first;
            }
            const auto skipped=std::max(after.value+1,block.header.first.value)-block.header.first.value;
            const auto start=static_cast<std::ptrdiff_t>(skipped);
            const auto count=static_cast<std::ptrdiff_t>(std::min(limit-result.size(),cache_.size()-static_cast<std::size_t>(start)));
            result.insert(result.end(),cache_.begin()+start,cache_.begin()+start+count);
            ++it;
        }
        return result;
    }
private:
    std::vector<std::shared_ptr<const storage::detail::EventBlock>> blocks_;
    std::size_t size_{},bytes_{};
    mutable EventId cache_first_;
    mutable std::vector<WorldEvent> cache_;
};
} // namespace antworld::r0
