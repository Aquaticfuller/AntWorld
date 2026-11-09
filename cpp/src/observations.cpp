#include "state.hpp"
#include <map>

namespace antworld {
BehaviorWindow WorldRuntime::behavior_window(AntRef ref, SimTime begin, SimTime end) const {
    if (!query_ant(ref) || begin.milliseconds<0 || end<begin || end>state_->m.now)
        throw std::invalid_argument("invalid biological observation window");
    BehaviorWindow out; out.begin=begin; out.end=end;
    const auto overlap=[&](SimTime from,SimTime to) {
        return static_cast<std::uint64_t>(std::max<std::int64_t>(0,std::min(to.milliseconds,end.milliseconds)-std::max(from.milliseconds,begin.milliseconds)));
    };
    std::map<ScheduledId,BehaviorObservation> active;
    std::vector<std::pair<SimTime,SimTime>> intervals;
    auto close=[&](const BehaviorObservation& o,SimTime at) {
        if (!o.duration_known) return;
        const auto duration=overlap(o.began_at,at); out.duration_ms[static_cast<std::size_t>(o.act)]+=duration;
        if (o.act==CareAct::Inactive) out.known_inactive_ms+=duration;
        else out.known_active_ms+=duration;
        if (duration) intervals.emplace_back(SimTime{std::max(begin.milliseconds,o.began_at.milliseconds)},SimTime{std::min(end.milliseconds,at.milliseconds)});
    };
    IndividualBehavior program=IndividualBehavior::Paused; SimTime program_begin{}; bool physiological=false,care_enabled=false;
    SimTime care_begin{};
    for (const auto& e:state_->journal) {
        if (e.time>end) break;
        if (e.actor!=ref.id) continue;
        if (e.kind==FactKind::PhysiologyEnabled) { physiological=true; program_begin=e.time; }
        if (e.kind==FactKind::BehaviorChanged || e.kind==FactKind::AntDied) {
            if (physiological) out.legacy_program_ms[static_cast<std::size_t>(program)]+=overlap(program_begin,e.time);
            program=e.kind==FactKind::AntDied?IndividualBehavior::Paused:static_cast<IndividualBehavior>(e.payload);
            program_begin=e.time; if (e.kind==FactKind::AntDied) physiological=false;
        }
        if (e.kind==FactKind::CareProgramChanged) {
            if (care_enabled) out.care_program_ms+=overlap(care_begin,e.time);
            care_enabled=e.payload!=0; care_begin=e.time;
        }
        if (e.kind!=FactKind::BiologicalObservation) continue;
        const auto& o=e.observation; const auto i=static_cast<std::size_t>(o.act);
        const bool in=e.time>=begin && e.time<end;
        if (o.phase==ObservationPhase::Opportunity) { if (in) ++out.contact_opportunities; }
        else if (o.phase==ObservationPhase::Selected) { if (in) ++out.selected[i]; }
        else if (o.phase==ObservationPhase::Started) { if (in) ++out.started[i]; if(o.duration_known) active[o.bout]=o; }
        else {
            if (o.duration_known && active.contains(o.bout)) { close(active.at(o.bout),e.time); active.erase(o.bout); }
            if (in) {
                if (o.phase==ObservationPhase::Completed) {
                    ++out.completed[i]; out.transferred=detail::sum(out.transferred,e.transferred);
                    if (!o.duration_known) ++out.unknown_duration_completions;
                    if (o.target.value && ((o.act>=CareAct::InspectBrood && o.act<=CareAct::CloseWorkerContact) ||
                        o.act==CareAct::TransferNutrition)) ++out.successful_contacts;
                } else ++out.interrupted[i];
            }
        }
    }
    for (const auto& [id,o]:active) { (void)id; close(o,end); }
    if (physiological) out.legacy_program_ms[static_cast<std::size_t>(program)]+=overlap(program_begin,end);
    if (care_enabled) out.care_program_ms+=overlap(care_begin,end);
    std::sort(intervals.begin(),intervals.end()); std::uint64_t covered=0; SimTime until=begin;
    for (const auto& [from,to]:intervals) { if(to>until) covered+=static_cast<std::uint64_t>(to.milliseconds-std::max(from.milliseconds,until.milliseconds)); until=std::max(until,to); }
    out.unknown_activity_ms=static_cast<std::uint64_t>(end.milliseconds-begin.milliseconds)-covered;
    return out;
}
} // namespace antworld
