#pragma once
#include "antworld/core/long_term.hpp"

#include "antworld/core/event.hpp"
#include "antworld/core/command.hpp"
#include "antworld/core/history.hpp"
#include "antworld/core/social.hpp"

#include <memory>
#include <optional>
#include <span>
#include <vector>

namespace antworld {
namespace detail { struct SurfaceConnector; struct Writer; }
struct WorldSnapshot {
    WorldId world;
    SimTime now;
    std::uint64_t seed{}, revision{}, pending_events{}, committed_events{};
    std::uint64_t next_entity_id{}, next_scheduled_id{}, next_event_id{}, next_sequence{};
    std::uint64_t rng_state{}, state_hash{}, trace_hash{};
    std::uint64_t ant_count{}, colony_count{}, food_source_count{}, living_ants{};
    FoodLedger food_ledger;
    std::optional<EventKey> execution_watermark;
    std::uint64_t events_at_current_time{};
    bool operator==(const WorldSnapshot&) const = default;
};

// Single-threaded owner. Query results are detached values, never live pointers.
class WorldRuntime {
public:
    static constexpr std::uint32_t schema_version = 8;
    static constexpr std::uint32_t physics_version = 9;
    static constexpr std::size_t max_records = 65536;
    static constexpr std::size_t max_same_time_events = 1024;

    WorldRuntime(WorldId world, std::uint64_t seed, WorldConfig config = {}, RuntimeLimits limits = {});
    ~WorldRuntime();
    WorldRuntime(WorldRuntime&&) noexcept;
    WorldRuntime& operator=(WorldRuntime&&) noexcept;
    WorldRuntime(const WorldRuntime&) = delete;
    WorldRuntime& operator=(const WorldRuntime&) = delete;

    EntityId allocate_entity_id();
    ScheduledId schedule(const EventRequest& request);
    bool cancel(ScheduledId id);
    void advance_to(SimTime target);
    ColonyRef seed_colony(PositionM nest = {});
    AntRef seed_ant(ColonyRef colony, const AntSeed& seed);
    FoodRef seed_food(PositionM position, FoodMass mass);
    CommandReceipt place_food(const PlaceFoodCommand&);
    [[nodiscard]] std::optional<CommandReceipt> command_receipt(WorldId, CommandId) const;
    [[nodiscard]] std::vector<CommandReceipt> command_receipts() const;
    [[nodiscard]] std::vector<AntState> ant_states() const;
    [[nodiscard]] std::vector<Colony> colonies() const;
    [[nodiscard]] std::vector<FoodSource> food_sources() const;
    ScheduledId submit(const ActionProposal& proposal);
    ScheduledId schedule_lifecycle(AntRef actor, SimTime at, LifeStage stage);
    void configure_surface(const SurfaceConfig&, std::span<const Cell> blocked, const BehaviorConfig& = {});
    void start_foraging(AntRef actor);
    void enable_physiology(AntRef, const PhysiologySeed& = {}, const PhysiologyConfig& = {});
    void set_behavior(AntRef, IndividualBehavior);
    void configure_social(const SocialConfig& = {});
    [[nodiscard]] std::optional<SocialConfig> social_config() const;
    // Pure, reproducible local encounters for the supplied individual decision counter.
    [[nodiscard]] ContactSample sample_contacts(AntRef, std::uint64_t decision) const;
    [[nodiscard]] ContactWork contact_work() const;
    void set_autonomy(AntRef, bool enabled = true);
    [[nodiscard]] std::optional<AutonomyState> query_autonomy(AntRef) const;
    ScheduledId submit_nutrition(const NutritionProposal&);
    [[nodiscard]] std::optional<PhysiologyState> query_physiology(AntRef) const;
    [[nodiscard]] NutritionSnapshot nutrition_snapshot() const;
    void configure_geometry(const GeometryConfig&, std::span<const BoxQ> seed_voids, std::span<const BoxQ> rocks = {});
    ScheduledId submit_soil(const SoilProposal&);
    [[nodiscard]] GeometrySnapshot geometry_snapshot() const;
    [[nodiscard]] Material query_material(PositionM) const;
    [[nodiscard]] std::uint64_t query_material_volume(BoxQ, Material) const;
    [[nodiscard]] double query_signed_distance(PositionM) const;
    [[nodiscard]] bool spatially_clear(PositionM, PositionM, std::int32_t half_extent_q = 0) const;
    [[nodiscard]] Neighborhood query_neighborhood(AntRef, double radius_m) const;
    [[nodiscard]] Route3D query_route(AntRef, PositionM destination) const;
    [[nodiscard]] std::vector<Portal3D> query_portals(AntRef) const;
    [[nodiscard]] bool validate_route(AntRef, const Route3D&) const;
    [[nodiscard]] std::vector<GeometryEdit> geometry_edits() const;
    [[nodiscard]] std::vector<SoilParcel> soil_parcels() const;
    [[nodiscard]] std::optional<SoilParcel> query_parcel(SoilParcelRef) const;
    [[nodiscard]] std::vector<PointQ> dirty_geometry_bricks() const;
    void rebuild_geometry_cache(std::span<const PointQ>);
    void discard_geometry_cache();
    [[nodiscard]] std::optional<SdfBrick> query_sdf_brick(PointQ) const;
    [[nodiscard]] std::vector<BoxQ> local_frontiers(AntRef) const;
    [[nodiscard]] std::optional<ExcavatorState> query_excavator(AntRef) const;

    [[nodiscard]] WorldSnapshot snapshot() const;
    // Cheap metadata query; hash fields are zero. snapshot() additionally computes audit hashes.
    [[nodiscard]] WorldSnapshot summary() const;
    [[nodiscard]] std::optional<AntState> query_ant(AntRef ref) const;
    [[nodiscard]] std::optional<Colony> query_colony(ColonyRef ref) const;
    [[nodiscard]] std::optional<FoodSource> query_food(FoodRef ref) const;
    [[nodiscard]] WorldConfig config() const;
    [[nodiscard]] std::optional<ForagerState> query_forager(AntRef) const;
    [[nodiscard]] LocalObservation sense(AntRef) const;
    [[nodiscard]] SurfaceSnapshot surface_snapshot() const;
    [[nodiscard]] std::vector<TrailSample> trails() const;
    [[nodiscard]] std::vector<CellVisit> visits() const;
    [[nodiscard]] std::vector<ScheduledEvent> pending_events() const;
    [[nodiscard]] std::vector<WorldEvent> committed_events() const;
    [[nodiscard]] std::vector<WorldEvent> events_after(EventId cursor, std::size_t limit) const;
    [[nodiscard]] std::vector<std::uint8_t> checkpoint() const;
    void restore(std::span<const std::uint8_t> bytes);
    // Application persistence boundary. Call on the sole runtime thread.
    // Capture seals buffers without changing ecological state or copying facts.
    [[nodiscard]] HistoryCapture capture_history() const;
    [[nodiscard]] std::vector<std::uint8_t> checkpoint_frame() const;
    void restore_frame(std::span<const std::uint8_t>,std::shared_ptr<const EventPrefix>);
    void acknowledge_history(const HistoryCapture&,std::shared_ptr<const EventPrefix>);
    void limit_unpublished_history(std::size_t count);
    [[nodiscard]] std::size_t unpublished_history() const noexcept;

private:
    struct State;
    class Transaction;
    std::unique_ptr<State> state_;
    RuntimeLimits limits_;
    void resolve_actions(Transaction&, const std::vector<ScheduledEvent>&);
    void execute(Transaction&, const ScheduledEvent&);
    void resolve_wakes(Transaction&, const std::vector<ScheduledEvent>&);
    [[nodiscard]] detail::SurfaceConnector discover_connector(PositionM depot) const;
    [[nodiscard]] bool can_forage(const AntState&) const;
    void prepare_forager(Transaction&,const AntState&,ForagerState&);
    void after_action(Transaction&, const ScheduledEvent&, WorldEvent&, const AntState& before);
    void stop_dead_forager(Transaction&, EntityId);
    void maintain_trails(Transaction&, const ScheduledEvent&);
    void execute_physiology(Transaction&, const ScheduledEvent&);
    void resolve_nutrition_wakes(Transaction&, const std::vector<ScheduledEvent>&);
    void resolve_nutrition_action(Transaction&, const ScheduledEvent&, WorldEvent&);
    void continue_nutrition_behavior(Transaction&, const ScheduledEvent&, const WorldEvent&);
    void schedule_physiology(Transaction&, EntityId);
    void stop_physiology(Transaction&, EntityId, DeathCause);
    void synchronize_physiology(Transaction&, EntityId);
    void validate_nutrition_capacity() const;
    void execute_reproduction(Transaction&, const ScheduledEvent&);
    void execute_resource_release(Transaction&, const ScheduledEvent&);
    void stop_reproduction(Transaction&, EntityId);
    void notify_return(Transaction&, EntityId);
    [[nodiscard]] bool local_space_demand(AntRef, std::size_t contacts) const;
    void inspect_decision(const ScheduledEvent&, const ContactSample&, std::uint64_t context,
                          std::uint64_t choice, EntityId recipient = {}) const;
    void resolve_soil_action(Transaction&, const ScheduledEvent&, WorldEvent&);
    void resolve_excavation_wakes(Transaction&, const std::vector<ScheduledEvent>&);
    void after_excavation_action(Transaction&, const ScheduledEvent&, const WorldEvent&, const AntState&);
    void stop_excavator(Transaction&, EntityId);
    void activate_excavator(Transaction&, EntityId);
    void index_position(Transaction&, EntityId, PositionM from, PositionM to);
    void index_contact(Transaction&, EntityId, std::optional<PositionM>);
    void change_behavior(Transaction&, AntRef, IndividualBehavior, ScheduledId source = {}, bool care_motor = false);
    void change_autonomy(Transaction&, AntRef, bool);
    void schedule_autonomy(Transaction&, EntityId);
    void stop_autonomy(Transaction&, EntityId);
    void resolve_autonomy_wakes(Transaction&, const std::vector<ScheduledEvent>&);
    [[nodiscard]] std::uint64_t carried_soil_ug(EntityId) const;
    [[nodiscard]] std::int32_t body_half(EntityId) const;
    static std::vector<std::uint8_t> encode(const State&, std::size_t byte_limit,bool frame = false);
    static void write_checkpoint(detail::Writer&,const State&,bool frame);
    static std::unique_ptr<State> decode(std::span<const std::uint8_t>, const RuntimeLimits&,
                                         std::shared_ptr<const EventPrefix> prefix = {});
public:
    static constexpr std::uint32_t long_term_schema_version = 9, long_term_physics_version = 11;
    static constexpr std::uint32_t allocation_schema_version = 10, allocation_physics_version = 12;
    void configure_long_term(const LongTermConfig& = {});
    [[nodiscard]] std::optional<LongTermConfig> long_term_config() const;
    void enable_reproduction(AntRef, const ReproductionConfig& = {});
    [[nodiscard]] std::optional<ReproductionState> query_reproduction(AntRef) const;
    void configure_resource_cycle(FoodRef, const ResourceCycleConfig&);
    [[nodiscard]] std::optional<ResourceCycleState> query_resource_cycle(FoodRef) const;
    [[nodiscard]] FoodMass resource_reserves() const;
    static constexpr std::uint32_t care_schema_version = 11, care_physics_version = 13;
    static constexpr std::uint32_t retrieval_schema_version = 12, retrieval_physics_version = 14;
    static constexpr std::uint32_t care_motion_schema_version = 13, care_motion_physics_version = 15;
    static constexpr std::uint32_t spatial_schema_version = 14, spatial_physics_version = 16;
    void configure_biology(const SpeciesCareProfile& = {}, const EnvironmentCareProfile& = {});
    void enable_brood_care(AntRef, const IndividualCareProfile& = {});
    void pause_brood_care(AntRef);
    [[nodiscard]] std::optional<CareState> query_care(AntRef) const;
    [[nodiscard]] std::optional<SpeciesCareProfile> care_profile() const;
    [[nodiscard]] BehaviorWindow behavior_window(AntRef, SimTime begin, SimTime end) const;
private:
    void resolve_care_wakes(Transaction&, const std::vector<ScheduledEvent>&);
    [[nodiscard]] bool local_care_available(AntRef) const;
    void start_autonomous_care(Transaction&, AntRef, ScheduledId);
    void collect_care_neighbors(AntRef, double radius, std::vector<AntRef>&) const;
    [[nodiscard]] bool clear_care_segment(PositionM from, PositionM to, std::int32_t half) const;
    void execute_care_action(Transaction&, const ScheduledEvent&);
    void interrupt_care(Transaction&, EntityId, Outcome, bool disable = false);
    void validate_active_care(Transaction&);
    [[nodiscard]] PositionM care_destination(const CareState&,const AntState&,PositionM goal,
                                             std::optional<PositionM> load={}) const;
    void schedule_care(Transaction&, EntityId, SimTime);
    void observe(Transaction&, EntityId, ScheduledId, const BehaviorObservation&, FoodMass = {}, Outcome = Outcome::Success);
    void observe_legacy_action(Transaction&, const ScheduledEvent&, const WorldEvent&);
};
} // namespace antworld
