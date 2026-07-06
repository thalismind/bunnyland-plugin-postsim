"""World-generation enrichment: give settlements a mailbox and a courier.

Generated rooms expose semantic ``tags``/``wants``/``needs`` and an intent ``description``.
This hook scans that text and, when a room reads like a *settlement* (a town, village, hub,
post, camp, and so on), drops a mailbox into it so mail has somewhere to be posted and
delivered. The first settlement it sees also gets a courier stationed there, so a generated
world has at least one carrier walking the network — without the core generator knowing this
plugin exists.
"""

from __future__ import annotations

from bunnyland.core.ecs import parse_entity_id
from bunnyland.core.events import RoomGeneratedEvent
from bunnyland.core.world_actor import WorldActor
from relics import World

from .bulletins import boards_in_room
from .components import CourierComponent, MailboxComponent
from .gazette import ensure_gazette
from .mailboxes import mailboxes_in_room
from .prefabs import spawn_bulletin_board, spawn_courier, spawn_mailbox

#: Words that mark a generated room as a settlement worth wiring into the postal network.
SETTLEMENT_TERMS = (
    "town",
    "village",
    "city",
    "hamlet",
    "settlement",
    "outpost",
    "post",
    "hub",
    "market",
    "square",
    "camp",
    "inn",
    "tavern",
    "waystation",
    "station",
    "harbor",
    "harbour",
    "port",
    "plaza",
)


def _text(event: RoomGeneratedEvent) -> str:
    generation = event.generation
    return " ".join(
        (
            event.room_key,
            event.biome,
            generation.description,
            *generation.tags,
            *generation.wants,
            *generation.needs,
        )
    ).casefold()


def _is_settlement(event: RoomGeneratedEvent) -> bool:
    text = _text(event)
    return any(term in text for term in SETTLEMENT_TERMS)


def _has_courier(world: World) -> bool:
    return bool(list(world.query().with_all([CourierComponent]).execute_entities()))


class PostWorldgenHook:
    """Wire every generated settlement into the postal network and the gossip sheet.

    Each settlement gets a mailbox (for v1 mail) and a bulletin board (for v2 news); the first
    settlement also stations a courier, and the world always ends up with exactly one gossip-sheet
    press. Every step is idempotent so re-running the hook never double-seeds a room.
    """

    def subscribe(self, actor: WorldActor) -> None:
        self._actor = actor
        actor.bus.subscribe(RoomGeneratedEvent, self._on_room)

    def _on_room(self, event: RoomGeneratedEvent) -> None:
        room_id = parse_entity_id(event.entity_id)
        if room_id is None or not self._actor.world.has_entity(room_id):
            return
        if not _is_settlement(event):
            return
        world = self._actor.world
        room = world.get_entity(room_id)
        if not any(box.has_component(MailboxComponent) for box in mailboxes_in_room(world, room)):
            spawn_mailbox(world, room_id=room_id)
        if not boards_in_room(world, room):
            spawn_bulletin_board(world, room_id=room_id)
        if not _has_courier(world):
            spawn_courier(world, room_id=room_id)
        ensure_gazette(world)


__all__ = ["PostWorldgenHook", "SETTLEMENT_TERMS"]
