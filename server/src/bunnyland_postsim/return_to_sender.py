"""Return-to-sender: undeliverable mail bounces back to whoever posted it.

Mail becomes undeliverable two ways:

- **Timeout** — it has spent more than its ``ttl_ticks`` in transit (a courier never managed
  to reach the destination in time).
- **No route** — the destination room is not connected to where the mail currently sits by any
  chain of ``ExitTo`` edges, so no courier could ever walk it there.

Either way the mail starts *returning*: its effective target flips from the addressee's room
to the sender's origin room, and a courier carries it home. This module owns the small,
pure decisions the courier consequence consults; the physical carrying stays in
``couriers.py``.
"""

from __future__ import annotations

from dataclasses import replace

from bunnyland.core.ecs import parse_entity_id, replace_component
from relics import Entity, World

from .components import MailInTransitComponent
from .routing import next_hop


def is_timed_out(transit: MailInTransitComponent) -> bool:
    """Return whether the mail has outlived its transit budget."""
    return transit.age_ticks >= transit.ttl_ticks


def is_unroutable(world: World, transit: MailInTransitComponent, current_room_id) -> bool:
    """Return whether the destination is unreachable from ``current_room_id`` by any route."""
    destination = parse_entity_id(transit.destination_room_id)
    if destination is None:
        return True
    if current_room_id == destination:
        return False
    return next_hop(world, current_room_id, destination) is None


def should_return(world: World, transit: MailInTransitComponent, current_room_id) -> bool:
    """Return whether mail that is *not yet* returning should begin its bounce home."""
    if transit.returning:
        return False
    return is_timed_out(transit) or is_unroutable(world, transit, current_room_id)


def begin_return(mail: Entity, transit: MailInTransitComponent) -> MailInTransitComponent:
    """Flip a piece of mail into its returning state and persist it."""
    updated = replace(transit, returning=True)
    replace_component(mail, updated)
    return updated


__all__ = [
    "begin_return",
    "is_timed_out",
    "is_unroutable",
    "should_return",
]
