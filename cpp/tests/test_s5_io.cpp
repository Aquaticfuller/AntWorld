#include "antworld/storage/store.hpp"
#include "sqlite3.h"
#include <cstdlib>
#include <iostream>
#include <string>

using namespace antworld;
using namespace antworld::storage;
namespace {
sqlite3_vfs *parent{};
sqlite3_vfs fault_vfs{};
int write_failure = -1, sync_failure = -1, crash_write = -1;
struct File {
    sqlite3_file base;
    sqlite3_file *underlying;
};
sqlite3_file *file(sqlite3_file *p) { return reinterpret_cast<File *>(p)->underlying; }
int close_file(sqlite3_file *p) { return file(p)->pMethods->xClose(file(p)); }
int read_file(sqlite3_file *p, void *b, int n, sqlite3_int64 offset) {
    return file(p)->pMethods->xRead(file(p), b, n, offset);
}
int write_file(sqlite3_file *p, const void *b, int n, sqlite3_int64 offset) {
    if (write_failure == 0)
        return SQLITE_IOERR_WRITE;
    if (write_failure > 0)
        --write_failure;
    const auto result = file(p)->pMethods->xWrite(file(p), b, n, offset);
    if (result == SQLITE_OK && crash_write == 0)
        std::_Exit(78);
    if (crash_write > 0)
        --crash_write;
    return result;
}
int truncate_file(sqlite3_file *p, sqlite3_int64 n) { return file(p)->pMethods->xTruncate(file(p), n); }
int sync_file(sqlite3_file *p, int flags) {
    if (sync_failure == 0)
        return SQLITE_IOERR_FSYNC;
    if (sync_failure > 0)
        --sync_failure;
    return file(p)->pMethods->xSync(file(p), flags);
}
int size_file(sqlite3_file *p, sqlite3_int64 *n) { return file(p)->pMethods->xFileSize(file(p), n); }
int lock_file(sqlite3_file *p, int flags) { return file(p)->pMethods->xLock(file(p), flags); }
int unlock_file(sqlite3_file *p, int flags) { return file(p)->pMethods->xUnlock(file(p), flags); }
int reserved(sqlite3_file *p, int *value) { return file(p)->pMethods->xCheckReservedLock(file(p), value); }
int control(sqlite3_file *p, int op, void *value) {
    return file(p)->pMethods->xFileControl(file(p), op, value);
}
int sector(sqlite3_file *p) { return file(p)->pMethods->xSectorSize(file(p)); }
int characteristics(sqlite3_file *p) { return file(p)->pMethods->xDeviceCharacteristics(file(p)); }
int shm_map(sqlite3_file *p, int a, int b, int c, void volatile **d) {
    return file(p)->pMethods->xShmMap(file(p), a, b, c, d);
}
int shm_lock(sqlite3_file *p, int a, int b, int c) { return file(p)->pMethods->xShmLock(file(p), a, b, c); }
void barrier(sqlite3_file *p) { file(p)->pMethods->xShmBarrier(file(p)); }
int unmap(sqlite3_file *p, int flag) { return file(p)->pMethods->xShmUnmap(file(p), flag); }
int fetch(sqlite3_file *p, sqlite3_int64 offset, int n, void **out) {
    if (file(p)->pMethods->iVersion < 3 || !file(p)->pMethods->xFetch) {
        *out = nullptr;
        return SQLITE_OK;
    }
    return file(p)->pMethods->xFetch(file(p), offset, n, out);
}
int unfetch(sqlite3_file *p, sqlite3_int64 offset, void *out) {
    return file(p)->pMethods->iVersion < 3 || !file(p)->pMethods->xUnfetch
               ? SQLITE_OK
               : file(p)->pMethods->xUnfetch(file(p), offset, out);
}
const sqlite3_io_methods methods{3,         close_file, read_file,       write_file,  truncate_file,
                                 sync_file, size_file,  lock_file,       unlock_file, reserved,
                                 control,   sector,     characteristics, shm_map,     shm_lock,
                                 barrier,   unmap,      fetch,           unfetch};
int open_file(sqlite3_vfs *, const char *name, sqlite3_file *p, int flags, int *result_flags) {
    auto *wrapper = reinterpret_cast<File *>(p);
    wrapper->underlying =
        reinterpret_cast<sqlite3_file *>(reinterpret_cast<unsigned char *>(p) + sizeof(File));
    const auto result = parent->xOpen(parent, name, wrapper->underlying, flags, result_flags);
    if (result == SQLITE_OK)
        p->pMethods = &methods;
    return result;
}
void require(bool ok, const char *message) {
    if (!ok)
        throw std::runtime_error(message);
}
void initialize() {
    parent = sqlite3_vfs_find(nullptr);
    require(parent != nullptr, "missing SQLite VFS");
    fault_vfs = *parent;
    fault_vfs.zName = "antworld-s5-fault-vfs";
    fault_vfs.szOsFile = static_cast<int>(sizeof(File)) + parent->szOsFile;
    fault_vfs.xOpen = open_file;
    require(sqlite3_vfs_register(&fault_vfs, 1) == SQLITE_OK, "VFS registration failed");
}
void clean(const std::filesystem::path &p) {
    for (const auto &suffix : {std::string{}, std::string{"-wal"}, std::string{"-shm"}}) {
        auto f = p;
        f += suffix;
        if (std::filesystem::is_regular_file(f))
            std::filesystem::remove(f);
    }
}
WorldRuntime fixture() {
    WorldRuntime w({5, 9}, 9);
    w.seed_colony();
    for (std::uint64_t i = 1; i <= 30; ++i)
        w.schedule(
            {{static_cast<std::int64_t>(i)}, Phase::Environment, 0, 0, i, DiagnosticAction::DrawRandom});
    return w;
}
void sweep(const std::filesystem::path &base,bool sync,StoreFormat format) {
    for (int n = 0; n < 512; ++n) {
        auto path = base;
        path += (sync ? "-sync-" : "-write-") + std::to_string(n);
        clean(path);
        auto w = fixture();
        const auto old = w.checkpoint();
        std::vector<std::uint8_t> next(0);
        bool success = false;
        {
            Store store(path,{},format);
            const auto token = store.save(w);
            store.checkpoint_wal();
            w.advance_to({30});
            next = w.checkpoint();
            if (sync)
                sync_failure = n;
            else
                write_failure = n;
            try {
                store.save(w, token);
                success = true;
            } catch (const std::exception &) {
            }
            write_failure = -1;
            sync_failure = -1;
            require(w.checkpoint() == next, "database I/O failure mutated live simulation");
        }
        {
            Store recovered(path);
            const auto bytes = recovered.load({5, 9}).world.checkpoint();
            require(bytes == old || bytes == next, "I/O failure left mixed/corrupt generation");
            if (success)
                require(bytes == next, "acknowledged save was lost");
        }
        clean(path);
        if (success) {
            std::cout << (sync ? "sync" : "write") << "_failure_positions=" << n << '\n';
            return;
        }
    }
    throw std::runtime_error("I/O fault sweep did not complete");
}
} // namespace
int main(int argc, char **argv) {
    try {
        if (argc!=3 && (argc!=4 || std::string_view(argv[3])!="SEGMENTED"))
            throw std::invalid_argument("usage: antworld_s5_io MODE DATABASE [SEGMENTED]");
        const auto format=argc==4?StoreFormat::Segmented:StoreFormat::Legacy;
        initialize();
        const std::string mode = argv[1];
        const std::filesystem::path path = argv[2];
        std::filesystem::create_directories(path.parent_path());
        if (mode == "SWEEP") {
            sweep(path,false,format);
            sweep(path,true,format);
        } else if (mode == "SEED") {
            clean(path);
            Store store(path,{},format);
            auto w = fixture();
            store.save(w);
            store.checkpoint_wal();
        } else if (mode == "CRASH") {
            Store store(path);
            auto loaded = store.load({5, 9});
            loaded.world.advance_to({30});
            crash_write = 1;
            store.save(loaded.world, loaded.token);
            throw std::runtime_error("WAL crash did not fire");
        } else if (mode == "VERIFY") {
            Store store(path);
            auto loaded = store.load({5, 9});
            require(loaded.world.checkpoint() == fixture().checkpoint(),
                    "partial WAL write published new generation");
        } else
            throw std::invalid_argument("unknown I/O test");
        std::cout << "PASS S5_IO_" << mode << '\n';
        return 0;
    } catch (const std::exception &e) {
        std::cerr << "FAIL: " << e.what() << '\n';
        return 1;
    }
}
