#include "anatomy.hpp"
#include "behavior_rng.hpp"
#include "care_internal.hpp"
#include "ecological_internal.hpp"
#include "social_internal.hpp"
#include "founding_internal.hpp"
#include "worker_motion.hpp"

namespace antworld {
using namespace detail;
void WorldRuntime::set_autonomy(AntRef ref, bool enabled) {
  Transaction tx(*state_, limits_);
  change_autonomy(tx, ref, enabled);
  tx.commit();
}
void WorldRuntime::change_autonomy(Transaction &tx, AntRef ref, bool enabled) {
  auto &s = *state_;
  const bool integrated=integrated_care(s);
  if (enabled && !integrated && care_owned(s,ref.id))
    throw std::invalid_argument("pause dedicated care before worker autonomy");
  profiling::Scope profile(profiling::Category::Policy);
  const auto ant = query_ant(ref);
  if (!s.social || !ant || !ant->alive() ||
      (ant->caste != Caste::Worker && !(integrated && ant->caste==Caste::Queen && ant->stage==LifeStage::Adult)) ||
      !s.physiology.contains(ref.id))
    throw std::invalid_argument(
        "autonomy requires a living physiological caste admitted by the social policy");
  if (enabled && s.long_term && s.external_resolution(ref.id))
    throw std::invalid_argument("resolve external actions before enrolling autonomy");
  if (enabled && !s.long_term && s.m.resolution_commands)
    for (const auto &[key, e] : s.queue) {
      if (e.actor == ref.id && key.phase == Phase::Resolution &&
          e.id != s.physiology.at(ref.id).behavior_event &&
          (!s.foragers.contains(ref.id) ||
           e.id != s.foragers.at(ref.id).action) &&
          (!s.excavators.contains(ref.id) ||
           e.id != s.excavators.at(ref.id).action))
        throw std::invalid_argument(
            "resolve external actions before enrolling autonomy");
    }
  if (!enabled && integrated && care_owned(s,ref.id))
    interrupt_care(tx,ref.id,Outcome::InvalidTransition,true);
  auto a = s.autonomy.contains(ref.id)
               ? s.autonomy.at(ref.id)
               : AutonomyState{false, 0, s.m.now, s.m.now, {}};
  if (chamber_return(s) && !s.autonomy.contains(ref.id)) a.enrollment_site=ant->position;
  if (a.wake.value && s.queue_index.contains(a.wake))
    tx.remove(s.queue_index.at(a.wake));
  a.enabled = enabled;
  a.wake = {};
  tx.autonomy.set(ref.id, a);
  schedule_autonomy(tx, ref.id);
  WorldEvent f;
  f.kind = FactKind::AutonomyChanged;
  f.actor = ref.id;
  f.colony = ant->colony;
  f.stage = ant->stage;
  f.position = ant->position;
  f.payload = enabled ? 1 : 0;
  tx.fact(f);
}
std::optional<AutonomyState> WorldRuntime::query_autonomy(AntRef ref) const {
  const auto &s = *state_;
  if (!query_ant(ref) || !s.autonomy.contains(ref.id))
    return {};
  return s.autonomy.at(ref.id);
}
void WorldRuntime::schedule_autonomy(Transaction &tx, EntityId id, SimTime delay) {
  auto &s = *state_;
  if (!s.autonomy.contains(id))
    return;
  auto a = s.autonomy.at(id);
  const auto ant = s.ants.get(s.ants.index.at(id));
  if (!a.enabled || ant.stage != LifeStage::Adult || a.wake.value)
    return;
  ScheduledEvent e;
  e.actor = id;
  e.kind = ScheduledEvent::Kind::AutonomyWake;
  e.issued_at = s.m.now;
  const auto wait = delay.milliseconds ? delay.milliseconds : autonomy_delay(s, id, ant.caste, a.decisions);
  e.key = {after(s.m.now, wait),
           Phase::Reschedule, 0, 0, 0};
  a.wake = tx.insert(e);
  tx.autonomy.set(id, a);
}
void WorldRuntime::stop_autonomy(Transaction &tx, EntityId id) {
  auto &s = *state_;
  if (!s.autonomy.contains(id))
    return;
  auto a = s.autonomy.at(id);
  if (a.wake.value && s.queue_index.contains(a.wake))
    tx.remove(s.queue_index.at(a.wake));
  a.enabled = false;
  a.wake = {};
  tx.autonomy.set(id, a);
}
std::optional<MealAccess> WorldRuntime::query_meal_access(AntRef ref,bool extended) const {
  const auto& s=*state_;
  const auto ant=query_ant(ref);
  if (!ant || ant->stage!=LifeStage::Adult || !mouth_range(s) || !s.founding_reserves.contains(ref.id)) return {};
  const auto& a=*ant;
  const auto p=*query_physiology(ref);
  const auto& colony=s.colonies.rows[s.colonies.index.at(a.colony)];
  const auto mouth=query_body(ref)->mouth_m;
  const auto depot=depot_mouth_target(a,colony.nest_position);
  const auto radius=s.care_profile->perception_radius_m;
  MealAccess d;
  d.depot_visible=within_distance(mouth,depot,radius,true) && spatially_clear(mouth,depot);
  d.at_berth=at_foraging_home(a);
  d.route=a.caste==Caste::Worker && can_forage(a);
  d.care_busy=care_owned(s,a.id);
  d.active=active_expenditure(p);
  const auto horizon=a.caste==Caste::Queen?p.config.absorption_period:worker_timing(s,a.caste)->check_interval;
  const auto need=founding_resupply_shortfall(s.founding->profile,p,s.founding_reserves.at(a.id),
                                             a.caste==Caste::Queen,horizon);
  d.needs_carbs=need.carbs_ug!=0;
  d.needs_water=need.water_ug!=0;
  if (const auto wick=local_wick_contact(a,p)) {
      d.wick=true;
      d.at_wick=mouth_at_supply(a,depot_mouth_target(a,*wick));
  }
  d.payable_sugar_ug=founding_gift_supply(s.founding->profile,p).carbs_ug;
  d.depot_step=worker_depot_step(a).has_value();
  const auto& g=s.geometry->config;
  if (const auto origin=nearest_grid_point(a.position,g,true)) {
      const auto extent=extended ? std::min(32,static_cast<int>(radius/g.quantum_m)) : 4;
      for (int dx=-extent;dx<=extent;++dx) for (int dz=-extent;dz<=extent;++dz)
        for (int dy=0;dy<=(extended?2:0);++dy) {
          const auto site=physical({origin->x+dx,origin->y+dy,origin->z+dz},g);
          if (!within_distance(a.position,site,radius,true)) continue;
          const bool clear=site==a.position || clear_worker_site(a,site,true);
          if (clear && site!=a.position) ++d.clear_steps;
          if (shallow_soil_cap(site)) {
              ++d.sensed_cap_stances;
              if (clear) ++d.direct_cap_stances;
          }
      }
  }
  return d;
}
void WorldRuntime::request_food_review(Transaction& tx,const AntState& founder,EntityId worker,bool wake_founder) {
  auto& s=*state_;
  const auto donor=query_ant({s.world,worker});
  const auto actor=wake_founder ? founder.id : worker;
  if (!responsive_meal(s) || !donor || donor->stage!=LifeStage::Adult || donor->caste!=Caste::Worker ||
      founder.colony!=donor->colony ||
      !s.autonomy.contains(actor) || care_owned(s,actor)) return;
  if (!oral_contact(founder,*donor)) {
    if (!local_solicitation(s)) return;
    const auto a=query_body({s.world,founder.id})->mouth_m, b=query_body({s.world,worker})->mouth_m;
    if (!within_distance(a,b,s.care_profile->perception_radius_m,true) || !spatially_clear(a,b)) return;
  }
  const auto p=*query_physiology({s.world,worker});
  const auto available=founding_gift_supply(s.founding->profile,p);
  if (active_expenditure(p) || p.behavior==IndividualBehavior::Forage || p.behavior==IndividualBehavior::Excavate ||
      (!available.carbs_ug && !(founder_appetite(s) && available.water_ug))) return;
  request_autonomy_review(tx,actor,solicited_meal_wake);
}
void WorldRuntime::request_autonomy_review(Transaction& tx,EntityId actor,std::uint64_t stimulus) {
  auto& s=*state_;
  const auto found=s.autonomy.find(actor);
  if (found==s.autonomy.end()) return;
  auto a=found->second;
  if (!a.enabled || !s.queue_index.contains(a.wake)) return;
  const auto key=s.queue_index.at(a.wake);
  const auto at=after(s.m.now,1);
  if (key.time<=at) return;
  tx.remove(key);
  ScheduledEvent review;
  review.kind=ScheduledEvent::Kind::AutonomyWake;
  review.actor=actor;
  review.issued_at=s.m.now;
  review.payload=stimulus;
  review.key={at,Phase::Reschedule,0,0,0};
  a.wake=tx.insert(review);
  tx.autonomy.set(actor,a);
}
void WorldRuntime::notify_local_food_delivery(Transaction& tx,const WorldEvent& delivery) {
  const auto& s=*state_;
  if (!s.founding || !s.care_profile) return;
  const auto founder=query_ant({s.world,s.founding->founder});
  if (!founder || founder->stage!=LifeStage::Adult || founder->colony!=delivery.colony || care_owned(s,founder->id)) return;
  const auto p=*query_physiology({s.world,founder->id});
  if (active_expenditure(p)) return;
  const auto& colony=s.colonies.rows[s.colonies.index.at(delivery.colony)];
  const auto mouth=query_body({s.world,founder->id})->mouth_m;
  const auto site=depot_mouth_target(*founder,colony.nest_position);
  if (!within_distance(mouth,site,s.care_profile->perception_radius_m,true) || !spatially_clear(mouth,site)) return;
  const auto meal=foundress_nest_meal(s.founding->profile,p,s.founding_reserves.at(founder->id),
                                     colony.nest_food,true);
  if (ingredient_min(meal,delivery.transferred).total_ug()) request_autonomy_review(tx,founder->id,local_stimulus_wake);
}
bool WorldRuntime::notify_refill_progress(Transaction& tx,const AntState& before) {
  const auto& s=*state_;
  if (!local_stimulus(s) || before.caste!=Caste::Worker) return false;
  const auto worker=*query_ant({s.world,before.id});
  if (worker.position==before.position || !familiar_liquid_exit(s,worker)) return false;
  const auto p=*query_physiology({s.world,worker.id});
  if (p.config.crop_capacity_ug-p.crop.total_ug()<p.config.transfer_limit_ug) return false;
  const auto berth=s.connectors.at(worker.id).points[0];
  const auto gap=[&](PositionM site) { return std::llround(portable_care_distance(site,berth)*1e6); };
  if (gap(worker.position)>=gap(before.position)) return false;
  request_autonomy_review(tx,worker.id,local_stimulus_wake);
  return true;
}
void WorldRuntime::resolve_autonomy_wakes(
    Transaction &tx, const std::vector<ScheduledEvent> &wakes) {
  profiling::Scope profile(profiling::Category::Policy);
  auto &s = *state_;
  const auto &config = *s.social;
  // Keep the frozen decision record scalar: only work counters survive local
  // perception. Moving a nested debug-STL vector inside a noexcept aggregate
  // move can terminate under allocation-failure injection on MSVC.
  struct Choice {
    ScheduledEvent event;
    IndividualBehavior behavior;
    ContactWork sample;
    bool care{};
    EntityId scout;
    EventId cue;
    bool recruited{};
    std::optional<PositionM> resting_site;
    EntityId contact_target;
    CareAct transit{CareAct::NestReposition};
    std::uint8_t meal_steps{};
    bool queen_meal{}, drink{};
    EntityId solicitation;
  };
  std::vector<Choice> choices(0);
  choices.reserve(wakes.size());
  for (const auto &wake : wakes) {
    const auto ant = s.ants.get(s.ants.index.at(wake.actor));
    const auto a = s.autonomy.at(ant.id);
    const auto p = *query_physiology({s.world, ant.id});
    if (!a.enabled || a.wake != wake.id || ant.stage != LifeStage::Adult)
      throw std::logic_error("invalid autonomy ownership");
    Choice choice{};
    choice.event = wake;
    choice.behavior = p.behavior;
    const auto &colony = s.colonies.rows[s.colonies.index.at(ant.colony)];
    const auto buffer = s.ecological && s.ecological->founding_habitat ?
        s.ecological->founding_habitat->pantry_buffer_ug : 0;
    // Ongoing journeys and carried resources remain owned by that worker.
    // Stationary workers may nurse locally away from the depot; only a real
    // depot return permits switching out of foraging/excavation.
    const bool at_depot = ant.position == colony.nest_position;
    const bool foraging_home = !buffer ? at_depot : at_foraging_home(ant);
    const bool stationary = p.behavior != IndividualBehavior::Forage &&
                            p.behavior != IndividualBehavior::Excavate;
    const auto excavation=s.excavators.find(ant.id);
    const bool at_dig_origin=local_entrance_work(s) && excavation!=s.excavators.end() && excavation->second.path_size==1 &&
        ant.position==physical(excavation->second.path[0],s.geometry->config);
    const bool can_switch = (at_depot || at_dig_origin || (p.behavior==IndividualBehavior::Forage && foraging_home) || stationary) &&
                            !ant.carried_food.total_ug() &&
                            !s.carriers.contains(ant.id);
    const auto timing = worker_timing(s, ant.caste);
    const auto program_time = timing ? timing->minimum_program_time : config.minimum_program_time;
    const bool ready =
        p.behavior == IndividualBehavior::Paused ||
        s.m.now.milliseconds - a.last_program_change.milliseconds >=
            program_time.milliseconds;
    bool urgent = p.body_energy_nj < p.config.energy_capacity_nj / 4 ||
                        p.hydration_ug < p.config.hydration_capacity_ug / 4;
    if (local_founding_feeding(s) && founding_foundress(ant.id) && has_founding_diet(p))
      urgent=founding_resupply_shortfall(s.founding->profile,p,*query_founding({s.world,ant.id}),true,p.config.absorption_period).total_ug()!=0;
    if (buffer && timing && ant.caste==Caste::Worker) {
      // Newly eclosed workers can have healthy short-term reserves well below
      // the maximum crop and body capacities. Use the actual metabolic budget
      // before ruling out work, including a response to a returning scout.
      if (const auto reserve=query_founding({s.world,ant.id}))
        urgent=founding_resupply_shortfall(s.founding->profile,p,*reserve,false,timing->check_interval).total_ug()!=0;
    }
    const auto giving_way = yield_to_loaded(s) &&
        (ant.caste==Caste::Worker || (sustained_supply(s) && founding_foundress(ant.id))) && stationary && can_switch &&
        !care_owned(s,ant.id) && !active_expenditure(p) ? carrier_yield_step(ant) : std::nullopt;
    bool at_wick=false;
    std::optional<PositionM> wick_step;
    if (sustained_supply(s) && stationary && can_switch && !care_owned(s,ant.id) && !giving_way) {
      if (const auto wick=local_wick_contact(ant,p)) {
        at_wick=mouth_at_supply(ant,depot_mouth_target(ant,*wick));
        if (!at_wick) {
          const auto step=wick_approach(ant,*wick);
          if (step!=ant.position) wick_step=step;
        }
      }
    }
    const bool return_review=wake.payload==completed_return_wake || wake.payload==carbohydrate_delivery_wake;
    const bool stimulated=wake.payload==local_stimulus_wake;
    const bool focused=stimulated && stimulus_meal_priority(s);
    const bool regular_work=!wake.payload || (stimulated && !focused);
    const bool returned=social_crop(s) && return_review && p.behavior==IndividualBehavior::Forage && foraging_home;
    const bool can_provision=!at_wick && !wick_step && local_founding_feeding(s) && local_founding_provisioning(s,ant.id) &&
        ant.caste==Caste::Worker && p.crop.total_ug() &&
        (stationary || returned) && can_switch && !urgent && !care_owned(s,ant.id) && !active_expenditure(p) && !giving_way;
    auto food_offer=can_provision ? local_food_offer(ant,true) : std::nullopt;
    const bool can_feed_brood=can_provision && !food_offer &&
        ingredient_min(founding_gift_supply(s.founding->profile,p),local_provisioning_shortfall(ant)).total_ug();
    if (social_crop(s) && can_provision && !food_offer && !can_feed_brood)
      food_offer=local_food_offer(ant);
    std::optional<PositionM> chamber_step;
    const auto nursery_arrival_m=founding_nutrition(s)==FoundingNutrition::NurseryArrival ?
        2*s.geometry->config.quantum_m : .002;
    if (chamber_return(s) && can_provision && !food_offer && !can_feed_brood &&
        (a.knows_depot || private_sampling_trip(s,ant) || (familiar_site_detour(s) && familiar_liquid_exit(s,ant))) &&
        (returned || a.decisions%4!=0) && founding_gift_supply(s.founding->profile,p).carbs_ug &&
        portable_care_distance(ant.position,a.enrollment_site)>nursery_arrival_m) {
      if (private_sampling_trip(s,ant) || familiar_site_detour(s)) chamber_step=worker_depot_step(ant,a.enrollment_site);
      else {
        const auto next=mouth_approach(ant,a.enrollment_site,{});
        if (next!=ant.position && clear_resting_site(ant,next)) chamber_step=next;
      }
    }
    // An experienced forager at the actual handoff can refill the extra
    // load of carbohydrate that a locally recruited worker could collect.
    const bool repeat_delivery=sustained_supply(s) && wake.payload==carbohydrate_delivery_wake &&
        p.behavior==IndividualBehavior::Forage && foraging_home && can_switch && !urgent &&
        (!social_crop(s) || (!food_offer && !can_feed_brood)) &&
        colony.nest_food.carbs_ug<std::uint64_t(buffer)+ant.carrying_capacity_ug;
    bool at_meal=false;
    std::optional<PositionM> meal_step;
    if (!at_wick && !wick_step && !food_offer && !can_feed_brood &&
        !repeat_delivery && !(sustained_supply(s) && giving_way) &&
        can_switch && !care_owned(s,ant.id) && seeks_nest_meal(ant,p)) {
      at_meal=mouth_at_supply(ant,depot_mouth_target(ant,colony.nest_position));
      if (!at_meal) {
        const auto next=nest_meal_step(ant,colony.nest_position);
        if (next!=ant.position) meal_step=next;
      }
    }
    std::optional<PositionM> food_search_step;
    if (founding_nutrition(s)==FoundingNutrition::MealSearch && ant.caste==Caste::Worker &&
        stationary && can_switch && !care_owned(s,ant.id) && !active_expenditure(p) && !giving_way &&
        !at_wick && !wick_step && !at_meal && !meal_step && !food_offer && !can_feed_brood &&
        a.decisions%2==0 && s.founding_reserves.contains(ant.id) &&
        founding_resupply_shortfall(s.founding->profile,p,s.founding_reserves.at(ant.id),false,
                                   p.config.absorption_period).carbs_ug) {
      // ENGINEERING_FIXTURE. A short, paid local search for a meal before
      // discretionary brood work. The bearing has no access to food positions.
      auto rng=individual_rng(s.seed ^ UINT64_C(0x5345454b4d45414c),ant.id,a.decisions);
      const auto pose=*query_body({s.world,ant.id});
      const auto length=std::min(s.care_profile->perception_radius_m,portable_care_distance(pose.mouth_m,pose.abdomen_tip_m));
      const auto first=bounded_draw(rng,8);
      for (unsigned offset=0;offset<8;++offset) {
        const auto bearing=static_cast<std::uint8_t>(1+(first+offset)%8);
        const auto next=snap_micro(translated(ant.position,scale(body_heading(bearing),length)));
        if (clear_worker_site(ant,next,true)) {
          food_search_step=next;
          break;
        }
      }
    }
    const auto body_orientation=body_orientation_enabled(s) && stationary && can_provision && !food_offer &&
        !can_feed_brood && founding_gift_supply(s.founding->profile,p).carbs_ug ?
        approach_visible_body(ant) : std::nullopt;
    const auto solicitation=meal_rendezvous(s) && stationary && can_switch && (urgent || responsive_meal(s)) &&
        !care_owned(s,ant.id) && !active_expenditure(p) ? local_donor(ant) : std::nullopt;
    // ENGINEERING_FIXTURE: a bounded share of idle local work reviews samples
    // an understocked handoff even when other brood work is simultaneously available.
    const bool review_exit=departure_review(s) && regular_work && ready &&
        ((a.decisions+ant.id.value)%4==0 ||
         (work_face_search(s) && ant.caste==Caste::Worker && s.geometry_edits.empty() &&
          shallow_soil_cap(ant.position)));
    bool resupply=repeat_delivery;
    std::optional<PositionM> resupply_step;
    std::optional<PositionM> roof_stance;
    bool revisiting_exit=false;
    bool refill_trip=false;
    std::optional<PositionM> refill_approach;
    if (sustained_supply(s) && ant.caste==Caste::Worker && local_founding_provisioning(s,ant.id) &&
        can_switch && !care_owned(s,ant.id) && !active_expenditure(p) && !giving_way &&
        stationary && (regular_work || focused) && config.forage_weight) {
      // A worker can approach the handoff it can perceive. A departure
      // still requires actual clearance and a usable return berth.
      const auto depot=colony.nest_position;
      const auto mouth=query_body({s.world,ant.id})->mouth_m;
      const auto patch=depot_mouth_target(ant,depot);
      const bool visible=within_distance(mouth,patch,s.care_profile->perception_radius_m,true) &&
          spatially_clear(mouth,patch);
      const auto opened=!s.geometry_edits.empty();
      const bool refill_fits=refill_crop_room(s) ? p.config.crop_capacity_ug-p.crop.total_ug()>=p.config.transfer_limit_ug :
                                             p.crop.carbs_ug<p.config.transfer_limit_ug;
      if (familiar_liquid_exit(s,ant) && refill_fits &&
          (!focused || (!food_offer && !can_feed_brood)) &&
          !at_wick && !wick_step && !at_meal &&
          (!food_offer || food_offer->first!=ant.position)) {
        // An experienced collector can refill at a familiar berth. The
        // scheduled trip still pays the source and fills real crop space.
        const auto origin=s.connectors.at(ant.id).points[0];
        if (spatially_clear(ant.position,origin)) {
          refill_trip=foraging_home && can_forage(ant);
          if (!refill_trip && ant.position!=origin) {
            refill_approach=worker_depot_step(ant,origin);
          }
        }
      }
      const bool depleted_handoff=visible && colony.nest_food.carbs_ug<buffer;
      const bool inspect_local_soil=local_crop_return(s) && !visible && review_exit && !p.crop.carbs_ug;
      const bool known_source=private_sampling_trip(s,ant) && s.foragers.at(ant.id).last_collected.value;
      const bool refill_crop=!p.crop.carbs_ug || (known_source && p.crop.carbs_ug<p.config.transfer_limit_ug);
      const bool sample_exit=worked_exit(s) && review_exit && refill_crop && foraging_home &&
          at_worked_site(s,ant.id,ant.position);
      if (review_exit && known_source && refill_crop && !foraging_home && !food_offer && !at_wick && !wick_step) {
        resupply_step=worker_depot_step(ant,s.connectors.at(ant.id).points[0]);
        revisiting_exit=resupply_step.has_value();
      }
      if (sample_exit) resupply=can_forage(ant);
      if (!resupply && !revisiting_exit && (depleted_handoff || inspect_local_soil) && !urgent) {
        resupply=depleted_handoff && foraging_home && can_forage(ant);
        if (local_entrance_work(s) && !resupply && !at_depot && !at_meal && !at_wick &&
            !meal_step && !wick_step && (review_exit || (!food_offer && !can_feed_brood)) && excavation==s.excavators.end()) {
          const auto& terrain=s.geometry->config;
          const auto nearby=nearest_grid_point(ant.position,terrain,true);
          if (nearby) {
            // Touch a nearby work surface before enrolling. Positions are
            // candidate local stances, never a known path to exterior food.
            for (const auto dx : {0,-2,2,-4,4}) {
              for (const auto dz : {0,-2,2,-4,4}) {
                const auto site=physical({nearby->x+dx,nearby->y,nearby->z+dz},terrain);
                if ((site==ant.position || clear_worker_site(ant,site,true)) && shallow_soil_cap(site)) {
                  roof_stance=site;
                  break;
                }
              }
              if (roof_stance) break;
            }
          }
        }
        if (responsive_meal(s) && review_exit && !opened && !roof_stance && !resupply &&
            !at_wick && !food_offer && excavation==s.excavators.end()) {
          const auto& g=s.geometry->config;
          const auto origin=nearest_grid_point(ant.position,g,true);
          const auto radius=s.care_profile->perception_radius_m;
          // Sample reachable bands of the local wall. A berth needs both a
          // visible roof and clearance for the existing loaded excavation path.
          // This search reveals neither a surface food location nor a safe exit.
          if (origin) {
            std::optional<PositionM> nearest;
            std::vector<PositionM> indirect;
            auto gap=std::numeric_limits<std::int64_t>::max();
            constexpr std::array<std::pair<int,int>,8> rays{{{1,0},{-1,0},{0,1},{0,-1},{1,1},{1,-1},{-1,1},{-1,-1}}};
            const auto extent=std::min(32,static_cast<int>(radius/g.quantum_m));
            if (work_face_search(s)) {
              // Interleave every lattice column across eight local reviews.
              // Thin corner berths can lie between compass rays. Include all
              // three body heights from the present floor to loaded clearance.
              const auto strip=static_cast<int>((a.decisions/4+ant.id.value)%8);
              for (int dx=-extent+strip;dx<=extent;dx+=8) for (int dz=-extent;dz<=extent;++dz) {
                for (int dy=0;dy<=2;++dy) {
                  const auto site=physical({origin->x+dx,origin->y+dy,origin->z+dz},g);
                  const auto distance=std::llround(portable_care_distance(ant.position,site)*1'000'000);
                  if (distance>=gap || !within_distance(ant.position,site,radius,true) ||
                      !spatially_clear(mouth,site) || !shallow_soil_cap(site)) continue;
                  if (site!=ant.position && !clear_worker_site(ant,site,true)) {
                    if (floor_work_detour(s) && site.y==ant.position.y) indirect.push_back(site);
                    continue;
                  }
                  gap=distance;
                  roof_stance=site;
                }
              }
            }
            for (int ring=0;ring<=extent && !roof_stance;ring+=2) {
              for (const auto& [x,z]:rays) {
                for (int dy=0;dy<=2;dy+=2) {
                  const auto site=physical({origin->x+x*ring,origin->y+dy,origin->z+z*ring},g);
                  if (!within_distance(ant.position,site,radius,true) || !spatially_clear(mouth,site) ||
                      !shallow_soil_cap(site)) continue;
                  if (site==ant.position || clear_worker_site(ant,site,true)) { roof_stance=site; break; }
                  const auto distance=std::llround(portable_care_distance(ant.position,site)*1'000'000);
                  if (distance<gap) { nearest=site; gap=distance; }
                }
                if (roof_stance || !ring) break;
              }
            }
            if (!roof_stance && !indirect.empty()) {
              const auto next=local_floor_route(ant,{},nullptr,indirect);
              if (next!=ant.position) roof_stance=next;
            }
            if (!roof_stance && nearest) {
              const auto goal=*nearest;
              for (std::uint8_t dir=1;dir<=8;++dir) {
                const auto next=snap_micro(translated(ant.position,scale(body_heading(dir),.001)));
                const auto remaining=std::llround(portable_care_distance(next,goal)*1'000'000);
                if (remaining<gap && clear_worker_site(ant,next,true)) {
                  gap=remaining;
                  roof_stance=next;
                }
              }
            }
          }
        }
        if (depleted_handoff && !resupply && !at_depot && !roof_stance) resupply_step=worker_depot_step(ant);
      }
      if (!resupply && !resupply_step && !roof_stance && (urgent || ready) && (opened || a.knows_depot) &&
          (visible || a.knows_depot) && !foraging_home) {
        // Previously visited stores can cue a search even out of sight.
        // The worker only tastes their inventory after returning to it.
        resupply_step=worker_depot_step(ant);
      }
    }
    if (integrated_care(s) && care_owned(s,ant.id)) {
      // The ordinary wake stays alive while the finite care lease owns motion.
      inspect_decision(wake,{},1,static_cast<std::uint64_t>(choice.behavior));
    } else if (at_wick || wick_step) {
      if (ant.caste==Caste::Worker) choice.behavior=IndividualBehavior::Rest;
      choice.drink=at_wick;
      choice.resting_site=wick_step;
      choice.transit=CareAct::DepotApproach;
      choice.meal_steps=s.care_profile->motion->search_steps;
      inspect_decision(wake,{},1,static_cast<std::uint64_t>(choice.behavior));
    } else if (solicitation) {
      if (solicitation->first==ant.position) choice.solicitation=solicitation->second;
      else {
        choice.resting_site=solicitation->first;
        choice.contact_target=solicitation->second;
        choice.transit=CareAct::ApproachNestmate;
        choice.meal_steps=s.care_profile->motion->search_steps;
      }
      inspect_decision(wake,{},1,static_cast<std::uint64_t>(choice.behavior));
    } else if (refill_trip || refill_approach) {
      if (refill_trip) choice.behavior=IndividualBehavior::Forage;
      else {
        choice.resting_site=refill_approach;
        // A visit to the depot is validated as a depot approach. The
        // ordinary resting-site action explicitly excludes this position.
        choice.transit=familiar_site_detour(s) && *refill_approach==colony.nest_position ?
            CareAct::DepotApproach : CareAct::NestReposition;
        if (stimulus_refill_intent(s) && choice.transit==CareAct::NestReposition)
          choice.meal_steps=1; // Carry one refill continuation through this local leg.
      }
      inspect_decision(wake,{},1,static_cast<std::uint64_t>(choice.behavior));
    } else if (body_orientation) {
      choice.resting_site=body_orientation;
      choice.transit=CareAct::NestReposition;
      inspect_decision(wake,{},1,static_cast<std::uint64_t>(choice.behavior));
    } else if (review_exit && (resupply || roof_stance || resupply_step) && !food_offer && !urgent) {
      if (resupply) choice.behavior=IndividualBehavior::Forage;
      else if (roof_stance && *roof_stance==ant.position) choice.behavior=IndividualBehavior::Excavate;
      else {
        choice.resting_site=roof_stance ? roof_stance : resupply_step;
        choice.transit=revisiting_exit || (work_face_search(s) && roof_stance && *roof_stance!=colony.nest_position) ?
                       CareAct::NestReposition : CareAct::DepotApproach;
      }
      inspect_decision(wake,{},1,static_cast<std::uint64_t>(choice.behavior));
    } else if (food_offer) {
      choice.contact_target=food_offer->second;
      if (food_offer->first==ant.position) choice.behavior=IndividualBehavior::Nurse;
      else {
        choice.resting_site=food_offer->first;
        choice.transit=CareAct::ApproachNestmate;
        if (crop_exchange(s)) choice.meal_steps=s.care_profile->motion->search_steps;
      }
      inspect_decision(wake,{},1,static_cast<std::uint64_t>(choice.behavior));
    } else if (can_feed_brood) {
      choice.care=true;
      choice.behavior=IndividualBehavior::Nurse;
      inspect_decision(wake,{},1,static_cast<std::uint64_t>(choice.behavior));
    } else if (chamber_step) {
      choice.resting_site=chamber_step;
      choice.transit=familiar_site_detour(s) && *chamber_step==colony.nest_position ?
          CareAct::DepotApproach : CareAct::NestReposition;
      inspect_decision(wake,{},1,static_cast<std::uint64_t>(choice.behavior));
    } else if (at_meal || meal_step) {
      if (at_meal) {
        if (ant.caste==Caste::Worker) choice.behavior=IndividualBehavior::Rest;
        else choice.queen_meal=local_founding_feeding(s) && founding_foundress(ant.id);
        urgent=true;
      } else {
        choice.resting_site=meal_step;
        choice.transit=CareAct::DepotApproach;
        choice.meal_steps=s.care_profile->motion->search_steps;
      }
      inspect_decision(wake,{},1,static_cast<std::uint64_t>(choice.behavior));
    } else if (giving_way) {
      if (ant.caste==Caste::Worker) choice.behavior=IndividualBehavior::Rest;
      choice.resting_site=giving_way->first;
      choice.contact_target=giving_way->second;
      choice.transit=CareAct::YieldToCarrier;
      inspect_decision(wake,{},1,static_cast<std::uint64_t>(choice.behavior));
    } else if (food_search_step) {
      choice.resting_site=food_search_step;
      choice.transit=CareAct::NestReposition;
      inspect_decision(wake,{},1,static_cast<std::uint64_t>(choice.behavior));
    } else if (ant.caste==Caste::Queen) {
      if (!mouth_access(s) && anatomical_nest(s) && can_switch && founding_foundress(ant.id) &&
          !within_contact(ant.position,colony.nest_position,s.config) &&
          within_distance(ant.position,colony.nest_position,s.care_profile->perception_radius_m,true) &&
          spatially_clear(ant.position,colony.nest_position) &&
          foundress_nest_meal(s.founding->profile,p,s.founding_reserves.at(ant.id),colony.nest_food).total_ug()) {
        // The already familiar, locally reachable handoff site can cue a
        // paid approach. Physiology still debits actual stock at intake.
        choice.resting_site=worker_depot_step(ant);
        choice.transit=CareAct::DepotApproach;
      }
      choice.care=!choice.resting_site && can_switch && !urgent && s.m.now>a.last_program_change &&
                  local_care_available({s.world,ant.id});
      inspect_decision(wake,{},1,static_cast<std::uint64_t>(choice.behavior));
    } else if (roof_stance && *roof_stance!=ant.position) {
      choice.resting_site=roof_stance;
      inspect_decision(wake,{},1,static_cast<std::uint64_t>(choice.behavior));
    } else if (resupply || resupply_step) {
      if (resupply) choice.behavior=IndividualBehavior::Forage;
      choice.resting_site=resupply_step;
      choice.transit=revisiting_exit && !(familiar_site_detour(s) && resupply_step==colony.nest_position) ?
          CareAct::NestReposition : CareAct::DepotApproach;
      inspect_decision(wake,{},1,static_cast<std::uint64_t>(choice.behavior));
    } else if (worker_motor(s) && (!a.decisions ||
               (buffer && !s.foragers.contains(ant.id) && s.care.contains(ant.id) &&
                s.care.at(ant.id).act==CareAct::DepotApproach)) && p.mother.value &&
               p.behavior==IndividualBehavior::Paused && !foraging_home && !roof_stance &&
               (choice.resting_site=worker_depot_step(ant))) {
      // Emergence schedules a direct review, before any return notification.
      choice.transit=CareAct::DepotApproach;
      inspect_decision(wake,{},1,static_cast<std::uint64_t>(choice.behavior));
    } else if (!worker_motor(s) && bounded_brood_space(s) && can_switch && !at_depot && stationary && p.mother.value &&
               (!local_nest_activity(s) || ready || urgent) &&
               within_contact(ant.position,colony.nest_position,s.config) &&
               clear_care_segment(ant.position,colony.nest_position,body_half(ant.id))) {
      // A worker emerging among the brood can see the nearby depot. Use the
      // existing paid return action before assigning a depot-owned program.
      choice.care=true;
      inspect_decision(wake,{},1,static_cast<std::uint64_t>(choice.behavior));
    } else if (can_switch && return_review && s.long_term) {
      choice.behavior=IndividualBehavior::Rest;
      ContactSample local;
      if (foraging_home && !urgent && config.exchange_enabled && local_founding_provisioning(s,ant.id)) {
        const auto stock=private_sampling_trip(s,ant) && !within_contact(ant.position,colony.nest_position,s.config)
            ? FoodMass{} : colony.nest_food;
        const auto available = sum(stock,founding_gift_supply(s.founding->profile,p));
        if (available.total_ug()) {
          local = sample_contacts({s.world,ant.id},a.decisions ^ UINT64_C(0x45434f4c4f4759));
          choice.sample = {0,local.candidates_examined,local.bucket_queries,local.tree_visits,0};
          for (const auto other : local.ants) {
            const auto receiver = query_physiology(other);
            const auto stage = query_ant(other)->stage;
            if (receiver && receiver->crop.total_ug()<receiver->config.crop_capacity_ug &&
                ingredient_min(available,signaled_need(*receiver,stage,true)).total_ug()) {
              choice.behavior=IndividualBehavior::Nurse;
              break;
            }
          }
        }
      }
      if (worker_motor(s) && at_depot && !urgent && choice.behavior==IndividualBehavior::Rest)
        choice.resting_site=local_resting_site(ant);
      inspect_decision(wake,local,1,static_cast<std::uint64_t>(choice.behavior));
    } else if (can_switch && ready && !focused) {
      const auto sample = sample_contacts(
          {s.world, ant.id}, a.decisions ^ UINT64_C(0x45434f4c4f4759));
      choice.sample = {0, sample.candidates_examined, sample.bucket_queries,
                       sample.tree_visits, 0};
      bool need = false, crop_work = false, unmet = false;
      const bool nest_contact =
          within_contact(ant.position,colony.nest_position,s.config) &&
          (!s.surface || s.geometry || s.config.continuous_spatial_motion ||
           s.surface->locate(ant.position) ==
               s.surface->locate(colony.nest_position)) &&
          spatially_clear(ant.position, colony.nest_position);
      const auto stock = nest_contact ? colony.nest_food : FoodMass{};
      // ENGINEERING_FIXTURE. A worker already in contact with the depot can
      // assess this supply. No estimate from a different part of the nest.
      const bool low_pantry = s.ecological && s.ecological->local_pantry_checks && s.surface && nest_contact &&
          (buffer ? (stock.carbs_ug < buffer || stock.water_ug < buffer) : stock.carbs_ug < p.config.transfer_limit_ug);
      const auto available = sum(p.crop, stock);
      for (const auto other : sample.ants) {
        const auto q = query_physiology(other);
        if (!q)
          continue;
        const auto stage = s.ants.get(s.ants.index.at(other.id)).stage;
        const auto signal=signaled_need(*q,stage,s.long_term!=nullptr);
        if (signal.total_ug() && ingredient_min(available,signal)!=signal) unmet=true;
        if (q->crop.total_ug() < q->config.crop_capacity_ug &&
            ingredient_min(available, signaled_need(*q, stage,s.long_term!=nullptr)).total_ug())
          need = true;
        if (q->crop.total_ug() < q->config.crop_capacity_ug &&
            ingredient_min(p.crop, signaled_need(*q, stage,s.long_term!=nullptr)).total_ug())
          crop_work = true;
      }
      bool forage = foraging_home && can_forage(ant);
      const bool forage_possible = forage;
      bool refill = false;
      if (forage && local_founding_provisioning(s,ant.id) && s.founding->profile.dietary &&
          s.founding->profile.dietary->local_resupply && s.foragers.contains(ant.id) && s.foragers.at(ant.id).collections) {
        const auto& founding=s.founding->profile;
        const auto understocked=[&](EntityId id,const PhysiologyState& local) {
          const auto deficit=founding_resupply_shortfall(founding,local,s.founding_reserves.at(id),
                               s.founding->founder==id,config.decision_interval);
          return ingredient_min(deficit,stock)!=deficit;
        };
        refill=understocked(ant.id,p);
        for (const auto other : sample.ants) {
          if (refill) break;
          if (s.founding_reserves.contains(other.id) && query_ant(other)->stage==LifeStage::Adult)
            refill=understocked(other.id,*query_physiology(other));
        }
      }
      bool soil = false;
      if (at_depot && s.geometry && (sample.ants.size()>=2 || local_nest_activity(s)) &&
          quantized(ant.position,s.geometry->config)) {
        const auto &g = s.geometry->config;
        const auto origin = *quantized(ant.position, g);
        constexpr std::array<PointQ, 6> directions{{{1, 0, 0},
                                                    {-1, 0, 0},
                                                    {0, 1, 0},
                                                    {0, -1, 0},
                                                    {0, 0, 1},
                                                    {0, 0, -1}}};
        for (const auto d : directions)
          for (std::int32_t step = 1; step <= g.reach_q; ++step) {
            const auto material = query_material(
                physical({origin.x + d.x * step, origin.y + d.y * step,
                          origin.z + d.z * step},
                         g));
            if (material == Material::Soil)
              soil = true;
            if (material != Material::Void)
              break; // Rock occludes soil behind it.
          }
      }
      if (!soil && at_depot && nest_scoring(s)!=NestScoring::Original && s.excavators.contains(ant.id))
        soil=s.excavators.at(ant.id).digs!=0;
      if (s.long_term && s.long_term->demand_feedback) {
        const auto self=signaled_need(p,ant.stage);
        forage=forage && (low_pantry || unmet || (self.total_ug() && ingredient_min(stock,self)!=self));
        const bool exit_work=buffer && !forage_possible &&
            ((at_depot && low_pantry && shallow_soil_cap(ant.position)) ||
             (roof_stance && *roof_stance==ant.position) || (at_dig_origin && low_pantry && shallow_soil_cap(ant.position)));
        soil=!urgent && (exit_work || (soil && local_space_demand({s.world,ant.id},sample.ants.size())));
      }
      if (urgent &&
          ingredient_min(stock, nutrient_demand(p, ant.stage)).total_ug())
        choice.behavior = IndividualBehavior::Rest;
      else if (refill)
        choice.behavior = IndividualBehavior::Forage;
      else if (config.local_work_continuation && !urgent &&
               config.exchange_enabled && crop_work &&
               p.behavior == IndividualBehavior::Nurse)
        // Continue work witnessed in this local encounter. No stored request,
        // global deficit or promised transfer survives a later failed contact.
        choice.behavior = IndividualBehavior::Nurse;
      else {
        const bool care=integrated_care(s) && !urgent && local_care_available({s.world,ant.id});
        const std::array<std::pair<IndividualBehavior, std::uint64_t>, 5>
            options{
                {{IndividualBehavior::Rest, config.rest_weight},
                 {IndividualBehavior::Forage,
                  forage ? config.forage_weight : 0U},
                 {IndividualBehavior::Nurse,
                  need && config.exchange_enabled ? config.nurse_weight : 0U},
                 {IndividualBehavior::Excavate,
                  soil ? config.excavate_weight : 0U},
                 {IndividualBehavior::Nurse, care ? config.nurse_weight : 0U}}};
        std::uint64_t total = 0;
        for (const auto &option : options)
          total += option.second;
        auto rng = individual_rng(s.seed ^ UINT64_C(0x533645434f4c4f47), ant.id,
                                  a.decisions);
        auto draw = bounded_draw(rng, total);
        for (std::size_t i=0;i<options.size();++i) {
          const auto [program,weight]=options[i];
          if (draw < weight) {
            choice.behavior = program;
            choice.care=i==options.size()-1;
            break;
          }
          draw -= weight;
        }
        // A successful delivery can satisfy the ordinary refill threshold at
        // the instant it leaves a cue. A local responder can still work toward
        // one additional load of carbohydrate above that threshold.
        const bool room_for_recruitment = !buffer || low_pantry || unmet ||
            stock.carbs_ug < buffer ||
            stock.carbs_ug-buffer < ant.carrying_capacity_ug;
        if (s.ecological && s.ecological->recruitment && forage_possible && !urgent && room_for_recruitment &&
            p.behavior != IndividualBehavior::Forage &&
            (!s.foragers.contains(ant.id) || !s.foragers.at(ant.id).collections)) {
          const auto consider=[&](EntityId scout,const auto& cue) {
            if (scout==ant.id || cue.fact<=choice.cue ||
                s.m.now.milliseconds-cue.time.milliseconds>=s.ecological->cue_lifetime.milliseconds ||
                !within_contact(ant.position,cue.position,s.config) ||
                !spatially_clear(ant.position,cue.position)) return;
            const auto other=query_ant({s.world,scout});
            if (other && other->stage==LifeStage::Adult && other->colony==ant.colony) {
              choice.scout=scout;
              choice.cue=cue.fact;
            }
          };
          if (buffer) {
            // A cue remains at the handoff point for its declared lifetime.
            // The other worker can detect it on arrival after the scout has
            // cleared the passage. Food coordinates are never transferred.
            for (const auto& [scout,cue]:s.recruitment_signals) consider(scout,cue);
          } else for (const auto other:sample.ants) {
            const auto cue=s.recruitment_signals.find(other.id);
            if (cue!=s.recruitment_signals.end()) consider(other.id,cue->second);
          }
          if (choice.cue.value && choice.behavior != IndividualBehavior::Forage) {
            auto response = individual_rng(s.seed ^ UINT64_C(0x524543525549544d), ant.id, a.decisions);
            if (bounded_draw(response, 1000000) < s.ecological->cue_response_ppm) {
              choice.behavior = IndividualBehavior::Forage;
              choice.care = false;
              choice.recruited = true;
            }
          }
        }
      }
      if (worker_motor(s) && !foraging_home && !choice.care && stationary && !roof_stance &&
          ((urgent && !nest_contact) || (!urgent && (unmet || low_pantry) && config.forage_weight &&
            s.surface && (p.crop.total_ug()<p.config.crop_capacity_ug/2 ||
                          choice.behavior==IndividualBehavior::Rest)))) {
        choice.resting_site=worker_depot_step(ant);
        if (choice.resting_site) choice.transit=CareAct::DepotApproach;
      }
      if (buffer && stationary && !urgent && !choice.care && !choice.resting_site &&
          choice.behavior==IndividualBehavior::Rest) {
        // ENGINEERING_FIXTURE. Adult experience raises a small lottery weight.
        // Competing work remains eligible at the next local review.
        const auto age=s.m.now.milliseconds-a.enrolled_at.milliseconds;
        const auto weight=8+std::min<std::int64_t>(3,age/(2*static_cast<std::int64_t>(founding_day_ms)));
        auto patrol=individual_rng(s.seed ^ UINT64_C(0x454e5452414e4345),ant.id,a.decisions);
        if (bounded_draw(patrol,32)<static_cast<std::uint64_t>(weight)) {
          choice.resting_site=entrance_patrol_step(ant);
          if (choice.resting_site) choice.transit=CareAct::EntrancePatrol;
        }
      }
      if (!choice.resting_site && (at_depot || worker_motor(s)) && !urgent &&
          choice.behavior==IndividualBehavior::Rest)
        choice.resting_site=local_resting_site(ant);
      inspect_decision(wake, sample, 1, static_cast<std::uint64_t>(choice.behavior));
    } else {
      inspect_decision(wake, {}, 1, static_cast<std::uint64_t>(choice.behavior));
    }
    const bool free_to_offer=!choice.resting_site || (local_founding_feeding(s) &&
        (choice.transit==CareAct::NestReposition || choice.transit==CareAct::EntrancePatrol));
    if (local_traffic(s) && ant.caste==Caste::Worker && can_switch && !urgent && !choice.care && free_to_offer &&
        !care_owned(s,ant.id) && !active_expenditure(p) && (p.behavior==IndividualBehavior::Rest || p.behavior==IndividualBehavior::Paused) &&
        (choice.behavior==IndividualBehavior::Rest || choice.behavior==IndividualBehavior::Paused)) {
      if (const auto offer=local_food_offer(ant)) {
        choice.contact_target=offer->second;
        if (offer->first==ant.position) {
          choice.resting_site.reset();
          choice.behavior=IndividualBehavior::Nurse;
        }
        else {
          choice.resting_site=offer->first;
          choice.transit=CareAct::ApproachNestmate;
          if (crop_exchange(s)) choice.meal_steps=s.care_profile->motion->search_steps;
        }
      } else if (!choice.resting_site) {
        if (const auto contact=local_contact_step(ant)) {
          choice.resting_site=contact->first;
          choice.contact_target=contact->second;
          choice.transit=CareAct::ApproachNestmate;
        }
      }
    }
    if (departure_review(s) && choice.behavior==IndividualBehavior::Excavate &&
        p.behavior!=IndividualBehavior::Excavate && excavation!=s.excavators.end() && excavation->second.path_size) {
      const auto& work=excavation->second;
      const auto end=physical(work.path[work.path_size-1],s.geometry->config);
      if (ant.position!=end) {
        // An off-depot worker cannot restart its old dig from a different berth.
        // Keep the itinerary. Only an actual local return can make it usable again.
        choice.behavior=IndividualBehavior::Rest;
        if (within_distance(ant.position,end,s.care_profile->perception_radius_m,true) &&
            clear_worker_site(ant,end,true)) {
          choice.resting_site=end;
          choice.transit=CareAct::DepotApproach;
        }
      }
    }
    choices.push_back(std::move(choice));
  }
  // Every choice uses the same committed boundary. Submission/enrollment order
  // does not determine an individual's program or its private random stream.
  std::sort(choices.begin(), choices.end(), [](const auto &a, const auto &b) {
    return a.event.actor < b.event.actor;
  });
  for (const auto &choice : choices) {
    const auto id = choice.event.actor;
    auto a = s.autonomy.at(id);
    a.wake = {};
    bump(a.decisions);
    tx.autonomy.set(id, a);
    if (choice.cue.value) {
      const auto ant = s.ants.get(s.ants.index.at(id));
      WorldEvent signal;
      signal.kind = FactKind::RecruitmentObserved;
      signal.actor = id; signal.colony = ant.colony; signal.stage = ant.stage;
      signal.position = ant.position; signal.source = choice.event.id;
      signal.payload = choice.scout.value; signal.random_value = choice.cue.value;
      tx.fact(signal);
      if (choice.recruited) {
        signal.kind = FactKind::RecruitmentActivated;
        tx.fact(signal);
      }
    }
    if (choice.care)
      start_autonomous_care(tx,{s.world,id},choice.event.id);
    else if (choice.resting_site)
      start_resting_move(tx,s.ants.get(s.ants.index.at(id)),*choice.resting_site,choice.event.id,choice.transit,
                         choice.contact_target,choice.meal_steps);
    else if (choice.behavior != s.physiology.at(id).behavior ||
             (local_founding_feeding(s) && choice.contact_target.value && choice.behavior==IndividualBehavior::Nurse))
      change_behavior(tx, {s.world, id}, choice.behavior, choice.event.id,false,choice.contact_target);
    const auto &sample = choice.sample;
    auto &work = s.m.contact_work;
    bump(work.decisions);
    work.candidates_examined =
        add(work.candidates_examined, sample.candidates_examined);
    work.bucket_queries = add(work.bucket_queries, sample.bucket_queries);
    work.tree_visits = add(work.tree_visits, sample.tree_visits);
    work.maximum_candidates =
        std::max(work.maximum_candidates, sample.candidates_examined);
    const auto ant = s.ants.get(s.ants.index.at(id));
    WorldEvent f;
    f.kind = FactKind::AutonomyDecision;
    f.source = choice.event.id;
    f.actor = id;
    f.colony = ant.colony;
    f.stage = ant.stage;
    f.position = ant.position;
    f.payload = a.decisions;
    f.random_value = sample.candidates_examined;
    tx.fact(f);
    if (choice.queen_meal) draw_foundress_meal(tx,ant,choice.event.id);
    if (choice.drink) draw_founding_water(tx,choice.event,ant);
    schedule_autonomy(tx, id);
  }
  for (const auto& choice:choices) if (choice.solicitation.value) {
    const auto queen=*query_ant({s.world,choice.event.actor});
    request_food_review(tx,queen,choice.solicitation);
  }
}
} // namespace antworld
