from __future__ import annotations

from bunnyland.core import ExitTo, RoomComponent, WorldActor, spawn_entity

from bunnyland_postsim.routing import exits_of, next_hop, next_hop_to_any


def _room(world, title):
    return spawn_entity(world, [RoomComponent(title=title)])


def _link(a, b, *, both=True):
    a.add_relationship(ExitTo(direction="out"), b.id)
    if both:
        b.add_relationship(ExitTo(direction="back"), a.id)


def _chain(world, n):
    rooms = [_room(world, f"r{i}") for i in range(n)]
    for a, b in zip(rooms, rooms[1:], strict=False):
        _link(a, b)
    return rooms


def test_next_hop_walks_toward_destination():
    actor = WorldActor()
    a, b, c = _chain(actor.world, 3)

    assert next_hop(actor.world, a.id, c.id) == b.id
    assert next_hop(actor.world, b.id, c.id) == c.id


def test_next_hop_is_none_for_same_room():
    actor = WorldActor()
    (a,) = _chain(actor.world, 1)
    assert next_hop(actor.world, a.id, a.id) is None


def test_next_hop_is_none_when_unreachable():
    actor = WorldActor()
    a = _room(actor.world, "a")
    z = _room(actor.world, "z")  # no exits between a and z
    assert next_hop(actor.world, a.id, z.id) is None


def test_exits_are_sorted_and_deduplicated():
    actor = WorldActor()
    a, b, c = _chain(actor.world, 3)
    a.add_relationship(ExitTo(direction="dupe"), b.id)  # duplicate exit to b
    exits = exits_of(actor.world, a.id)
    assert exits == sorted(exits, key=lambda i: (i.prefab, i.sequence))
    assert exits.count(b.id) == 1


def test_next_hop_to_any_picks_nearest_target():
    actor = WorldActor()
    a, b, c = _chain(actor.world, 3)
    far = _room(actor.world, "far")
    _link(a, far)  # far is one hop from a, c is two hops

    hop = next_hop_to_any(actor.world, a.id, {c.id, far.id})
    assert hop == far.id


def test_next_hop_to_any_is_none_when_no_target_reachable():
    actor = WorldActor()
    a = _room(actor.world, "a")
    z = _room(actor.world, "z")
    assert next_hop_to_any(actor.world, a.id, {z.id}) is None
