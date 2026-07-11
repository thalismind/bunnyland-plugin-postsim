"""Couriers: the per-tick consequence that carries mail across rooms and delivers it.

A :class:`~bunnyland_postsim.components.CourierComponent` NPC is the moving part of the postal
system. The :class:`PostConsequence` runs every tick and, for each courier (in deterministic
id order):

1. **Ages** every piece of in-transit mail so return-to-sender timeouts advance.
2. If the courier is **carrying** mail, walks it one room-hop toward its destination (or the
   sender's room while it is returning) via a deterministic BFS over ``ExitTo``. On arrival it
   drops the mail in the destination mailbox, strips the transit marker, warms the recipient
   for a care package, and notifies the addressee's controller.
3. If the courier is **empty-handed**, it picks up waiting mail in its room, or walks one hop
   toward the nearest room that has waiting mail, or drifts home.

Movement is the single ``Contains`` reparent from ``spatial.move_entity`` — the same primitive
characters use to walk — so a courier physically carries mail in its inventory the whole way.
Delivery emits a :class:`MailDeliveredEvent`/:class:`MailReturnedEvent` and drops a
``ControllerOutboxMessageComponent`` so an integration (Discord, etc.) can tell the recipient.
"""

from __future__ import annotations

from dataclasses import replace

from bunnyland.core import (
    ContainmentMode,
    ControlledBy,
    ControllerOutboxMessageComponent,
    IdentityComponent,
    container_of,
    contents,
    spawn_entity,
)
from bunnyland.core.ecs import parse_entity_id, replace_component
from bunnyland.core.events import DomainEvent, EventVisibility, event_base
from relics import Entity, World

from .care_packages import apply_care_package_delivery
from .components import (
    CourierComponent,
    LetterComponent,
    MailboxComponent,
    MailInTransitComponent,
    ParcelComponent,
)
from .events import MailDeliveredEvent, MailReturnedEvent
from .mailboxes import mailbox_in_room
from .return_to_sender import begin_return, should_return
from .routing import next_hop, next_hop_to_any
from .spatial import move_entity, room_of


def _id_key(entity: Entity) -> tuple[str, int]:
    return (entity.id.prefab, entity.id.sequence)


def _in_transit_mail(world: World) -> list[Entity]:
    mail = list(world.query().with_all([MailInTransitComponent]).execute_entities())
    return sorted(mail, key=_id_key)


class PostConsequence:
    """Advance in-transit mail one room-hop per tick and deliver it on arrival."""

    def process(self, world: World, epoch: int) -> list[DomainEvent]:
        self._age_mail(world)
        events: list[DomainEvent] = []
        for courier in sorted(
            world.query().with_all([CourierComponent]).execute_entities(), key=_id_key
        ):
            events.extend(self._act(world, epoch, courier))
        return events

    # -- aging -------------------------------------------------------------------------

    def _age_mail(self, world: World) -> None:
        for mail in _in_transit_mail(world):
            transit = mail.get_component(MailInTransitComponent)
            replace_component(mail, replace(transit, age_ticks=transit.age_ticks + 1))

    # -- per-courier action ------------------------------------------------------------

    def _act(self, world: World, epoch: int, courier: Entity) -> list[DomainEvent]:
        courier_room = room_of(world, courier.id)
        if courier_room is None:
            return []
        carried = self._carried_mail(world, courier)
        if carried:
            return self._advance(world, epoch, courier, courier_room, carried[0])
        return self._collect_or_seek(world, courier, courier_room)

    def _carried_mail(self, world: World, courier: Entity) -> list[Entity]:
        carried = [
            world.get_entity(item_id)
            for item_id in contents(courier)
            if world.has_entity(item_id)
            and world.get_entity(item_id).has_component(MailInTransitComponent)
        ]
        return sorted(carried, key=_id_key)

    # -- carrying and delivering -------------------------------------------------------

    def _advance(
        self, world: World, epoch: int, courier: Entity, courier_room: Entity, mail: Entity
    ) -> list[DomainEvent]:
        transit = self._sync_room(mail, courier_room)
        if should_return(world, transit, courier_room.id):
            transit = begin_return(mail, transit)

        target_raw = transit.origin_room_id if transit.returning else transit.destination_room_id
        target_id = parse_entity_id(target_raw)
        if target_id is not None and courier_room.id == target_id:
            return self._deliver(world, epoch, courier_room, mail, transit)

        hop = next_hop(world, courier_room.id, target_id) if target_id is not None else None
        if hop is None:
            # Nowhere left to route it (even the sender's room is unreachable/gone): drop it here.
            return self._deliver(world, epoch, courier_room, mail, transit)

        move_entity(world, courier.id, hop, mode=ContainmentMode.ROOM_CONTENT)
        self._sync_carried(world, courier, hop)
        return []

    def _deliver(
        self,
        world: World,
        epoch: int,
        room: Entity,
        mail: Entity,
        transit: MailInTransitComponent,
    ) -> list[DomainEvent]:
        box = mailbox_in_room(world, room)
        if box is not None:
            move_entity(world, mail.id, box.id, mode=ContainmentMode.CONTAINER)
        else:
            move_entity(world, mail.id, room.id, mode=ContainmentMode.ROOM_CONTENT)
        mail.remove_component(MailInTransitComponent)

        if transit.returning:
            return self._complete_return(world, epoch, room, mail, transit)
        return self._complete_delivery(world, epoch, room, mail, transit)

    def _complete_delivery(
        self,
        world: World,
        epoch: int,
        room: Entity,
        mail: Entity,
        transit: MailInTransitComponent,
    ) -> list[DomainEvent]:
        is_care = (
            mail.has_component(ParcelComponent) and mail.get_component(ParcelComponent).care_package
        )
        if is_care:
            apply_care_package_delivery(world, transit.sender_id, transit.addressee_id)
        kind = "care package" if is_care else "letter"
        self._notify(
            world,
            epoch,
            transit.addressee_id,
            f"A {kind} has arrived for you in the {room.get_component(IdentityComponent).name}."
            if room.has_component(IdentityComponent)
            else f"A {kind} has arrived for you.",
        )
        return [
            MailDeliveredEvent(
                **event_base(
                    epoch,
                    default_visibility=EventVisibility.DIRECTED,
                    room_id=str(room.id),
                    target_ids=(str(mail.id), transit.addressee_id),
                    mail_id=str(mail.id),
                    addressee_id=transit.addressee_id,
                    room_id_delivered=str(room.id),
                    is_care_package=is_care,
                )
            )
        ]

    def _complete_return(
        self,
        world: World,
        epoch: int,
        room: Entity,
        mail: Entity,
        transit: MailInTransitComponent,
    ) -> list[DomainEvent]:
        # Re-address the bounced mail to its sender so they can ``check-mail`` and get it back.
        if mail.has_component(LetterComponent):
            letter = mail.get_component(LetterComponent)
            replace_component(mail, replace(letter, addressee_id=transit.sender_id))
        self._notify(
            world,
            epoch,
            transit.sender_id,
            "Your mail could not be delivered and has been returned to you.",
        )
        return [
            MailReturnedEvent(
                **event_base(
                    epoch,
                    default_visibility=EventVisibility.DIRECTED,
                    room_id=str(room.id),
                    target_ids=(str(mail.id), transit.sender_id),
                    mail_id=str(mail.id),
                    sender_id=transit.sender_id,
                    room_id_returned=str(room.id),
                )
            )
        ]

    # -- collecting and roaming --------------------------------------------------------

    def _collect_or_seek(
        self, world: World, courier: Entity, courier_room: Entity
    ) -> list[DomainEvent]:
        waiting = self._waiting_mail(world)
        here = [mail for mail, room in waiting if room.id == courier_room.id]
        if here:
            move_entity(world, here[0].id, courier.id, mode=ContainmentMode.INVENTORY)
            self._sync_room(here[0], courier_room)
            return []

        target_rooms = {room.id for _mail, room in waiting}
        hop = next_hop_to_any(world, courier_room.id, target_rooms)
        if hop is None:
            hop = self._toward_home(world, courier, courier_room)
        if hop is not None:
            move_entity(world, courier.id, hop, mode=ContainmentMode.ROOM_CONTENT)
        return []

    def _waiting_mail(self, world: World) -> list[tuple[Entity, Entity]]:
        """In-transit mail resting in a mailbox (not yet on a courier), with its room."""
        waiting: list[tuple[Entity, Entity]] = []
        for mail in _in_transit_mail(world):
            container_id = container_of(mail)
            if container_id is None or not world.has_entity(container_id):
                continue
            container = world.get_entity(container_id)
            if not container.has_component(MailboxComponent):
                continue
            room = room_of(world, mail.id)
            if room is not None:
                waiting.append((mail, room))
        return waiting

    def _toward_home(self, world: World, courier: Entity, courier_room: Entity):
        home_raw = courier.get_component(CourierComponent).home_room_id
        home_id = parse_entity_id(home_raw) if home_raw else None
        if home_id is None or home_id == courier_room.id or not world.has_entity(home_id):
            return None
        return next_hop(world, courier_room.id, home_id)

    # -- helpers -----------------------------------------------------------------------

    def _sync_room(self, mail: Entity, room: Entity) -> MailInTransitComponent:
        transit = mail.get_component(MailInTransitComponent)
        if transit.current_room_id != str(room.id):
            transit = replace(transit, current_room_id=str(room.id))
            replace_component(mail, transit)
        return transit

    def _sync_carried(self, world: World, courier: Entity, room_id) -> None:
        for mail in self._carried_mail(world, courier):
            transit = mail.get_component(MailInTransitComponent)
            if transit.current_room_id != str(room_id):
                replace_component(mail, replace(transit, current_room_id=str(room_id)))

    def _notify(self, world: World, epoch: int, character_id: str, text: str) -> None:
        parsed = parse_entity_id(character_id)
        if parsed is None or not world.has_entity(parsed):
            return
        character = world.get_entity(parsed)
        for _edge, controller_id in sorted(
            character.get_relationships(ControlledBy), key=lambda pair: _key_of(pair[1])
        ):
            if not world.has_entity(controller_id):
                continue
            spawn_entity(
                world,
                [
                    IdentityComponent(name="mail notice", kind="mail_notice", tags=("postsim",)),
                    ControllerOutboxMessageComponent(
                        controller_id=str(controller_id),
                        text=text,
                        created_at_epoch=epoch,
                    ),
                ],
            )


def _key_of(entity_id) -> tuple[str, int]:
    return (entity_id.prefab, entity_id.sequence)


__all__ = ["PostConsequence"]
