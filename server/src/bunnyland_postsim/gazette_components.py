"""Components and typed edges for the v2 world gossip sheet and bulletin boards.

The v2 headline reworks the postal pack into a town-crier for the whole fleet. Alongside the v1
private letters, a :class:`GazetteComponent` press reads the shared **world history** stream and
publishes editions of a :class:`GossipSheetComponent` gossip sheet; the news is read at
:class:`BulletinBoardComponent` boards across every settlement, where characters also pin their
own :class:`BulletinNoticeComponent` notices.

Everything is a frozen pydantic-dataclass ``relics.Component`` (state swapped whole via
``replace_component``) exactly like v1. Relationships are modelled as their own typed
``relics.Edge`` subclasses -- never lists on a component -- so each relationship is its own
index: :class:`Reports` (edition -> the history record it reported) and :class:`PostedBy`
(notice -> the character who posted it).
"""

from __future__ import annotations

from pydantic.dataclasses import dataclass
from relics import Component, Edge

#: How many ticks a gazette waits between editions once fresh news is available. The default of
#: one tick means the press publishes as soon as the world produces something worth reporting.
DEFAULT_PUBLISH_INTERVAL_TICKS = 1

#: How many headlines a single edition carries at most, so the sheet stays a digest.
MAX_EDITION_HEADLINES = 6


@dataclass(frozen=True)
class BulletinBoardComponent(Component):
    """Marks a public board in a room where the gossip sheet is read and notices are pinned.

    A board is spawned as a plain container (not a mailbox, so ordinary couriers ignore it):
    characters pin :class:`BulletinNoticeComponent` notices onto it, and the latest published
    edition of the world gossip sheet can be read at any board.
    """

    label: str = "bulletin board"


@dataclass(frozen=True)
class GazetteComponent(Component):
    """The town-crier press: composes editions from world history and breaking events.

    ``last_published_epoch`` starts at ``-1`` so the very first tick with news publishes.
    ``edition_seq`` is the running edition number; ``interval_ticks`` paces publication.
    """

    name: str = "gazette"
    edition_seq: int = 0
    last_published_epoch: int = -1
    interval_ticks: int = DEFAULT_PUBLISH_INTERVAL_TICKS
    home_room_id: str = ""


@dataclass(frozen=True)
class NewsdeskComponent(Component):
    """Breaking-news buffer captured from the domain-event bus, awaiting the next edition.

    The reactor stamps notable events here as they happen; the consequence folds them into the
    next edition alongside durable history records and then clears the buffer.
    """

    headlines: tuple[str, ...] = ()
    source_event_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class GossipSheetComponent(Component):
    """A published edition of the world gossip sheet, readable at any bulletin board."""

    edition: int = 0
    headlines: tuple[str, ...] = ()
    body: str = ""
    claim_ids: tuple[str, ...] = ()
    published_at_epoch: int = 0
    scandal: bool = False


@dataclass(frozen=True)
class BulletinNoticeComponent(Component):
    """A character-posted notice pinned to a bulletin board."""

    text: str = ""
    author_id: str = ""
    claim_id: str = ""
    posted_at_epoch: int = 0


@dataclass(frozen=True)
class Reports(Edge):
    """gossip-sheet edition -> the world-history record it reported (provenance)."""

    headline: str = ""


@dataclass(frozen=True)
class PostedBy(Edge):
    """bulletin notice -> the character who posted it."""

    role: str = "author"


__all__ = [
    "DEFAULT_PUBLISH_INTERVAL_TICKS",
    "MAX_EDITION_HEADLINES",
    "BulletinBoardComponent",
    "BulletinNoticeComponent",
    "GazetteComponent",
    "GossipSheetComponent",
    "NewsdeskComponent",
    "PostedBy",
    "Reports",
]
