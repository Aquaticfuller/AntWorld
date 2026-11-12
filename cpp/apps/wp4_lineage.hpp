#pragma once

#include "antworld/core/world_runtime.hpp"

#include <fstream>
#include <iomanip>
#include <set>
#include <sstream>
#include <stdexcept>

namespace antworld::wp4 {
inline constexpr std::size_t individual_limit = 128;
inline constexpr std::size_t projection_limit = 256 * 1024;

inline void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

inline std::ostream& mass(std::ostream& out, const FoodMass& value) {
    for (const auto component : value.components()) out << ',' << component;
    return out;
}

inline std::ofstream output(const std::filesystem::path& path) {
    std::ofstream stream(path, std::ios::binary);
    stream.exceptions(std::ios::badbit | std::ios::failbit);
    stream << std::setprecision(17);
    return stream;
}

// Caller owns the immutable cut. The SQLite sidecar stays on its accepted schema.
class Lineage {
public:
    explicit Lineage(const std::filesystem::path& folder)
        : states_(output(folder / "lineage.csv")), inputs_(output(folder / "lineage_inputs.csv")) {
        states_ << "cut,cursor,sim_ms,id,stage,caste,x_m,y_m,z_m,program,death_cause,settled_at_ms,"
                   "next_uptake_ms,progress_ms,energy_nj,hydration_ug,tissue_ug,oxidized_carbs_ug,lost_water_ug,"
                   "dissipated_nj,exported_nj,water_remainder,crop_carbs_ug,crop_protein_ug,crop_water_ug,crop_other_ug\n";
        inputs_ << "id,mother,born_ms,first_cut,initial_energy_nj,initial_water_ug,initial_tissue_ug,"
                   "initial_carbs_ug,initial_protein_ug,initial_crop_water_ug,initial_other_ug,"
                   "basal_nj_per_ms,active_nj_per_ms,yield_nj_per_ug,water_ug_per_period,water_period_ms,"
                   "uptake_period_ms,egg_ms,larva_ms,pupa_ms,larva_target_ug,adult_protein_target_ug,"
                   "carb_rate_ug_per_s,protein_rate_ug_per_s,water_rate_ug_per_s,"
                   "energy_cap_nj,hydration_cap_ug,crop_cap_ug,transfer_limit_ug,behavior_ms\n";
    }

    std::size_t capture(const WorldRuntime& world, std::size_t cut, std::uint64_t cursor, SimTime at) {
        require(world.summary().ant_count <= individual_limit, "WP-4 lineage census exceeded its cap");
        std::ostringstream states, inputs;
        states << std::setprecision(17);
        const auto world_id = world.summary().world;
        for (const auto& ant : world.ant_states()) {
            const auto p = world.query_physiology({world_id, ant.id});
            require(p.has_value(), "WP-4 expected physiology on every fixture individual");
            if (seen_.insert(ant.id).second) initial(inputs, ant, *p, cut);
            states << cut << ',' << cursor << ',' << at.milliseconds << ',' << ant.id.value << ','
                   << static_cast<unsigned>(ant.stage) << ',' << static_cast<unsigned>(ant.caste) << ','
                   << ant.position.x << ',' << ant.position.y << ',' << ant.position.z << ','
                   << static_cast<unsigned>(p->behavior) << ',' << static_cast<unsigned>(p->death_cause)
                   << ',' << p->updated_at.milliseconds << ',' << p->next_absorption.milliseconds << ','
                   << p->stage_progress.milliseconds << ',' << p->body_energy_nj << ',' << p->hydration_ug
                   << ',' << p->tissue_protein_ug << ',' << p->oxidized_carbs_ug << ',' << p->lost_water_ug
                   << ',' << p->dissipated_energy_nj << ',' << p->exported_energy_nj << ',' << p->water_loss_remainder;
            mass(states, p->crop) << '\n';
        }
        const auto bytes = states.view().size() + inputs.view().size();
        require(bytes <= projection_limit, "WP-4 lineage cut exceeded its byte cap");
        states_ << states.view();
        inputs_ << inputs.view();
        return bytes;
    }

    void close() {
        states_.close();
        inputs_.close();
    }

private:
    static void initial(std::ostream& out, const AntState& ant, const PhysiologyState& p, std::size_t cut) {
        const auto& c = p.config;
        out << ant.id.value << ',' << p.mother.value << ',' << ant.born_at.milliseconds << ',' << cut << ','
            << p.initial.body_energy_nj << ',' << p.initial.hydration_ug << ',' << p.initial.tissue_protein_ug;
        mass(out, p.initial.crop) << ',' << c.basal_nj_per_ms << ',' << c.active_nj_per_ms << ','
            << c.carbohydrate_yield_nj_per_ug << ',' << c.water_loss_ug_per_period << ',' << c.water_loss_period.milliseconds
            << ',' << c.absorption_period.milliseconds << ',' << c.egg_duration.milliseconds << ','
            << c.larva_duration.milliseconds << ',' << c.pupa_duration.milliseconds << ','
            << c.larval_protein_requirement_ug << ',' << c.adult_protein_target_ug << ',' << c.carb_absorption_ug_per_s
            << ',' << c.protein_absorption_ug_per_s << ',' << c.water_absorption_ug_per_s << ',' << c.energy_capacity_nj
            << ',' << c.hydration_capacity_ug << ',' << c.crop_capacity_ug << ',' << c.transfer_limit_ug
            << ',' << c.behavior_interval.milliseconds << '\n';
    }

    std::ofstream states_, inputs_;
    std::set<EntityId> seen_;
};
} // namespace antworld::wp4
