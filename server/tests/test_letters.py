from __future__ import annotations

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    HoldableComponent,
    IdentityComponent,
    PortableComponent,
    RoomComponent,
    WorldActor,
    spawn_entity,
)
from bunnyland.core.commands import CommandCost, Lane, build_submitted_command
from bunnyland.core.ecs import parse_entity_id
from bunnyland.core.handlers import HandlerContext

from bunnyland_postsim import (
    LetterComponent,
    MailInTransitComponent,
    ParcelComponent,
    spawn_mailbox,
)
from bunnyland_postsim.letters import SendParcelHandler, WriteLetterHandler
from bunnyland_postsim.mailboxes import mail_in_mailbox


def _room(world, title):
    return spawn_entity(world, [RoomComponent(title=title)])


def _character(world, room, name):
    character = spawn_entity(
        world, [IdentityComponent(name=name, kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), character.id)
    return character


def _hold(holder, item):
    holder.add_relationship(Contains(mode=ContainmentMode.INVENTORY), item.id)


def _cmd(character_id, command_type, payload):
    return build_submitted_command(
        character_id=str(character_id),
        controller_id="ctrl",
        controller_generation=0,
        command_type=command_type,
        cost=CommandCost(action=1),
        lane=Lane.WORLD,
        payload=payload,
    )


def _ctx(actor):
    return HandlerContext(world=actor.world, epoch=0)


def _scenario():
    actor = WorldActor()
    origin = _room(actor.world, "Post Office")
    dest = _room(actor.world, "Cottage")
    sender = _character(actor.world, origin, "Vin")
    addressee = _character(actor.world, dest, "Kell")
    mailbox = spawn_mailbox(actor.world, room_id=origin.id)
    return actor, origin, dest, sender, addressee, mailbox


# -- write-letter -----------------------------------------------------------------------


def test_write_letter_creates_addressed_letter_in_inventory():
    actor, _origin, _dest, sender, addressee, _box = _scenario()

    result = WriteLetterHandler().execute(
        _ctx(actor),
        _cmd(sender.id, "write-letter", {"text": "hello", "addressee_id": str(addressee.id)}),
    )

    assert result.ok
    letters = list(actor.world.query().with_all([LetterComponent]).execute_entities())
    assert len(letters) == 1
    letter = letters[0].get_component(LetterComponent)
    assert letter.text == "hello"
    assert letter.sender_id == str(sender.id)
    assert letter.addressee_id == str(addressee.id)


def test_write_letter_rejects_empty_text():
    actor, _origin, _dest, sender, addressee, _box = _scenario()
    result = WriteLetterHandler().execute(
        _ctx(actor),
        _cmd(sender.id, "write-letter", {"text": "  ", "addressee_id": str(addressee.id)}),
    )
    assert not result.ok
    assert result.reason == "a letter needs some text"


def test_write_letter_rejects_missing_addressee():
    actor, _origin, _dest, sender, _addressee, _box = _scenario()
    result = WriteLetterHandler().execute(
        _ctx(actor),
        _cmd(sender.id, "write-letter", {"text": "hi", "addressee_id": "entity_9999"}),
    )
    assert not result.ok
    assert result.reason == "addressee does not exist"


def test_write_letter_rejects_invalid_character():
    actor, _origin, _dest, _sender, addressee, _box = _scenario()
    result = WriteLetterHandler().execute(
        _ctx(actor),
        _cmd("???", "write-letter", {"text": "hi", "addressee_id": str(addressee.id)}),
    )
    assert not result.ok
    assert result.reason == "invalid character id"


# -- send-parcel ------------------------------------------------------------------------


def _write(actor, sender, addressee, text="hello"):
    result = WriteLetterHandler().execute(
        _ctx(actor),
        _cmd(sender.id, "write-letter", {"text": text, "addressee_id": str(addressee.id)}),
    )
    letter_id = result.events[0].mail_id
    return actor.world.get_entity(parse_entity_id(letter_id))


def test_send_parcel_posts_letter_into_mailbox():
    actor, _origin, dest, sender, addressee, mailbox = _scenario()
    letter = _write(actor, sender, addressee)

    result = SendParcelHandler().execute(
        _ctx(actor), _cmd(sender.id, "send-parcel", {"item_id": str(letter.id)})
    )

    assert result.ok
    assert letter.has_component(MailInTransitComponent)
    transit = letter.get_component(MailInTransitComponent)
    assert transit.destination_room_id == str(dest.id)
    # The letter now sits inside the mailbox, not the sender's hands.
    assert [m.id for m in mail_in_mailbox(actor.world, mailbox)] == [letter.id]


def test_send_parcel_wraps_a_gift_as_a_care_package():
    actor, _origin, _dest, sender, addressee, _box = _scenario()
    letter = _write(actor, sender, addressee)
    gift = spawn_entity(
        actor.world,
        [IdentityComponent(name="cookies", kind="item"), PortableComponent(), HoldableComponent()],
    )
    _hold(sender, gift)

    result = SendParcelHandler().execute(
        _ctx(actor),
        _cmd(
            sender.id,
            "send-parcel",
            {"item_id": str(letter.id), "gift_id": str(gift.id), "care_package": True},
        ),
    )

    assert result.ok
    assert letter.has_component(ParcelComponent)
    parcel = letter.get_component(ParcelComponent)
    assert parcel.care_package is True
    assert parcel.wrapped_item_id == str(gift.id)


def test_send_parcel_rejects_letter_not_held():
    actor, origin, _dest, sender, addressee, _box = _scenario()
    letter = _write(actor, sender, addressee)
    # Drop the letter on the floor of the room instead of holding it.
    sender.remove_relationship(Contains, letter.id)
    origin.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), letter.id)

    result = SendParcelHandler().execute(
        _ctx(actor), _cmd(sender.id, "send-parcel", {"item_id": str(letter.id)})
    )
    assert not result.ok
    assert result.reason == "you are not holding that letter"


def test_send_parcel_rejects_non_letter_item():
    actor, _origin, _dest, sender, _addressee, _box = _scenario()
    thing = spawn_entity(
        actor.world,
        [IdentityComponent(name="rock", kind="item"), PortableComponent(), HoldableComponent()],
    )
    _hold(sender, thing)

    result = SendParcelHandler().execute(
        _ctx(actor), _cmd(sender.id, "send-parcel", {"item_id": str(thing.id)})
    )
    assert not result.ok
    assert result.reason == "that is not a letter"


def test_send_parcel_rejects_when_no_mailbox_in_room():
    actor = WorldActor()
    origin = _room(actor.world, "Field")  # no mailbox here
    dest = _room(actor.world, "Cottage")
    sender = _character(actor.world, origin, "Vin")
    addressee = _character(actor.world, dest, "Kell")
    letter = _write(actor, sender, addressee)

    result = SendParcelHandler().execute(
        _ctx(actor), _cmd(sender.id, "send-parcel", {"item_id": str(letter.id)})
    )
    assert not result.ok
    assert result.reason == "there is no mailbox here"


def test_send_parcel_rejects_when_addressee_has_no_room():
    actor, _origin, dest, sender, addressee, _box = _scenario()
    letter = _write(actor, sender, addressee)
    # Remove the addressee from the world entirely.
    actor.world.remove(addressee.id)

    result = SendParcelHandler().execute(
        _ctx(actor), _cmd(sender.id, "send-parcel", {"item_id": str(letter.id)})
    )
    assert not result.ok
    assert result.reason == "the addressee is nowhere to be found"
