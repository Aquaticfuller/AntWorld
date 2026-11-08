#pragma once
#include "checkpoint_codec.hpp"
#include "social_internal.hpp"

namespace antworld::detail {
template<class S> void write_social(Writer& w, const S& s) {
    w.put(s.social != nullptr,1);
    if (s.social) {
        const auto& c = *s.social;
        w.put(c.demand_sensitive,1); w.put(c.bounded_contacts,1); w.put(c.exchange_enabled,1);
        w.put(c.encounter_budget,4); w.time(c.decision_interval); w.time(c.minimum_program_time);
        w.put(c.rest_weight,4); w.put(c.forage_weight,4); w.put(c.nurse_weight,4); w.put(c.excavate_weight,4);
        const auto& a=s.m.contact_work;
        w.put(a.decisions); w.put(a.candidates_examined); w.put(a.bucket_queries); w.put(a.tree_visits); w.put(a.maximum_candidates);
    }
}
template<class S> void read_social(Reader& r, S& s) {
    if (r.flag()) {
        auto c = std::make_shared<SocialConfig>();
        c->demand_sensitive=r.flag(); c->bounded_contacts=r.flag(); c->exchange_enabled=r.flag();
        c->encounter_budget=static_cast<std::uint32_t>(r.get(4));
        c->decision_interval=r.time(); c->minimum_program_time=r.time();
        c->rest_weight=static_cast<std::uint32_t>(r.get(4)); c->forage_weight=static_cast<std::uint32_t>(r.get(4));
        c->nurse_weight=static_cast<std::uint32_t>(r.get(4)); c->excavate_weight=static_cast<std::uint32_t>(r.get(4));
        validate_social(*c); s.social=std::move(c);
        s.m.contact_work={r.get(),r.get(),r.get(),r.get(),r.get()};
    }
    std::uint64_t configured=0;
    for (const auto& e:s.journal) if (e.kind==FactKind::SocialConfigured) {
        ensure(s.social && e.time==SimTime{} && !e.actor.value && !e.colony.value && !e.source.value &&
            !e.payload && !e.random_value && e.position==PositionM{},"invalid social configuration evidence");
        ++configured;
    }
    ensure(configured==(s.social?1U:0U),"missing/duplicate social policy evidence");
    ContactWork audit;
    for (const auto& e:s.journal) if (e.kind==FactKind::NutritionDecision) {
        if (s.social) {
            bump(audit.decisions); audit.candidates_examined=add(audit.candidates_examined,e.random_value);
            audit.maximum_candidates=std::max(audit.maximum_candidates,e.random_value);
        } else ensure(!e.random_value,"unexpected legacy encounter count");
    }
    const auto& actual=s.m.contact_work;
    ensure(audit.decisions==actual.decisions && audit.candidates_examined==actual.candidates_examined &&
        audit.maximum_candidates==actual.maximum_candidates,"contact work disagrees with decisions");
    if (s.social && s.social->bounded_contacts)
        ensure(actual.maximum_candidates<=s.social->encounter_budget && actual.bucket_queries<=multiply(actual.decisions,27),
            "contact budget exceeded");
    rebuild_contacts(s);
}
} // namespace antworld::detail
