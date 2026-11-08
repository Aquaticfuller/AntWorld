#include "scenario.hpp"

#include <charconv>
#include <cmath>
#include <limits>
#include <map>
#include <stdexcept>
#include <variant>
#include <vector>

namespace antworld::app {
namespace {
struct Number { std::string text; };
struct Json {
    using Object = std::map<std::string, Json>;
    using Array = std::vector<Json>;
    std::variant<std::nullptr_t, bool, Number, std::string, Object, Array> value;
    template <typename T> const T& as() const {
        const auto* found = std::get_if<T>(&value);
        if (!found) throw std::invalid_argument("scenario field has the wrong JSON type");
        return *found;
    }
};
// Bounded JSON reader for the CLI boundary. Numbers retain their original text.
class Parser {
public:
    explicit Parser(std::string_view input) : input_(input) {
        if (input.size() > 1024 * 1024) fail("scenario exceeds 1 MiB");
    }
    Json parse() {
        auto value = read(0);
        whitespace();
        if (pos_ != input_.size()) fail("trailing JSON data");
        return value;
    }
private:
    std::string_view input_;
    std::size_t pos_{};
    [[noreturn]] void fail(std::string_view reason) const {
        throw std::invalid_argument(std::string(reason) + " at byte " + std::to_string(pos_));
    }
    char peek() const { return pos_ < input_.size() ? input_[pos_] : '\0'; }
    char take() { if (pos_ == input_.size()) fail("unexpected end of JSON"); return input_[pos_++]; }
    static bool digit(char c) { return c >= '0' && c <= '9'; }
    void whitespace() { while (peek() == ' ' || peek() == '\t' || peek() == '\r' || peek() == '\n') ++pos_; }
    bool accept(char c) { if (peek() != c) return false; ++pos_; return true; }
    void expect(char c) { if (!accept(c)) fail("unexpected JSON token"); }
    std::uint32_t hex4() {
        std::uint32_t value = 0;
        for (int i = 0; i < 4; ++i) {
            const char c = take();
            const int d = c >= '0' && c <= '9' ? c - '0' : c >= 'a' && c <= 'f' ? c - 'a' + 10 :
                c >= 'A' && c <= 'F' ? c - 'A' + 10 : -1;
            if (d < 0) fail("invalid Unicode escape");
            value = value * 16 + static_cast<std::uint32_t>(d);
        }
        return value;
    }
    static void utf8(std::string& out, std::uint32_t cp) {
        if (cp < 0x80) { out += static_cast<char>(cp); return; }
        if (cp < 0x800) out += static_cast<char>(0xc0 | (cp >> 6));
        else if (cp < 0x10000) {
            out += static_cast<char>(0xe0 | (cp >> 12));
            out += static_cast<char>(0x80 | ((cp >> 6) & 63));
        } else {
            out += static_cast<char>(0xf0 | (cp >> 18));
            out += static_cast<char>(0x80 | ((cp >> 12) & 63));
            out += static_cast<char>(0x80 | ((cp >> 6) & 63));
        }
        out += static_cast<char>(0x80 | (cp & 63));
    }
    std::string string() {
        expect('"');
        std::string out;
        while (peek() != '"') {
            const auto c = static_cast<unsigned char>(take());
            if (c < 0x20) fail("control character in JSON string");
            if (c >= 0x80) {
                const int count = c >= 0xc2 && c <= 0xdf ? 1 : c >= 0xe0 && c <= 0xef ? 2 :
                    c >= 0xf0 && c <= 0xf4 ? 3 : -1;
                if (count < 0) fail("invalid UTF-8 lead byte");
                std::uint32_t cp = c & (count == 1 ? 31u : count == 2 ? 15u : 7u);
                for (int i = 0; i < count; ++i) {
                    const auto next = static_cast<unsigned char>(take());
                    if ((next & 0xc0) != 0x80) fail("invalid UTF-8 continuation");
                    cp = (cp << 6) | (next & 63);
                }
                if (cp < (count == 1 ? 0x80u : count == 2 ? 0x800u : 0x10000u) ||
                    cp > 0x10ffff || (cp >= 0xd800 && cp <= 0xdfff)) fail("invalid UTF-8 codepoint");
                utf8(out, cp);
            } else if (c != '\\') out += static_cast<char>(c);
            else {
                switch (take()) {
                case '"': out += '"'; break;
                case '\\': out += '\\'; break;
                case '/': out += '/'; break;
                case 'b': out += '\b'; break;
                case 'f': out += '\f'; break;
                case 'n': out += '\n'; break;
                case 'r': out += '\r'; break;
                case 't': out += '\t'; break;
                case 'u': {
                    auto cp = hex4();
                    if (cp >= 0xd800 && cp <= 0xdbff) {
                        expect('\\'); expect('u'); const auto low = hex4();
                        if (low < 0xdc00 || low > 0xdfff) fail("invalid surrogate pair");
                        cp = 0x10000 + ((cp - 0xd800) << 10) + (low - 0xdc00);
                    } else if (cp >= 0xdc00 && cp <= 0xdfff) fail("unpaired surrogate");
                    utf8(out, cp); break;
                }
                default: fail("invalid JSON escape");
                }
            }
        }
        expect('"');
        return out;
    }
    Json read(unsigned depth) {
        if (depth > 32) fail("JSON nesting limit exceeded");
        whitespace();
        if (peek() == '"') return {string()};
        if (accept('{')) {
            Json::Object result;
            whitespace();
            if (accept('}')) return {result};
            do {
                whitespace(); auto key = string(); whitespace(); expect(':');
                auto value = read(depth + 1);
                if (!result.emplace(std::move(key), std::move(value)).second) fail("duplicate JSON key");
                whitespace();
                if (accept('}')) return {result};
                expect(',');
            } while (true);
        }
        if (accept('[')) {
            Json::Array result;
            whitespace();
            if (accept(']')) return {result};
            do {
                result.push_back(read(depth + 1)); whitespace();
                if (accept(']')) return {result};
                expect(',');
            } while (true);
        }
        for (auto token : {std::string_view("true"), std::string_view("false"), std::string_view("null")}) {
            if (input_.substr(pos_, token.size()) == token) {
                pos_ += token.size();
                if (token == "null") return {nullptr};
                return {token == "true"};
            }
        }
        const auto start = pos_;
        accept('-');
        if (!accept('0')) {
            if (!digit(peek()) || peek() == '0') fail("invalid JSON number");
            while (digit(peek())) ++pos_;
        }
        if (accept('.')) {
            if (!digit(peek())) fail("invalid fraction");
            while (digit(peek())) ++pos_;
        }
        if (accept('e') || accept('E')) {
            if (!accept('+')) accept('-');
            if (!digit(peek())) fail("invalid exponent");
            while (digit(peek())) ++pos_;
        }
        return {Number{std::string(input_.substr(start, pos_ - start))}};
    }
};
const Json::Object& object(const Json& j, std::initializer_list<std::string_view> keys) {
    const auto& obj = j.as<Json::Object>();
    for (const auto& [key, value] : obj) {
        (void)value;
        bool known = false;
        for (auto allowed : keys) known |= key == allowed;
        if (!known) throw std::invalid_argument("unknown scenario field: " + key);
    }
    for (auto key : keys) if (!obj.contains(std::string(key)))
        throw std::invalid_argument("missing scenario field: " + std::string(key));
    return obj;
}
void equals(const Json& j, std::string_view expected) {
    if (j.as<std::string>() != expected) throw std::invalid_argument("unsupported scenario value; expected " + std::string(expected));
}
double numeric(const Json& j) {
    const auto& text = j.as<Number>().text;
    double value{};
    const auto result = std::from_chars(text.data(), text.data() + text.size(), value);
    if (result.ec != std::errc{} || result.ptr != text.data() + text.size() || !std::isfinite(value))
        throw std::invalid_argument("scenario coordinate must be a finite number");
    return value;
}
} // namespace
std::uint64_t parse_unsigned(std::string_view text) {
    if (text.empty() || text.find_first_not_of("0123456789") != text.npos)
        throw std::invalid_argument("expected a nonnegative decimal integer token");
    std::uint64_t value{};
    const auto parsed = std::from_chars(text.data(), text.data() + text.size(), value);
    if (parsed.ec != std::errc{} || parsed.ptr != text.data() + text.size())
        throw std::invalid_argument("integer outside uint64 range");
    return value;
}
Scenario parse_scenario(std::string_view json) {
    const auto parsed = Parser(json).parse();
    const auto& root = object(parsed, {"scenario_schema_version", "scenario_name", "status", "world",
        "colonies", "food_sources", "requested_observation_ms"});
    if (parse_unsigned(root.at("scenario_schema_version").as<Number>().text) != 1)
        throw std::invalid_argument("unsupported scenario schema version");
    if (root.at("scenario_name").as<std::string>().empty()) throw std::invalid_argument("empty scenario name");
    equals(root.at("status"), "ENGINEERING_FIXTURE");
    if (!root.at("colonies").as<Json::Array>().empty() || !root.at("food_sources").as<Json::Array>().empty())
        throw std::invalid_argument("S0 supports empty colonies and food_sources only");
    const auto& w = object(root.at("world"), {"world_id", "seed", "model_version", "time_unit", "position_unit", "mass_unit", "bounds_m"});
    const auto id = WorldId::parse(w.at("world_id").as<std::string>());
    const auto seed = parse_unsigned(w.at("seed").as<Number>().text);
    (void)w.at("model_version").as<std::string>();
    equals(w.at("time_unit"), "ms"); equals(w.at("position_unit"), "m"); equals(w.at("mass_unit"), "ug");
    const auto& bounds = object(w.at("bounds_m"), {"x_min", "x_max", "y_min", "y_max", "z_min", "z_max"});
    for (auto axis : {"x", "y", "z"}) {
        if (numeric(bounds.at(std::string(axis) + "_min")) >= numeric(bounds.at(std::string(axis) + "_max")))
            throw std::invalid_argument("scenario bounds must have min < max");
    }
    const auto observation = parse_unsigned(root.at("requested_observation_ms").as<Number>().text);
    if (observation > static_cast<std::uint64_t>(std::numeric_limits<std::int64_t>::max()))
        throw std::invalid_argument("observation time outside int64 range");
    return {id, seed, {static_cast<std::int64_t>(observation)}};
}
} // namespace antworld::app
