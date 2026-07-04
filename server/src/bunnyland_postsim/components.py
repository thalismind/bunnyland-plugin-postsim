"""Components for the postal pack: letters, parcels, mailboxes, and couriers.

Everything is a frozen pydantic-dataclass ``relics.Component`` so state is swapped whole with
``replace_component(entity, replace(component, ...))`` rather than mutated in place.

The pieces:

- :class:`LetterComponent` — the written message on a mail *item* entity (text + who it is
  from and to). ``write-letter`` produces one; it lives in a character's inventory until it
  is posted.
- :class:`ParcelComponent` — wraps a gift/consumable item that rides along with a letter.
  ``care_package`` flags the warm-fuzzy variant that raises the recipient's affect and the
  sender <-> recipient social bond on delivery.
- :class:`MailInTransitComponent` — the routing/lifecycle state added when mail is posted and
  removed on delivery. A courier reads ``destination_room_id`` (or ``origin_room_id`` while
  ``returning``) to know where to walk, and ``age_ticks``/``ttl_ticks`` drive return-to-sender.
- :class:`MailboxComponent` — marks a container in a room where mail is dropped off and picked
  up.
- :class:`CourierComponent` — marks an NPC that carries posted mail across rooms over ticks.
"""

from __future__ import annotations

from pydantic.dataclasses import dataclass
from relics import Component

#: Default number of ticks a piece of mail may spend in transit before it bounces back to its
#: sender (return-to-sender timeout). Chosen to comfortably exceed a small settlement's
#: diameter so ordinary deliveries never time out.
DEFAULT_TTL_TICKS = 32


@dataclass(frozen=True)
class LetterComponent(Component):
    """A written message on a mail item entity: its text and its addressing."""

    text: str = ""
    sender_id: str = ""
    addressee_id: str = ""


@dataclass(frozen=True)
class ParcelComponent(Component):
    """Marks a mail item as a parcel wrapping a gift item that travels with the letter."""

    wrapped_item_id: str = ""
    care_package: bool = False


@dataclass(frozen=True)
class MailInTransitComponent(Component):
    """Routing + lifecycle state for a posted piece of mail, until it is delivered.

    ``origin_room_id`` is where it was posted, ``destination_room_id`` is the addressee's
    room at posting time. ``current_room_id`` is a cached mirror of where the mail physically
    is (updated as a courier carries it) so consequences avoid re-walking containment every
    tick. ``returning`` flips once the mail is bouncing back to its sender.
    """

    sender_id: str
    addressee_id: str
    origin_room_id: str
    destination_room_id: str
    current_room_id: str
    posted_at_epoch: int = 0
    age_ticks: int = 0
    ttl_ticks: int = DEFAULT_TTL_TICKS
    returning: bool = False


@dataclass(frozen=True)
class MailboxComponent(Component):
    """Marks a container entity in a room as a mailbox: drop mail in, pick mail up."""

    label: str = "mailbox"


@dataclass(frozen=True)
class CourierComponent(Component):
    """Marks an NPC that collects posted mail and carries it toward its destination.

    ``home_room_id`` is where the courier idles when there is nothing to carry; empty means
    it simply waits wherever it last stopped.
    """

    home_room_id: str = ""


__all__ = [
    "DEFAULT_TTL_TICKS",
    "CourierComponent",
    "LetterComponent",
    "MailInTransitComponent",
    "MailboxComponent",
    "ParcelComponent",
]
