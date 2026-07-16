"""The gossip-sheet press: reads the shared world history stream and publishes editions.

The v2 headline mechanic. A :class:`~bunnyland_postsim.gazette_components.GazetteComponent`
press is the town-crier for the whole world. Every tick :class:`GazetteConsequence`:

1. Reads the durable, cross-pack **world history** stream (``world_history_records`` -- the same
   projection every pack's notable events flow into) for records newer than the last edition, and
   folds in any **breaking headlines** buffered on the press's
   :class:`~bunnyland_postsim.gazette_components.NewsdeskComponent` (populated by the optional
   :class:`NewsdeskReactor` synergy).
2. When there is fresh news and the publishing interval has elapsed, composes a
   :class:`~bunnyland_postsim.gazette_components.GossipSheetComponent` edition, links it to the
   history records it reported via :class:`~bunnyland_postsim.gazette_components.Reports` edges,
   and drops it in a room where any bulletin board can read it.
3. When the news is a *scandal* (a death, a loss, a curse), registers a **core storyteller
   incident** so the world's rumour pressure is paced alongside every other pack.

The press does not re-derive its own event log: it consumes core history, so a legendary catch,
a confirmed cryptid, or a festival from any other pack becomes shared awareness with no
pack-to-pack dependency. The optional wilderness-news synergy is a bonus that degrades to a
logged warning when ``bunnyland.wildsim`` is not loaded.
"""

from __future__ import annotations

import logging
from dataclasses import replace

from bunnyland.core import (
    ContainmentMode,
    Contains,
    IdentityComponent,
    RoomComponent,
    spawn_entity,
)
from bunnyland.core.ecs import parse_entity_id, replace_component
from bunnyland.core.events import DomainEvent, EventVisibility, event_base
from bunnyland.foundation.history.mechanics import (
    WorldHistoryRecordComponent,
    world_history_records,
)
from bunnyland.foundation.storyteller.mechanics import IncidentComponent
from relics import Entity, World

from .events import GazettePublishedEvent
from .gazette_components import (
    MAX_EDITION_HEADLINES,
    GazetteComponent,
    GossipSheetComponent,
    NewsdeskComponent,
    Reports,
)

logger = logging.getLogger(__name__)

#: History tags / event types that make an edition a *scandal* worth a storyteller incident.
SCANDAL_TAGS = frozenset({"death", "loss", "curse", "scandal"})
SCANDAL_EVENT_TYPES = frozenset({"CharacterDiedEvent"})

#: The core storyteller incident kind a scandalous edition registers.
GAZETTE_INCIDENT_KIND = "gossip_scandal"

#: Breaking headlines a partner event contributes, keyed by the event's class name.
PARTNER_HEADLINES: dict[str, str] = {
    "GameBaggedEvent": "A hunter has bagged fresh game out in the wilds.",
    "GameTrappedEvent": "A trapper's snare sprang shut on quarry beyond the walls.",
    "PredatorIncursionEvent": "Predators are prowling close to the settlements -- stay wary.",
}

#: How many breaking headlines the newsdesk buffer holds before it drops the oldest.
MAX_NEWSDESK_HEADLINES = 8


def _id_key(entity: Entity) -> tuple[str, int]:
    return (entity.id.prefab, entity.id.sequence)


def gazette_presses(world: World) -> list[Entity]:
    """Every gossip-sheet press in the world, in deterministic id order."""
    presses = list(world.query().with_all([GazetteComponent]).execute_entities())
    return sorted(presses, key=_id_key)


def ensure_gazette(world: World) -> Entity:
    """Return the world's single gossip-sheet press, spawning one if none exists yet.

    Idempotent: called from both install and worldgen, so a world only ever holds one press.
    """
    presses = gazette_presses(world)
    if presses:
        return presses[0]
    return spawn_entity(
        world,
        [
            IdentityComponent(name="gossip sheet", kind="gazette", tags=("postsim",)),
            GazetteComponent(),
            NewsdeskComponent(),
        ],
    )


def _rooms(world: World) -> list[Entity]:
    rooms = list(world.query().with_all([RoomComponent]).execute_entities())
    return sorted(rooms, key=_id_key)


def _publish_room(world: World, press: GazetteComponent) -> Entity | None:
    """The room a new edition is dropped in: the press's home room, else the lowest-id room."""
    if press.home_room_id:
        home_id = parse_entity_id(press.home_room_id)
        if home_id is not None and world.has_entity(home_id):
            home = world.get_entity(home_id)
            if home.has_component(RoomComponent):
                return home
    rooms = _rooms(world)
    return rooms[0] if rooms else None


def _is_scandal(record: WorldHistoryRecordComponent) -> bool:
    return bool(SCANDAL_TAGS.intersection(record.tags)) or record.event_type in SCANDAL_EVENT_TYPES


def append_breaking(world: World, headline: str, source_event_id: str) -> bool:
    """Buffer a breaking headline on every press's newsdesk. Returns whether anything changed.

    Deduplicated by ``source_event_id`` so a re-emitted event never double-prints, and capped so
    the buffer stays a digest.
    """
    text = " ".join(str(headline).split())
    if not text:
        return False
    changed = False
    for press_entity in gazette_presses(world):
        desk = press_entity.get_component(NewsdeskComponent)
        if source_event_id and source_event_id in desk.source_event_ids:
            continue
        headlines = (*desk.headlines, text)[-MAX_NEWSDESK_HEADLINES:]
        source_ids = (*desk.source_event_ids, source_event_id)[-MAX_NEWSDESK_HEADLINES:]
        replace_component(
            press_entity, replace(desk, headlines=headlines, source_event_ids=source_ids)
        )
        changed = True
    return changed


class GazetteConsequence:
    """Publish a gossip-sheet edition whenever the world produces fresh news."""

    def process(self, world: World, epoch: int) -> list[DomainEvent]:
        events: list[DomainEvent] = []
        for press_entity in gazette_presses(world):
            event = self._maybe_publish(world, epoch, press_entity)
            if event is not None:
                events.append(event)
        return events

    def _maybe_publish(self, world: World, epoch: int, press_entity: Entity):
        press = press_entity.get_component(GazetteComponent)
        if epoch < press.last_published_epoch + press.interval_ticks:
            return None

        desk = press_entity.get_component(NewsdeskComponent)
        fresh = [
            (entity, record)
            for entity, record in world_history_records(world)
            if record.created_at_epoch > press.last_published_epoch
        ]
        if not desk.headlines and not fresh:
            return None  # a quiet day: nothing worth an edition

        breaking = list(desk.headlines)
        room_budget = max(0, MAX_EDITION_HEADLINES - len(breaking))
        used_records = fresh[:room_budget]
        headlines = tuple((*breaking, *(record.summary for _entity, record in used_records)))[
            :MAX_EDITION_HEADLINES
        ]
        claim_ids = tuple(record.source_event_id for _entity, record in used_records)
        scandal = any(_is_scandal(record) for _entity, record in used_records)

        edition_number = press.edition_seq + 1
        room = _publish_room(world, press)
        edition = spawn_entity(
            world,
            [
                IdentityComponent(
                    name=f"gossip sheet #{edition_number}", kind="gossip-sheet", tags=("postsim",)
                ),
                GossipSheetComponent(
                    edition=edition_number,
                    headlines=headlines,
                    body="  ".join(headlines),
                    claim_ids=claim_ids,
                    published_at_epoch=epoch,
                    scandal=scandal,
                ),
            ],
        )
        if room is not None:
            room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), edition.id)
        for entity, record in used_records:
            edition.add_relationship(Reports(headline=record.summary), entity.id)

        replace_component(
            press_entity,
            replace(
                press,
                edition_seq=edition_number,
                last_published_epoch=epoch,
            ),
        )
        replace_component(press_entity, replace(desk, headlines=(), source_event_ids=()))

        if scandal:
            self._register_scandal(world, epoch, room)

        return GazettePublishedEvent(
            **event_base(
                epoch,
                default_visibility=EventVisibility.PUBLIC,
                actor_id=str(press_entity.id),
                room_id=str(room.id) if room is not None else "",
                target_ids=(str(edition.id),),
                gazette_id=str(press_entity.id),
                edition=edition_number,
                headline_count=len(headlines),
                scandal=scandal,
            )
        )

    def _register_scandal(self, world: World, epoch: int, room: Entity | None) -> None:
        # Idempotent: only one open scandal at a time so incidents never pile up.
        for entity in world.query().with_all([IncidentComponent]).execute_entities():
            incident = entity.get_component(IncidentComponent)
            if incident.kind == GAZETTE_INCIDENT_KIND and incident.resolved_at_epoch is None:
                return
        incident_entity = spawn_entity(
            world,
            [
                IdentityComponent(name="a spreading scandal", kind="incident", tags=("postsim",)),
                IncidentComponent(
                    kind=GAZETTE_INCIDENT_KIND,
                    budget_spent=1.0,
                    started_at_epoch=epoch,
                ),
            ],
        )
        if room is not None:
            room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), incident_entity.id)


def _wild_news_events() -> tuple[type, ...]:
    """Partner event classes to buffer as breaking news, or ``()`` when wildsim is absent.

    Optional synergy: if ``bunnyland.wildsim`` is loaded, its hunt/predator events flavour the
    gossip sheet. When it is not, the synergy is simply disabled and a warning is logged.
    """
    try:
        from bunnyland_wildsim.events import (
            GameBaggedEvent,
            GameTrappedEvent,
            PredatorIncursionEvent,
        )
    except ImportError:
        logger.warning(
            "postsim gazette: recommended pack 'bunnyland.wildsim' is not loaded; "
            "wilderness breaking-news synergy is disabled."
        )
        return ()
    return (GameBaggedEvent, GameTrappedEvent, PredatorIncursionEvent)


class NewsdeskReactor:
    """Buffer breaking headlines from optional partner events onto the press's newsdesk."""

    def __init__(self, world: World) -> None:
        self.world = world

    def subscribe(self, bus) -> None:
        for event_type in _wild_news_events():
            bus.subscribe(event_type, self._on_partner_event)

    def _on_partner_event(self, event: DomainEvent) -> None:
        headline = PARTNER_HEADLINES.get(
            type(event).__name__, "Word travels in from beyond the walls."
        )
        append_breaking(self.world, headline, event.event_id)


def install_gazette(actor) -> None:
    """Register the gossip-sheet press: its per-tick consequence and the newsdesk reactor."""
    ensure_gazette(actor.world)
    actor.register_consequence(GazetteConsequence())
    NewsdeskReactor(actor.world).subscribe(actor.bus)


__all__ = [
    "GAZETTE_INCIDENT_KIND",
    "MAX_NEWSDESK_HEADLINES",
    "PARTNER_HEADLINES",
    "SCANDAL_EVENT_TYPES",
    "SCANDAL_TAGS",
    "GazetteConsequence",
    "NewsdeskReactor",
    "append_breaking",
    "ensure_gazette",
    "gazette_presses",
    "install_gazette",
]
