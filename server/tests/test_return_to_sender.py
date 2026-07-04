from __future__ import annotations

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    ExitTo,
    IdentityComponent,
    RoomComponent,
    WorldActor,
    spawn_entity,
)

from bunnyland_postsim import (
    MailReturnedEvent,
    PostConsequence,
    is_timed_out,
    is_unroutable,
    should_return,
    spawn_courier,
    spawn_mailbox,
    spawn_parcel,
)
from bunnyland_postsim.components import MailInTransitComponent
from bunnyland_postsim.mailboxes import mail_in_mailbox


def _transit(origin, dest, current, *, age=0, ttl=32, returning=False):
    return MailInTransitComponent(
        sender_id="s",
        addressee_id="a",
        origin_room_id=str(origin),
        destination_room_id=str(dest),
        current_room_id=str(current),
        age_ticks=age,
        ttl_ticks=ttl,
        returning=returning,
    )


def test_is_timed_out_compares_age_to_budget():
    assert is_timed_out(_transit("r_1", "r_2", "r_1", age=32, ttl=32)) is True
    assert is_timed_out(_transit("r_1", "r_2", "r_1", age=31, ttl=32)) is False


def test_is_unroutable_when_no_path_exists():
    actor = WorldActor()
    a = spawn_entity(actor.world, [RoomComponent(title="A")])
    z = spawn_entity(actor.world, [RoomComponent(title="Z")])
    transit = _transit(a.id, z.id, a.id)
    assert is_unroutable(actor.world, transit, a.id) is True


def test_is_routable_when_a_path_exists():
    actor = WorldActor()
    a = spawn_entity(actor.world, [RoomComponent(title="A")])
    b = spawn_entity(actor.world, [RoomComponent(title="B")])
    a.add_relationship(ExitTo(direction="out"), b.id)
    transit = _transit(a.id, b.id, a.id)
    assert is_unroutable(actor.world, transit, a.id) is False


def test_should_return_on_timeout_but_not_when_already_returning():
    actor = WorldActor()
    a = spawn_entity(actor.world, [RoomComponent(title="A")])
    b = spawn_entity(actor.world, [RoomComponent(title="B")])
    a.add_relationship(ExitTo(direction="out"), b.id)
    b.add_relationship(ExitTo(direction="back"), a.id)
    timed_out = _transit(a.id, b.id, a.id, age=40, ttl=32)
    assert should_return(actor.world, timed_out, a.id) is True
    assert should_return(actor.world, _transit(a.id, b.id, a.id, age=40, returning=True), a.id) is (
        False
    )


def _character(world, room, name):
    character = spawn_entity(
        world, [IdentityComponent(name=name, kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), character.id)
    return character


def test_timed_out_parcel_bounces_back_mid_journey():
    actor = WorldActor()
    a = spawn_entity(actor.world, [RoomComponent(title="Post Office")])
    b = spawn_entity(actor.world, [RoomComponent(title="Lane")])
    c = spawn_entity(actor.world, [RoomComponent(title="Cottage")])
    a.add_relationship(ExitTo(direction="out"), b.id)
    b.add_relationship(ExitTo(direction="back"), a.id)
    b.add_relationship(ExitTo(direction="on"), c.id)
    c.add_relationship(ExitTo(direction="back"), b.id)
    box_a = spawn_mailbox(actor.world, room_id=a.id)
    sender = _character(actor.world, a, "Vin")
    addressee = _character(actor.world, c, "Kell")
    spawn_courier(actor.world, room_id=a.id)

    parcel = spawn_parcel(
        actor.world,
        text="hi",
        sender_id=str(sender.id),
        addressee_id=str(addressee.id),
    )
    box_a.add_relationship(Contains(mode=ContainmentMode.CONTAINER), parcel.id)
    # A tiny TTL guarantees the parcel times out before it can reach C.
    parcel.add_component(
        MailInTransitComponent(
            sender_id=str(sender.id),
            addressee_id=str(addressee.id),
            origin_room_id=str(a.id),
            destination_room_id=str(c.id),
            current_room_id=str(a.id),
            ttl_ticks=1,
        )
    )

    consequence = PostConsequence()
    events = []
    for epoch in range(1, 12):
        events.extend(consequence.process(actor.world, epoch))

    assert not parcel.has_component(MailInTransitComponent)
    assert [m.id for m in mail_in_mailbox(actor.world, box_a)] == [parcel.id]
    assert any(isinstance(e, MailReturnedEvent) for e in events)
