#include "wp6b_fixture.hpp"
#include "process_memory.hpp"
#include "antworld/storage/live_history.hpp"
#include <charconv>
#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <type_traits>
#ifdef ANTWORLD_STORAGE_TIMING
#include "founding_sqlite_timing.hpp"
#endif
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
    const bool scope=c.arm=="scope-balanced-60" || c.arm=="scope-balanced-120";
    c.integrated_assay=scope || c.arm.starts_with("integrated-");
    require(c.horizon.milliseconds==(scope?180:c.integrated_assay?150:90)*day_ms,"invalid F1 assay horizon");
    if (c.integrated_assay) {
        if (scope) {
            c.release_days=c.arm=="scope-balanced-60"?60U:120U;
            c.arm="balanced";
        } else c.arm.erase(0,11);
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

void observe(WorldRuntime& w, std::ostream& cuts, std::ostream& people
#ifdef ANTWORLD_STORAGE_TIMING
             , double& state_ms, double& csv_ms
#endif
             ) {
#ifdef ANTWORLD_STORAGE_TIMING
    auto phase_start=Clock::now();
#endif
    const auto s = w.summary();
    const auto n = w.nutrition_snapshot();
    const auto f = w.founding_budget();
    const auto g = w.geometry_snapshot();
    require(n.introduced==n.accounted && n.energy_input_nj==n.body_energy_nj+n.dissipated_energy_nj &&
            f.introduced_lipid_ug==f.owned_lipid_ug+f.spent_lipid_ug &&
            g.ledger.initial_q3==g.ledger.remaining_q3+g.ledger.carried_q3+g.ledger.deposited_q3,
            "unbalanced F1 census");
#ifdef ANTWORLD_STORAGE_TIMING
    state_ms+=ms(phase_start);
    phase_start=Clock::now();
#endif
    CsvRow row;
    row.add(s.now.milliseconds,s.committed_events,s.pending_events,s.rng_state,s.living_ants);
    row.mass(n.introduced); row.mass(n.accounted); row.mass(s.food_ledger.available); row.mass(s.food_ledger.stored);
    row.add(n.energy_input_nj,n.body_energy_nj,n.dissipated_energy_nj,n.lost_water_ug,
            f.owned_lipid_ug,f.spent_lipid_ug,f.owned_mobile_protein_ug,g.geometry_revision,
            g.ledger.initial_q3,g.ledger.remaining_q3,g.ledger.carried_q3,g.ledger.deposited_q3);
    row.write(cuts);
#ifdef ANTWORLD_STORAGE_TIMING
    csv_ms+=ms(phase_start);
    phase_start=Clock::now();
#endif
    const auto ants=w.ant_states();
#ifdef ANTWORLD_STORAGE_TIMING
    state_ms+=ms(phase_start);
#endif
    for (const auto& a : ants) {
#ifdef ANTWORLD_STORAGE_TIMING
        phase_start=Clock::now();
#endif
        const AntRef ref{s.world, a.id};
        const auto p = *w.query_physiology(ref);
        const auto r = w.query_founding(ref);
#ifdef ANTWORLD_STORAGE_TIMING
        state_ms+=ms(phase_start);
        phase_start=Clock::now();
#endif
        row.add(s.now.milliseconds,s.committed_events,a.id.value,p.mother.value,
                static_cast<unsigned>(a.caste),static_cast<unsigned>(a.stage),a.born_at.milliseconds,
                a.position.x,a.position.y,a.position.z,a.position_revision,static_cast<unsigned>(p.death_cause),
                static_cast<unsigned>(p.behavior),p.stage_progress.milliseconds,p.next_absorption.milliseconds,
                p.body_energy_nj,p.hydration_ug,p.tissue_protein_ug,p.lost_water_ug,p.dissipated_energy_nj,p.oxidized_carbs_ug);
        row.mass(p.crop); row.mass(a.carried_food); row.add(static_cast<unsigned>(r.has_value()));
        if (r) row.add(r->lipid_ug,r->spent_lipid_ug,r->mobile_protein_ug,r->energy_remainder,r->water_remainder);
        else row.empty(5);
        row.write(people);
#ifdef ANTWORLD_STORAGE_TIMING
        csv_ms+=ms(phase_start);
#endif
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

[[noreturn]] void interrupt_publication(WorldRuntime& world, storage::Store& store, const storage::SaveToken& saved,
                                       const Path& directory, SimTime next) {
    auto frame=output(directory/"published.frame");
    write_bytes(frame,world.checkpoint_frame());
    frame.close();
    world.advance_to(next);
    storage::SaveOptions failure;
    failure.fault_hook=[&](storage::SaveStage stage) {
        if (stage!=storage::SaveStage::BeforeCommit) return;
        auto marker=output(directory/"interruption.csv");
        marker << "published_generation,published_cursor,attempted_time_ms\n"
               << saved.generation << ',' << saved.cursor << ',' << world.summary().now.milliseconds << '\n';
        marker.close();
        std::_Exit(78);
    };
    store.save(world,saved,failure);
    throw std::logic_error("interruption did not stop the child");
}

void resume_interrupted(const Case& c, const Path& evidence, const Path& dir) {
    const auto limits=s6_3_1_fixture::limits();
    storage::Store store(evidence,limits,storage::StoreFormat::Segmented);
    const WorldId id{646,c.identity};
    auto loaded=store.load(id);
    require(loaded.token.generation==1 && loaded.world.summary().now==SimTime{75*day_ms} &&
            loaded.world.founding_profile()==c.profile,"interrupted store lost its original publication");
    const auto cursor=loaded.token.cursor;
    const auto midpoint=loaded.world.checkpoint_frame();
    auto initial=output(dir/"restored_midpoint.frame");
    write_bytes(initial,midpoint);
    initial.close();
    loaded.world.advance_to({c.horizon.milliseconds/2+1});
    for (auto at=c.horizon.milliseconds/2+day_ms; at<=c.horizon.milliseconds; at+=day_ms)
        loaded.world.advance_to({at});
    check_ledgers(loaded.world);
    auto final=output(dir/"final.frame");
    write_bytes(final,loaded.world.checkpoint_frame());
    final.close();
    auto facts=output(dir/"facts.bin");
    write_facts(loaded.world,facts);
    facts.close();
    const auto state=loaded.world.snapshot();
    auto receipt=output(dir/"resumed.csv");
    receipt << "generation,cursor,midpoint_ms,time_ms,state_hash,trace_hash,rng,events\n"
            << loaded.token.generation << ',' << cursor << ',' << 75*day_ms << ',' << state.now.milliseconds
            << ',' << state.state_hash << ',' << state.trace_hash << ',' << state.rng_state << ',' << state.committed_events << '\n';
}

#ifdef ANTWORLD_STORAGE_TIMING
double thread_cpu_ms() {
#ifdef _WIN32
    FILETIME created{}, exited{}, kernel{}, user{};
    require(GetThreadTimes(GetCurrentThread(),&created,&exited,&kernel,&user)!=0,"cannot read thread CPU time");
    const auto ticks=[](FILETIME t) { return (std::uint64_t{t.dwHighDateTime}<<32) | t.dwLowDateTime; };
    return static_cast<double>(ticks(kernel)+ticks(user))/10'000;
#else
    timespec time{};
    require(clock_gettime(CLOCK_THREAD_CPUTIME_ID,&time)==0,"cannot read thread CPU time");
    return static_cast<double>(time.tv_sec)*1'000+static_cast<double>(time.tv_nsec)/1'000'000;
#endif
}

struct DiagnosticTiming {
    storage::timing::Counts storage{};
    qualification::SqliteIo sqlite{};
    std::optional<qualification::TimedVfs> vfs;
    double cpu_start{}, initial_encode{}, observation_state{}, observation_csv{}, midpoint_encode{},
        sqlite_open{}, save{}, restore{}, restore_encode{}, sqlite_close{}, output_close{}, final_frame{}, fact_export{};

    explicit DiagnosticTiming(bool enabled) {
        if (enabled) {
            cpu_start=thread_cpu_ms();
            vfs.emplace(sqlite);
            storage::timing::active=&storage;
        }
    }
    ~DiagnosticTiming() { if (vfs) storage::timing::active=nullptr; }
    void publish(const Path& dir) const {
        const auto cpu=thread_cpu_ms()-cpu_start;
        auto stream=output(dir/"phases.csv");
        stream << "thread_cpu_ms,initial_encode_ms,observation_state_ms,observation_csv_ms,midpoint_encode_ms,sqlite_open_ms,save_ms,restore_ms,"
                  "restore_encode_ms,sqlite_close_ms,output_close_ms,final_frame_ms,fact_export_ms";
        for (const auto name:storage::timing::names) stream << ',' << name << "_ms," << name << "_calls";
        stream << ",vfs_read_ms,vfs_read_calls,vfs_read_bytes,vfs_write_ms,vfs_write_calls,vfs_written_bytes,vfs_sync_ms,vfs_sync_calls\n";
        stream << cpu << ',' << initial_encode << ',' << observation_state << ',' << observation_csv << ',' << midpoint_encode
               << ',' << sqlite_open << ',' << save << ',' << restore << ',' << restore_encode << ',' << sqlite_close
               << ',' << output_close << ',' << final_frame << ',' << fact_export;
        for (const auto& item:storage) stream << ',' << static_cast<double>(item.ns)/1e6 << ',' << item.calls;
        stream << ',' << static_cast<double>(sqlite.read.ns)/1e6 << ',' << sqlite.read.calls << ',' << sqlite.read_bytes
               << ',' << static_cast<double>(sqlite.write.ns)/1e6 << ',' << sqlite.write.calls << ',' << sqlite.written_bytes
               << ',' << static_cast<double>(sqlite.sync.ns)/1e6 << ',' << sqlite.sync.calls << '\n';
    }
};
#endif

void run(const Case& c, const Path& dir, bool observation, bool durable, bool profile, bool interrupted) {
    const auto start = Clock::now();
#ifdef ANTWORLD_STORAGE_TIMING
    DiagnosticTiming diagnostic(profile);
#endif
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
#ifdef ANTWORLD_STORAGE_TIMING
        const auto encode=Clock::now();
#endif
        write_bytes(initial, w.checkpoint());
#ifdef ANTWORLD_STORAGE_TIMING
        diagnostic.initial_encode=ms(encode);
#endif
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
        if (observation) observe(w,cuts,people
#ifdef ANTWORLD_STORAGE_TIMING
                                , diagnostic.observation_state, diagnostic.observation_csv
#endif
                                );
        const auto cut_time = ms(observe_start);
        capture += cut_time;
        timings << at << ',' << elapsed << ',' << cut_time << ',' << s.committed_events << ',' << s.pending_events << '\n';
        if (durable && at==c.horizon.milliseconds/2) {
            const auto limits = s6_3_1_fixture::limits();
            const auto save_start = Clock::now();
            const auto bytes = w.checkpoint();
#ifdef ANTWORLD_STORAGE_TIMING
            diagnostic.midpoint_encode=ms(save_start);
            const auto sqlite_begin=Clock::now();
            Clock::time_point close_start;
#endif
            {
                storage::Store store(dir/"midpoint.sqlite", limits, storage::StoreFormat::Segmented);
#ifdef ANTWORLD_STORAGE_TIMING
                diagnostic.sqlite_open=ms(sqlite_begin);
                const auto write_start=Clock::now();
#endif
                const auto saved = store.save(w);
                durable_ms = ms(save_start);
#ifdef ANTWORLD_STORAGE_TIMING
                diagnostic.save=ms(write_start);
#endif
                if (interrupted) interrupt_publication(w,store,saved,dir,{at+day_ms});
                const auto reopen = Clock::now();
                auto loaded = store.load(id);
                restore_ms = ms(reopen);
                require(loaded.token==saved && loaded.world.checkpoint()==bytes,"F1 midpoint durable recovery differs");
#ifdef ANTWORLD_STORAGE_TIMING
                diagnostic.restore=restore_ms;
                diagnostic.restore_encode=ms(reopen)-restore_ms;
                close_start=Clock::now();
#endif
                w = std::move(loaded.world);
            }
#ifdef ANTWORLD_STORAGE_TIMING
            diagnostic.sqlite_close=ms(close_start);
#endif
        }
    }
#ifdef ANTWORLD_STORAGE_TIMING
    const auto closing=Clock::now();
#endif
    cuts.close(); people.close(); inputs.close(); timings.close();
#ifdef ANTWORLD_STORAGE_TIMING
    diagnostic.output_close=ms(closing);
#endif
    const auto checkpoint_start = Clock::now();
    const auto s = w.snapshot();
    const auto frame = w.checkpoint_frame();
    const auto checkpoint_ms = ms(checkpoint_start);
    check_ledgers(w);
    auto final = output(dir/"final.frame");
    write_bytes(final, frame);
    final.close();
#ifdef ANTWORLD_STORAGE_TIMING
    diagnostic.final_frame=ms(checkpoint_start);
    const auto export_start=Clock::now();
#endif
    auto facts = output(dir/"facts.bin");
    write_facts(w, facts);
    facts.close();
#ifdef ANTWORLD_STORAGE_TIMING
    diagnostic.fact_export=ms(export_start);
#endif
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
#ifdef ANTWORLD_STORAGE_TIMING
        diagnostic.publish(dir);
#endif
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
    if (argc!=4 && argc!=6 && argc!=7 && argc!=8 && argc!=10 && argc!=11 && argc!=12) {
        std::cerr << "Usage: antworld_s6_4_wp6b CASE OUTPUT MODE [WINDOW_MS REPEAT_PPM [AFFINITY_MASK [EARLY_ACCESS_MASK [LOCAL_EXCHANGE SUGAR_YIELD [DIETARY_MASK]]]]]\n";
        return 1;
    }
    const std::string_view mode = argv[3];
    try {
        const bool profile=mode=="profile-observed" || mode=="profile-unobserved";
        const bool interrupted=mode=="interrupt-save", resume=mode=="resume-save";
        require((profile || mode=="observed" || mode=="unobserved" || mode=="durable" || interrupted || resume) &&
                ((argc==12)==resume),"unknown F1 observation mode or recovery path");
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
        if (argc>=11) {
            const auto flags=integer(argv[10]);
            require((flags>=1 && flags<=3) || flags==7 || flags==15,"invalid dietary assay mask");
            c.profile.dietary=FoundingDietaryAccess{(flags&1)!=0,(flags&2)!=0,(flags&4)!=0,(flags&8)!=0};
        }
        std::filesystem::create_directories(argv[2]);
        if (resume || interrupted)
            require(c.integrated_assay && c.horizon==SimTime{150*day_ms} && c.profile.model_version()==FoundingProfile::resupply_version,
                    "recovery witness requires the frozen 150-day model");
        if (resume) resume_interrupted(c,argv[11],argv[2]);
        else run(c, argv[2], mode!="unobserved" && mode!="profile-unobserved", mode=="durable" || profile || interrupted, profile, interrupted);
        return 0;
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
