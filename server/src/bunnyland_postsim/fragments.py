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

from .components import LetterComponent, MailInTransitComponent, ParcelComponent
from .mailboxes import mail_in_mailbox, mailboxes_in_room
from .spatial import room_of


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


__all__ = ["postsim_fragments"]
