#pragma once

#include "antworld/core/world_runtime.hpp"
#include "event_block.hpp"
#include <algorithm>
#include <stdexcept>

namespace antworld::r0 {
// Keep new canonical facts in lossless memory blocks. A restored prefix can
// stay in SQLite. The runtime continues to assign every fact and event ID.
class DiagnosticHistory final : public EventPrefix {
public:
    [[nodiscard]] std::size_t size() const noexcept override { return size_; }
    [[nodiscard]] std::size_t first_cursor() const noexcept override { return first_cursor_; }
    [[nodiscard]] std::size_t encoded_bytes() const noexcept { return bytes_; }
    [[nodiscard]] std::size_t stored_facts() const noexcept { return base_ ? base_->size() : 0; }

    static std::shared_ptr<const DiagnosticHistory> publish(WorldRuntime& world) {
        using namespace storage::detail;
        const auto capture=world.capture_history();
        auto next=std::make_shared<DiagnosticHistory>();
        next->first_cursor_=capture.first_cursor();
        if (const auto former=std::dynamic_pointer_cast<const DiagnosticHistory>(capture.prefix())) {
            next->base_=former->base_;
            next->blocks_=former->blocks_;
            next->size_=former->size_;
            next->bytes_=former->bytes_;
        } else {
            next->base_=capture.prefix();
            next->size_=std::max(next->first_cursor_,next->stored_facts());
        }
        auto previous=next->blocks_.empty() ? Digest{} : next->blocks_.back()->header.digest;
        const auto ecology=world.ecological_closure();
        const auto schema=ecology && ecology->founding_habitat &&
            ecology->founding_habitat->nutrition>=FoundingNutrition::SustainedSupply ?
            FactSchema::SustainedSupply : FactSchema::EcologicalClosure;
        while (next->size_<capture.size()) {
            const auto facts=capture.read({next->size_},block_records);
            auto block=std::make_shared<const EventBlock>(seal_block(facts,previous,schema));
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
        after.value=std::max(after.value,static_cast<std::uint64_t>(first_cursor_));
        if (after.value>=size_ || !limit) return result;
        if (after.value<stored_facts()) {
            const auto count=std::min(limit,stored_facts()-static_cast<std::size_t>(after.value));
            result=base_->read(after,count);
            if (result.size()!=count) throw std::runtime_error("incomplete base history");
        }
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
    std::shared_ptr<const EventPrefix> base_;
    std::vector<std::shared_ptr<const storage::detail::EventBlock>> blocks_;
    std::size_t first_cursor_{},size_{},bytes_{};
    mutable EventId cache_first_;
    mutable std::vector<WorldEvent> cache_;
};
} // namespace antworld::r0
