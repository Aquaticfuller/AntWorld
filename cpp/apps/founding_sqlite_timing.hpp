#pragma once
#include "sqlite3.h"
#include "storage_timing.hpp"

#include <cstddef>
#include <cstdint>
#include <stdexcept>

namespace antworld::wp6b::qualification {
using Clock = std::chrono::steady_clock;
inline std::uint64_t elapsed(Clock::time_point start) {
    return static_cast<std::uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now()-start).count());
}

// Scoped to the diagnostic executable. Forward the exact production VFS operation.
struct SqliteIo {
    storage::timing::Counter read, write, sync;
    std::uint64_t read_bytes{}, written_bytes{};
};
namespace detail {
struct alignas(std::max_align_t) TimedFile { sqlite3_file base; };
inline sqlite3_vfs* parent{};
inline SqliteIo* io{};
inline sqlite3_file* inner(sqlite3_file* f) {
    return reinterpret_cast<sqlite3_file*>(reinterpret_cast<unsigned char*>(f)+sizeof(TimedFile));
}
inline int close(sqlite3_file* f) { auto* p=inner(f); return p->pMethods->xClose(p); }
inline int read(sqlite3_file* f, void* b, int n, sqlite3_int64 offset) {
    auto* p=inner(f); const auto start=Clock::now();
    const auto result=p->pMethods->xRead(p,b,n,offset);
    ++io->read.calls; io->read.ns+=elapsed(start); io->read_bytes+=static_cast<unsigned>(n);
    return result;
}
inline int write(sqlite3_file* f, const void* b, int n, sqlite3_int64 offset) {
    auto* p=inner(f); const auto start=Clock::now();
    const auto result=p->pMethods->xWrite(p,b,n,offset);
    ++io->write.calls; io->write.ns+=elapsed(start); io->written_bytes+=static_cast<unsigned>(n);
    return result;
}
inline int truncate(sqlite3_file* f,sqlite3_int64 n) { auto* p=inner(f); return p->pMethods->xTruncate(p,n); }
inline int sync(sqlite3_file* f, int flags) {
    auto* p=inner(f); const auto start=Clock::now();
    const auto result=p->pMethods->xSync(p,flags);
    ++io->sync.calls; io->sync.ns+=elapsed(start);
    return result;
}
inline int size(sqlite3_file* f,sqlite3_int64* n) { auto* p=inner(f); return p->pMethods->xFileSize(p,n); }
inline int lock(sqlite3_file* f,int n) { auto* p=inner(f); return p->pMethods->xLock(p,n); }
inline int unlock(sqlite3_file* f,int n) { auto* p=inner(f); return p->pMethods->xUnlock(p,n); }
inline int reserved(sqlite3_file* f,int* v) { auto* p=inner(f); return p->pMethods->xCheckReservedLock(p,v); }
inline int control(sqlite3_file* f,int op,void* v) { auto* p=inner(f); return p->pMethods->xFileControl(p,op,v); }
inline int sector(sqlite3_file* f) { auto* p=inner(f); return p->pMethods->xSectorSize(p); }
inline int characteristics(sqlite3_file* f) { auto* p=inner(f); return p->pMethods->xDeviceCharacteristics(p); }
inline int map(sqlite3_file* f,int i,int n,int e,void volatile** v) {
    auto* p=inner(f); return p->pMethods->xShmMap(p,i,n,e,v);
}
inline int shm_lock(sqlite3_file* f,int offset,int n,int flags) {
    auto* p=inner(f); return p->pMethods->xShmLock(p,offset,n,flags);
}
inline void barrier(sqlite3_file* f) { auto* p=inner(f); p->pMethods->xShmBarrier(p); }
inline int unmap(sqlite3_file* f,int flags) { auto* p=inner(f); return p->pMethods->xShmUnmap(p,flags); }
inline int fetch(sqlite3_file* f,sqlite3_int64 o,int n,void** v) { auto* p=inner(f); return p->pMethods->xFetch(p,o,n,v); }
inline int unfetch(sqlite3_file* f,sqlite3_int64 o,void* v) { auto* p=inner(f); return p->pMethods->xUnfetch(p,o,v); }
inline const sqlite3_io_methods methods1{1,close,read,write,truncate,sync,size,lock,unlock,reserved,control,sector,
    characteristics,nullptr,nullptr,nullptr,nullptr,nullptr,nullptr};
inline const sqlite3_io_methods methods2{2,close,read,write,truncate,sync,size,lock,unlock,reserved,control,sector,
    characteristics,map,shm_lock,barrier,unmap,nullptr,nullptr};
inline const sqlite3_io_methods methods3{3,close,read,write,truncate,sync,size,lock,unlock,reserved,control,sector,
    characteristics,map,shm_lock,barrier,unmap,fetch,unfetch};
inline int open(sqlite3_vfs*,const char* name,sqlite3_file* f,int flags,int* output_flags) {
    f->pMethods=nullptr;
    auto* p=inner(f);
    const auto result=parent->xOpen(parent,name,p,flags,output_flags);
    if (p->pMethods) {
        const auto version=p->pMethods->iVersion;
        f->pMethods=version>=3 && p->pMethods->xFetch && p->pMethods->xUnfetch ? &methods3 :
                    version>=2 ? &methods2 : &methods1;
    }
    return result;
}
} // namespace detail

class TimedVfs {
public:
    explicit TimedVfs(SqliteIo& io) {
        if (detail::io || !(detail::parent=sqlite3_vfs_find(nullptr))) throw std::logic_error("missing native SQLite VFS");
        wrapper=*detail::parent;
        wrapper.zName="antworld-founding-timing";
        wrapper.szOsFile+=static_cast<int>(sizeof(detail::TimedFile));
        wrapper.xOpen=detail::open;
        if (sqlite3_vfs_register(&wrapper,1)!=SQLITE_OK) throw std::runtime_error("failed to register timing VFS");
        detail::io=&io;
    }
    ~TimedVfs() {
        sqlite3_vfs_unregister(&wrapper);
        detail::io=nullptr;
    }
    TimedVfs(const TimedVfs&) = delete;
    TimedVfs& operator=(const TimedVfs&) = delete;
private:
    sqlite3_vfs wrapper{};
};
} // namespace antworld::wp6b::qualification
