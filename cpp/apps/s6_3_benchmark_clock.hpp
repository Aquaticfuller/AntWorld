#pragma once
#include "s3_fixture.hpp"
#include <chrono>
#ifdef _WIN32
#define NOMINMAX
// clang-format off
#include <windows.h>
#include <psapi.h>
// clang-format on
#else
#include <sys/resource.h>
#endif
namespace antworld::s6_3_benchmark {
struct Stamp {
    std::chrono::steady_clock::time_point wall{std::chrono::steady_clock::now()};
    std::int64_t utc{std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::system_clock::now().time_since_epoch()).count()};
    std::uint64_t cpu{},cycles{};
    unsigned processor{};
    Stamp() {
#ifdef _WIN32
        FILETIME created{},exited{},kernel{},user{};
        s3_fixture::require(GetProcessTimes(GetCurrentProcess(),&created,&exited,&kernel,&user)!=0,"CPU time unavailable");
        auto value=[](FILETIME t){return (static_cast<std::uint64_t>(t.dwHighDateTime)<<32)|t.dwLowDateTime;};
        cpu=(value(kernel)+value(user))*100;
        s3_fixture::require(QueryProcessCycleTime(GetCurrentProcess(),&cycles)!=0,"CPU cycles unavailable");
        processor=GetCurrentProcessorNumber();
#else
        rusage usage{}; s3_fixture::require(getrusage(RUSAGE_SELF,&usage)==0,"CPU time unavailable");
        cpu=static_cast<std::uint64_t>(usage.ru_utime.tv_sec+usage.ru_stime.tv_sec)*1000000000+
            static_cast<std::uint64_t>(usage.ru_utime.tv_usec+usage.ru_stime.tv_usec)*1000;
#endif
    }
};
} // namespace antworld::s6_3_benchmark
