#include "event_block.hpp"
#include "sqlite_internal.hpp"
#include "zlib.h"
#include <algorithm>

namespace antworld::storage::detail {
namespace {
constexpr std::uint64_t block_magic=UINT64_C(0x3130544341465741); // AWFACT01
constexpr std::uint64_t founding_block_magic=UINT64_C(0x3230544341465741); // AWFACT02
constexpr std::uint64_t persistence_block_magic=UINT64_C(0x3330544341465741); // AWFACT03
constexpr std::uint64_t access_block_magic=UINT64_C(0x3430544341465741); // AWFACT04
constexpr std::uint64_t provisioning_block_magic=UINT64_C(0x3530544341465741); // AWFACT05
constexpr std::uint64_t dietary_block_magic=UINT64_C(0x3630544341465741); // AWFACT06
constexpr std::uint64_t uptake_block_magic=UINT64_C(0x3730544341465741); // AWFACT07
constexpr std::uint64_t resupply_block_magic=UINT64_C(0x3830544341465741); // AWFACT08
constexpr std::size_t hashed_header=104, header_size=136;

void put(std::vector<std::uint8_t>& bytes,std::uint64_t value,unsigned width) {
    for (unsigned i=0;i<width;++i) bytes.push_back(static_cast<std::uint8_t>(value>>(i*8)));
}

std::uint64_t get(std::span<const std::uint8_t> bytes,std::size_t& cursor,unsigned width) {
    require(width<=bytes.size()-cursor,"truncated event block");
    std::uint64_t result=0;
    for (unsigned i=0;i<width;++i) result|=std::uint64_t{bytes[cursor++]}<<(i*8);
    return result;
}

void validate_event(const WorldEvent& event,const BlockHeader& header,EventId expected,
                    SimTime previous_time,std::uint64_t previous_revision) {
    require(event.id==expected && event.world==header.world &&
            event.kind<=(header.fact_schema>=7?FactKind::FoundingBoundaryUptake:header.fact_schema==6?FactKind::FoundingDietaryEggFunded:header.fact_schema>=4?FactKind::FoundingHatchCue:
                         header.fact_schema>=2?FactKind::FoundingRation:FactKind::BroodMoved) &&
            (!founding_fact(event.kind) || valid_founding_payload(event)) &&
            (event.kind!=FactKind::FoundingConfigured || event.random_value==header.fact_schema-1) &&
            (event.kind!=FactKind::CareTick || !event.random_value ||
                (header.fact_schema>=3 && valid_founding_care_wake(event))) &&
            event.time>=previous_time && event.time<=header.end && event.revision>previous_revision,
            "invalid canonical event block order or fact");
}
} // namespace

EventBlock seal_block(std::span<const WorldEvent> facts,const Digest& previous,FactSchema schema) {
    require(!facts.empty() && facts.size()<=block_records,"invalid event block record count");
    const auto& first=facts.front();
    const auto& last=facts.back();
    BlockHeader header{first.world,first.id,last.id,first.time,last.time,0,0,previous,{}};
    header.fact_schema=static_cast<unsigned>(schema);
    std::vector<std::uint8_t> raw(0);
    raw.reserve(facts.size()*214);
    std::uint64_t revision=0;
    auto now=first.time;
    for (std::size_t i=0;i<facts.size();++i) {
        const auto& event=facts[i];
        validate_event(event,header,{checked_add(first.id.value,i)},now,revision);
        const auto bytes=encode_event(event);
        put(raw,bytes.size(),4);
        raw.insert(raw.end(),bytes.begin(),bytes.end());
        now=event.time;
        revision=event.revision;
    }
    auto packed_size=compressBound(static_cast<uLong>(raw.size()));
    std::vector<std::uint8_t> packed(static_cast<std::size_t>(packed_size));
    require(compress2(packed.data(),&packed_size,raw.data(),static_cast<uLong>(raw.size()),3)==Z_OK,
            "event block compression failed");
    packed.resize(static_cast<std::size_t>(packed_size));
    header.raw_bytes=raw.size();
    header.compressed_bytes=packed.size();
    std::vector<std::uint8_t> bytes(0);
    bytes.reserve(header_size+packed.size());
    put(bytes,schema==FactSchema::FoundingResupply ? resupply_block_magic : schema==FactSchema::FoundingUptake ? uptake_block_magic : schema==FactSchema::FoundingDietary ? dietary_block_magic : schema==FactSchema::FoundingProvisioning ? provisioning_block_magic : schema==FactSchema::FoundingEarlyAccess ? access_block_magic : schema==FactSchema::FoundingPersistence ? persistence_block_magic :
        schema==FactSchema::Founding ? founding_block_magic : block_magic,8);
    for (unsigned value:{header.fact_schema,1U,header.fact_schema,0U}) put(bytes,value,2); // Block, codec, fact schema, reserved.
    for (const auto value:{first.world.high,first.world.low,first.id.value,last.id.value,
             static_cast<std::uint64_t>(first.time.milliseconds),static_cast<std::uint64_t>(last.time.milliseconds)})
        put(bytes,value,8);
    put(bytes,raw.size(),4);
    put(bytes,packed.size(),4);
    bytes.insert(bytes.end(),previous.begin(),previous.end());
    header.digest=sha256(bytes,packed);
    bytes.insert(bytes.end(),header.digest.begin(),header.digest.end());
    bytes.insert(bytes.end(),packed.begin(),packed.end());
    return {header,std::move(bytes)};
}

BlockHeader inspect_block(std::span<const std::uint8_t> bytes) {
    require(bytes.size()>=header_size && bytes.size()<=block_encoded_limit,"invalid event block length");
    std::size_t cursor=0;
    const auto magic=get(bytes,cursor,8);
    const unsigned schema=magic==resupply_block_magic?8U:magic==uptake_block_magic?7U:magic==dietary_block_magic?6U:magic==provisioning_block_magic?5U:magic==access_block_magic?4U:magic==persistence_block_magic?3U:magic==founding_block_magic?2U:1U;
    require((schema>1 || magic==block_magic) && get(bytes,cursor,2)==schema && get(bytes,cursor,2)==1 &&
            get(bytes,cursor,2)==schema && get(bytes,cursor,2)==0,"unsupported canonical event block");
    BlockHeader header{};
    header.fact_schema=schema;
    header.world={get(bytes,cursor,8),get(bytes,cursor,8)};
    header.first={get(bytes,cursor,8)};
    header.last={get(bytes,cursor,8)};
    const auto first_time=get(bytes,cursor,8),last_time=get(bytes,cursor,8);
    require(first_time<=last_time && last_time<=INT64_MAX && header.world!=WorldId{} &&
            header.first.value && header.last>=header.first &&
            header.last.value-header.first.value<block_records,"invalid block identity or time");
    header.begin={static_cast<std::int64_t>(first_time)};
    header.end={static_cast<std::int64_t>(last_time)};
    header.raw_bytes=static_cast<std::size_t>(get(bytes,cursor,4));
    header.compressed_bytes=static_cast<std::size_t>(get(bytes,cursor,4));
    const auto count=header.last.value-header.first.value+1;
    require(header.raw_bytes>=count*163 && header.raw_bytes<=count*214 &&
            header.compressed_bytes==bytes.size()-header_size && header.compressed_bytes,
            "event block byte count mismatch");
    std::copy_n(bytes.data()+cursor,header.previous.size(),header.previous.begin());
    std::copy_n(bytes.data()+hashed_header,header.digest.size(),header.digest.begin());
    require(sha256(bytes.first(hashed_header),bytes.subspan(header_size))==header.digest,
            "event block SHA-256 mismatch");
    return header;
}

std::vector<WorldEvent> read_block(std::span<const std::uint8_t> bytes,const BlockHeader& header) {
    std::vector<std::uint8_t> raw(header.raw_bytes);
    auto size=static_cast<uLongf>(raw.size());
    auto consumed=static_cast<uLong>(header.compressed_bytes);
    require(uncompress2(raw.data(),&size,bytes.data()+header_size,&consumed)==Z_OK &&
            size==raw.size() && consumed==header.compressed_bytes,"invalid compressed event block");
    const auto count=static_cast<std::size_t>(header.last.value-header.first.value+1);
    std::vector<WorldEvent> facts(0);
    facts.reserve(count);
    std::size_t cursor=0;
    auto now=header.begin;
    std::uint64_t revision=0;
    for (std::size_t i=0;i<count;++i) {
        const auto size_word=get(raw,cursor,4);
        require((size_word==159 || size_word==210) && size_word<=raw.size()-cursor,
                "invalid length-prefixed canonical fact");
        const auto length=static_cast<std::size_t>(size_word);
        auto event=decode_event(std::span{raw}.subspan(cursor,length));
        validate_event(event,header,{header.first.value+i},now,revision);
        cursor+=length;
        now=event.time;
        revision=event.revision;
        facts.push_back(event);
    }
    require(cursor==raw.size() && facts.front().time==header.begin && facts.back().time==header.end,
            "event block boundaries disagree with facts");
    return facts;
}
} // namespace antworld::storage::detail
