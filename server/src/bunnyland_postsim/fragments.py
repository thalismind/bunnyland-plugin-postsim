"""Prompt fragments: surface waiting mail to whoever is standing in the room.

A single ``(world, character) -> list[str]`` provider feeds both the LLM actor context and the
human character-chat prompt. It looks into any mailbox in the character's room and reports:

- that there is mail in the box at all ("There is mail in the mailbox here."), and
- that a specific delivered letter/parcel is addressed to *this* character ("A letter for you
  has arrived in the mailbox here.").

Lines are collected, de-duplicated, and returned sorted so the output is deterministic.
"""

from __future__ import annotations

from relics import Entity, World

from .bulletins import boards_in_room, latest_edition, notices_on_board
from .components import LetterComponent, MailInTransitComponent, ParcelComponent
from .gazette_components import BulletinNoticeComponent, GossipSheetComponent
from .mailboxes import mail_in_mailbox, mailboxes_in_room
from .spatial import room_of

#: How many gossip-sheet headlines / board notices a fragment surfaces, so the prompt stays lean.
_FRAGMENT_LIMIT = 3


def postsim_fragments(world: World, character: Entity) -> list[str]:
    if character is None:
        return []
    room = room_of(world, character.id)
    if room is None:
        return []
    character_id = str(character.id)
    lines: list[str] = []
    for mailbox in mailboxes_in_room(world, room):
        mail = mail_in_mailbox(world, mailbox)
        delivered = [item for item in mail if not item.has_component(MailInTransitComponent)]
        if delivered:
            lines.append("There is mail in the mailbox here.")
        for item in delivered:
            if item.get_component(LetterComponent).addressee_id != character_id:
                continue
            noun = "parcel" if item.has_component(ParcelComponent) else "letter"
            lines.append(f"A {noun} for you has arrived in the mailbox here.")
    return sorted(dict.fromkeys(lines))


def bulletin_fragments(world: World, character: Entity) -> list[str]:
    """Surface the latest gossip-sheet headlines and board notices where a character stands.

    Only fires when a bulletin board shares the character's room. Lines are capped, de-duplicated,
    and returned sorted so the prompt is concise and deterministic.
    """
    if character is None:
        return []
    room = room_of(world, character.id)
    if room is None:
        return []
    boards = boards_in_room(world, room)
    if not boards:
        return []
    lines: list[str] = []
    edition = latest_edition(world)
    if edition is not None:
        sheet = edition.get_component(GossipSheetComponent)
        for headline in sheet.headlines[:_FRAGMENT_LIMIT]:
            lines.append(f"Gossip sheet #{sheet.edition}: {headline}")
    for board in boards:
        for notice in notices_on_board(world, board)[:_FRAGMENT_LIMIT]:
            text = notice.get_component(BulletinNoticeComponent).text
            lines.append(f"A notice on the board here reads: {text}")
    return sorted(dict.fromkeys(lines))


__all__ = ["bulletin_fragments", "postsim_fragments"]
