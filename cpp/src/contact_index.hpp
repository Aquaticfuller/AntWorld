#pragma once
#include "antworld/core/geometry.hpp"
#include "antworld/core/rng.hpp"
#include "antworld/core/profiling.hpp"
#include <cmath>
#include <map>
#include <stdexcept>

namespace antworld::detail {
// Disposable order-statistic treaps. Identity-hashed priorities give a unique
// shape on restore; rank selection never enumerates a crowded bucket.
struct ContactNode {
  PointQ bucket;
  EntityId left, right;
  std::uint64_t size{1}, priority{};
  // std::map node addresses survive insertion and node-handle rollback.
  // Disposable child references avoid an additional logarithmic lookup at
  // every rank-walk edge. Journaled IDs remain the mutation authority.
  const ContactNode *left_node{}, *right_node{};
};
using ContactNodes = std::map<EntityId, ContactNode>;
using ContactRoots = std::map<PointQ, EntityId>;
inline PointQ contact_key(PositionM p, double radius) {
  const double width = radius > 0 ? radius : 1.0;
  auto component = [&](double x) {
    const auto q = std::floor(x / width);
    if (!std::isfinite(q) || q < INT32_MIN + 2.0 || q > INT32_MAX - 2.0)
      throw std::invalid_argument(
          "contact index coordinate exceeds host range");
    return static_cast<std::int32_t>(q);
  };
  return {component(p.x), component(p.y), component(p.z)};
}
inline ContactNode contact_node(EntityId id, PointQ key) {
  Rng rng(id.value ^ UINT64_C(0x5336434f4e544143));
  return {key, {}, {}, 1, rng.next()};
}
inline std::uint64_t contact_size(const ContactNodes &nodes, EntityId id) {
  return id.value ? nodes.at(id).size : 0;
}
inline bool contact_before(const ContactNodes &nodes, EntityId a, EntityId b) {
  const auto x = nodes.at(a).priority, y = nodes.at(b).priority;
  return x != y ? x < y : a < b;
}
template <class Journal>
void contact_set(const ContactNodes &nodes, Journal &journal, EntityId id,
                 ContactNode node) {
  node.size =
      1 + contact_size(nodes, node.left) + contact_size(nodes, node.right);
  node.left_node = node.left.value ? &nodes.at(node.left) : nullptr;
  node.right_node = node.right.value ? &nodes.at(node.right) : nullptr;
  journal.set(id, node);
}
template <class Journal>
EntityId contact_merge(const ContactNodes &nodes, Journal &journal, EntityId a,
                       EntityId b) {
  if (!a.value)
    return b;
  if (!b.value)
    return a;
  if (contact_before(nodes, a, b)) {
    auto n = nodes.at(a);
    n.right = contact_merge(nodes, journal, n.right, b);
    contact_set(nodes, journal, a, n);
    return a;
  }
  auto n = nodes.at(b);
  n.left = contact_merge(nodes, journal, a, n.left);
  contact_set(nodes, journal, b, n);
  return b;
}
template <class Journal>
EntityId contact_insert(const ContactNodes &nodes, Journal &journal,
                        EntityId root, EntityId id) {
  if (!root.value)
    return id;
  auto n = nodes.at(root);
  if (id < root) {
    n.left = contact_insert(nodes, journal, n.left, id);
    contact_set(nodes, journal, root, n);
    if (contact_before(nodes, n.left, root)) {
      const auto top = n.left;
      auto child = nodes.at(top);
      n.left = child.right;
      contact_set(nodes, journal, root, n);
      child.right = root;
      contact_set(nodes, journal, top, child);
      return top;
    }
  } else {
    n.right = contact_insert(nodes, journal, n.right, id);
    contact_set(nodes, journal, root, n);
    if (contact_before(nodes, n.right, root)) {
      const auto top = n.right;
      auto child = nodes.at(top);
      n.right = child.left;
      contact_set(nodes, journal, root, n);
      child.left = root;
      contact_set(nodes, journal, top, child);
      return top;
    }
  }
  return root;
}
template <class Journal>
EntityId contact_remove(const ContactNodes &nodes, Journal &journal,
                        EntityId root, EntityId id) {
  if (!root.value)
    throw std::logic_error("missing contact index identity");
  auto n = nodes.at(root);
  if (root == id)
    return contact_merge(nodes, journal, n.left, n.right);
  if (id < root)
    n.left = contact_remove(nodes, journal, n.left, id);
  else
    n.right = contact_remove(nodes, journal, n.right, id);
  contact_set(nodes, journal, root, n);
  return root;
}
inline EntityId contact_rank(const ContactNodes &nodes, EntityId root,
                             std::uint64_t rank, std::uint64_t &visits) {
  const auto *node = root.value ? &nodes.at(root) : nullptr;
  while (root.value) {
    ++visits;
    const auto &n = *node;
    const auto left = n.left_node ? n.left_node->size : 0;
    if (rank == left)
      return root;
    if (rank < left) {
      root = n.left; node = n.left_node;
    } else {
      rank -= left + 1;
      root = n.right; node = n.right_node;
    }
  }
  throw std::logic_error("contact rank outside bucket");
}
// Restore already owns a detached candidate State; no rollback journal is
// needed.
struct ContactRebuilder {
  ContactNodes &nodes;
  void set(EntityId id, const ContactNode &node) {
    nodes.insert_or_assign(id, node);
  }
};
template <class S> void rebuild_contacts(S &s) {
  profiling::Scope profile(profiling::Category::Index);
  if (!s.social || !s.social->bounded_contacts)
    return;
  ContactRebuilder journal{s.contact_nodes};
  for (std::size_t i = 0; i < s.ants.size(); ++i) {
    const auto a = s.ants.get(i);
    if (!a.alive())
      continue;
    const auto key = contact_key(a.position, s.config.contact_distance_m);
    journal.set(a.id, contact_node(a.id, key));
    s.contact_roots[key] =
        contact_insert(s.contact_nodes, journal, s.contact_roots[key], a.id);
  }
}
} // namespace antworld::detail
