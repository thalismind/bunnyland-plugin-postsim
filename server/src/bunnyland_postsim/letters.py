"""Letters and parcels: the ``write-letter`` and ``send-parcel`` verbs.

``write-letter`` produces a :class:`LetterComponent` mail item in the writer's inventory,
addressed to another character. ``send-parcel`` posts a held letter into a mailbox in the
current room, beginning its journey toward the addressee's room; it may optionally *wrap* a
held item to send along (a parcel), and flag that parcel as a care package so its delivery
warms the recipient.

Posting is the moment a courier can pick the mail up: it attaches a
:class:`MailInTransitComponent` (routing + return-to-sender state) and moves the letter from
the sender's hands into the mailbox. Validation order follows the project convention:
invalid id -> missing entity -> not held / wrong kind -> addressing/room checks -> apply.
"""

from __future__ import annotations

from bunnyland.core import (
    ContainmentMode,
    Contains,
    HoldableComponent,
    IdentityComponent,
    PortableComponent,
    spawn_entity,
)
from bunnyland.core.actions import ActionArgument, ActionDefinition, ActionEffort, effort_cost
from bunnyland.core.commands import Lane, SubmittedCommand
from bunnyland.core.ecs import replace_component
from bunnyland.core.events import EventVisibility
from bunnyland.core.handlers import (
    HandlerContext,
    HandlerResult,
    ok,
    rejected,
    require_character,
    require_entity,
)

from .components import (
    DEFAULT_TTL_TICKS,
    LetterComponent,
    MailInTransitComponent,
    ParcelComponent,
)
from .events import LetterWrittenEvent, MailPostedEvent
from .mailboxes import mailbox_in_room
from .spatial import holder_of, move_entity, room_of


class WriteLetterHandler:
    """Write a letter addressed to another character; it appears in your inventory."""

    command_type = "write-letter"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        character_id, character, rejection = require_character(ctx, command.character_id)
        if rejection is not None:
            return rejection
        text = str(command.payload.get("text", "")).strip()
        if not text:
            return rejected("a letter needs some text")
        addressee_id, _addressee, rejection = require_entity(
            ctx,
            command.payload.get("addressee_id"),
            invalid_reason="invalid addressee id",
            missing_reason="addressee does not exist",
        )
        if rejection is not None:
            return rejection

        letter = spawn_entity(
            ctx.world,
            [
                IdentityComponent(name="letter", kind="mail", tags=("postsim",)),
                PortableComponent(),
                HoldableComponent(slot="hand"),
                LetterComponent(
                    text=text,
                    sender_id=str(character_id),
                    addressee_id=str(addressee_id),
                ),
            ],
        )
        character.add_relationship(Contains(mode=ContainmentMode.INVENTORY), letter.id)
        return ok(
            LetterWrittenEvent(
                **ctx.event_base(
                    visibility=EventVisibility.PRIVATE,
                    actor_id=str(character_id),
                    target_ids=(str(letter.id),),
                    mail_id=str(letter.id),
                    addressee_id=str(addressee_id),
                )
            )
        )


class SendParcelHandler:
    """Post a held letter into a mailbox, optionally wrapping a held gift to send along."""

    command_type = "send-parcel"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        character_id, _character, rejection = require_character(ctx, command.character_id)
        if rejection is not None:
            return rejection

        letter_id, letter, rejection = require_entity(
            ctx,
            command.payload.get("item_id"),
            invalid_reason="invalid item id",
            missing_reason="item does not exist",
        )
        if rejection is not None:
            return rejection
        holder = holder_of(ctx.world, letter_id)
        if holder is None or holder.id != character_id:
            return rejected("you are not holding that letter")
        if not letter.has_component(LetterComponent):
            return rejected("that is not a letter")

        letter_component = letter.get_component(LetterComponent)
        addressee_id, addressee, rejection = require_entity(
            ctx,
            letter_component.addressee_id,
            invalid_reason="the letter has no valid addressee",
            missing_reason="the addressee is nowhere to be found",
        )
        if rejection is not None:
            return rejection
        destination = room_of(ctx.world, addressee_id)
        if destination is None:
            return rejected("the addressee is nowhere to be found")

        origin = room_of(ctx.world, character_id)
        if origin is None:
            return rejected("you are not in a room")
        mailbox = mailbox_in_room(ctx.world, origin)
        if mailbox is None:
            return rejected("there is no mailbox here")

        gift, rejection = self._resolve_gift(ctx, character_id, command)
        if rejection is not None:
            return rejection

        care_package = bool(command.payload.get("care_package", False))
        is_parcel = gift is not None or care_package
        if is_parcel:
            replace_component(
                letter,
                ParcelComponent(
                    wrapped_item_id=str(gift.id) if gift is not None else "",
                    care_package=care_package,
                ),
            )
            if gift is not None:
                move_entity(ctx.world, gift.id, letter.id, mode=ContainmentMode.CONTAINER)

        replace_component(
            letter,
            MailInTransitComponent(
                sender_id=str(character_id),
                addressee_id=str(addressee_id),
                origin_room_id=str(origin.id),
                destination_room_id=str(destination.id),
                current_room_id=str(origin.id),
                posted_at_epoch=ctx.epoch,
                ttl_ticks=int(command.payload.get("ttl_ticks", DEFAULT_TTL_TICKS)),
            ),
        )
        move_entity(ctx.world, letter_id, mailbox.id, mode=ContainmentMode.CONTAINER)
        return ok(
            MailPostedEvent(
                **ctx.event_base(
                    visibility=EventVisibility.ROOM,
                    actor_id=str(character_id),
                    room_id=str(origin.id),
                    target_ids=(str(letter_id), str(mailbox.id)),
                    mail_id=str(letter_id),
                    mailbox_id=str(mailbox.id),
                    addressee_id=str(addressee_id),
                    is_parcel=is_parcel,
                    is_care_package=care_package,
                )
            )
        )

    def _resolve_gift(self, ctx: HandlerContext, character_id, command: SubmittedCommand):
        raw_gift = command.payload.get("gift_id")
        if raw_gift is None:
            return None, None
        gift_id, gift, rejection = require_entity(
            ctx,
            raw_gift,
            invalid_reason="invalid gift id",
            missing_reason="gift does not exist",
        )
        if rejection is not None:
            return None, rejection
        holder = holder_of(ctx.world, gift_id)
        if holder is None or holder.id != character_id:
            return None, rejected("you are not holding that gift")
        return gift, None


WRITE_LETTER_DEF = ActionDefinition(
    command_type="write-letter",
    title="Write letter",
    description="Write a letter addressed to another character.",
    lane=Lane.WORLD,
    cost=effort_cost(action=ActionEffort.ROUTINE),
    arguments={
        "text": ActionArgument(
            title="Text", description="What the letter says.", kind="string", required=True
        ),
        "addressee_id": ActionArgument(
            title="Addressee",
            description="The character the letter is for.",
            kind="entity",
            required=True,
        ),
    },
)

SEND_PARCEL_DEF = ActionDefinition(
    command_type="send-parcel",
    title="Send parcel",
    description="Post a held letter into a mailbox, optionally wrapping a gift to send along.",
    lane=Lane.WORLD,
    cost=effort_cost(action=ActionEffort.ROUTINE),
    arguments={
        "item_id": ActionArgument(
            title="Letter",
            description="The held letter to send.",
            kind="entity",
            required=True,
        ),
        "gift_id": ActionArgument(
            title="Gift",
            description="An optional held item to wrap and send along with the letter.",
            kind="entity",
        ),
        "care_package": ActionArgument(
            title="Care package",
            description="Mark the parcel a care package so its delivery warms the recipient.",
            kind="boolean",
        ),
    },
)

LETTER_ACTION_DEFINITIONS = (WRITE_LETTER_DEF, SEND_PARCEL_DEF)
LETTER_ACTION_HANDLERS = (WriteLetterHandler, SendParcelHandler)


__all__ = [
    "LETTER_ACTION_DEFINITIONS",
    "LETTER_ACTION_HANDLERS",
    "SEND_PARCEL_DEF",
    "WRITE_LETTER_DEF",
    "SendParcelHandler",
    "WriteLetterHandler",
]
