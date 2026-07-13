"""Mailboxes: a per-room drop box, plus the ``check-mail`` verb to collect delivered mail.

A :class:`~bunnyland_postsim.components.MailboxComponent` marks a container resting in a room.
Posted mail waits in a mailbox until a courier collects it, and delivered mail waits in the
addressee's mailbox until they ``check-mail``.

Helpers here answer the questions the verbs, fragments, and courier consequence all share:
which mailbox is in a room, and what mail is sitting in it. ``check-mail`` moves *delivered*
mail (mail no longer carrying a :class:`MailInTransitComponent`) addressed to the caller into
their inventory. Validation order follows the project convention: invalid id -> missing
entity -> not in a room -> no mailbox -> nothing to collect.
"""

from __future__ import annotations

from bunnyland.core import ContainmentMode, Contains, contents
from bunnyland.core.actions import ActionArgument, ActionDefinition, ActionEffort, effort_cost
from bunnyland.core.commands import Lane, SubmittedCommand
from bunnyland.core.events import EventVisibility
from bunnyland.core.handlers import (
    HandlerContext,
    HandlerResult,
    planned,
    rejected,
    require_character,
    require_entity,
)
from bunnyland.core.mutations import AddEdge, MutationPlan, RemoveEdge
from relics import Entity, World

from .components import LetterComponent, MailboxComponent, MailInTransitComponent
from .events import MailCheckedEvent
from .spatial import room_of


def mailboxes_in_room(world: World, room: Entity) -> list[Entity]:
    """Return the mailbox entities resting in ``room``, sorted by id for determinism."""
    found = [
        world.get_entity(item_id)
        for item_id in contents(room)
        if world.has_entity(item_id) and world.get_entity(item_id).has_component(MailboxComponent)
    ]
    return sorted(found, key=lambda entity: (entity.id.prefab, entity.id.sequence))


def mailbox_in_room(world: World, room: Entity) -> Entity | None:
    """Return the first mailbox in ``room`` (lowest id), or ``None`` if there is none."""
    boxes = mailboxes_in_room(world, room)
    return boxes[0] if boxes else None


def mail_in_mailbox(world: World, mailbox: Entity) -> list[Entity]:
    """Return the mail (letter) items resting in ``mailbox``, sorted by id."""
    found = [
        world.get_entity(item_id)
        for item_id in contents(mailbox)
        if world.has_entity(item_id) and world.get_entity(item_id).has_component(LetterComponent)
    ]
    return sorted(found, key=lambda entity: (entity.id.prefab, entity.id.sequence))


def delivered_mail_for(world: World, mailbox: Entity, addressee_id: str) -> list[Entity]:
    """Delivered mail in ``mailbox`` addressed to ``addressee_id`` (still-in-transit excluded)."""
    return [
        mail
        for mail in mail_in_mailbox(world, mailbox)
        if not mail.has_component(MailInTransitComponent)
        and mail.get_component(LetterComponent).addressee_id == addressee_id
    ]


class CheckMailHandler:
    """Collect delivered mail addressed to you from a mailbox in your room."""

    command_type = "check-mail"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        character_id, character, rejection = require_character(ctx, command.character_id)
        if rejection is not None:
            return rejection
        room = room_of(ctx.world, character_id)
        if room is None:
            return rejected("you are not in a room")

        raw_mailbox = command.payload.get("mailbox_id")
        if raw_mailbox is not None:
            mailbox_id, mailbox, rejection = require_entity(
                ctx,
                raw_mailbox,
                invalid_reason="invalid mailbox id",
                missing_reason="mailbox does not exist",
            )
            if rejection is not None:
                return rejection
            if not mailbox.has_component(MailboxComponent):
                return rejected("that is not a mailbox")
            box_room = room_of(ctx.world, mailbox_id)
            if box_room is None or box_room.id != room.id:
                return rejected("that mailbox is not here")
        else:
            mailbox = mailbox_in_room(ctx.world, room)
            if mailbox is None:
                return rejected("there is no mailbox here")

        collected = delivered_mail_for(ctx.world, mailbox, str(character_id))
        if not collected:
            return rejected("there is no mail for you here")
        operations = []
        for mail in collected:
            operations.extend(
                (
                    RemoveEdge(mailbox.id, mail.id, Contains),
                    AddEdge(character_id, mail.id, Contains(mode=ContainmentMode.INVENTORY)),
                )
            )
        return planned(
            MutationPlan(tuple(operations)),
            MailCheckedEvent(
                **ctx.event_base(
                    visibility=EventVisibility.PRIVATE,
                    actor_id=str(character_id),
                    room_id=str(room.id),
                    target_ids=tuple(str(mail.id) for mail in collected),
                    mailbox_id=str(mailbox.id),
                    mail_ids=tuple(str(mail.id) for mail in collected),
                )
            ),
        )


CHECK_MAIL_DEF = ActionDefinition(
    command_type="check-mail",
    title="Check mail",
    description="Collect delivered mail addressed to you from a mailbox in your room.",
    lane=Lane.WORLD,
    cost=effort_cost(action=ActionEffort.ROUTINE),
    arguments={
        "mailbox_id": ActionArgument(
            title="Mailbox",
            description="The mailbox to check; omit to use the first mailbox in the room.",
            kind="entity",
        ),
    },
)

MAILBOX_ACTION_DEFINITIONS = (CHECK_MAIL_DEF,)
MAILBOX_ACTION_HANDLERS = (CheckMailHandler,)


__all__ = [
    "CHECK_MAIL_DEF",
    "MAILBOX_ACTION_DEFINITIONS",
    "MAILBOX_ACTION_HANDLERS",
    "CheckMailHandler",
    "delivered_mail_for",
    "mail_in_mailbox",
    "mailbox_in_room",
    "mailboxes_in_room",
]
