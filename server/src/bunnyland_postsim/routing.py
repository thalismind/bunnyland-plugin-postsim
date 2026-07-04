"""Deterministic room-graph routing over ``ExitTo`` edges.

Couriers walk the world graph one hop per tick. ``next_hop`` runs a breadth-first search from
one room to another and returns the *first* step of a shortest path, so a courier only ever
needs to know "which door do I take next". The search is fully deterministic — neighbours are
visited in sorted id order and ties are broken by id — so the same world always routes mail
the same way, with no reliance on ``random`` or dict/set iteration order.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable

from bunnyland.core import ExitTo
from relics import EntityId, World


def exits_of(world: World, room_id: EntityId) -> list[EntityId]:
    """Return the rooms directly reachable from ``room_id``, sorted for determinism."""
    if not world.has_entity(room_id):
        return []
    targets = {
        target_id
        for _edge, target_id in world.get_entity(room_id).get_relationships(ExitTo)
        if world.has_entity(target_id)
    }
    return sorted(targets, key=_id_key)


def next_hop(world: World, from_room_id: EntityId, to_room_id: EntityId) -> EntityId | None:
    """Return the next room to step into on a shortest path ``from_room -> to_room``.

    Returns ``None`` when the two rooms are the same, when either is missing, or when no path
    of ``ExitTo`` edges connects them.
    """
    if from_room_id == to_room_id:
        return None
    if not world.has_entity(from_room_id) or not world.has_entity(to_room_id):
        return None

    # BFS recording, for every reachable room, the first hop taken to get there.
    first_hop: dict[EntityId, EntityId] = {}
    queue: deque[EntityId] = deque()
    for neighbour in exits_of(world, from_room_id):
        if neighbour not in first_hop:
            first_hop[neighbour] = neighbour
            queue.append(neighbour)
    while queue:
        room_id = queue.popleft()
        if room_id == to_room_id:
            return first_hop[room_id]
        for neighbour in exits_of(world, room_id):
            if neighbour not in first_hop:
                first_hop[neighbour] = first_hop[room_id]
                queue.append(neighbour)
    return None


def next_hop_to_any(
    world: World, from_room_id: EntityId, targets: Iterable[EntityId]
) -> EntityId | None:
    """Return the next hop toward the *nearest* of ``targets`` from ``from_room_id``.

    The nearest target wins; equal-distance ties resolve by the deterministic BFS order (exits
    are always visited in sorted id order). Returns ``None`` when none of the targets are
    reachable (or the only reachable target is the current room).
    """
    target_set = {target for target in targets if target != from_room_id}
    if not target_set:
        return None
    first_hop: dict[EntityId, EntityId] = {}
    queue: deque[EntityId] = deque()
    for neighbour in exits_of(world, from_room_id):
        if neighbour not in first_hop:
            first_hop[neighbour] = neighbour
            queue.append(neighbour)
    while queue:
        room_id = queue.popleft()
        if room_id in target_set:
            return first_hop[room_id]
        for neighbour in exits_of(world, room_id):
            if neighbour not in first_hop:
                first_hop[neighbour] = first_hop[room_id]
                queue.append(neighbour)
    return None


def _id_key(entity_id: EntityId) -> tuple[str, int]:
    return (entity_id.prefab, entity_id.sequence)


__all__ = ["exits_of", "next_hop", "next_hop_to_any"]
