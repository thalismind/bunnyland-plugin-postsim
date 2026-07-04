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
from bunnyland.core.commands import CommandCost, Lane, build_submitted_command
from bunnyland.core.handlers import HandlerContext

from bunnyland_postsim import CheckMailHandler, spawn_letter, spawn_mailbox
from bunnyland_postsim.mailboxes import mailbox_in_room
from bunnyland_postsim.spatial import holder_of


def _room(world, title):
    return spawn_entity(world, [RoomComponent(title=title)])


def _character(world, room, name):
    character = spawn_entity(
        world, [IdentityComponent(name=name, kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), character.id)
    return character


def _cmd(character_id, payload):
    return build_submitted_command(
        character_id=str(character_id),
        controller_id="ctrl",
        controller_generation=0,
        command_type="check-mail",
        cost=CommandCost(action=1),
        lane=Lane.WORLD,
        payload=payload,
    )


def _ctx(actor):
    return HandlerContext(world=actor.world, epoch=0)


def _deliver_into(world, mailbox, addressee_id, sender_id="entity_1"):
    """Drop a delivered (not in transit) letter addressed to ``addressee_id`` into a mailbox."""
    letter = spawn_letter(
        world, text="hi", sender_id=sender_id, addressee_id=str(addressee_id)
    )
    mailbox.add_relationship(Contains(mode=ContainmentMode.CONTAINER), letter.id)
    return letter


def test_check_mail_collects_delivered_mail_for_you():
    actor = WorldActor()
    room = _room(actor.world, "Hall")
    reader = _character(actor.world, room, "Kell")
    mailbox = spawn_mailbox(actor.world, room_id=room.id)
    letter = _deliver_into(actor.world, mailbox, reader.id)

    result = CheckMailHandler().execute(_ctx(actor), _cmd(reader.id, {}))

    assert result.ok
    assert result.events[0].mail_ids == (str(letter.id),)
    # The letter is now in the reader's inventory.
    assert holder_of(actor.world, letter.id).id == reader.id


def test_check_mail_ignores_mail_for_others():
    actor = WorldActor()
    room = _room(actor.world, "Hall")
    reader = _character(actor.world, room, "Kell")
    other = _character(actor.world, room, "Vin")
    mailbox = spawn_mailbox(actor.world, room_id=room.id)
    _deliver_into(actor.world, mailbox, other.id)

    result = CheckMailHandler().execute(_ctx(actor), _cmd(reader.id, {}))
    assert not result.ok
    assert result.reason == "there is no mail for you here"


def test_check_mail_rejects_when_not_in_a_room():
    actor = WorldActor()
    loner = spawn_entity(
        actor.world, [IdentityComponent(name="Kell", kind="character"), CharacterComponent()]
    )
    result = CheckMailHandler().execute(_ctx(actor), _cmd(loner.id, {}))
    assert not result.ok
    assert result.reason == "you are not in a room"


def test_check_mail_rejects_when_no_mailbox():
    actor = WorldActor()
    room = _room(actor.world, "Field")
    reader = _character(actor.world, room, "Kell")
    result = CheckMailHandler().execute(_ctx(actor), _cmd(reader.id, {}))
    assert not result.ok
    assert result.reason == "there is no mailbox here"


def test_check_mail_rejects_invalid_character():
    actor = WorldActor()
    result = CheckMailHandler().execute(_ctx(actor), _cmd("???", {}))
    assert not result.ok
    assert result.reason == "invalid character id"


def test_check_mail_rejects_non_mailbox_target():
    actor = WorldActor()
    room = _room(actor.world, "Hall")
    reader = _character(actor.world, room, "Kell")
    not_a_box = spawn_entity(
        actor.world, [IdentityComponent(name="crate", kind="item")]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), not_a_box.id)

    result = CheckMailHandler().execute(
        _ctx(actor), _cmd(reader.id, {"mailbox_id": str(not_a_box.id)})
    )
    assert not result.ok
    assert result.reason == "that is not a mailbox"


def test_mailbox_in_room_returns_lowest_id_box():
    actor = WorldActor()
    room = _room(actor.world, "Hall")
    first = spawn_mailbox(actor.world, room_id=room.id)
    spawn_mailbox(actor.world, room_id=room.id)
    assert mailbox_in_room(actor.world, room).id == first.id
