#pragma once
#include "checkpoint_codec.hpp"
#include <set>

namespace antworld::detail {
template <class S> void write_commands(Writer &w, const S &s) {
    w.put(s.commands.size());
    for (const auto &[id, r] : s.commands) {
        w.put(id.high);
        w.put(id.low);
        w.position(r.command.position);
        w.mass(r.command.mass);
        w.put(r.resource.value);
        w.put(r.event.value);
        w.time(r.applied_at);
        w.put(r.revision);
    }
}
template <class S> void read_commands(Reader &r, S &s, const RuntimeLimits &limits) {
    const auto count = r.count(limits.committed_events, 104);
    std::set<EventId> linked;
    for (std::size_t i = 0; i < count; ++i) {
        CommandReceipt receipt;
        receipt.command.world = s.world;
        receipt.command.id = {r.get(), r.get()};
        receipt.command.position = r.position();
        receipt.command.mass = r.mass();
        receipt.resource = {r.get()};
        receipt.event = {r.get()};
        receipt.applied_at = r.time();
        receipt.revision = r.get();
        ensure(receipt.command.id != CommandId{} && receipt.event.value &&
                   receipt.event.value <= s.journal.size(),
               "invalid command identity/evidence");
        const auto &e = s.journal.at(static_cast<std::size_t>(receipt.event.value - 1));
        ensure(e.kind == FactKind::FoodPlaced && e.resource == receipt.resource &&
                   e.time == receipt.applied_at && e.revision == receipt.revision &&
                   e.position == receipt.command.position && e.transferred == receipt.command.mass &&
                   linked.insert(e.id).second && s.commands.emplace(receipt.command.id, receipt).second,
               "command receipt disagrees with committed fact");
    }
    for (const auto &e : s.journal)
        if (e.kind == FactKind::FoodPlaced)
            ensure(linked.contains(e.id), "placed food lacks command receipt");
}
} // namespace antworld::detail
