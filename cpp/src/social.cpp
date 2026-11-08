#include "social_internal.hpp"
#include "behavior_rng.hpp"

namespace antworld {
void WorldRuntime::configure_social(const SocialConfig& config) {
    auto& s = *state_;
    if (s.social || s.m.now != SimTime{} || s.m.watermark)
        throw std::invalid_argument("social policy requires an unexecuted world");
    detail::validate_social(config);
    auto policy = std::make_shared<const SocialConfig>(config);
    Transaction tx(s,limits_); s.social = std::move(policy);
    for (std::size_t i=0;i<s.ants.size();++i) {
        const auto a=s.ants.get(i); if (a.alive()) index_contact(tx,a.id,a.position);
    }
    WorldEvent fact; fact.kind = FactKind::SocialConfigured; tx.fact(fact); tx.commit();
}
std::optional<SocialConfig> WorldRuntime::social_config() const {
    return state_->social ? std::optional<SocialConfig>{*state_->social} : std::nullopt;
}
ContactWork WorldRuntime::contact_work() const { return state_->m.contact_work; }
void WorldRuntime::index_contact(Transaction& tx, EntityId id, std::optional<PositionM> position) {
    using namespace detail;
    auto& s=*state_; if (!s.social || !s.social->bounded_contacts) return;
    const auto key=position ? std::optional<PointQ>{contact_key(*position,s.config.contact_distance_m)} : std::nullopt;
    if (s.contact_nodes.contains(id)) {
        const auto old=s.contact_nodes.at(id).bucket; if (key && *key==old) return;
        const auto root=contact_remove(s.contact_nodes,tx.contact_nodes,s.contact_roots.at(old),id);
        if (root.value) tx.contact_roots.set(old,root); else tx.contact_roots.erase(old);
        tx.contact_nodes.erase(id);
    }
    if (key) {
        tx.contact_nodes.set(id,contact_node(id,*key));
        const auto root=s.contact_roots.contains(*key)?s.contact_roots.at(*key):EntityId{};
        tx.contact_roots.set(*key,contact_insert(s.contact_nodes,tx.contact_nodes,root,id));
    }
}
ContactSample WorldRuntime::sample_contacts(AntRef ref, std::uint64_t decision) const {
    using namespace detail;
    const auto& s=*state_; const auto ant=query_ant(ref);
    if (!ant || !ant->alive() || !s.social) throw std::invalid_argument("contact sampling requires a living social actor");
    ContactSample result;
    auto consider=[&](EntityId id) {
        ++result.candidates_examined; const auto other=s.ants.get(s.ants.index.at(id));
        if (id!=ref.id && other.alive() && other.colony==ant->colony &&
            distance(ant->position,other.position)<=s.config.contact_distance_m &&
            spatially_clear(ant->position,other.position)) result.ants.push_back({s.world,id});
    };
    if (!s.social->bounded_contacts) {
        // Deliberate exhaustive ablation, never used by default S6 individual policies.
        for (const auto& id:s.ants.identities) consider(id.id);
        return result;
    }
    std::vector<std::pair<EntityId,std::uint64_t>> buckets(0);
    const auto key=contact_key(ant->position,s.config.contact_distance_m);
    std::uint64_t total=0;
    for (int x=-1;x<=1;++x) for (int y=-1;y<=1;++y) for (int z=-1;z<=1;++z) {
        ++result.bucket_queries; const auto it=s.contact_roots.find({key.x+x,key.y+y,key.z+z});
        if (it!=s.contact_roots.end()) { total+=contact_size(s.contact_nodes,it->second); buckets.emplace_back(it->second,total); }
    }
    const auto count=std::min<std::uint64_t>(s.social->encounter_budget,total);
    auto rng=individual_rng(s.seed ^ UINT64_C(0x5336434f4e544143),ref.id,decision);
    // Floyd sampling is bounded by the encounter budget even in dense buckets.
    std::vector<std::uint64_t> ranks(0); ranks.reserve(static_cast<std::size_t>(count));
    for (std::uint64_t j=total-count;j<total;++j) {
        const auto draw=bounded_draw(rng,j+1);
        ranks.push_back(std::find(ranks.begin(),ranks.end(),draw)!=ranks.end()?j:draw);
    }
    std::sort(ranks.begin(),ranks.end());
    for (const auto rank:ranks) {
        std::uint64_t previous=0;
        for (const auto& [root,end]:buckets) {
            if (rank<end) { consider(contact_rank(s.contact_nodes,root,rank-previous,result.tree_visits)); break; }
            previous=end;
        }
    }
    std::sort(result.ants.begin(),result.ants.end(),[](auto a,auto b){return a.id<b.id;});
    return result;
}
} // namespace antworld
