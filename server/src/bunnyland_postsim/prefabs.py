"""Spawn factories for the postal furniture: mailboxes, couriers, letters, and parcels.

The loader does not consume ``ContentContribution.prefabs``, so these ``spawn_entity`` helpers
are how tests, admin tooling, and the worldgen hook create postal entities. Pass ``room_id`` to
drop the entity into a room, or leave it out to spawn it uncontained.
"""

from __future__ import annotations

from bunnyland.core import (
    CharacterComponent,
    ContainerComponent,
    ContainmentMode,
    Contains,
    HoldableComponent,
    IdentityComponent,
    PortableComponent,
    spawn_entity,
)
from relics import Entity, World

from .components import CourierComponent, LetterComponent, MailboxComponent, ParcelComponent
from .gazette_components import BulletinBoardComponent, GazetteComponent, NewsdeskComponent


def _link_into_room(world: World, entity: Entity, room_id) -> None:
    if room_id is None or not world.has_entity(room_id):
        return
    world.get_entity(room_id).add_relationship(
        Contains(mode=ContainmentMode.ROOM_CONTENT), entity.id
    )


def spawn_mailbox(world: World, *, room_id=None, label: str = "mailbox") -> Entity:
    """Spawn a mailbox container, optionally placed in ``room_id``."""
    mailbox = spawn_entity(
        world,
        [
            IdentityComponent(name=label, kind="mailbox", tags=("postsim",)),
            ContainerComponent(),
            MailboxComponent(label=label),
        ],
    )
    _link_into_room(world, mailbox, room_id)
    return mailbox


def spawn_courier(world: World, *, room_id=None, name: str = "courier") -> Entity:
    """Spawn a courier NPC, optionally placed in ``room_id`` (also used as its home)."""
    courier = spawn_entity(
        world,
        [
            IdentityComponent(name=name, kind="character", tags=("postsim",)),
            CharacterComponent(),
            CourierComponent(home_room_id=str(room_id) if room_id is not None else ""),
        ],
    )
    _link_into_room(world, courier, room_id)
    return courier


def spawn_letter(
    world: World,
    *,
    text: str,
    sender_id: str,
    addressee_id: str,
    room_id=None,
) -> Entity:
    """Spawn a written letter item, optionally placed in ``room_id``."""
    letter = spawn_entity(
        world,
        [
            IdentityComponent(name="letter", kind="mail", tags=("postsim",)),
            PortableComponent(),
            HoldableComponent(slot="hand"),
            LetterComponent(text=text, sender_id=sender_id, addressee_id=addressee_id),
        ],
    )
    _link_into_room(world, letter, room_id)
    return letter


def spawn_parcel(
    world: World,
    *,
    text: str,
    sender_id: str,
    addressee_id: str,
    wrapped_item_id: str = "",
    care_package: bool = False,
    room_id=None,
) -> Entity:
    """Spawn a parcel (a letter carrying a :class:`ParcelComponent`), optionally in ``room_id``."""
    parcel = spawn_entity(
        world,
        [
            IdentityComponent(name="parcel", kind="mail", tags=("postsim",)),
            PortableComponent(),
            HoldableComponent(slot="hand"),
            LetterComponent(text=text, sender_id=sender_id, addressee_id=addressee_id),
            ParcelComponent(wrapped_item_id=wrapped_item_id, care_package=care_package),
        ],
    )
    _link_into_room(world, parcel, room_id)
    return parcel


def spawn_bulletin_board(
    world: World, *, room_id=None, label: str = "bulletin board"
) -> Entity:
    """Spawn a public bulletin-board container, optionally placed in ``room_id``."""
    board = spawn_entity(
        world,
        [
            IdentityComponent(name=label, kind="bulletin-board", tags=("postsim",)),
            ContainerComponent(),
            BulletinBoardComponent(label=label),
        ],
    )
    _link_into_room(world, board, room_id)
    return board


def spawn_gazette(world: World, *, name: str = "gossip sheet", home_room_id: str = "") -> Entity:
    """Spawn a gossip-sheet press (with its newsdesk buffer), optionally homed to a room."""
    return spawn_entity(
        world,
        [
            IdentityComponent(name=name, kind="gazette", tags=("postsim",)),
            GazetteComponent(name=name, home_room_id=home_room_id),
            NewsdeskComponent(),
        ],
    )


__all__ = [
    "spawn_bulletin_board",
    "spawn_courier",
    "spawn_gazette",
    "spawn_letter",
    "spawn_mailbox",
    "spawn_parcel",
]
