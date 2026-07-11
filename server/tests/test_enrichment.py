import asyncio

from bunnyland.core import WorldActor
from bunnyland.plugins import apply_plugins
from bunnyland.worldgen import RoomSpec, WorldProposal, instantiate

from bunnyland_postsim.components import CourierComponent, MailboxComponent
from bunnyland_postsim.mailboxes import mailboxes_in_room
from bunnyland_postsim.plugin import bunnyland_plugins as _plugins


def _world(*rooms: RoomSpec):
    actor = WorldActor()
    apply_plugins(_plugins(), actor)
    result = asyncio.run(instantiate(actor, WorldProposal(seed="seed", rooms=list(rooms))))
    return actor, result


def _couriers(actor):
    return list(actor.world.query().with_all([CourierComponent]).execute_entities())


def test_settlement_room_gets_a_mailbox():
    actor, result = _world(RoomSpec(key="town", title="Town", tags=("friendly",)))
    room = actor.world.get_entity(result.rooms["town"])
    assert any(box.has_component(MailboxComponent) for box in mailboxes_in_room(actor.world, room))


def test_settlement_detected_from_description_text():
    actor, result = _world(
        RoomSpec(key="harbor", title="Harbor", description="a bustling harbour market")
    )
    room = actor.world.get_entity(result.rooms["harbor"])
    assert mailboxes_in_room(actor.world, room)


def test_wilderness_room_gets_nothing():
    actor, result = _world(
        RoomSpec(
            key="forest",
            title="Forest",
            tags=("forest",),
            description="a lonely stretch of pines",
        )
    )
    room = actor.world.get_entity(result.rooms["forest"])
    assert mailboxes_in_room(actor.world, room) == []
    assert _couriers(actor) == []


def test_only_first_settlement_gets_singleton_children():
    actor, result = _world(
        RoomSpec(key="first", title="First Village"),
        RoomSpec(key="second", title="Second Village"),
    )
    assert len(_couriers(actor)) == 1
    first = actor.world.get_entity(result.rooms["first"])
    second = actor.world.get_entity(result.rooms["second"])
    assert len(mailboxes_in_room(actor.world, first)) == 1
    assert len(mailboxes_in_room(actor.world, second)) == 1
