#include "wp6b_fixture.hpp"
#include "process_memory.hpp"
#include "antworld/storage/live_history.hpp"
#include <charconv>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <type_traits>
#ifndef _WIN32
#include <fcntl.h>
#endif

namespace {
using namespace antworld;
using namespace antworld::wp6b;
using Path = std::filesystem::path;
using Clock = std::chrono::steady_clock;

std::ofstream output(const Path& path) {
    std::ofstream stream;
    stream.exceptions(std::ios::badbit | std::ios::failbit);
    stream.open(path, std::ios::binary);
    stream << std::setprecision(17);
    return stream;
}

Case read_case(const Path& path) {
    std::ifstream stream(path);
    Case c{};
    unsigned population;
    if (!(stream >> c.identity >> c.seed >> population >> c.arm >> c.care >> c.workers >> c.horizon.milliseconds >>
          c.food.carbs_ug >> c.food.protein_ug >> c.food.water_ug >> c.food.other_ug) ||
        (population != 1 && population != 2) ||
        (c.workers && c.workers != 8 && c.workers != 32)) throw std::invalid_argument("invalid frozen F1 case header");
    c.integrated_assay=c.arm.starts_with("integrated-");
    require(c.horizon.milliseconds==(c.integrated_assay?150:90)*day_ms,"invalid F1 assay horizon");
    if (c.integrated_assay) {
        c.arm.erase(0,11);
        require(!c.workers && c.care,"the integrated assay begins with one active queen");
        const std::map<std::string,FoodMass> inputs{
            {"balanced",{6000,3000,18000,0}},{"limited",{752,376,2252,0}},{"water",{0,0,18000,0}},
            {"carbohydrate",{6000,0,0,0}},{"no-protein",{6000,0,18000,0}},{"blocked",{6000,3000,18000,0}},{"absent",{}}};
        require(inputs.contains(c.arm) && inputs.at(c.arm)==c.food,"invalid integrated resource fixture");
    }
    c.profile = nominal(static_cast<FoundingPopulation>(population));
    std::map<std::string, std::uint64_t> values;
    std::string key;
    std::uint64_t value;
    while (stream >> key >> value) require(values.emplace(key, value).second, "duplicate F1 case parameter");
    require(stream.eof() && values.size()==33, "invalid number of F1 case parameters");
    const auto v = [&](const std::string& name) { return values.at(name); };
    const auto t = [&](const std::string& name) {
        const auto n = v(name);
        require(n <= INT64_MAX, "overflowing F1 case time");
        return SimTime{static_cast<std::int64_t>(n)};
    };
    auto& f = c.profile;
    std::size_t i = 0;
    for (const std::string stage : {"egg", "larva", "pupa"})
        f.brood[i++] = {t(stage+"_ms"), v(stage+"_basal"), v(stage+"_water_loss")};
    f.worker.absorption_period = t("refill_period");
    f.first_lay = t("first_lay_delay_ms"); f.opening_width = t("opening_bout_width_ms");
    f.opening_spacing = t("opening_lay_spacing"); f.later_spacing = t("lay_interval_ms");
    f.maintenance_floor = t("maternal_floor_ms"); f.wet_mass_ug = v("foundress_wet_mass");
    f.structural_minimum_ug = v("structural_minimum"); f.lipid_ug = v("maternal_lipid");
    f.protein_ug = v("maternal_protein"); f.water_ug = v("maternal_water"); f.lipid_yield_nj_per_ug = v("lipid_yield");
    f.basal_nj_per_day = v("queen_basal"); f.active_nj_per_ms = v("queen_active"); f.water_ug_per_day = v("queen_water_loss");
    f.egg_lipid_ug = v("egg_lipid"); f.egg_protein_ug = v("egg_protein"); f.egg_water_ug = v("egg_water");
    f.lay_overhead_nj = v("lay_overhead"); f.larval_tissue_ug = v("larval_tissue_target");
    f.larval_lipid_capacity_ug = v("larval_lipid_capacity"); f.ration_lipid_ug = v("ration_lipid_limit");
    f.ration_protein_ug = v("ration_protein_limit"); f.ration_water_ug = v("ration_water_limit");
    return c;
}

void write_bytes(std::ofstream& stream, std::span<const std::uint8_t> bytes) {
    stream.write(reinterpret_cast<const char*>(bytes.data()), static_cast<std::streamsize>(bytes.size()));
}

class CsvRow {
public:
    template<class... Numbers> void add(Numbers... values) { (number(values), ...); }
    void mass(FoodMass f) { for (auto value : f.components()) number(value); }
    void empty(std::size_t count) { row_.append(count,','); }
    void write(std::ostream& stream) {
        row_.push_back('\n');
        stream.write(row_.data(),static_cast<std::streamsize>(row_.size()));
        row_.clear();
    }
private:
    std::string row_;
    template<class Number> void number(Number value) {
        char buffer[48];
        const auto end=std::end(buffer);
        const auto result=[&] {
            if constexpr (std::is_same_v<Number,double>)
                return std::to_chars(buffer,end,value,std::chars_format::general,17);
            else return std::to_chars(buffer,end,value);
        }();
        require(result.ec==std::errc{},"cannot encode census value");
        if (!row_.empty()) row_.push_back(',');
        row_.append(buffer,result.ptr);
    }
};

double ms(Clock::time_point start) { return std::chrono::duration<double, std::milli>(Clock::now()-start).count(); }

std::uint64_t integer(std::string_view text) {
    std::uint64_t value{};
    const auto end=text.data()+text.size();
    const auto result=std::from_chars(text.data(),end,value);
    require(result.ec==std::errc{} && result.ptr==end,"invalid F1-R1 assay integer");
    return value;
}

void synchronize_output(const Path& path) {
#ifdef _WIN32
    const auto file=CreateFileW(path.c_str(),GENERIC_WRITE,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);
    require(file!=INVALID_HANDLE_VALUE,"cannot open assay output for synchronization");
    const auto success=FlushFileBuffers(file);
    CloseHandle(file);
#else
    const auto file=open(path.c_str(),O_RDWR);
    require(file>=0,"cannot open assay output for synchronization");
    const auto success=fsync(file)==0;
    close(file);
#endif
    require(success,"cannot synchronize assay output");
}

void observe(WorldRuntime& w, std::ostream& cuts, std::ostream& people) {
    const auto s = w.summary();
    const auto n = w.nutrition_snapshot();
    const auto f = w.founding_budget();
    const auto g = w.geometry_snapshot();
    require(n.introduced==n.accounted && n.energy_input_nj==n.body_energy_nj+n.dissipated_energy_nj &&
            f.introduced_lipid_ug==f.owned_lipid_ug+f.spent_lipid_ug &&
            g.ledger.initial_q3==g.ledger.remaining_q3+g.ledger.carried_q3+g.ledger.deposited_q3,
            "unbalanced F1 census");
    CsvRow row;
    row.add(s.now.milliseconds,s.committed_events,s.pending_events,s.rng_state,s.living_ants);
    row.mass(n.introduced); row.mass(n.accounted); row.mass(s.food_ledger.available); row.mass(s.food_ledger.stored);
    row.add(n.energy_input_nj,n.body_energy_nj,n.dissipated_energy_nj,n.lost_water_ug,
            f.owned_lipid_ug,f.spent_lipid_ug,f.owned_mobile_protein_ug,g.geometry_revision,
            g.ledger.initial_q3,g.ledger.remaining_q3,g.ledger.carried_q3,g.ledger.deposited_q3);
    row.write(cuts);
    for (const auto& a : w.ant_states()) {
        const AntRef ref{s.world, a.id};
        const auto p = *w.query_physiology(ref);
        const auto r = w.query_founding(ref);
        row.add(s.now.milliseconds,s.committed_events,a.id.value,p.mother.value,
                static_cast<unsigned>(a.caste),static_cast<unsigned>(a.stage),a.born_at.milliseconds,
                a.position.x,a.position.y,a.position.z,a.position_revision,static_cast<unsigned>(p.death_cause),
                static_cast<unsigned>(p.behavior),p.stage_progress.milliseconds,p.next_absorption.milliseconds,
                p.body_energy_nj,p.hydration_ug,p.tissue_protein_ug,p.lost_water_ug,p.dissipated_energy_nj,p.oxidized_carbs_ug);
        row.mass(p.crop); row.mass(a.carried_food); row.add(static_cast<unsigned>(r.has_value()));
        if (r) row.add(r->lipid_ug,r->spent_lipid_ug,r->mobile_protein_ug,r->energy_remainder,r->water_remainder);
        else row.empty(5);
        row.write(people);
    }
}

void write_facts(const WorldRuntime& w, std::ofstream& stream) {
    EventId after;
    for (;;) {
        const auto page = w.events_after(after, 4096);
        if (page.empty()) return;
        for (const auto& event : page) {
            const auto bytes = encode_event(event);
            const auto n = bytes.size();
            const std::array length{static_cast<std::uint8_t>(n), static_cast<std::uint8_t>(n>>8), std::uint8_t{}, std::uint8_t{}};
            write_bytes(stream, length);
            write_bytes(stream, bytes);
        }
        after = page.back().id;
    }
}

void run(const Case& c, const Path& dir, bool observation, bool durable, bool profile) {
    const auto start = Clock::now();
    auto scene = setup(c);
    auto& w = scene.world;
    const auto setup_ms = ms(start);
    const auto id = w.summary().world;
    auto inputs = output(dir/"interventions.csv");
    inputs << "issued_ms,execute_ms,scheduled_id,operation,x_m,y_m,z_m\n";
    auto cuts = output(dir/"cuts.csv");
    cuts << "time_ms,cursor,queue,rng,living,introduced_c,introduced_p,introduced_w,introduced_o,accounted_c,accounted_p,accounted_w,accounted_o,"
            "available_c,available_p,available_w,available_o,nest_c,nest_p,nest_w,nest_o,energy_input_nj,body_energy_nj,dissipated_nj,"
            "water_lost_ug,owned_lipid_ug,spent_lipid_ug,mobile_protein_ug,geometry_revision,initial_q3,remaining_q3,carried_q3,deposited_q3\n";
    auto people = output(dir/"individuals.csv");
    people << "time_ms,cursor,id,mother,caste,stage,born_ms,x_m,y_m,z_m,position_revision,death_cause,program,stage_progress_ms,next_absorption_ms,"
              "energy_nj,hydration_ug,tissue_protein_ug,lost_water_ug,dissipated_nj,oxidized_carb_ug,crop_c,crop_p,crop_w,crop_o,carried_c,"
              "carried_p,carried_w,carried_o,enrolled,lipid_ug,spent_lipid_ug,mobile_protein_ug,energy_carry,water_carry\n";
    auto timings = output(dir/"timings.csv");
    timings << "time_ms,advance_ms,cut_ms,committed,pending\n";
    {
        auto initial = output(dir/"initial.chk");
        write_bytes(initial, w.checkpoint());
    }
    std::uint64_t peak_queue{};
    double advance{}, capture{}, durable_ms{}, restore_ms{};
    for (Time at = 0; at <= c.horizon.milliseconds; at += day_ms) {
        const auto before = Clock::now();
        w.advance_to({at});
        const auto elapsed = ms(before);
        advance += elapsed;
        const auto s = w.summary();
        peak_queue = std::max(peak_queue, s.pending_events);
        const auto observe_start = Clock::now();
        if (observation) observe(w,cuts,people);
        const auto cut_time = ms(observe_start);
        capture += cut_time;
        timings << at << ',' << elapsed << ',' << cut_time << ',' << s.committed_events << ',' << s.pending_events << '\n';
        if (durable && at==c.horizon.milliseconds/2) {
            const auto limits = s6_3_1_fixture::limits();
            const auto save_start = Clock::now();
            const auto bytes = w.checkpoint();
            storage::Store store(dir/"midpoint.sqlite", limits, storage::StoreFormat::Segmented);
            const auto saved = store.save(w);
            durable_ms = ms(save_start);
            const auto reopen = Clock::now();
            auto loaded = store.load(id);
            restore_ms = ms(reopen);
            require(loaded.token==saved && loaded.world.checkpoint()==bytes,"F1 midpoint durable recovery differs");
            w = std::move(loaded.world);
        }
    }
    cuts.close(); people.close(); inputs.close(); timings.close();
    const auto checkpoint_start = Clock::now();
    const auto s = w.snapshot();
    const auto frame = w.checkpoint_frame();
    const auto checkpoint_ms = ms(checkpoint_start);
    check_ledgers(w);
    auto final = output(dir/"final.frame");
    write_bytes(final, frame);
    final.close();
    auto facts = output(dir/"facts.bin");
    write_facts(w, facts);
    facts.close();
    const auto [rss, peak] = performance::memory();
    if (profile) {
        const auto synchronize=Clock::now();
        for (const auto* file : {"initial.chk","final.frame","facts.bin"}) synchronize_output(dir/file);
        const auto common_ms=ms(synchronize);
        const auto optional_start=Clock::now();
        if (observation) for (const auto* file : {"cuts.csv","individuals.csv"}) synchronize_output(dir/file);
        const auto optional_ms=ms(optional_start);
        const auto total=ms(start);
        auto cost=output(dir/"profile.csv");
        cost << "total_ms,common_sync_ms,optional_sync_ms,post_cut_ms,model_version\n" << total << ',' << common_ms
             << ',' << optional_ms << ',' << ms(checkpoint_start) << ',' << c.profile.model_version() << '\n';
    }
    auto receipt = output(dir/"summary.csv");
    receipt << "world,seed,queen,state_hash,trace_hash,rng,events,time_ms,peak_sampled_queue,setup_ms,advance_ms,cut_ms,checkpoint_ms,"
               "midpoint_save_ms,midpoint_restore_ms,frame_bytes,facts_bytes,rss_bytes,peak_rss_bytes,reserve_record_bytes\n"
            << id.str() << ',' << c.seed << ',' << scene.queen.id.value << ',' << s.state_hash << ',' << s.trace_hash << ',' << s.rng_state
            << ',' << s.committed_events << ',' << s.now.milliseconds << ',' << peak_queue << ',' << setup_ms << ',' << advance << ',' << capture
            << ',' << checkpoint_ms << ',' << durable_ms << ',' << restore_ms << ',' << frame.size() << ',' << std::filesystem::file_size(dir/"facts.bin")
            << ',' << rss << ',' << peak << ',' << sizeof(FoundingReserve) << '\n';
}
} // namespace

int main(int argc, char** argv) {
    if (argc!=4 && argc!=6 && argc!=7 && argc!=8 && argc!=10 && argc!=11) {
        std::cerr << "Usage: antworld_s6_4_wp6b CASE OUTPUT MODE [WINDOW_MS REPEAT_PPM [AFFINITY_MASK [EARLY_ACCESS_MASK [LOCAL_EXCHANGE SUGAR_YIELD [DIETARY_MASK]]]]]\n";
        return 1;
    }
    const std::string_view mode = argv[3];
    try {
        const bool profile=mode=="profile-observed" || mode=="profile-unobserved";
        require(profile || mode=="observed" || mode=="unobserved" || mode=="durable", "unknown F1 observation mode");
        if (argc>=7) {
            const auto mask=integer(argv[6]);
#ifdef _WIN32
            require(mask==0 || SetProcessAffinityMask(GetCurrentProcess(),static_cast<DWORD_PTR>(mask)),"cannot pin assay child");
#else
            require(mask==0,"use external affinity on this host");
#endif
        }
        auto c=read_case(argv[1]);
        if (argc>=6) {
            const auto window=integer(argv[4]);
            const auto ppm=integer(argv[5]);
            require(window<=INT64_MAX && ppm<=UINT32_MAX && (window || !ppm),"invalid F1-R1 assay option");
            if (window) c.profile.feeding_persistence=FoundingFeedingPersistence{
                {static_cast<std::int64_t>(window)},static_cast<std::uint32_t>(ppm)};
        }
        if (argc>=8) {
            const auto flags=integer(argv[7]);
            require(flags>=1 && flags<=3 && c.profile.feeding_persistence,"invalid F1-R2 option");
            c.profile.early_access=FoundingEarlyAccess{(flags&1)!=0,(flags&2)!=0};
        }
        if (argc>=10) {
            const auto exchange=integer(argv[8]);
            require(exchange<=1,"invalid provisioning option");
            c.profile.provisioning=FoundingProvisioning{exchange!=0};
            c.profile.worker.carbohydrate_yield_nj_per_ug=integer(argv[9]);
            if (exchange) c.profile.worker.behavior_interval={hour_ms};
        }
        if (argc==11) {
            const auto flags=integer(argv[10]);
            require((flags>=1 && flags<=3) || flags==7 || flags==15,"invalid dietary assay mask");
            c.profile.dietary=FoundingDietaryAccess{(flags&1)!=0,(flags&2)!=0,(flags&4)!=0,(flags&8)!=0};
        }
        std::filesystem::create_directories(argv[2]);
        run(c, argv[2], mode!="unobserved" && mode!="profile-unobserved", mode=="durable" || profile, profile);
        return 0;
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
