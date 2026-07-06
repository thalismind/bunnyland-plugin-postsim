"""Bulletin boards: read the gossip sheet and pin your own notices in a settlement.

A :class:`~bunnyland_postsim.gazette_components.BulletinBoardComponent` marks a public board
container standing in a room. Two verbs act on it:

- ``post-notice`` pins a character-written
  :class:`~bunnyland_postsim.gazette_components.BulletinNoticeComponent` to a board in their
  room, linked to its author by a :class:`~bunnyland_postsim.gazette_components.PostedBy` edge.
- ``read-board`` reads the board: the latest published gossip-sheet edition (world-wide news)
  plus the local notices pinned to *this* board.

The helpers answer the questions the verbs, fragments, and the press all share: which boards
are in a room, which notices sit on a board, and which gossip-sheet edition is the newest.
Validation follows the project convention: invalid id -> missing entity -> not in a room ->
wrong-kind / not-here -> apply.
"""

from __future__ import annotations

from bunnyland.core import ContainmentMode, Contains, IdentityComponent, contents, spawn_entity
from bunnyland.core.actions import ActionArgument, ActionDefinition
from bunnyland.core.commands import CommandCost, Lane, SubmittedCommand
from bunnyland.core.events import EventVisibility
from bunnyland.core.handlers import (
    HandlerContext,
    HandlerResult,
    ok,
    rejected,
    require_character,
    require_entity,
)
from relics import Entity, World

from .events import BoardReadEvent, NoticePostedEvent
from .gazette_components import (
    BulletinBoardComponent,
    BulletinNoticeComponent,
    GossipSheetComponent,
    PostedBy,
)
from .spatial import room_of


def _id_key(entity: Entity) -> tuple[str, int]:
    return (entity.id.prefab, entity.id.sequence)


def boards_in_room(world: World, room: Entity) -> list[Entity]:
    """Return the bulletin-board entities resting in ``room``, sorted by id for determinism."""
    found = [
        world.get_entity(item_id)
        for item_id in contents(room)
        if world.has_entity(item_id)
        and world.get_entity(item_id).has_component(BulletinBoardComponent)
    ]
    return sorted(found, key=_id_key)


def board_in_room(world: World, room: Entity) -> Entity | None:
    """Return the first bulletin board in ``room`` (lowest id), or ``None``."""
    boards = boards_in_room(world, room)
    return boards[0] if boards else None


def notices_on_board(world: World, board: Entity) -> list[Entity]:
    """Return the notices pinned to ``board``, oldest first (by post epoch, then id)."""
    found = [
        world.get_entity(item_id)
        for item_id in contents(board)
        if world.has_entity(item_id)
        and world.get_entity(item_id).has_component(BulletinNoticeComponent)
    ]
    return sorted(
        found,
        key=lambda entity: (
            entity.get_component(BulletinNoticeComponent).posted_at_epoch,
            entity.id.prefab,
            entity.id.sequence,
        ),
    )


def latest_edition(world: World) -> Entity | None:
    """Return the newest published gossip-sheet edition entity, or ``None`` if none exists."""
    editions = list(world.query().with_all([GossipSheetComponent]).execute_entities())
    if not editions:
        return None
    return max(
        editions,
        key=lambda entity: (
            entity.get_component(GossipSheetComponent).edition,
            entity.get_component(GossipSheetComponent).published_at_epoch,
            entity.id.prefab,
            entity.id.sequence,
        ),
    )


def _resolve_board(
    ctx: HandlerContext, command: SubmittedCommand, room: Entity
) -> tuple[Entity | None, HandlerResult | None]:
    raw_board = command.payload.get("board_id")
    if raw_board is not None:
        board_id, board, rejection = require_entity(
            ctx,
            raw_board,
            invalid_reason="invalid board id",
            missing_reason="board does not exist",
        )
        if rejection is not None:
            return None, rejection
        if not board.has_component(BulletinBoardComponent):
            return None, rejected("that is not a bulletin board")
        board_room = room_of(ctx.world, board_id)
        if board_room is None or board_room.id != room.id:
            return None, rejected("that bulletin board is not here")
        return board, None
    board = board_in_room(ctx.world, room)
    if board is None:
        return None, rejected("there is no bulletin board here")
    return board, None


class PostNoticeHandler:
    """Pin a written notice to a bulletin board in your room."""

    command_type = "post-notice"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        character_id, _character, rejection = require_character(ctx, command.character_id)
        if rejection is not None:
            return rejection
        text = str(command.payload.get("text", "")).strip()
        if not text:
            return rejected("a notice needs some text")
        room = room_of(ctx.world, character_id)
        if room is None:
            return rejected("you are not in a room")
        board, rejection = _resolve_board(ctx, command, room)
        if rejection is not None:
            return rejection

        notice = spawn_entity(
            ctx.world,
            [
                IdentityComponent(name="notice", kind="notice", tags=("postsim",)),
                BulletinNoticeComponent(
                    text=text,
                    author_id=str(character_id),
                    posted_at_epoch=ctx.epoch,
                ),
            ],
        )
        board.add_relationship(Contains(mode=ContainmentMode.CONTAINER), notice.id)
        notice.add_relationship(PostedBy(), character_id)
        return ok(
            NoticePostedEvent(
                **ctx.event_base(
                    visibility=EventVisibility.ROOM,
                    actor_id=str(character_id),
                    room_id=str(room.id),
                    target_ids=(str(notice.id), str(board.id)),
                    notice_id=str(notice.id),
                    board_id=str(board.id),
                    author_id=str(character_id),
                )
            )
        )


class ReadBoardHandler:
    """Read a bulletin board: the latest gossip sheet plus the notices pinned here."""

    command_type = "read-board"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        character_id, _character, rejection = require_character(ctx, command.character_id)
        if rejection is not None:
            return rejection
        room = room_of(ctx.world, character_id)
        if room is None:
            return rejected("you are not in a room")
        board, rejection = _resolve_board(ctx, command, room)
        if rejection is not None:
            return rejection

        edition = latest_edition(ctx.world)
        notices = notices_on_board(ctx.world, board)
        if edition is None and not notices:
            return rejected("there is nothing posted on the board here")
        edition_number = (
            edition.get_component(GossipSheetComponent).edition if edition is not None else 0
        )
        return ok(
            BoardReadEvent(
                **ctx.event_base(
                    visibility=EventVisibility.PRIVATE,
                    actor_id=str(character_id),
                    room_id=str(room.id),
                    target_ids=(str(board.id),),
                    board_id=str(board.id),
                    edition=edition_number,
                    notice_count=len(notices),
                )
            )
        )


POST_NOTICE_DEF = ActionDefinition(
    command_type="post-notice",
    title="Post notice",
    description="Pin a written notice to a bulletin board in your room.",
    lane=Lane.WORLD,
    cost=CommandCost(action=1),
    arguments={
        "text": ActionArgument(
            title="Text", description="What the notice says.", kind="string", required=True
        ),
        "board_id": ActionArgument(
            title="Board",
            description="The board to pin to; omit to use the first board in the room.",
            kind="entity",
        ),
    },
)

READ_BOARD_DEF = ActionDefinition(
    command_type="read-board",
    title="Read board",
    description="Read the latest gossip sheet and the notices on a bulletin board.",
    lane=Lane.FOCUS,
    cost=CommandCost(focus=1),
    arguments={
        "board_id": ActionArgument(
            title="Board",
            description="The board to read; omit to use the first board in the room.",
            kind="entity",
        ),
    },
)

BULLETIN_ACTION_DEFINITIONS = (POST_NOTICE_DEF, READ_BOARD_DEF)
BULLETIN_ACTION_HANDLERS = (PostNoticeHandler, ReadBoardHandler)


__all__ = [
    "BULLETIN_ACTION_DEFINITIONS",
    "BULLETIN_ACTION_HANDLERS",
    "POST_NOTICE_DEF",
    "READ_BOARD_DEF",
    "PostNoticeHandler",
    "ReadBoardHandler",
    "board_in_room",
    "boards_in_room",
    "latest_edition",
    "notices_on_board",
]
