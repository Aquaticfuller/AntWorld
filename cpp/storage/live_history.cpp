#include "antworld/storage/live_history.hpp"
#include "segmented_archive.hpp"
#include <chrono>
#include <future>

namespace antworld::storage {
namespace {
using Clock=std::chrono::steady_clock;
double milliseconds(Clock::time_point from) {
    return std::chrono::duration<double,std::milli>(Clock::now()-from).count();
}

struct CompletedSave {
    Publication publication;
    HistoryCapture history;
    std::shared_ptr<const EventPrefix> prefix;
};

std::size_t capture_bytes(const SaveFrame& frame) {
    auto size=checked_add(frame.history.resident_bytes(),frame.checkpoint.capacity());
    for (auto amount:{frame.ants.capacity()*sizeof(AntState),frame.edits.capacity()*sizeof(GeometryEdit),
             frame.receipts.capacity()*sizeof(CommandReceipt),frame.observation.values.capacity()*sizeof(MetricValue)})
        size=checked_add(size,amount);
    if (size>SIZE_MAX) throw std::length_error("capture size exceeds host");
    return static_cast<std::size_t>(size);
}
} // namespace

struct LiveHistoryWriter::Impl {
    std::filesystem::path path;
    RuntimeLimits runtime_limits;
    LiveHistoryLimits limits;
    WorldRuntime* owner{};
    std::future<CompletedSave> job;
};

LiveHistoryWriter::LiveHistoryWriter(const std::filesystem::path& path,RuntimeLimits runtime,LiveHistoryLimits limits)
    :impl_(std::make_unique<Impl>()) {
    if (!limits.capture_bytes || !limits.unpublished_facts) throw std::invalid_argument("invalid live history budget");
    impl_->path=std::filesystem::absolute(path);
    impl_->runtime_limits=runtime;
    impl_->limits=limits;
}

LiveHistoryWriter::~LiveHistoryWriter() = default;

void LiveHistoryWriter::bind(WorldRuntime& world) const {
    world.limit_unpublished_history(impl_->limits.unpublished_facts);
}

bool LiveHistoryWriter::try_submit(WorldRuntime& world,std::optional<SaveToken> expected,const SaveOptions& options) {
    if (pending()) return false;
    bind(world);
    const auto started=Clock::now();
    auto checkpoint=world.checkpoint_frame();
    Publication publication{};
    publication.checkpoint_ms=milliseconds(started);
    publication.frame_bytes=checkpoint.size();
    SaveFrame frame{world.summary(),std::move(checkpoint),world.capture_history(),observe(world),
                           world.geometry_snapshot(),world.geometry_edits(),world.ant_states(),world.command_receipts()};
    publication.captured_bytes=capture_bytes(frame);
    if (publication.captured_bytes>impl_->limits.capture_bytes)
        throw std::length_error("immutable save capture exceeds queue byte budget");
    publication.capture_ms=milliseconds(started);
    auto work=[path=impl_->path,limits=impl_->runtime_limits,frame=std::move(frame),expected,options,publication]() mutable {
        const auto started=Clock::now();
        Store store(path,limits,StoreFormat::Segmented);
        publication.token=store.save_segmented(frame,expected,options);
        auto prefix=store.published_prefix(publication.token);
        publication.background_ms=milliseconds(started);
        return CompletedSave{publication,std::move(frame.history),std::move(prefix)};
    };
    impl_->job=std::async(std::launch::async,std::move(work));
    impl_->owner=&world;
    return true;
}

bool LiveHistoryWriter::pending() const noexcept { return impl_->job.valid(); }

bool LiveHistoryWriter::ready() const {
    return pending() && impl_->job.wait_for(std::chrono::seconds{0})==std::future_status::ready;
}

Publication LiveHistoryWriter::finish(WorldRuntime& world) {
    if (!pending() || impl_->owner!=&world) throw std::invalid_argument("publication belongs to another runtime or is absent");
    auto work=std::move(impl_->job);
    impl_->owner=nullptr;
    const auto result=work.get();
    if (result.publication.token.world!=world.summary().world)
        throw std::invalid_argument("runtime changed worlds before publication acknowledgement");
    world.acknowledge_history(result.history,result.prefix);
    return result.publication;
}
} // namespace antworld::storage
