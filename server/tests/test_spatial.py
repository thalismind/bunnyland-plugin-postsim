"""Spatial helpers: holder_of, room_of, and move_entity."""

from __future__ import annotations

from bunnyland.core import (
    ContainmentMode,
    Contains,
    IdentityComponent,
    RoomComponent,
    WorldActor,
    container_of,
    spawn_entity,
)

from bunnyland_postsim.spatial import holder_of, move_entity, room_of


def _item(world, name="parcel"):
    return spawn_entity(world, [IdentityComponent(name=name, kind="item")])


def _room(world):
    return spawn_entity(world, [RoomComponent(title="Depot")])


def _hold(holder, item, mode=ContainmentMode.INVENTORY):
    holder.add_relationship(Contains(mode=mode), item.id)


# -- holder_of --------------------------------------------------------------------------


def test_holder_of_missing_item_is_none():
    actor = WorldActor()
    item = _item(actor.world)
    gone = item.id
    actor.world.remove(gone)
    assert holder_of(actor.world, gone) is None


def test_holder_of_uncontained_item_is_none():
    actor = WorldActor()
    assert holder_of(actor.world, _item(actor.world).id) is None


def test_holder_of_loose_in_room_is_none():
    actor = WorldActor()
    room = _room(actor.world)
    item = _item(actor.world)
    _hold(room, item, ContainmentMode.ROOM_CONTENT)
    assert holder_of(actor.world, item.id) is None


def test_holder_of_carried_item_returns_the_courier():
    actor = WorldActor()
    room = _room(actor.world)
    courier = _item(actor.world, "courier")
    _hold(room, courier, ContainmentMode.ROOM_CONTENT)
    item = _item(actor.world)
    _hold(courier, item)
    assert holder_of(actor.world, item.id).id == courier.id


# -- room_of ----------------------------------------------------------------------------


def test_room_of_missing_entity_is_none():
    actor = WorldActor()
    item = _item(actor.world)
    gone = item.id
    actor.world.remove(gone)
    assert room_of(actor.world, gone) is None


def test_room_of_loose_entity_finds_its_room():
    actor = WorldActor()
    room = _room(actor.world)
    item = _item(actor.world)
    _hold(room, item, ContainmentMode.ROOM_CONTENT)
    assert room_of(actor.world, item.id).id == room.id


def test_room_of_resolves_through_a_holder():
    actor = WorldActor()
    room = _room(actor.world)
    courier = _item(actor.world, "courier")
    _hold(room, courier, ContainmentMode.ROOM_CONTENT)
    item = _item(actor.world)
    _hold(courier, item)
    assert room_of(actor.world, item.id).id == room.id


def test_room_of_uncontained_is_none():
    actor = WorldActor()
    assert room_of(actor.world, _item(actor.world).id) is None


def test_room_of_gives_up_past_the_depth_limit():
    actor = WorldActor()
    chain = [_item(actor.world, f"box{i}") for i in range(10)]
    for parent, child in zip(chain, chain[1:], strict=False):
        _hold(parent, child)
    assert room_of(actor.world, chain[-1].id) is None


# -- move_entity ------------------------------------------------------------------------


def test_move_entity_reparents_from_one_container_to_another():
    actor = WorldActor()
    origin = _room(actor.world)
    dest = _room(actor.world)
    item = _item(actor.world)
    _hold(origin, item, ContainmentMode.ROOM_CONTENT)
    move_entity(actor.world, item.id, dest.id, mode=ContainmentMode.ROOM_CONTENT)
    assert container_of(actor.world.get_entity(item.id)) == dest.id


def test_move_entity_places_an_uncontained_item():
    actor = WorldActor()
    dest = _room(actor.world)
    item = _item(actor.world)  # not in any container yet
    move_entity(actor.world, item.id, dest.id, mode=ContainmentMode.ROOM_CONTENT)
    assert container_of(actor.world.get_entity(item.id)) == dest.id
