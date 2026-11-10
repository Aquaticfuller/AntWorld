#include "state.hpp"

namespace antworld {
using namespace detail;
CommandReceipt WorldRuntime::place_food(const PlaceFoodCommand &command) {
    auto &s = *state_;
    if (command.world != s.world || command.id == CommandId{})
        throw std::invalid_argument("invalid world-qualified command identity");
    if (const auto it = s.commands.find(command.id); it != s.commands.end()) {
        if (it->second.command != command)
            throw std::invalid_argument("command ID payload conflict");
        return it->second;
    }
    const EventKey key{s.m.now, Phase::Input, 0, 0, s.m.next_sequence};
    if ((s.m.watermark && key <= *s.m.watermark) || (!s.queue.empty() && s.queue.begin()->first < key))
        throw std::invalid_argument("food command requires an unexecuted input boundary");
    if (!inside(command.position, s.config) || !command.mass.total_ug() ||
        !spatially_clear(command.position, command.position))
        throw std::invalid_argument("invalid placed food position or mass");
    std::optional<Cell> cell;
    if (s.surface) {
        cell = ground_cell(*s.surface,command.position,s.config.continuous_spatial_motion);
        if (!cell || s.food_cells.contains(*cell))
            throw std::invalid_argument("food needs a unique walkable cell");
    }
    Transaction tx(s, limits_);
    tx.entity_budget();
    ScheduledEvent source;
    source.id = {take(s.m.next_scheduled)};
    source.key = key;
    (void)take(s.m.next_sequence);
    tx.executing(source);
    const ResourceId id{take(s.m.next_entity)};
    s.foods.append({id, command.position, command.mass, command.mass});
    if (cell)
        tx.food_cells.set(*cell, id);
    if (s.geometry)
        tx.spatial_index.set({spatial_key(command.position), id.value}, 2);
    s.m.ledger.introduced = sum(s.m.ledger.introduced, command.mass);
    (void)s.m.ledger.introduced.total_ug();
    s.m.ledger.available = sum(s.m.ledger.available, command.mass);
    WorldEvent fact;
    fact.kind = FactKind::FoodPlaced;
    fact.source = source.id;
    fact.resource = id;
    fact.position = command.position;
    fact.transferred = command.mass;
    const EventId event{s.m.next_event};
    tx.fact(fact);
    const CommandReceipt receipt{command, id, event, s.m.now, s.m.revision};
    tx.commands.set(command.id, receipt);
    validate_nutrition_capacity();
    tx.commit();
    return receipt;
}
std::optional<CommandReceipt> WorldRuntime::command_receipt(WorldId world, CommandId id) const {
    if (world != state_->world)
        return {};
    const auto it = state_->commands.find(id);
    return it == state_->commands.end() ? std::optional<CommandReceipt>{} : it->second;
}
std::vector<CommandReceipt> WorldRuntime::command_receipts() const {
    std::vector<CommandReceipt> result(0);
    for (const auto &[id, receipt] : state_->commands) {
        (void)id;
        result.push_back(receipt);
    }
    return result;
}
std::vector<AntState> WorldRuntime::ant_states() const {
    std::vector<AntState> result(0);
    result.reserve(state_->ants.size());
    for (std::size_t i = 0; i < state_->ants.size(); ++i)
        result.push_back(state_->ants.get(i));
    return result;
}
std::vector<Colony> WorldRuntime::colonies() const { return state_->colonies.rows; }
std::vector<FoodSource> WorldRuntime::food_sources() const { return state_->foods.rows; }
} // namespace antworld
