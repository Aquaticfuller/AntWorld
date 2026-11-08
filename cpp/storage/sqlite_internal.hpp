#pragma once
#include "antworld/storage/store.hpp"
#include "sqlite3.h"
#include <charconv>
#include <stdexcept>
#include <string>

namespace antworld::storage::detail {
inline void check(int code, sqlite3 *db) {
    if (code != SQLITE_OK && code != SQLITE_ROW && code != SQLITE_DONE)
        throw std::runtime_error(std::string("SQLite error ") + std::to_string(code) + ": " +
                                 sqlite3_errmsg(db));
}
inline void exec(sqlite3 *db, const char *sql) {
    check(sqlite3_exec(db, sql, nullptr, nullptr, nullptr), db);
}
struct Statement {
    sqlite3 *db;
    sqlite3_stmt *p{};
    Statement(sqlite3 *d, const char *sql) : db(d) {
        check(sqlite3_prepare_v2(db, sql, -1, &p, nullptr), db);
    }
    ~Statement() { sqlite3_finalize(p); }
    Statement(const Statement &) = delete;
    Statement &operator=(const Statement &) = delete;
    void text(int i, const std::string &s) {
        check(sqlite3_bind_text(p, i, s.data(), static_cast<int>(s.size()), SQLITE_TRANSIENT), db);
    }
    void u64(int i, std::uint64_t n) { text(i, hex64(n)); }
    void number(int i, std::int64_t n) { check(sqlite3_bind_int64(p, i, n), db); }
    void real(int i, double n) { check(sqlite3_bind_double(p, i, n), db); }
    void blob(int i, std::span<const std::uint8_t> bytes) {
        check(sqlite3_bind_blob64(p, i, bytes.data(), bytes.size(), SQLITE_TRANSIENT), db);
    }
    bool row() {
        const auto result = sqlite3_step(p);
        check(result, db);
        return result == SQLITE_ROW;
    }
    void done() {
        if (row())
            throw std::runtime_error("unexpected SQL row");
    }
    void reset() {
        check(sqlite3_reset(p), db);
        check(sqlite3_clear_bindings(p), db);
    }
    std::string text(int i) const {
        if (sqlite3_column_type(p, i) != SQLITE_TEXT)
            throw std::runtime_error("invalid SQL text field");
        return {reinterpret_cast<const char *>(sqlite3_column_text(p, i)),
                static_cast<std::size_t>(sqlite3_column_bytes(p, i))};
    }
    std::uint64_t u64(int i) const {
        const auto s = text(i);
        std::uint64_t n{};
        const auto result = std::from_chars(s.data(), s.data() + s.size(), n, 16);
        if (s.size() != 16 || result.ec != std::errc{} || result.ptr != s.data() + s.size() || hex64(n) != s)
            throw std::runtime_error("invalid exact uint64 field");
        return n;
    }
    std::int64_t number(int i) const {
        if (sqlite3_column_type(p, i) != SQLITE_INTEGER)
            throw std::runtime_error("invalid SQL integer field");
        return sqlite3_column_int64(p, i);
    }
    std::vector<std::uint8_t> blob(int i, std::size_t limit) const {
        if (sqlite3_column_type(p, i) != SQLITE_BLOB)
            throw std::runtime_error("invalid SQL blob field");
        const auto size = static_cast<std::size_t>(sqlite3_column_bytes(p, i));
        if (size > limit)
            throw std::length_error("database blob host budget exceeded");
        const auto *data = static_cast<const std::uint8_t *>(sqlite3_column_blob(p, i));
        return size ? std::vector<std::uint8_t>(data, data + size) : std::vector<std::uint8_t>(0);
    }
};
struct Transaction {
    sqlite3 *db;
    bool committed{};
    explicit Transaction(sqlite3 *d, bool write = true) : db(d) {
        exec(db, write ? "BEGIN IMMEDIATE" : "BEGIN");
    }
    ~Transaction() {
        if (!committed)
            sqlite3_exec(db, "ROLLBACK", nullptr, nullptr, nullptr);
    }
    void commit() {
        exec(db, "COMMIT");
        committed = true;
    }
};
inline std::uint64_t hash(std::span<const std::uint8_t> bytes,
                          std::uint64_t state = UINT64_C(14695981039346656037)) {
    for (auto b : bytes)
        state = (state ^ b) * UINT64_C(1099511628211);
    return state;
}
inline void require(bool ok, const char *message) {
    if (!ok)
        throw std::runtime_error(message);
}
inline void range(SimTime begin, SimTime end, std::size_t limit = 100) {
    if (begin.milliseconds < 0 || end < begin || !limit || limit > 10000)
        throw std::invalid_argument("invalid bounded query range");
}
} // namespace antworld::storage::detail
