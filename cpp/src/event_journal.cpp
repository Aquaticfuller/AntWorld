#include "event_journal.hpp"

namespace antworld {
std::size_t HistoryCapture::resident_bytes() const {
    auto bytes=chunks_.capacity()*sizeof(Chunk);
    for (const auto& chunk:chunks_) {
        const auto capacity=chunk.events->capacity();
        if (capacity>(std::numeric_limits<std::size_t>::max()-bytes)/sizeof(WorldEvent))
            throw std::overflow_error("history capture size overflow");
        bytes+=capacity*sizeof(WorldEvent);
    }
    return bytes;
}

std::vector<WorldEvent> HistoryCapture::read(EventId after,std::size_t limit) const {
    std::vector<WorldEvent> result(0);
    if (after.value>=size_ || !limit) return result;
    auto cursor=static_cast<std::size_t>(after.value);
    const auto end=cursor+std::min(limit,size_-cursor);
    result.reserve(end-cursor);
    if (prefix_ && cursor<prefix_->size()) {
        const auto count=std::min(end,prefix_->size())-cursor;
        const auto page=prefix_->read(after,count);
        if (page.size()!=count) throw std::runtime_error("short immutable history prefix");
        result.insert(result.end(),page.begin(),page.end());
        cursor+=count;
    }
    for (const auto& chunk:chunks_) {
        if (cursor==end) break;
        const auto& events=*chunk.events;
        if (cursor>=chunk.begin+events.size()) continue;
        const auto offset=cursor-chunk.begin;
        const auto count=std::min(end-cursor,events.size()-offset);
        const auto first=events.begin()+static_cast<std::ptrdiff_t>(offset);
        result.insert(result.end(),first,first+static_cast<std::ptrdiff_t>(count));
        cursor+=count;
    }
    if (cursor!=end) throw std::logic_error("incomplete captured history");
    return result;
}
} // namespace antworld

namespace antworld::detail {
std::size_t EventJournal::resident_bytes() const {
    auto bytes=sealed_.capacity()*sizeof(HistoryCapture::Chunk);
    const auto add=[&](std::size_t capacity) {
        if (capacity>(std::numeric_limits<std::size_t>::max()-bytes)/sizeof(WorldEvent))
            throw std::overflow_error("resident history size overflow");
        bytes+=capacity*sizeof(WorldEvent);
    };
    for (const auto& chunk:sealed_) add(chunk.events->capacity());
    add(active_.capacity());
    add(cache_.capacity());
    return bytes;
}

WorldEvent EventJournal::at(std::size_t index) const {
    if (index>=sealed_end_) return active_.at(index-sealed_end_);
    if (index<cold_size()) {
        if (index<cache_begin_ || index-cache_begin_>=cache_.size()) {
            const auto begin=index-index%page_size;
            const auto count=std::min(page_size,cold_size()-begin);
            auto page=prefix_->read({begin},count);
            if (page.size()!=count) throw std::runtime_error("short durable journal page");
            cache_.swap(page);
            cache_begin_=begin;
        }
        return cache_[index-cache_begin_];
    }
    const auto chunk=std::upper_bound(sealed_.begin(),sealed_.end(),index,
        [](std::size_t value,const auto& item) { return value<item.begin; });
    const auto& selected=*std::prev(chunk);
    return selected.events->at(index-selected.begin);
}

std::vector<WorldEvent> EventJournal::read(EventId after,std::size_t limit) const {
    if (after.value>=size() || !limit) return std::vector<WorldEvent>(0);
    const auto first=static_cast<std::size_t>(after.value);
    const auto count=std::min(limit,size()-first);
    if (first>=sealed_end_) {
        const auto begin=active_.begin()+static_cast<std::ptrdiff_t>(first-sealed_end_);
        return {begin,begin+static_cast<std::ptrdiff_t>(count)};
    }
    auto cursor=first;
    const auto end=first+count;
    std::vector<WorldEvent> result(0);
    if (cursor<cold_size()) {
        const auto count_from_prefix=std::min(end,cold_size())-cursor;
        result=prefix_->read(after,count_from_prefix);
        if (result.size()!=count_from_prefix) throw std::runtime_error("short durable journal page");
        cursor+=count_from_prefix;
    }
    result.reserve(count);
    auto chunk=std::upper_bound(sealed_.begin(),sealed_.end(),cursor,
        [](std::size_t value,const auto& item) { return value<item.begin; });
    if (cursor<sealed_end_ && chunk!=sealed_.begin()) --chunk;
    for (; cursor<end && cursor<sealed_end_ && chunk!=sealed_.end(); ++chunk) {
        const auto& events=*chunk->events;
        const auto begin=events.begin()+static_cast<std::ptrdiff_t>(cursor-chunk->begin);
        const auto take=std::min(end-cursor,events.size()-(cursor-chunk->begin));
        result.insert(result.end(),begin,begin+static_cast<std::ptrdiff_t>(take));
        cursor+=take;
    }
    if (cursor<end) {
        const auto begin=active_.begin()+static_cast<std::ptrdiff_t>(cursor-sealed_end_);
        result.insert(result.end(),begin,begin+static_cast<std::ptrdiff_t>(end-cursor));
    }
    return result;
}

HistoryCapture EventJournal::capture() const {
    if (!active_.empty()) {
        auto page=std::make_shared<std::vector<WorldEvent>>(0);
        sealed_.reserve(sealed_.size()+1);
        page->swap(active_);
        sealed_.push_back({sealed_end_,page});
        sealed_end_+=page->size();
    }
    HistoryCapture result;
    result.prefix_=prefix_;
    result.chunks_=sealed_;
    result.size_=sealed_end_;
    return result;
}

void EventJournal::acknowledge(const HistoryCapture& captured,std::shared_ptr<const EventPrefix> published) {
    if (!published || published->size()!=captured.size_ || captured.prefix_!=prefix_ ||
        captured.chunks_.size()>sealed_.size() ||
        !std::equal(captured.chunks_.begin(),captured.chunks_.end(),sealed_.begin()))
        throw std::invalid_argument("durable acknowledgement is not this runtime's captured prefix");
    prefix_=std::move(published);
    sealed_.erase(sealed_.begin(),sealed_.begin()+static_cast<std::ptrdiff_t>(captured.chunks_.size()));
    cache_.clear();
}

void EventJournal::attach(std::shared_ptr<const EventPrefix> prefix) {
    assert(empty() && prefix);
    prefix_=std::move(prefix);
    sealed_end_=prefix_->size();
}
} // namespace antworld::detail
