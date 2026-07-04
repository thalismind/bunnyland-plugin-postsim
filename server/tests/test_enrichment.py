from __future__ import annotations

import asyncio

from bunnyland.core import RoomComponent, WorldActor, spawn_entity
from bunnyland.core.components import GenerationIntentComponent
from bunnyland.core.events import RoomGeneratedEvent, event_base
from bunnyland.plugins import apply_plugins, load_modules

from bunnyland_postsim.components import CourierComponent, MailboxComponent
from bunnyland_postsim.mailboxes import mailboxes_in_room


def _actor():
    actor = WorldActor()
    apply_plugins(load_modules(["bunnyland_postsim"]), actor)
    return actor


def _publish(actor, event):
    asyncio.run(actor.bus.publish(event))


def _generate_room(actor, *, title="room", tags=(), description="", biome="unknown"):
    room = spawn_entity(actor.world, [RoomComponent(title=title, biome=biome)])
    event = RoomGeneratedEvent(
        **event_base(0),
        seed="seed",
        entity_id=str(room.id),
        entity_key="room",
        entity_kind="room",
        generation=GenerationIntentComponent(tags=tuple(tags), description=description),
        room_key="room",
        biome=biome,
    )
    _publish(actor, event)
    return room


def _has_courier(world):
    return bool(list(world.query().with_all([CourierComponent]).execute_entities()))


def test_settlement_room_gets_a_mailbox():
    actor = _actor()
    room = _generate_room(actor, tags=("town", "friendly"))
    boxes = mailboxes_in_room(actor.world, actor.world.get_entity(room.id))
    assert any(box.has_component(MailboxComponent) for box in boxes)


def test_settlement_detected_from_description_text():
    actor = _actor()
    room = _generate_room(actor, description="a bustling harbour market")
    assert mailboxes_in_room(actor.world, actor.world.get_entity(room.id))


def test_wilderness_room_gets_nothing():
    actor = _actor()
    room = _generate_room(actor, tags=("forest",), description="a lonely stretch of pines")
    assert mailboxes_in_room(actor.world, actor.world.get_entity(room.id)) == []
    assert not _has_courier(actor.world)


def test_first_settlement_gets_a_courier_but_the_second_does_not():
    actor = _actor()
    _generate_room(actor, title="first", tags=("village",))
    assert _has_courier(actor.world)
    couriers_after_first = list(
        actor.world.query().with_all([CourierComponent]).execute_entities()
    )
    _generate_room(actor, title="second", tags=("village",))
    couriers_after_second = list(
        actor.world.query().with_all([CourierComponent]).execute_entities()
    )
    assert len(couriers_after_first) == 1
    assert len(couriers_after_second) == 1


def test_mailbox_is_not_duplicated_on_repeat_events():
    actor = _actor()
    room = _generate_room(actor, title="town", tags=("town",))
    # Re-publish for the same room (idempotency guard).
    event = RoomGeneratedEvent(
        **event_base(0),
        seed="seed",
        entity_id=str(room.id),
        entity_key="room",
        entity_kind="room",
        generation=GenerationIntentComponent(tags=("town",)),
        room_key="room",
    )
    _publish(actor, event)
    boxes = mailboxes_in_room(actor.world, actor.world.get_entity(room.id))
    assert len(boxes) == 1
