#include "segmented_archive.hpp"
#include <algorithm>

namespace antworld::storage::detail {
namespace {
Digest anchor_digest(const SaveToken& token,SimTime time,std::span<const std::uint8_t> frame,
                     const Digest& parent,const Digest& tail) {
    std::vector<std::uint8_t> header{'A','W','A','N','C','H','0','1'};
    for (auto value:{token.world.high,token.world.low,token.generation,token.revision,token.cursor,
                    token.checkpoint_hash,static_cast<std::uint64_t>(time.milliseconds)})
        for (unsigned i=0;i<8;++i) header.push_back(static_cast<std::uint8_t>(value>>(i*8)));
    header.insert(header.end(),parent.begin(),parent.end());
    header.insert(header.end(),tail.begin(),tail.end());
    return sha256(header,frame);
}
} // namespace

bool founding_frame(std::span<const std::uint8_t> bytes) {
    constexpr std::array<std::uint8_t,8> magic{'A','W','C','K','P','T','F',0};
    return bytes.size()>=16 && std::equal(magic.begin(),magic.end(),bytes.begin()+8);
}

SaveFrame capture_frame(const WorldRuntime& world) {
    return {world.summary(),world.checkpoint_frame(),world.capture_history(),observe(world),
            world.geometry_snapshot(),world.geometry_edits(),world.ant_states(),world.command_receipts()};
}

Database open_readonly(const std::filesystem::path& path) {
    sqlite3* raw=nullptr;
    const auto filename=path.u8string();
    const auto result=sqlite3_open_v2(reinterpret_cast<const char*>(filename.c_str()),&raw,
                                     SQLITE_OPEN_READONLY|SQLITE_OPEN_FULLMUTEX,nullptr);
    Database db(raw);
    check(result,db.get());
    check(sqlite3_busy_timeout(db.get(),5000),db.get());
    exec(db.get(),"PRAGMA trusted_schema=OFF; PRAGMA cache_size=-4096;");
    return db;
}

Digest column_digest(const Statement& row,int column) {
    const auto bytes=row.blob(column,Digest{}.size());
    Digest digest{};
    require(bytes.size()==digest.size(),"invalid history digest length");
    std::copy(bytes.begin(),bytes.end(),digest.begin());
    return digest;
}

Digest block_tail(sqlite3* db,WorldId world,EventId cursor) {
    if (!cursor.value) return {};
    Statement q(db,"SELECT digest FROM fact_blocks WHERE world=? AND last_id=?");
    q.text(1,world.str()); q.u64(2,cursor.value);
    require(q.row(),"missing fact block at published cursor");
    return column_digest(q,0);
}

BlockCursor::BlockCursor(sqlite3* db,WorldId world,EventId after,EventId through)
    :db_(db),world_(world),cursor_(after),through_(through),
     query_(db,"SELECT first_id,last_id,begin_ms,end_ms,raw_bytes,digest,envelope FROM fact_blocks "
               "WHERE world=? AND last_id>? AND last_id<=? ORDER BY last_id") {
    require(after<=through,"reversed committed history cursors");
    query_.text(1,world.str());
    query_.u64(2,after.value);
    query_.u64(3,through.value);
}

std::optional<EventBlock> BlockCursor::next() {
    if (cursor_==through_) return {};
    require(query_.row(),"missing contiguous durable history block");
    auto bytes=query_.blob(6,block_encoded_limit);
    const auto h=inspect_block(bytes);
    require(h.world==world_ && h.first.value==query_.u64(0) && h.last.value==query_.u64(1) &&
            h.begin.milliseconds==query_.number(2) && h.end.milliseconds==query_.number(3) &&
            h.raw_bytes==static_cast<std::uint64_t>(query_.number(4)) && h.digest==column_digest(query_,5) &&
            h.first.value<=cursor_.value+1 && h.last>cursor_ && h.last<=through_,
            "fact block index disagrees with canonical header");
    if (previous_)
        require(h.first.value==cursor_.value+1 && h.begin>=previous_time_ && h.previous==*previous_,
                "fact block chain or time order mismatch");
    else
        require(h.previous==block_tail(db_,world_,{h.first.value-1}),"missing or divergent predecessor block");
    cursor_=h.last;
    previous_time_=h.end;
    previous_=h.digest;
    return EventBlock{h,std::move(bytes)};
}

SqlEventPrefix::SqlEventPrefix(const std::filesystem::path& path,WorldId world,std::size_t size,Digest tail)
    :db_(open_readonly(path)),world_(world),size_(size),tail_(tail) {}

std::vector<WorldEvent> SqlEventPrefix::read(EventId after,std::size_t limit) const {
    std::vector<WorldEvent> out(0);
    if (after.value>=size_ || !limit) return out;
    const auto count=std::min<std::size_t>(limit,size_-static_cast<std::size_t>(after.value));
    out.reserve(count);
    BlockCursor cursor(db_.get(),world_,after,{size_});
    while (out.size()<count) {
        const auto block=cursor.next();
        require(block.has_value(),"short durable history range");
        if (block->header.last.value==size_) require(block->header.digest==tail_,"durable prefix tail changed");
        const auto facts=read_block(block->bytes,block->header);
        for (const auto& fact:facts) {
            if (fact.id>after) out.push_back(fact);
            if (out.size()==count) break;
        }
    }
    return out;
}

Digest append_blocks(sqlite3* db,WorldId world,const HistoryCapture& capture,EventId from,EventId through,bool founding) {
    require(from<=through && through.value<=capture.size(),"invalid captured block range");
    auto previous=block_tail(db,world,from);
    Statement put(db,"INSERT INTO fact_blocks VALUES(?,?,?,?,?,?,?,?)");
    while (from<through) {
        const auto count=static_cast<std::size_t>(std::min<std::uint64_t>(block_records,through.value-from.value));
        const auto facts=capture.read(from,count);
        require(facts.size()==count && facts.front().id.value==from.value+1 && facts.front().world==world,
                "captured suffix does not continue published facts");
        const auto block=seal_block(facts,previous,founding);
        const auto& h=block.header;
        put.text(1,world.str());
        put.u64(2,h.first.value); put.u64(3,h.last.value);
        put.number(4,h.begin.milliseconds); put.number(5,h.end.milliseconds);
        put.number(6,static_cast<std::int64_t>(h.raw_bytes));
        put.blob(7,h.digest); put.blob(8,block.bytes);
        put.done(); put.reset();
        from=h.last;
        previous=h.digest;
    }
    return previous;
}

void verify_blocks(sqlite3* db,WorldId world,EventId from,EventId through,const Digest& tail) {
    BlockCursor cursor(db,world,from,through);
    auto seen=block_tail(db,world,from);
    while (const auto block=cursor.next()) {
        require(block->header.first.value==from.value+1 && block->header.previous==seen,
                "published cut does not start at an exact block boundary");
        from=block->header.last;
        seen=block->header.digest;
    }
    require(seen==tail,"fact chain does not match checkpoint anchor");
}

void require_history_prefix(sqlite3* db,WorldId world,const HistoryCapture& capture,EventId count,
                            const Digest& tail) {
    require(count.value<=capture.size(),"captured history is shorter than the published prefix");
    if (const auto* prefix=dynamic_cast<const SqlEventPrefix*>(capture.prefix().get());
        prefix && prefix->matches(world,count.value,tail)) return;
    BlockCursor cursor(db,world,{},count);
    auto seen=Digest{};
    while (const auto block=cursor.next()) {
        const auto facts=read_block(block->bytes,block->header);
        const auto other=capture.read({block->header.first.value-1},facts.size());
        require(other.size()==facts.size(),"short candidate history prefix");
        for (std::size_t i=0;i<facts.size();++i)
            require(encode_event(facts[i])==encode_event(other[i]),"divergent committed history prefix");
        seen=block->header.digest;
    }
    require(seen==tail,"divergent published history tail");
}

void put_anchor(sqlite3* db,const SaveToken& token,SimTime time,std::span<const std::uint8_t> frame,
                const Digest& parent,const Digest& tail) {
    Statement q(db,"INSERT INTO history_anchors VALUES(?,?,?,?,?)");
    q.text(1,token.world.str()); q.u64(2,token.generation);
    q.blob(3,parent); q.blob(4,tail); q.blob(5,anchor_digest(token,time,frame,parent,tail));
    q.done();
}

HistoryAnchor read_anchor(sqlite3* db,WorldId world,std::uint64_t generation,std::size_t byte_limit) {
    Statement q(db,"SELECT g.generation,g.revision,g.cursor,g.checkpoint_hash,g.time_ms,g.checkpoint,"
                   "a.parent,a.tail,a.digest FROM generations g JOIN history_anchors a USING(world,generation) "
                   "WHERE g.world=? AND g.generation=?");
    q.text(1,world.str()); q.u64(2,generation);
    require(q.row(),"complete state frame or history anchor unavailable");
    HistoryAnchor anchor{token(q,world),{q.number(4)},column_digest(q,6),column_digest(q,7),column_digest(q,8),
                         q.blob(5,byte_limit)};
    require(anchor.time.milliseconds>=0 && hash(anchor.frame)==anchor.token.checkpoint_hash &&
            anchor.digest==anchor_digest(anchor.token,anchor.time,anchor.frame,anchor.parent,anchor.tail) &&
            anchor.tail==block_tail(db,world,{anchor.token.cursor}),"checkpoint anchor or frame checksum mismatch");
    return anchor;
}
} // namespace antworld::storage::detail
