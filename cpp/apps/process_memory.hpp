#pragma once
#include <cstdint>
#include <stdexcept>
#include <utility>
#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
// clang-format off: Windows definitions must precede PSAPI declarations.
#include <windows.h>
#include <psapi.h>
// clang-format on
#else
#include <fstream>
#include <sys/resource.h>
#include <unistd.h>
#endif
namespace antworld::performance {
inline std::pair<std::uint64_t, std::uint64_t> memory() {
#ifdef _WIN32
    PROCESS_MEMORY_COUNTERS counters{};
    if (!GetProcessMemoryInfo(GetCurrentProcess(), &counters, sizeof(counters)))
        throw std::runtime_error("process memory query failed");
    return {counters.WorkingSetSize, counters.PeakWorkingSetSize};
#else
    rusage usage{};
    if (getrusage(RUSAGE_SELF, &usage))
        throw std::runtime_error("process peak memory unavailable");
    std::ifstream stat("/proc/self/statm");
    std::uint64_t pages{}, resident{};
    stat >> pages >> resident;
    if (!stat)
        throw std::runtime_error("resident process memory unavailable");
    return {resident * static_cast<std::uint64_t>(sysconf(_SC_PAGESIZE)),
            static_cast<std::uint64_t>(usage.ru_maxrss) * 1024};
#endif
}
} // namespace antworld::performance
