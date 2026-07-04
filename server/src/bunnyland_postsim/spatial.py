"""Spatial helpers: who holds an item, which room an entity is in, and moving between them.

The core ``container_of`` only returns an entity's *direct* ``Contains`` parent. Mail can sit
loose in a room, nested inside a mailbox (a container in a room), or carried in a courier's or
character's inventory, so these helpers resolve the two questions the postal logic actually
asks:

- ``holder_of(item)`` — which creature is carrying this item (``None`` if it is loose or in a
  container that is not a creature)?
- ``room_of(entity)`` — which room is this entity ultimately in, walking up through any
  holder or mailbox?

``move_entity`` reparents an entity from wherever it is into a new container, the single
mutation couriers use to walk mail room to room.
"""

from __future__ import annotations

from bunnyland.core import ContainmentMode, Contains, RoomComponent, container_of
from relics import Entity, EntityId, World

#: Guard against pathological containment cycles while walking up to a room.
_MAX_CONTAINMENT_DEPTH = 8


def holder_of(world: World, item_id) -> Entity | None:
    """Return the creature holding ``item_id``, or ``None`` if it is loose or in a room.

    "Holding" means the item's direct container is neither a room nor absent — i.e. a
    character or courier is carrying it. A mailbox is a container, not a creature, so mail
    sitting in a mailbox is *not* held.
    """
    if not world.has_entity(item_id):
        return None
    parent_id = container_of(world.get_entity(item_id))
    if parent_id is None or not world.has_entity(parent_id):
        return None
    parent = world.get_entity(parent_id)
    if parent.has_component(RoomComponent):
        return None
    return parent


def room_of(world: World, entity_id) -> Entity | None:
    """Return the room ``entity_id`` is ultimately in, resolving through any container.

    Walks ``Contains`` parents upward until an entity with :class:`RoomComponent` is found, so
    it works for something resting on a room floor, tucked in a mailbox, or carried by a
    courier.
    """
    if not world.has_entity(entity_id):
        return None
    current = world.get_entity(entity_id)
    for _ in range(_MAX_CONTAINMENT_DEPTH):
        parent_id = container_of(current)
        if parent_id is None or not world.has_entity(parent_id):
            return None
        parent = world.get_entity(parent_id)
        if parent.has_component(RoomComponent):
            return parent
        current = parent
    return None


def move_entity(
    world: World,
    entity_id: EntityId,
    container_id: EntityId,
    *,
    mode: ContainmentMode = ContainmentMode.CONTAINER,
) -> None:
    """Reparent ``entity_id`` out of its current container and into ``container_id``."""
    current_container_id = container_of(world.get_entity(entity_id))
    if current_container_id is not None and world.has_entity(current_container_id):
        world.get_entity(current_container_id).remove_relationship(Contains, entity_id)
    world.get_entity(container_id).add_relationship(Contains(mode=mode), entity_id)


__all__ = ["holder_of", "move_entity", "room_of"]
