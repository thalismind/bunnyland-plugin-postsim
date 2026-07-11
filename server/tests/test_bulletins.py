"""Behaviour tests for v2 bulletin boards: post-notice / read-board verbs and board helpers."""

from __future__ import annotations

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    IdentityComponent,
    RoomComponent,
    WorldActor,
    spawn_entity,
)
from bunnyland.core.commands import CommandCost, Lane, build_submitted_command
from bunnyland.core.handlers import HandlerContext

from bunnyland_postsim.bulletins import (
    PostNoticeHandler,
    ReadBoardHandler,
    board_in_room,
    boards_in_room,
    latest_edition,
    notices_on_board,
)
from bunnyland_postsim.gazette_components import (
    BulletinNoticeComponent,
    GossipSheetComponent,
    PostedBy,
)
from bunnyland_postsim.prefabs import spawn_bulletin_board

# --------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------


def _room(world, title="Town Square"):
    return spawn_entity(world, [RoomComponent(title=title)])


def _character(world, room, name="Vin"):
    character = spawn_entity(
        world, [IdentityComponent(name=name, kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), character.id)
    return character


def _cmd(character_id, command_type, payload):
    return build_submitted_command(
        character_id=str(character_id),
        controller_id="ctrl",
        controller_generation=0,
        command_type=command_type,
        cost=CommandCost(action=1),
        lane=Lane.WORLD,
        payload=payload,
    )


def _ctx(actor, epoch=0):
    return HandlerContext(world=actor.world, epoch=epoch)


def _scenario():
    actor = WorldActor()
    room = _room(actor.world)
    character = _character(actor.world, room)
    board = spawn_bulletin_board(actor.world, room_id=room.id)
    return actor, room, character, board


def _edition(world, *, edition=1, headlines=("News!",), epoch=0):
    return spawn_entity(
        world,
        [
            IdentityComponent(name=f"gossip sheet #{edition}", kind="gossip-sheet"),
            GossipSheetComponent(edition=edition, headlines=headlines, published_at_epoch=epoch),
        ],
    )


# --------------------------------------------------------------------------------------
# helpers: boards / notices / editions
# --------------------------------------------------------------------------------------


def test_board_lookup_helpers():
    actor, room, _character, board = _scenario()
    assert [b.id for b in boards_in_room(actor.world, room)] == [board.id]
    assert board_in_room(actor.world, room).id == board.id


def test_board_in_empty_room_is_none():
    actor = WorldActor()
    room = _room(actor.world)
    assert board_in_room(actor.world, room) is None
    assert boards_in_room(actor.world, room) == []


def test_latest_edition_picks_highest_edition():
    actor = WorldActor()
    _edition(actor.world, edition=1)
    newest = _edition(actor.world, edition=3)
    _edition(actor.world, edition=2)
    assert latest_edition(actor.world).id == newest.id


def test_latest_edition_none_when_unpublished():
    actor = WorldActor()
    assert latest_edition(actor.world) is None


# --------------------------------------------------------------------------------------
# post-notice
# --------------------------------------------------------------------------------------


def test_post_notice_pins_and_links_author():
    actor, _room, character, board = _scenario()
    result = PostNoticeHandler().execute(
        _ctx(actor), _cmd(character.id, "post-notice", {"text": "Lost cat, reward!"})
    )
    assert result.ok
    notices = notices_on_board(actor.world, board)
    assert len(notices) == 1
    notice = notices[0]
    assert notice.get_component(BulletinNoticeComponent).text == "Lost cat, reward!"
    assert notice.get_component(BulletinNoticeComponent).author_id == str(character.id)
    authors = [target for _edge, target in notice.get_relationships(PostedBy)]
    assert authors == [character.id]


def test_post_notice_explicit_board_id():
    actor, _room, character, board = _scenario()
    result = PostNoticeHandler().execute(
        _ctx(actor),
        _cmd(character.id, "post-notice", {"text": "Meeting tonight", "board_id": str(board.id)}),
    )
    assert result.ok
    assert len(notices_on_board(actor.world, board)) == 1


def test_post_notice_requires_text():
    actor, _room, character, _board = _scenario()
    result = PostNoticeHandler().execute(
        _ctx(actor), _cmd(character.id, "post-notice", {"text": "   "})
    )
    assert not result.ok
    assert result.reason == "a notice needs some text"


def test_post_notice_requires_room():
    actor = WorldActor()
    # A character with no room around it.
    character = spawn_entity(
        actor.world, [IdentityComponent(name="Drifter", kind="character"), CharacterComponent()]
    )
    result = PostNoticeHandler().execute(
        _ctx(actor), _cmd(character.id, "post-notice", {"text": "hello"})
    )
    assert not result.ok
    assert result.reason == "you are not in a room"


def test_post_notice_requires_a_board():
    actor = WorldActor()
    room = _room(actor.world)
    character = _character(actor.world, room)
    result = PostNoticeHandler().execute(
        _ctx(actor), _cmd(character.id, "post-notice", {"text": "hello"})
    )
    assert not result.ok
    assert result.reason == "there is no bulletin board here"


def test_post_notice_invalid_board_id():
    actor, _room, character, _board = _scenario()
    result = PostNoticeHandler().execute(
        _ctx(actor),
        _cmd(character.id, "post-notice", {"text": "hi", "board_id": "not-an-id"}),
    )
    assert not result.ok
    assert result.reason == "invalid board id"


def test_post_notice_wrong_kind_board():
    actor, room, character, _board = _scenario()
    rock = spawn_entity(actor.world, [IdentityComponent(name="rock", kind="item")])
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), rock.id)
    result = PostNoticeHandler().execute(
        _ctx(actor),
        _cmd(character.id, "post-notice", {"text": "hi", "board_id": str(rock.id)}),
    )
    assert not result.ok
    assert result.reason == "that is not a bulletin board"


def test_post_notice_board_in_another_room():
    actor, room, character, _board = _scenario()
    elsewhere = _room(actor.world, "Far Field")
    far_board = spawn_bulletin_board(actor.world, room_id=elsewhere.id)
    result = PostNoticeHandler().execute(
        _ctx(actor),
        _cmd(character.id, "post-notice", {"text": "hi", "board_id": str(far_board.id)}),
    )
    assert not result.ok
    assert result.reason == "that bulletin board is not here"


def test_post_notice_missing_character():
    actor, _room, _character, _board = _scenario()
    result = PostNoticeHandler().execute(
        _ctx(actor), _cmd("bogus-9", "post-notice", {"text": "hi"})
    )
    assert not result.ok


# --------------------------------------------------------------------------------------
# read-board
# --------------------------------------------------------------------------------------


def test_read_board_reports_edition_and_notice_count():
    actor, _room, character, board = _scenario()
    _edition(actor.world, edition=4, headlines=("Big news!",))
    # Pin one notice first.
    PostNoticeHandler().execute(
        _ctx(actor), _cmd(character.id, "post-notice", {"text": "For sale"})
    )
    result = ReadBoardHandler().execute(_ctx(actor), _cmd(character.id, "read-board", {}))
    assert result.ok
    event = result.events[0]
    assert event.board_id == str(board.id)
    assert event.edition == 4
    assert event.notice_count == 1


def test_read_board_with_only_notices_and_no_edition():
    actor, _room, character, _board = _scenario()
    PostNoticeHandler().execute(_ctx(actor), _cmd(character.id, "post-notice", {"text": "notice"}))
    result = ReadBoardHandler().execute(_ctx(actor), _cmd(character.id, "read-board", {}))
    assert result.ok
    assert result.events[0].edition == 0
    assert result.events[0].notice_count == 1


def test_read_empty_board_is_rejected():
    actor, _room, character, _board = _scenario()
    result = ReadBoardHandler().execute(_ctx(actor), _cmd(character.id, "read-board", {}))
    assert not result.ok
    assert result.reason == "there is nothing posted on the board here"


def test_read_board_requires_room():
    actor = WorldActor()
    character = spawn_entity(
        actor.world, [IdentityComponent(name="Drifter", kind="character"), CharacterComponent()]
    )
    result = ReadBoardHandler().execute(_ctx(actor), _cmd(character.id, "read-board", {}))
    assert not result.ok
    assert result.reason == "you are not in a room"


def test_read_board_requires_a_board():
    actor = WorldActor()
    room = _room(actor.world)
    character = _character(actor.world, room)
    result = ReadBoardHandler().execute(_ctx(actor), _cmd(character.id, "read-board", {}))
    assert not result.ok
    assert result.reason == "there is no bulletin board here"


def test_read_board_invalid_board_id():
    actor, _room, character, _board = _scenario()
    result = ReadBoardHandler().execute(
        _ctx(actor), _cmd(character.id, "read-board", {"board_id": "999"})
    )
    assert not result.ok
    assert result.reason == "invalid board id"


def test_read_board_missing_board_entity():
    actor, _room, character, _board = _scenario()
    # A well-formed id whose entity has been removed resolves to the missing-entity path.
    ghost = spawn_entity(actor.world, [IdentityComponent(name="gone", kind="item")])
    ghost_id = str(ghost.id)
    actor.world.remove(ghost.id)
    result = ReadBoardHandler().execute(
        _ctx(actor), _cmd(character.id, "read-board", {"board_id": ghost_id})
    )
    assert not result.ok
    assert result.reason == "board does not exist"


def test_notices_sorted_by_post_epoch():
    actor, _room, character, board = _scenario()
    PostNoticeHandler().execute(
        _ctx(actor, epoch=5), _cmd(character.id, "post-notice", {"text": "later"})
    )
    PostNoticeHandler().execute(
        _ctx(actor, epoch=1), _cmd(character.id, "post-notice", {"text": "earlier"})
    )
    texts = [
        entity.get_component(BulletinNoticeComponent).text
        for entity in notices_on_board(actor.world, board)
    ]
    assert texts == ["earlier", "later"]
