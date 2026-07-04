from __future__ import annotations

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    IdentityComponent,
    RoomComponent,
    WorldActor,
    spawn_entity,
)

from bunnyland_postsim import postsim_fragments, spawn_letter, spawn_mailbox, spawn_parcel
from bunnyland_postsim.components import MailInTransitComponent


def _room(world, title="Hall"):
    return spawn_entity(world, [RoomComponent(title=title)])


def _character(world, room, name):
    character = spawn_entity(
        world, [IdentityComponent(name=name, kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), character.id)
    return character


def _drop(mailbox, mail):
    mailbox.add_relationship(Contains(mode=ContainmentMode.CONTAINER), mail.id)


def test_letter_for_you_is_announced():
    actor = WorldActor()
    room = _room(actor.world)
    reader = _character(actor.world, room, "Kell")
    mailbox = spawn_mailbox(actor.world, room_id=room.id)
    _drop(mailbox, spawn_letter(actor.world, text="hi", sender_id="s", addressee_id=str(reader.id)))

    lines = postsim_fragments(actor.world, reader)

    assert "There is mail in the mailbox here." in lines
    assert "A letter for you has arrived in the mailbox here." in lines


def test_parcel_for_you_uses_the_parcel_noun():
    actor = WorldActor()
    room = _room(actor.world)
    reader = _character(actor.world, room, "Kell")
    mailbox = spawn_mailbox(actor.world, room_id=room.id)
    _drop(
        mailbox,
        spawn_parcel(actor.world, text="hi", sender_id="s", addressee_id=str(reader.id)),
    )

    lines = postsim_fragments(actor.world, reader)

    assert "A parcel for you has arrived in the mailbox here." in lines


def test_mail_for_someone_else_is_generic_only():
    actor = WorldActor()
    room = _room(actor.world)
    reader = _character(actor.world, room, "Kell")
    mailbox = spawn_mailbox(actor.world, room_id=room.id)
    _drop(mailbox, spawn_letter(actor.world, text="hi", sender_id="s", addressee_id="entity_777"))

    lines = postsim_fragments(actor.world, reader)

    assert lines == ["There is mail in the mailbox here."]


def test_in_transit_mail_is_not_announced():
    actor = WorldActor()
    room = _room(actor.world)
    reader = _character(actor.world, room, "Kell")
    mailbox = spawn_mailbox(actor.world, room_id=room.id)
    letter = spawn_letter(actor.world, text="hi", sender_id="s", addressee_id=str(reader.id))
    _drop(mailbox, letter)
    letter.add_component(
        MailInTransitComponent(
            sender_id="s",
            addressee_id=str(reader.id),
            origin_room_id=str(room.id),
            destination_room_id=str(room.id),
            current_room_id=str(room.id),
        )
    )

    assert postsim_fragments(actor.world, reader) == []


def test_no_mailbox_means_no_lines():
    actor = WorldActor()
    room = _room(actor.world)
    reader = _character(actor.world, room, "Kell")
    assert postsim_fragments(actor.world, reader) == []
