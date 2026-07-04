from __future__ import annotations

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    ControlledBy,
    ControllerOutboxMessageComponent,
    ExitTo,
    IdentityComponent,
    RoomComponent,
    WorldActor,
    spawn_entity,
)

from bunnyland_postsim import (
    MailDeliveredEvent,
    MailInTransitComponent,
    MailReturnedEvent,
    PostConsequence,
    spawn_courier,
    spawn_mailbox,
    spawn_parcel,
)
from bunnyland_postsim.components import LetterComponent
from bunnyland_postsim.mailboxes import mail_in_mailbox
from bunnyland_postsim.spatial import holder_of, room_of


def _room(world, title):
    return spawn_entity(world, [RoomComponent(title=title)])


def _link(a, b):
    a.add_relationship(ExitTo(direction="out"), b.id)
    b.add_relationship(ExitTo(direction="back"), a.id)


def _character(world, room, name):
    character = spawn_entity(
        world, [IdentityComponent(name=name, kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), character.id)
    return character


def _post(world, mailbox, *, sender_id, addressee_id, origin, dest, ttl=32, care=False, epoch=0):
    parcel = spawn_parcel(
        world,
        text="hello",
        sender_id=str(sender_id),
        addressee_id=str(addressee_id),
        care_package=care,
    )
    mailbox.add_relationship(Contains(mode=ContainmentMode.CONTAINER), parcel.id)
    parcel.add_component(
        MailInTransitComponent(
            sender_id=str(sender_id),
            addressee_id=str(addressee_id),
            origin_room_id=str(origin.id),
            destination_room_id=str(dest.id),
            current_room_id=str(origin.id),
            posted_at_epoch=epoch,
            ttl_ticks=ttl,
        )
    )
    return parcel


def _run(consequence, world, ticks, *, start=1):
    events = []
    for epoch in range(start, start + ticks):
        events.extend(consequence.process(world, epoch))
    return events


def test_parcel_travels_room_to_room_and_is_delivered():
    actor = WorldActor()
    a = _room(actor.world, "Post Office")
    b = _room(actor.world, "Lane")
    c = _room(actor.world, "Cottage")
    _link(a, b)
    _link(b, c)
    box_a = spawn_mailbox(actor.world, room_id=a.id)
    box_c = spawn_mailbox(actor.world, room_id=c.id)
    sender = _character(actor.world, a, "Vin")
    addressee = _character(actor.world, c, "Kell")
    courier = spawn_courier(actor.world, room_id=a.id)

    parcel = _post(
        actor.world, box_a, sender_id=sender.id, addressee_id=addressee.id, origin=a, dest=c
    )
    consequence = PostConsequence()

    # Tick 1: courier collects the waiting parcel in room A (it is now in the courier's hands).
    consequence.process(actor.world, 1)
    assert room_of(actor.world, parcel.id).id == a.id
    assert holder_of(actor.world, parcel.id).id == courier.id

    # Tick 2: courier walks the parcel one hop toward C -> now in room B.
    consequence.process(actor.world, 2)
    assert room_of(actor.world, parcel.id).id == b.id

    # Remaining ticks: it reaches C and is delivered into C's mailbox.
    events = _run(consequence, actor.world, ticks=6, start=3)

    assert not parcel.has_component(MailInTransitComponent)
    assert [m.id for m in mail_in_mailbox(actor.world, box_c)] == [parcel.id]
    delivered = [e for e in events if isinstance(e, MailDeliveredEvent)]
    assert len(delivered) == 1
    assert delivered[0].addressee_id == str(addressee.id)
    assert delivered[0].room_id_delivered == str(c.id)


def test_undeliverable_parcel_returns_to_sender():
    actor = WorldActor()
    a = _room(actor.world, "Post Office")
    z = _room(actor.world, "Unreachable Isle")  # deliberately not linked to A
    box_a = spawn_mailbox(actor.world, room_id=a.id)
    sender = _character(actor.world, a, "Vin")
    addressee = _character(actor.world, z, "Kell")
    spawn_courier(actor.world, room_id=a.id)

    parcel = _post(
        actor.world, box_a, sender_id=sender.id, addressee_id=addressee.id, origin=a, dest=z
    )
    consequence = PostConsequence()

    events = _run(consequence, actor.world, ticks=5)

    assert not parcel.has_component(MailInTransitComponent)
    # It bounced back into the origin mailbox...
    assert [m.id for m in mail_in_mailbox(actor.world, box_a)] == [parcel.id]
    returned = [e for e in events if isinstance(e, MailReturnedEvent)]
    assert len(returned) == 1
    assert returned[0].sender_id == str(sender.id)
    # ...and is re-addressed to the sender so they can collect it.
    assert parcel.get_component(LetterComponent).addressee_id == str(sender.id)


def test_delivery_notifies_the_addressees_controller():
    actor = WorldActor()
    a = _room(actor.world, "Post Office")
    c = _room(actor.world, "Cottage")
    _link(a, c)
    box_a = spawn_mailbox(actor.world, room_id=a.id)
    spawn_mailbox(actor.world, room_id=c.id)
    sender = _character(actor.world, a, "Vin")
    addressee = _character(actor.world, c, "Kell")
    controller = spawn_entity(actor.world, [IdentityComponent(name="ctrl", kind="controller")])
    addressee.add_relationship(ControlledBy(generation=0), controller.id)
    spawn_courier(actor.world, room_id=a.id)

    _post(actor.world, box_a, sender_id=sender.id, addressee_id=addressee.id, origin=a, dest=c)
    consequence = PostConsequence()
    _run(consequence, actor.world, ticks=6)

    outbox = list(
        actor.world.query().with_all([ControllerOutboxMessageComponent]).execute_entities()
    )
    assert len(outbox) == 1
    message = outbox[0].get_component(ControllerOutboxMessageComponent)
    assert message.controller_id == str(controller.id)
    assert "arrived for you" in message.text


def test_courier_walks_to_collect_mail_posted_elsewhere():
    actor = WorldActor()
    a = _room(actor.world, "Depot")  # courier starts here, empty-handed
    b = _room(actor.world, "Lane")
    c = _room(actor.world, "Cottage")
    _link(a, b)
    _link(b, c)
    box_c = spawn_mailbox(actor.world, room_id=c.id)
    sender = _character(actor.world, c, "Vin")
    addressee = _character(actor.world, a, "Kell")
    courier = spawn_courier(actor.world, room_id=a.id)

    # Mail is waiting in C, but the courier is in A: it must walk over to collect it.
    parcel = _post(
        actor.world, box_c, sender_id=sender.id, addressee_id=addressee.id, origin=c, dest=a
    )
    consequence = PostConsequence()
    _run(consequence, actor.world, ticks=10)

    assert not parcel.has_component(MailInTransitComponent)
    assert room_of(actor.world, parcel.id).id == a.id
    assert room_of(actor.world, courier.id).id == a.id
